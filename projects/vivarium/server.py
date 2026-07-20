"""Live viewer server for the dock-and-morph dish (read-only, watchable).

Runs an Engine in a background thread and serves snapshots; the browser polls and
draws the morphing blobs. Zero external deps (stdlib http.server).

    bazel run //projects/vivarium:serve -- --port 8788
    tailscale serve --bg 8788          # expose on your tailnet

Routes:
    GET  /         → viewer.html
    GET  /state    → JSON snapshot (positions + grounded contours + edges + aliveness)
    POST /pause /resume /restart
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

from aliveness import score
from config import VivariumConfig, load_config
from engine import Engine

_HERE = Path(__file__).resolve().parent
_VIEWER = _HERE / "viewer.html"
_CONFIG = _HERE / "configs" / "vivarium.yaml"


class Sim:
    """Steps an engine in a background thread; publishes the latest snapshot."""

    def __init__(self, cfg: VivariumConfig, seed: int, hz: float, make_engine=None,
                 knob_names=("noise", "spin", "nonrecip", "scale", "rd")) -> None:
        self.cfg = cfg
        self.seed = seed
        self.hz = hz
        self._make = make_engine or (lambda s: Engine(cfg, s))
        self.knob_names = knob_names
        self.lock = threading.Lock()
        self.engine = self._make(seed)
        self.paused = False
        self._stop = False
        self._alive = 0.0
        self._buf: deque = deque(maxlen=40)  # rolling positions for cheap aliveness (no fork)
        self._snap = self._build_snapshot()
        threading.Thread(target=self._run, daemon=True).start()

    def _build_snapshot(self) -> dict:
        snap = self.engine.snapshot()
        snap["aliveness"] = self._alive
        snap["pos_bound"] = self.cfg.pos_bound
        snap["knobs"] = {k: float(getattr(self.engine, k)) for k in self.knob_names
                         if hasattr(self.engine, k)}
        return snap

    def set_knobs(self, updates: dict) -> None:
        with self.lock:
            for k in self.knob_names:
                if k in updates and hasattr(self.engine, k):
                    try:
                        setattr(self.engine, k, max(0.0, float(updates[k])))
                    except (TypeError, ValueError):
                        pass

    def _run(self) -> None:
        dt = 1.0 / self.hz
        n = 0
        while not self._stop:
            if not self.paused:
                with self.lock:
                    self.engine.step()
                    self._buf.append(self.engine.X[:, :2].copy())  # positions only (cheap)
                    snap = self._build_snapshot()
                self._snap = snap
                n += 1
                # cheap aliveness on the rolling window — NO fork, NO extra stepping (fixes lag).
                if n % 20 == 0 and len(self._buf) >= 10:
                    states = np.stack(self._buf)
                    self._alive = round(float(score(states, self.cfg)["aliveness"]), 3)
            time.sleep(dt)

    def state(self) -> dict:
        return self._snap

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def restart(self, seed: int | None = None) -> None:
        with self.lock:
            self.seed = self.seed + 1 if seed is None else seed
            self.engine = self._make(self.seed)
            self._alive = 0.0
            self._snap = self._build_snapshot()


class Handler(BaseHTTPRequestHandler):
    sim: Sim  # set on the server

    def log_message(self, *a) -> None:  # silence
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        # suffix-match so we work whether mounted at / or under a path prefix (e.g. /vivarium/).
        if self.path.endswith("/state"):
            self._send(200, json.dumps(self.server.sim.state()).encode(), "application/json")
        else:
            self._send(200, _VIEWER.read_bytes(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        sim = self.server.sim
        path = self.path.split("?", 1)[0]
        if path.endswith("/pause"):
            sim.set_paused(True)
        elif path.endswith("/resume"):
            sim.set_paused(False)
        elif path.endswith("/restart"):
            sim.restart()
        elif path.endswith("/set"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            sim.set_knobs({k: v[0] for k, v in q.items()})
        else:
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, b"{}", "application/json")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="vivarium live viewer")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8788)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--hz", type=float, default=18.0)
    p.add_argument("--config", default=str(_CONFIG))
    p.add_argument("--pure", action="store_true",
                   help="serve the PURE-TRANSFORMER engine (transformer moves + morphs everything)")
    p.add_argument("--pack", action="store_true",
                   help="serve the PACKING engine (boundaries + induced-fit, periodic domain)")
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    seed = cfg.seed if args.seed is None else args.seed
    make_engine = None
    knob_names = ("noise", "spin", "nonrecip", "scale", "rd")
    label = "force-based dock-and-morph"
    if args.pack:
        from pure import PureEngine  # noqa: F401  (keep import graph stable)

        from pack import PackEngine
        make_engine = lambda s: PackEngine(cfg, s)  # noqa: E731  (alive-packing defaults)
        knob_names = ("repel", "attract", "skew", "morph", "momentum")
        label = "PACKING (1/d² clash-repel + complementary-fit + induced morph, periodic)"
    elif args.pure:
        from dataclasses import replace

        from pure import PureEngine
        # the winning pure-transformer config: non-reciprocal attention + skew + free positions.
        cfg = replace(cfg, morph_spin=0.3, dist_lambda=0.5)
        # flat-pos: skew drives only the shape, so positions move by interaction (no global spin);
        # gentler scale for smoother, less-frantic motion.
        make_engine = lambda s: PureEngine(  # noqa: E731
            cfg, s, nonrecip=1.0, ln_pos=False, scale=0.3, spin_pos=False, rd=0.5)
        label = "PURE TRANSFORMER (non-reciprocal attention + reaction-diffusion, free positions)"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.sim = Sim(cfg, seed, args.hz, make_engine, knob_names)
    print(f"serving: {label}")
    print(
        f"vivarium viewer on http://{args.host}:{server.server_address[1]}\n"
        f"expose on your tailnet:  tailscale serve --bg {server.server_address[1]}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.sim._stop = True
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
