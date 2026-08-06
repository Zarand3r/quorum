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


# Slider ranges belong to the ENGINE, not to the client. One hardcoded KMAX table in viewer.html
# served three engines whose parameters differ by orders of magnitude -- the 3-D showcase runs
# repel~0.6 while the 2-D lipid dish runs repel=12 -- so the dish's slider clamped a 12 down to 0.6,
# displayed the wrong value, and cut excluded volume 20x on the first drag. Ranges are derived ONCE
# from the launch defaults; deriving them from the LIVE value instead would make the axis crawl
# outward as the user drags.
_KNOB_HARD_MAX = {"momentum": 0.98, "rigidity": 1.0, "collision": 1.0}

# Integrator stability: per-step displacement must stay under DISP_MAX or the run blows up (the
# failure that was once misread as the membrane melting, 2026-07-28c). `speed` multiplies that
# displacement directly, so a blanket 4x-of-default range handed the user a slider that reaches
# 0.004 against a limit near 0.0012 -- three times past blowup.
_DISP_MAX = 0.05


def speed_ceiling(engine) -> float:
    """Largest `speed` that keeps speed * k_bond / (1 - momentum) under DISP_MAX."""
    k_bond = float(getattr(engine, "k_bond", 0.0) or 0.0)
    mom = float(getattr(engine, "momentum", 0.0) or 0.0)
    if k_bond <= 0.0:
        return 0.0
    return _DISP_MAX * max(1e-3, 1.0 - mom) / k_bond


def knob_range(name: str, value: float, engine=None) -> float:
    """Upper end of a knob's slider: a hard physical bound where one exists, else 4x the default."""
    hard = _KNOB_HARD_MAX.get(name)
    if hard is not None:
        return hard
    if name == "speed" and engine is not None:
        ceil = speed_ceiling(engine)
        if ceil > 0.0:
            return min(4.0 * value, ceil) if value > 0.0 else ceil
    return 4.0 * value if value > 0.0 else 1.0


class Sim:
    """Steps an engine in a background thread; publishes the latest snapshot."""

    def __init__(self, cfg: VivariumConfig, seed: int, hz: float, make_engine=None,
                 knob_names=("noise", "spin", "nonrecip", "scale", "rd")) -> None:
        self.cfg = cfg
        self.seed = seed
        self.hz = hz
        # SSE push rate. Measured: the control endpoints answer in 0-7 ms and the status flag flips
        # in 1-4 ms, so the click lag was never server-side -- it is the BROWSER main thread. At 30 Hz
        # a 47 KB frame is ~1.4 MB/s of JSON.parse plus redraw on the same thread that handles the
        # buttons, so clicks queue behind rendering. 20 Hz is still smooth and gives the UI thread a
        # third of its time back.
        self.stream_hz = min(20.0, hz)
        self._make = make_engine or (lambda s: Engine(cfg, s))
        self.knob_names = knob_names
        # pseudo-knobs: name → (getter, setter). Unlike real knobs (a live setattr), these need a
        # restart (e.g. changing the water COUNT re-assigns species). Set after construction.
        self.pseudo: dict = {}
        self.defaults: dict = {}
        self.ranges: dict = {}   # knob -> slider max, sent to the client so it never guesses  # canonical showcase knob values → /reset restores these (never stale)
        self.substeps = 1         # engine steps per displayed frame. A physically-correct timestep
        #   is much smaller than the old capped one, so without substepping the dish would appear to
        #   crawl; this restores the apparent rate of motion at proportional CPU cost.
        self.autopause = 0        # if >0, auto-pause ONCE when engine.t reaches this step. It must
        #   latch: without the flag it re-pauses on every subsequent tick, so pressing resume looks
        #   like it does nothing (which is exactly what happened once substepping sped the sim up).
        self._autopaused = False
        self.lock = threading.Lock()
        self._edges, self._edges_at = None, 0.0
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
                # Take the lock PER STEP, not across the whole substep batch. A step costs ~25 ms, so
                # holding it for substeps=2 kept the lock for ~50 ms and every viewer poll had to wait
                # that long -- which is what the render lag actually was. Per-step locking lets a poll
                # interleave between substeps and halves the worst-case wait.
                for _ in range(max(1, self.substeps)):
                    if self.paused:            # honour pause between substeps, not just per frame
                        break
                    with self.lock:
                        self.engine.step()
                with self.lock:
                    self._buf.append(self.engine.X[:, :2].copy())  # positions only (cheap)
                if (self.autopause and not self._autopaused
                        and self.engine.t >= self.autopause):
                    self._autopaused = True
                    self.paused = True                # fires once; resume then works normally
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
            snap = self.engine.snapshot(with_edges=self._edges is None
                                        or time.perf_counter() - self._edges_at > 0.5)
        # `edges` needs a full O(N^2) attention pass (4.6 ms of a 5.0 ms snapshot) and the binding
        # graph changes far slower than the frame rate, so it is refreshed at most twice a second and
        # reused in between.
        if snap.get("edges") is None:
            snap["edges"] = self._edges
        else:
            self._edges, self._edges_at = snap["edges"], time.perf_counter()
        snap["status"] = "paused" if self.paused else "running"  # honest: reflect the real pause state
        snap["aliveness"] = self._alive
        snap["pos_bound"] = self.cfg.pos_bound
        snap["knobs"] = {k: float(getattr(self.engine, k)) for k in self.knob_names
                         if hasattr(self.engine, k)}
        snap["ranges"] = self.ranges
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
        self._autopaused = False   # a fresh run may auto-pause again
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
        # NEVER cache. The viewer was served with no Cache-Control, no ETag and no Last-Modified, so
        # browsers and the reverse proxy cached it heuristically -- three rendering fixes were served
        # correctly by this process and never reached the screen, through repeated hard refreshes,
        # because the copy in front of it was stale. /state must not be cached either or the dish
        # appears frozen. The bodies are small and regenerated per request; there is nothing to save.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
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
        elif path.endswith("/reset"):
            sim.set_knobs(sim.defaults)     # restore canonical showcase defaults (server-side truth)
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
    p.add_argument("--dim3", action="store_true",
                   help="run the polar showcase in a 3-D dish (spherical-harmonic contour)")
    p.add_argument("--plant", default="", choices=["", "clump", "ribbon", "micelle"],
                   help="2-D initial condition: empty = fully dispersed (micelles EMERGE, ~6k "
                        "steps); clump = pre-concentrated but disordered; ribbon/micelle = planted")
    p.add_argument("--lipid2d", action="store_true",
                   help="2-D LIPID MEMBRANE dish: the validated chain-lipid parameters, not the "
                        "generic polar showcase. Without this the 2-D path serves a different "
                        "system from the one the 2-D research runs use, which makes the hosted "
                        "viewer unrepresentative of the results.")
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
        cfg = replace(cfg, N=190)   # ≈ full-box packing (dish holds ~183 at Ø=1): no free volume
        water_box = [0.90]          #  ⇒ water can't pull away from the walls into a drop; it fills
        lipid_box = [0.08]     # dilute amphiphile lipids in bulk water (0.90 = the water pseudo-cap)
        amphi_box = [0.0]      # EMERGENT single-bead amphiphile (superseded by the chain lipid)
        chain_box = [0.0]      # 3-BEAD BONDED LIPID — the configuration that actually aggregates
        if args.dim3:
            # 3-D dish: the contour becomes real spherical harmonics (K=2 keeps pos3+shape8+hidden5
            # inside d=16) and the box shrinks so N tokens fill a VOLUME at liquid density. The
            # solute is the EMERGENT amphiphile (a normal token, polar head + neutral tail) — no
            # explicit lipid rod, no k_hydro: membrane behaviour must come from the three forces.
            # 3-D showcase = the VALIDATED chain-lipid physics (docs/BILAYER_REVIEW.md F10/F11):
            # 3-bead bonded lipids, FDT Langevin with no velocity cap, soft bonds and soft excluded
            # volume so a physically stable timestep is affordable, attraction range ~1.6 sigma.
            cfg = replace(cfg, N=380, pos_dim=3, n_harmonics=2, pos_bound=4.0)
            #  pos_bound 4.0 -> ~39% packing, a proper dense liquid. This MUST be recomputed
            #  whenever a bead radius changes: sizing water as a MARTINI bead (0.30 -> 0.50) without
            #  re-sizing the box left the dish at 92% packing, above the 64% random-close-packing
            #  limit, so it was jammed solid and could not rearrange at all.
            #  DEFAULT composition: water + lipids only. ACTIVE (the generic morphing tokens) are
            #  simply the remainder, so water + lipid_frac summing to 1 leaves none — dial either
            #  slider DOWN to bring them back. No species is removed in code.
            water_box, lipid_box = [0.60], [0.0]
            amphi_box[0] = 0.0
            chain_box[0] = 0.40
            # the remaining ~10% are ACTIVE tokens: the original morphing blobs. Water and the
            # amphiphile are RIGID molecules (they only reorient), so without these nothing in the
            # dish would actually morph — the induced-fit deformation vivarium is named for.

        if args.lipid2d:
            # THE EXACT CONFIGURATION THAT PRODUCED MICELLES, taken from fig2d.py -- the run behind
            # the four-micelle figure and the dispersed-start emergence result (head enrichment 3.00,
            # the theoretical maximum for a 1-head/2-tail lipid).
            #
            #     n_lip 63, n_water 250, bound 11.0  ->  N = 63*3 + 250 = 439
            #     repel 12.0, attract 1.0, k_bond 30.0, speed 0.001, satt 0.30, kt 0.02
            #
            # repel is 12, NOT 24. The 24 came from the planted-BILAYER stability sweep, a different
            # experiment: it makes the lamellar phase more stable and assembly slower. Hosting it
            # gave aggregates with head enrichment 0.52 -- below the random null of ~1.0, i.e. heads
            # DEPLETED from the surface, an inverted structure rather than a micelle. Matching 26
            # config fields was necessary and not sufficient; the check that matters is structural.
            cfg = replace(cfg, N=439, pos_dim=2, n_harmonics=3, pos_bound=11.0)
            water_box, lipid_box = [250.0 / 439.0], [0.0]
            amphi_box[0] = 0.0
            chain_box[0] = 189.0 / 439.0

        def make_engine_lipid2d(s):
            """Delegate to bicelle2d.build -- the SAME function every 2-D result was produced with.

            Reimplementing its construction in this file drifted twice: first missing the
            species-pair matrix entirely, then matching all 26 compared fields and STILL producing
            head enrichment 0.71 (below the random null) where the real builder gives 3.00. Whatever
            the remaining difference was -- initial condition, water_dipole, a default not in the
            diff -- reusing the builder removes the entire class of error instead of chasing it.

            The parameters are fig2d.py's, i.e. the four-micelle figure and the dispersed-start
            emergence result.
            """
            from bicelle2d import build as _build2d
            e = _build2d(s, n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
                         satt=0.30, plant=(plant_box[0] or False), n_tail=2, attract=1.0,
                         bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)
            return e

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
                                amphi_frac=amphi_box[0], chain_frac=chain_box[0],
                                k_bond=(30.0 if args.lipid2d else 8.0),
                                #  aniso 0 and rad_head 0 are NOT cosmetic in 2-D. aniso > 0 takes the
                                #  anisotropic branch of _contact_distance, which discards per-species
                                #  sigma -- so head and tail would have the SAME steric radius and the
                                #  packing parameter P = v/(a0*l) could not be expressed at all.
                                **({"aniso": 0.0, "rad_head": 0.0} if args.lipid2d else {}),
                                repel=(12.0 if args.lipid2d else 12.0 if args.dim3 else 5.00),
                                attract=(1.00 if args.lipid2d else 0.30),
                                polarity=0.80, cohesion=0.00, skew=0.00,
                                morph=0.70, momentum=0.30,
                                speed=(0.001 if args.lipid2d else 0.02 if args.dim3 else 1.20))
            #  speed 0.02, not 0.10: with langevin the velocity CAP is gone, and the cap was the
            #  only thing bounding the step on the capped path. At 0.10 the measured displacement is
            #  ~0.51 sigma/step and the lipid bonds stretch to ~2x their rest length.
            #  NOTE (2026-07-25): once the electrostatic force was made genuinely conservative, the
            #  dish collapsed at repel=5 (occupancy 29/64). A truly conservative cohesive liquid
            #  condenses unless excluded volume is stiff enough to hold it open: repel=40 → 56/64.
            #  water (fills the box, no collapse to a ball); overdamped viscous dish
            e.conservative = True      # symmetric CONSERVATIVE forces → relaxes to a free-energy min
            # Gaussian decay rates λ. In 3-D the box is half as wide (to keep liquid density in a
            # volume), so the electrostatic range must shorten too or molecules interact with their
            # own periodic images: at λ=0.25 the kernel is still 0.105 at L/2. λ=0.55 → 7e-3.
            e.sink_repel, e.sink_attract = 6.0, 1.0
            # 0.90 in 3-D, not 0.55: correcting water's steric radius downward lowered the
            # packing, so the box had to shrink to stay a liquid — and a smaller box needs a shorter
            # electrostatic range or molecules interact with their own periodic images. Physically
            # fine: bulk-water electrostatics is Debye-screened.
            e.sink_polarity = 0.90 if args.dim3 else 0.25
            if args.dim3:
                # 0.55 (range ~1.35 sigma), not 0.39 (1.6): van der Waals is now the LONGEST-ranged
                # force, so IT sets the smallest legal box. 1.6 sigma would demand pos_bound >= 3.44
                # and ~507 particles (7x the pair work) to stay a liquid; 1.35 sigma needs 3.0 and
                # 380 (4x), and is still well inside Cooke's fluid-membrane window (> ~0.7 sigma).
                e.sink_attract = 0.55
                e.langevin = True          # FDT thermostat, no velocity cap
            if args.lipid2d:
                # THE SPECIES-PAIR MATRIX, without which this dish cannot demix at all. Geometric
                # (Lorentz-Berthelot) mixing CANNOT express hydrophobicity: by AM-GM the cross term
                # is pinned at or above sqrt(eps_ii*eps_jj), while the real hydrophobic effect needs
                # tail-water BELOW that -- water cohering with itself and squeezing tails out. Every
                # 2-D result in docs/ was measured with this matrix; serving the dish without it
                # would display a system that cannot form the micelles those results report.
                m = np.full((7, 7), 0.15)          # WATER=0, MOL_HEAD=5, MOL_TAIL=6
                m[0, 0] = 0.60                     # water-water: the hydrogen-bond analogue
                m[6, 6] = 1.00                     # tail-tail
                m[0, 6] = m[6, 0] = 0.02           # tail-water: FAR below the geometric mean
                m[5, 5] = 0.10                     # head-head: weak, heads must not cohere
                m[0, 5] = m[5, 0] = 0.60           # head-water: heads are hydrophilic
                m[5, 6] = m[6, 5] = 0.05
                e.eps_pair = m
                e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 0.30, 0.90
                e.langevin = True                  # FDT thermostat, no velocity cap
            e.repel_contact = 1.00     # σ = particle diameter; repel acts only on overlap
            e.rigidity = 0.00
            e.selectivity = 0.30
            # NB: set LAST, and per-mode — an earlier `if args.dim3: e.temperature = 0.02` was
            # silently clobbered by this line, so the 3-D dish ran at 2.5x its intended kT.
            e.temperature = 0.02 if (args.dim3 or args.lipid2d) else 0.05
            e.k_tail, e.k_hydro = 1.5, 1.0   # amphiphile: tail cohesion + hydrophobic effect
            return e
        knob_names = ("repel", "sink_repel", "repel_contact", "attract", "sink_attract",
                      "polarity", "sink_polarity", "k_tail", "k_hydro", "morph", "rigidity",
                      "selectivity", "temperature", "momentum", "speed")
        label = ("POLAR PACK 3-D (spherical-harmonic contour · emergent amphiphiles)" if args.dim3
                 else "POLAR PACK (water + amphiphile lipids → membrane self-assembly)")
    if args.lipid2d and not args.polar:
        # `make_engine_lipid2d` is defined only inside the `elif args.polar:` branch, so --lipid2d on
        # its own fell through and died with "UnboundLocalError: cannot access local variable
        # 'make_engine_lipid2d'" -- 40 lines from the actual mistake. Fail here, where the fix is.
        raise SystemExit("--lipid2d requires --polar (the 2-D lipid dish is a polar-pack engine)")
    plant_box = [args.plant]      # defined BEFORE the closure that reads it
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.sim = Sim(cfg, seed, args.hz,
                     make_engine_lipid2d if args.lipid2d else make_engine, knob_names)
    # The 3-D showcase auto-pauses past its assembly transient; the 2-D lipid dish must NOT. Its
    # transients are far longer (micelles ~6k steps, ribbons ~150k), and a 5000-step pause froze it
    # before anything could form -- the hosted dish showed a still frame of a disordered start,
    # which is exactly what it looked like.
    if args.polar:
        # 10000 for the 2-D lipid dish: well PAST the ~6k where micelles form, so it settles on a
        # frame that shows the result rather than freezing mid-transient. At 5000 it stopped just
        # short and the hosted view was a still of a disordered start.
        server.sim.autopause = 10000 if args.lipid2d else 5000
    if args.polar:
        # auto-pause well past the assembly transient. With substepping the 3-D showcase covers
        # 5000 steps in seconds, and once t exceeds the limit it re-pauses every tick, so a low
        # value made the dish look permanently frozen.
        #
        # THE 2-D LIPID DISH NEEDS FAR MORE. Its timestep is 0.001, twenty times smaller than the
        # 3-D showcase's, and the measured transients are: micelles ~6k steps from a clump and ~20k
        # from a dispersed start, the ribbon phase ~150k. Autopausing at 5000 froze it BEFORE
        # anything could form, so the hosted dish showed a still frame of a disordered start and
        # looked like nothing was happening -- which is exactly what it looked like.
        server.sim.autopause = 60000 if args.lipid2d else 5000

        def _restarter(box, v, lo, hi):
            v = max(lo, min(hi, v))
            if abs(v - box[0]) > 0.02:
                box[0] = v
                server.sim.restart(seed=server.sim.seed)
        server.sim.pseudo = {
            "water": (lambda: water_box[0], lambda v: _restarter(water_box, v, 0.0, 1.0)),   # up to 100% for a pure-water control
        }
        if args.lipid2d:
            # 0.001 is a 20x smaller timestep than the 3-D showcase, so without substepping the dish
            # advances ~27 steps/s and a dispersed start needs ~12 minutes to reach micelles. Four
            # substeps brings that under 4 minutes. Kept modest because each substep runs holding the
            # state lock, and a large count starves /state and makes pause/resume feel delayed.
            server.sim.substeps = 4
        if args.dim3:   # bonded chain lipids replace both the rod and the single-bead amphiphile
            server.sim.substeps = 2        # smaller physical timestep → substep to keep motion
            #   legible. Kept modest on purpose: every substep runs holding the state lock, so a
            #   large count starves /state and makes pause/resume feel delayed.
            server.sim.pseudo["lipid_frac"] = (lambda: chain_box[0],
                                               lambda v: _restarter(chain_box, v, 0.0, 0.6))
        else:
            server.sim.pseudo["lipid"] = (lambda: lipid_box[0],
                                          lambda v: _restarter(lipid_box, v, 0.0, 0.9))
        # canonical showcase defaults, captured at launch — /reset restores exactly these, so playing
        # with the sliders can never strand the sim (a stale browser tab can't override them).
        server.sim.defaults = {**{k: float(getattr(server.sim.engine, k)) for k in knob_names},
                               "water": water_box[0],
                               ("lipid_frac" if args.dim3 else "lipid"):
                                   (chain_box[0] if args.dim3 else lipid_box[0])}
        server.sim.ranges = {k: knob_range(k, v, server.sim.engine)
                             for k, v in server.sim.defaults.items()}
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
