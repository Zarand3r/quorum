"""M2.4 — NCA engine (M2.4). Gates Q1 (full-run conservation), Q6 (determinism)."""

from __future__ import annotations

from pathlib import Path

from env.config import load_world_config
from model.config import load_model_config
from sim.controller import SimController, SimStatus
from sim.nca_engine import NCAEngine

_ROOT = Path(__file__).resolve().parent.parent
_WORLD = _ROOT / "configs" / "world.yaml"
_MODEL = _ROOT / "configs" / "model.yaml"


def _cfgs():
    return load_world_config(_WORLD), load_model_config(_MODEL)


def test_engine_conserves_mass() -> None:
    wcfg, mcfg = _cfgs()
    e = NCAEngine(wcfg, mcfg, seed=42)
    for _ in range(800):
        e.step()
    assert e.residual() < 1e-9  # Q1: mass conserved across the whole tick


def test_engine_determinism() -> None:
    wcfg, mcfg = _cfgs()
    a = NCAEngine(wcfg, mcfg, seed=42)
    b = NCAEngine(wcfg, mcfg, seed=42)
    for _ in range(200):
        a.step()
        b.step()
    assert a.state.state_hash() == b.state.state_hash()


def test_snapshot_schema() -> None:
    wcfg, mcfg = _cfgs()
    e = NCAEngine(wcfg, mcfg, seed=1)
    e.step()
    snap = e.snapshot(SimStatus.RUNNING)
    assert len(snap["mass"]) == wcfg.height and len(snap["mass"][0]) == wcfg.width
    assert len(snap["hidden"]) == wcfg.height
    assert "residual" in snap and snap["tick"] == 1


def test_runs_through_controller() -> None:
    wcfg, mcfg = _cfgs()
    c = SimController(
        wcfg,
        default_seed=42,
        autostart_thread=False,
        engine_factory=lambda seed: NCAEngine(wcfg, mcfg, seed),
    )
    c.start(seed=42)
    for _ in range(50):
        c._tick_now()
    snap = c.snapshot()
    assert snap["status"] == "RUNNING"
    assert snap["tick"] == 50
    assert snap["mass"] is not None
