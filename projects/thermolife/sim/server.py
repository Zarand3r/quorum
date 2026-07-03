"""Stdlib HTTP control server for the Slice-0 simulation (Step 6).

Zero external deps (IMPLEMENTATION_PLAN §D1): a ``ThreadingHTTPServer`` whose
handlers *only* call ``SimController`` methods — they never touch the world (P8).
Exposes the control surface + a polled state feed + the canvas viewer:

    GET  /            → viewer.html
    GET  /state       → JSON snapshot (tick, status, residual, nutrient grid, …)
    POST /start       → build world (optional {"seed": N}) and run
    POST /pause /resume /restart /stop  → control transitions (409 if illegal)

Bind to loopback and expose over Tailscale with ``tailscale serve`` — see
sim/README.md. The app is unauthenticated by design; access control is delegated
to the tailnet.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from env.config import load_world_config
from sim.controller import ControllerError, SimController

_HERE = Path(__file__).resolve().parent
_VIEWER = _HERE / "viewer.html"
_DEFAULT_CONFIG = _HERE.parent / "configs" / "world.yaml"

_CONTROLS = {
    "/start": lambda c, body: c.start(seed=body.get("seed")),
    "/pause": lambda c, body: c.pause(),
    "/resume": lambda c, body: c.resume(),
    "/restart": lambda c, body: c.restart(),
    "/stop": lambda c, body: c.stop(),
}


class ControlServer(ThreadingHTTPServer):
    def __init__(self, addr, controller: SimController) -> None:
        super().__init__(addr, ControlHandler)
        self.controller = controller


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
        if self.path == "/" or self.path == "/index.html":
            html = _VIEWER.read_bytes()
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


def build_server(host: str, port: int, controller: SimController) -> ControlServer:
    return ControlServer((host, port), controller)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="thermolife Slice-0 web control server")
    p.add_argument("--config", default=str(_DEFAULT_CONFIG))
    p.add_argument("--scenario", default="static_gradient")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--step-hz", type=float, default=50.0)
    args = p.parse_args(argv)

    cfg = load_world_config(args.config, scenario=args.scenario)
    controller = SimController(cfg, default_seed=args.seed, step_hz=args.step_hz)
    server = build_server(args.host, args.port, controller)
    print(
        f"thermolife serving on http://{args.host}:{server.server_address[1]}  "
        f"(scenario={args.scenario})\n"
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
