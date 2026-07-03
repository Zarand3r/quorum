"""Step 6 — HTTP control API over loopback. IMPLEMENTATION_PLAN.md Step 6.

No stepping thread (``autostart_thread=False``), so the assertions are on the
routing, the /state schema, and the transition responses — all deterministic.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from env.config import load_world_config
from sim.controller import SimController
from sim.server import build_server

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _serve():
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    controller = SimController(cfg, default_seed=42, autostart_thread=False)
    server = build_server("127.0.0.1", 0, controller)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, controller, server.server_address[1]


def _get_json(port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
        return json.loads(r.read())


def _post(port: int, path: str) -> int:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=b"", method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_state_schema_and_control_flow() -> None:
    server, controller, port = _serve()
    try:
        st = _get_json(port, "/state")
        assert st["status"] == "IDLE"

        assert _post(port, "/start") == 200
        st = _get_json(port, "/state")
        assert st["status"] == "RUNNING"
        assert st["height"] == 64 and st["width"] == 64
        assert len(st["nutrient"]) == 64 and len(st["nutrient"][0]) == 64
        assert "residual" in st and "forager" in st

        assert _post(port, "/pause") == 200
        assert _get_json(port, "/state")["status"] == "PAUSED"
        assert _post(port, "/pause") == 409  # illegal transition → 409, not a crash

        assert _post(port, "/resume") == 200
        assert _post(port, "/restart") == 200
        assert _get_json(port, "/state")["tick"] == 0

        assert _post(port, "/stop") == 200
        assert _get_json(port, "/state")["status"] == "IDLE"

        assert _post(port, "/bogus") == 404
    finally:
        server.shutdown()
        server.server_close()
        controller.shutdown()


def test_root_serves_viewer_html() -> None:
    server, controller, port = _serve()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
            body = r.read().decode()
        assert "<canvas" in body and "thermolife" in body
    finally:
        server.shutdown()
        server.server_close()
        controller.shutdown()
