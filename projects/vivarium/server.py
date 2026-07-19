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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aliveness import evaluate
from config import VivariumConfig, load_config
from engine import Engine

_HERE = Path(__file__).resolve().parent
_VIEWER = _HERE / "viewer.html"
_CONFIG = _HERE / "configs" / "vivarium.yaml"


class Sim:
    """Steps an Engine in a background thread; publishes the latest snapshot."""

    def __init__(self, cfg: VivariumConfig, seed: int, hz: float) -> None:
        self.cfg = cfg
        self.seed = seed
        self.hz = hz
        self.lock = threading.Lock()
        self.engine = Engine(cfg, seed)
        self.paused = False
        self._stop = False
        self._alive = 0.0
        self._snap = self._build_snapshot()
        threading.Thread(target=self._run, daemon=True).start()

    def _build_snapshot(self) -> dict:
        snap = self.engine.snapshot()
        snap["aliveness"] = self._alive
        snap["pos_bound"] = self.cfg.pos_bound
        return snap

    def _run(self) -> None:
        dt = 1.0 / self.hz
        while not self._stop:
            if not self.paused:
                with self.lock:
                    self.engine.step()
                    t = self.engine.t
                    snap = self._build_snapshot()
                self._snap = snap
                if t % 60 == 0:  # aliveness is expensive (forks + rolls) — sample periodically
                    with self.lock:
                        self._alive = round(float(evaluate(self.engine, 40)["aliveness"]), 3)
            time.sleep(dt)

    def state(self) -> dict:
        return self._snap

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def restart(self, seed: int | None = None) -> None:
        with self.lock:
            self.seed = self.seed + 1 if seed is None else seed
            self.engine = Engine(self.cfg, self.seed)
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
        if self.path in ("/", "/index.html"):
            self._send(200, _VIEWER.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/state":
            self._send(200, json.dumps(self.server.sim.state()).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        sim = self.server.sim
        if self.path == "/pause":
            sim.set_paused(True)
        elif self.path == "/resume":
            sim.set_paused(False)
        elif self.path == "/restart":
            sim.restart()
        else:
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, b"{}", "application/json")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="vivarium live viewer")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8788)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--hz", type=float, default=30.0)
    p.add_argument("--config", default=str(_CONFIG))
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    seed = cfg.seed if args.seed is None else args.seed
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.sim = Sim(cfg, seed, args.hz)
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
