"""Stdlib HTTP control server for the embedding-folding sim (PLAN.md §5, §7).

Zero external deps: a ``ThreadingHTTPServer`` whose handlers *only* call
``SimController`` methods. Routes:

    GET  /            → viewer.html (morphing blobs + docking edges)
    GET  /state       → JSON snapshot (tick, fold_step, tokens[blobs], edges)
    POST /start       → build a fresh fold (optional {"seed": N}) and run
    POST /pause /resume /restart /stop  → control transitions (409 if illegal)

Bind to loopback and expose over Tailscale (sim/host.sh). Unauthenticated by
design; access control is delegated to the tailnet.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from eco.config import load_eco_config
from fold.config import load_fold_config
from fold.engine import FoldEngine
from sim.controller import ControllerError, SimController

_HERE = Path(__file__).resolve().parent
_VIEWER = _HERE / "viewer.html"
_ECO_VIEWER = _HERE / "eco_viewer.html"
_DEFAULT_CONFIG = _HERE.parent / "configs" / "fold.yaml"
_ECO_CONFIG = _HERE.parent / "configs" / "eco.yaml"
_MORPH_CONFIG = _HERE.parent / "configs" / "morph.yaml"

_CONTROLS = {
    "/start": lambda c, body: c.start(seed=body.get("seed")),
    "/pause": lambda c, body: c.pause(),
    "/resume": lambda c, body: c.resume(),
    "/restart": lambda c, body: c.restart(),
    "/next": lambda c, body: c.next_scene(),
    "/stop": lambda c, body: c.stop(),
}


class ControlServer(ThreadingHTTPServer):
    def __init__(self, addr, controller: SimController, viewer: Path) -> None:
        super().__init__(addr, ControlHandler)
        self.controller = controller
        self.viewer = viewer


class ControlHandler(BaseHTTPRequestHandler):
    server: ControlServer  # type: ignore[assignment]

    def log_message(self, *args) -> None:  # silence default stderr logging
        pass

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            html = self.server.viewer.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif self.path == "/state":
            self._send_json(200, self.server.controller.snapshot())
        else:
            self._send_json(404, {"error": f"not found: {self.path}"})

    def do_POST(self) -> None:
        action = _CONTROLS.get(self.path)
        if action is None:
            self._send_json(404, {"error": f"not found: {self.path}"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = {}
        if length:
            raw = self.rfile.read(length)
            if raw.strip():
                body = json.loads(raw)
        try:
            action(self.server.controller, body)
        except ControllerError as exc:
            self._send_json(409, {"error": str(exc)})
            return
        self._send_json(200, {"status": self.server.controller.status().value})


def build_server(host: str, port: int, controller: SimController,
                 viewer: Path = _VIEWER) -> ControlServer:
    return ControlServer((host, port), controller, viewer)


def _eco_factory(cfg, policy_name: str, theta_npz: str | None = None):
    """Build an eco engine factory(seed) for the chosen policy.

    ``attention`` uses the E1 operator: a random θ by default, or the EVOLVED θ
    (E2) when ``theta_npz`` is given — the same weights the E2 gate scores, so the
    viewer shows the learned foraging, not untrained noise."""
    from eco.engine import EcoEngine
    from eco.interaction import make_attention_policy
    from eco.policies import frozen, hand_forager

    weights = None
    if theta_npz is not None:
        from train.es_eco import load_theta
        weights = load_theta(theta_npz, cfg)

    def factory(seed: int):
        if policy_name == "attention":
            return EcoEngine(cfg, policy=make_attention_policy(cfg, seed=seed, weights=weights))
        if policy_name == "frozen":
            return EcoEngine(cfg, policy=frozen)
        return EcoEngine(cfg, policy=hand_forager)
    return factory


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="thermolife sim server (fold or economy)")
    p.add_argument("--config", default=None, help="defaults to the mode's config")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--step-hz", type=float, default=20.0)
    p.add_argument("--trained", default=None,
                   help="fold mode: path to trained weights .npz → learned docking")
    p.add_argument("--eco", action="store_true",
                   help="serve the ECONOMY (eco/) instead of the fold")
    p.add_argument("--eco-policy", choices=["forager", "attention", "frozen"],
                   default="forager", help="eco mode: which policy drives the population")
    p.add_argument("--eco-theta", default=None,
                   help="eco attention mode: path to evolved θ .npz (E2) → learned foraging")
    p.add_argument("--morph", action="store_true",
                   help="serve the reaction–diffusion MORPH (fold/morph.py): shapes grow "
                        "from one seed and move/morph as the transformer block does RD")
    args = p.parse_args(argv)

    if args.morph:
        from fold.morph import MorphEngine, load_morph
        cfg, params = load_morph(args.config or str(_MORPH_CONFIG))
        seed = cfg.seed if args.seed is None else args.seed
        controller = SimController(lambda s: MorphEngine(cfg, s, params=params),
                                   default_seed=seed, step_hz=args.step_hz)
        viewer, label = _VIEWER, "reaction–diffusion morph"
    elif args.eco:
        cfg = load_eco_config(args.config or str(_ECO_CONFIG))
        seed = cfg.seed if args.seed is None else args.seed
        controller = SimController(_eco_factory(cfg, args.eco_policy, args.eco_theta),
                                   default_seed=seed, step_hz=args.step_hz)
        tag = args.eco_policy + (" · evolved θ" if args.eco_theta else "")
        viewer, label = _ECO_VIEWER, f"economy · {tag}"
    else:
        cfg = load_fold_config(args.config or str(_DEFAULT_CONFIG))
        seed = cfg.seed if args.seed is None else args.seed
        controller = SimController(
            lambda s: FoldEngine(cfg, s, trained_npz=args.trained),
            default_seed=seed, step_hz=args.step_hz,
        )
        viewer, label = _VIEWER, "fold"

    server = build_server(args.host, args.port, controller, viewer)
    print(
        f"thermolife ({label}) serving on http://{args.host}:{server.server_address[1]}\n"
        f"expose on your tailnet:  tailscale serve --bg {server.server_address[1]}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
