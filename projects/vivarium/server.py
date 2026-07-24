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
        self.stream_hz = min(30.0, hz)   # SSE push rate (≤ sim rate; no point pushing faster)
        self._make = make_engine or (lambda s: Engine(cfg, s))
        self.knob_names = knob_names
        # pseudo-knobs: name → (getter, setter). Unlike real knobs (a live setattr), these need a
        # restart (e.g. changing the water COUNT re-assigns species). Set after construction.
        self.pseudo: dict = {}
        self.autopause = 0        # if >0, auto-pause when engine.t reaches this step (resumable)
        self.lock = threading.Lock()
        self.engine = self._make(seed)
        self.paused = False
        self._stop = False
        self._alive = 0.0
        self._buf: deque = deque(maxlen=40)  # rolling positions for aliveness
        # Two dedicated threads keep the step loop hot: stepping is the ONLY thing on the critical
        # path. The (expensive) aliveness runs on its own clock, and the snapshot is built lazily
        # per poll — so neither ever hitches the frame cadence (fixes rendering lag).
        threading.Thread(target=self._run, daemon=True).start()
        threading.Thread(target=self._alive_loop, daemon=True).start()

    def set_knobs(self, updates: dict) -> None:
        with self.lock:
            for k in self.knob_names:
                if k in updates and hasattr(self.engine, k):
                    try:
                        setattr(self.engine, k, max(0.0, float(updates[k])))
                    except (TypeError, ValueError):
                        pass
        # pseudo-knobs are applied OUTSIDE the lock — their setter may call restart() (re-acquires it).
        for name, (_get, setr) in self.pseudo.items():
            if name in updates:
                try:
                    setr(float(updates[name]))
                except (TypeError, ValueError):
                    pass

    def _run(self) -> None:
        """The hot loop: step + buffer positions, nothing else. Paced to a steady cadence."""
        dt = 1.0 / self.hz
        while not self._stop:
            t0 = time.perf_counter()
            if not self.paused:
                with self.lock:
                    self.engine.step()
                    self._buf.append(self.engine.X[:, :2].copy())  # positions only (cheap)
                if self.autopause and self.engine.t >= self.autopause:
                    self.paused = True                            # auto-pause at the given step (resumable)
            # sleep the *remaining* time so the cadence is stable regardless of step cost
            time.sleep(max(0.0, dt - (time.perf_counter() - t0)))

    def _alive_loop(self) -> None:
        """Aliveness on its own clock, off the step thread. Copies the buffer under the lock
        (fast), then computes the (expensive) score without holding it."""
        while not self._stop:
            states = period = None
            with self.lock:
                if len(self._buf) >= 10:
                    states = np.stack(self._buf)
                    period = getattr(self.engine, "L", None)
            if states is not None:
                self._alive = round(float(score(states, self.cfg, period)["aliveness"]), 3)
            time.sleep(0.7)

    def state(self) -> dict:
        """Build the snapshot on demand (only when the viewer polls) — off the step hot loop."""
        with self.lock:
            snap = self.engine.snapshot()
        snap["status"] = "paused" if self.paused else "running"  # honest: reflect the real pause state
        snap["aliveness"] = self._alive
        snap["pos_bound"] = self.cfg.pos_bound
        snap["knobs"] = {k: float(getattr(self.engine, k)) for k in self.knob_names
                         if hasattr(self.engine, k)}
        for name, (get, _set) in self.pseudo.items():
            snap["knobs"][name] = round(float(get()), 3)
        # live plasticity readout: ‖W_fast‖ shows how much has been learned (0 → grows → plateaus).
        # The matrix itself (small) is sent only when plasticity is on, for the live heatmap.
        if hasattr(self.engine, "W_fast"):
            wf = self.engine.W_fast
            snap["plast_norm"] = round(float(np.linalg.norm(wf)), 3)
            if getattr(self.engine, "plasticity", 0.0) > 0.0:
                snap["plast_w"] = [[round(float(x), 3) for x in row] for row in wf]
        return snap

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def restart(self, seed: int | None = None) -> None:
        with self.lock:
            # preserve the current knob values across restart — a fresh engine would otherwise
            # revert to defaults, silently ignoring the sliders (e.g. attract snapping back to 0.35).
            knobs = {k: getattr(self.engine, k) for k in self.knob_names
                     if hasattr(self.engine, k)}
            self.seed = self.seed + 1 if seed is None else seed
            self.engine = self._make(self.seed)
            for k, v in knobs.items():
                if hasattr(self.engine, k):
                    setattr(self.engine, k, v)
            self.vel_reset()
            self._alive = 0.0
            self._buf.clear()
        self.paused = False        # a restart resumes (past any auto-pause)

    def vel_reset(self) -> None:
        if hasattr(self.engine, "vel"):
            self.engine.vel[:] = 0.0


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
        if self.path.endswith("/stream"):
            self._stream()
        elif self.path.endswith("/state"):
            self._send(200, json.dumps(self.server.sim.state()).encode(), "application/json")
        else:
            self._send(200, _VIEWER.read_bytes(), "text/html; charset=utf-8")

    def _stream(self) -> None:
        """Server-Sent Events: push a snapshot every frame over ONE persistent connection, so the
        browser never does a per-frame round-trip — the fix for network-bound rendering lag."""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")   # ask proxies not to buffer the stream
            self.end_headers()
            dt = 1.0 / self.server.sim.stream_hz
            while not self.server.sim._stop:
                payload = json.dumps(self.server.sim.state())
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                time.sleep(dt)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # client went away — end this stream thread

    def do_POST(self) -> None:
        sim = self.server.sim
        path = self.path.split("?", 1)[0]
        if path.endswith("/pause"):
            sim.set_paused(True)
        elif path.endswith("/resume"):
            sim.set_paused(False)
        elif path.endswith("/restart"):
            from urllib.parse import parse_qs, urlparse
            same = "same" in parse_qs(urlparse(self.path).query)
            sim.restart(seed=sim.seed if same else None)  # same seed → replay identical run
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
    p.add_argument("--hz", type=float, default=30.0)
    p.add_argument("--config", default=str(_CONFIG))
    p.add_argument("--pure", action="store_true",
                   help="serve the PURE-TRANSFORMER engine (transformer moves + morphs everything)")
    p.add_argument("--pack", action="store_true",
                   help="serve the PACKING engine (boundaries + induced-fit, periodic domain)")
    p.add_argument("--polar", action="store_true",
                   help="serve the POLAR PACK engine (electrostatic polarity head from the contour + water)")
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
        knob_names = ("repel", "attract", "cohesion", "temperature", "skew", "morph",
                      "momentum", "speed", "plasticity")
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
    elif args.polar:
        from pack import PackEngine  # noqa: F401  (keep import graph stable)

        from dataclasses import replace

        from polar_pack import PolarPackEngine
        # DENSER dish so water is the BULK MEDIUM everywhere (a viscous solvent fills its container),
        # not a drop floating in vacuum. More tokens + mostly water; lipids are the dilute solute.
        cfg = replace(cfg, N=150)
        water_box = [0.85]
        lipid_box = [0.15]     # dilute amphiphile lipids in bulk water

        def make_engine(s):
            # sensible SHOWCASE defaults (base-case identity is defined vs PackEngine's own defaults, so
            # setting these here does not weaken it — dial polarity→0, water→0 to recover the prev sim).
            # Most-physical defaults for EMERGENCE (transformer-only): no cohesion shortcut (surface
            # tension must EMERGE from attraction), no artificial skew, no plasticity. PER-FORCE decay
            # ranges: repel/attract die within ~a diameter (short-ranged Pauli/vdW), polarity reaches
            # farther (electrostatics). selectivity = softmax τ; temperature = REAL thermal noise.
            # FUNDAMENTAL FORCES ONLY, tuned to the real molecular hierarchy (a soft-potential / DPD
            # regime, since the hard requirement forbids divergent 1/r kernels; overdamped, as a
            # viscous dish is). Energy hierarchy: excluded volume (repel) ≫ electrostatics / H-bond
            # (polarity, ~10 kT) ≫ van der Waals dispersion (attract, ~1 kT) ~ thermal kT (temperature).
            # Range hierarchy: Pauli (repel) < vdW (attract) < electrostatic (polarity).
            e = PolarPackEngine(cfg, s, water_frac=water_box[0], lipid_frac=lipid_box[0],
                                repel=5.00, attract=0.30, polarity=0.80, cohesion=0.00, skew=0.00,
                                morph=0.70, momentum=0.30, speed=1.20)   # strong repel = INCOMPRESSIBLE
            #  water (fills the box, no collapse to a ball); overdamped viscous dish
            e.conservative = True      # symmetric CONSERVATIVE forces → relaxes to a free-energy min
            e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 1.0, 0.25   # Gaussian decay rates λ
            e.repel_contact = 1.00     # σ = particle diameter; repel acts only on overlap
            e.rigidity = 0.00
            e.selectivity = 0.30
            e.temperature = 0.05       # low kT → let the membrane settle
            e.k_tail, e.k_hydro = 1.5, 1.0   # amphiphile: tail cohesion + hydrophobic effect
            return e
        knob_names = ("repel", "sink_repel", "repel_contact", "attract", "sink_attract",
                      "polarity", "sink_polarity", "k_tail", "k_hydro", "morph", "rigidity",
                      "selectivity", "temperature", "momentum", "speed")
        label = "POLAR PACK (water + amphiphile lipids → membrane self-assembly)"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.sim = Sim(cfg, seed, args.hz, make_engine, knob_names)
    if args.polar:
        server.sim.autopause = 5000       # auto-pause at 5000 steps (resumable / restart resumes)

        def _restarter(box, v, lo, hi):
            v = max(lo, min(hi, v))
            if abs(v - box[0]) > 0.02:
                box[0] = v
                server.sim.restart(seed=server.sim.seed)
        server.sim.pseudo = {
            "water": (lambda: water_box[0], lambda v: _restarter(water_box, v, 0.0, 0.9)),
            "lipid": (lambda: lipid_box[0], lambda v: _restarter(lipid_box, v, 0.0, 0.9)),
        }
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
