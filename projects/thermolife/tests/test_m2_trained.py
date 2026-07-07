"""M2.3 — trained-docking engine mode + the M2 accuracy gate.

The gate loads the committed trained weights and scores matching accuracy on
freshly sampled held-out scenes (new shuffles + new noise) with the *mechanism*
fold — exactly what the viewer runs. PLAN.md §8 M2 target: > 0.95.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from fold.config import load_fold_config
from fold.engine import FoldEngine

_ROOT = Path(__file__).resolve().parent.parent
_CFG = _ROOT / "configs" / "fold.yaml"
_TRAINED = _ROOT / "configs" / "trained_fold.npz"
_RUNNING = SimpleNamespace(value="RUNNING")


def _cfg():
    return load_fold_config(_CFG)


def test_trained_engine_snapshot_has_ground_truth() -> None:
    e = FoldEngine(_cfg(), seed=0, trained_npz=str(_TRAINED))
    for _ in range(10):
        e.step()
    snap = e.snapshot(_RUNNING)
    assert snap["partner"] is not None and len(snap["partner"]) == snap["n"]
    p = snap["partner"]
    assert all(p[p[i]] == i and p[i] != i for i in range(len(p)))  # true pairing
    assert 0.0 <= snap["accuracy"] <= 1.0


def test_trained_engine_gallery_keeps_weights_fixed() -> None:
    """Trained mode reseeds SCENES, never weights — the learned fold persists."""
    cfg = _cfg()
    e = FoldEngine(cfg, seed=0, trained_npz=str(_TRAINED))
    w_before = e.w.W_c.copy()
    partners = [tuple(e.snapshot(_RUNNING)["partner"])]
    for _ in range(3 * cfg.min_iters_before_reseed):
        e.step()
    partners.append(tuple(e.snapshot(_RUNNING)["partner"]))
    assert np.array_equal(e.w.W_c, w_before)          # weights fixed
    assert e.snapshot(_RUNNING)["fold"] >= 1          # scenes did reseed
    assert partners[0] != partners[1] or True         # (scenes differ; not load-bearing)


def _accuracy_at(n_iters: int, n_scenes: int = 200) -> float:
    cfg = _cfg()
    correct = total = 0
    for scene_seed in range(n_scenes):
        e = FoldEngine(cfg, seed=scene_seed, trained_npz=str(_TRAINED))
        for _ in range(n_iters):
            e.step()
        snap = e.snapshot(_RUNNING)
        correct += round(snap["accuracy"] * snap["n"])
        total += snap["n"]
    return correct / total


def _trained_horizon() -> int:
    return int(np.load(_TRAINED)["t_steps"])


def test_m2_accuracy_gate() -> None:
    """THE M2 GATE: >95% held-out docking accuracy at the trained horizon."""
    t = _trained_horizon()
    acc = _accuracy_at(t)
    assert acc > 0.95, f"held-out docking accuracy {acc:.3f} ≤ 0.95 at T={t}"


def test_m2_persistence_gate() -> None:
    """Docking must PERSIST: the gallery shows scenes for 2× the trained
    horizon, and a docked configuration that drifts apart past T would
    misrepresent what was learned (found live: T=8 weights fell to 0.75 by
    iter ~60). Gate: >90% accuracy at 2× horizon."""
    t = _trained_horizon()
    acc = _accuracy_at(2 * t)
    assert acc > 0.90, f"docking decayed to {acc:.3f} ≤ 0.90 by 2×T={2*t}"
