"""S0 FoldEngine — determinism (J2), snapshot schema, bounded fold."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from fold.config import load_fold_config
from fold.engine import FoldEngine
from sim.controller import SimController

_CFG = Path(__file__).resolve().parent.parent / "configs" / "fold.yaml"
_RUNNING = SimpleNamespace(value="RUNNING")


def _cfg():
    return load_fold_config(_CFG)


def test_determinism() -> None:
    """J2: same seed → identical fold trajectory."""
    cfg = _cfg()
    a, b = FoldEngine(cfg, 0), FoldEngine(cfg, 0)
    for _ in range(100):
        a.step()
        b.step()
    assert a.state_hash() == b.state_hash()
    assert FoldEngine(cfg, 1).state_hash() != a.state_hash() or a.tick != 0


def test_snapshot_schema() -> None:
    cfg = _cfg()
    e = FoldEngine(cfg, 0)
    for _ in range(20):
        e.step()
    snap = e.snapshot(_RUNNING)
    assert snap["status"] == "RUNNING" and snap["tick"] == 20
    assert snap["n"] == cfg.n_tokens
    assert len(snap["tokens"]) == cfg.n_tokens
    tok = snap["tokens"][0]
    assert len(tok["pos"]) == 2
    assert len(tok["contour"]) == cfg.contour_points and len(tok["contour"][0]) == 2
    assert 0.0 <= snap["max_attn"] <= 1.0
    for i, j, wgt in snap["edges"]:
        assert i != j and 0.0 <= wgt <= 1.0


def test_fold_step_finite_and_bounded() -> None:
    """J5 at engine level: the fold displacement stays finite and bounded."""
    cfg = _cfg()
    e = FoldEngine(cfg, 3)
    steps = []
    for _ in range(200):
        e.step()
        steps.append(e.residual())
    steps = np.array(steps)
    assert np.isfinite(steps).all()
    assert steps.max() < 10.0


def test_fold_gallery_advances() -> None:
    """A settled fold reseeds into a fresh one (PLAN.md D3), deterministically."""
    cfg = _cfg()
    a, b = FoldEngine(cfg, 0), FoldEngine(cfg, 0)
    for _ in range(300):
        a.step()
        b.step()
    assert a.snapshot(_RUNNING)["fold"] >= 1  # converged at least once and reseeded
    assert a.state_hash() == b.state_hash()   # reseeds are deterministic (J2 holds)


def test_runs_through_controller() -> None:
    cfg = _cfg()
    c = SimController(lambda s: FoldEngine(cfg, s), default_seed=0, autostart_thread=False)
    c.start(seed=0)
    for _ in range(50):
        c._tick_now()
    snap = c.snapshot()
    assert snap["status"] == "RUNNING" and snap["tick"] == 50
    assert len(snap["tokens"]) == cfg.n_tokens
    c.stop()
    assert c.snapshot()["tokens"] == []  # IDLE snapshot is empty
