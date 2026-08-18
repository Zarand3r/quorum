"""Plasticity — the fast-weight (Hebbian linear-attention) memory: off by default, learns when
on, stays bounded (homeostasis), and doesn't change the slow weights (the physics stay fixed)."""

from __future__ import annotations

import numpy as np

from config import DEFAULTS, VivariumConfig
from pack import PackEngine


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_off_by_default() -> None:
    # default plasticity=0 → W_fast never accumulates and the run matches a no-plasticity engine.
    a = PackEngine(_cfg(), seed=0)
    assert a.plasticity == 0.0
    for _ in range(30):
        a.step()
    assert np.allclose(a.W_fast, 0.0), "W_fast must stay empty when plasticity is off"


def test_weights_learn_while_alive_when_on() -> None:
    e = PackEngine(_cfg(), seed=0)
    e.plasticity = 1.0
    assert np.allclose(e.W_fast, 0.0)
    for _ in range(30):
        e.step()
    assert not np.allclose(e.W_fast, 0.0), "fast weights must adapt (learn) while the sim runs"


def test_slow_weights_stay_fixed() -> None:
    # the physics (slow weights) never change — only the fast weights learn.
    e = PackEngine(_cfg(), seed=0)
    e.plasticity = 1.0
    slow = {n: getattr(e, n).copy() for n in ("W_v", "W1", "W2", "M", "J", "W_c" if False else "W_k")}
    for _ in range(30):
        e.step()
    for n, before in slow.items():
        assert np.array_equal(getattr(e, n), before), f"slow weight {n} must stay fixed"


def test_fast_weights_bounded() -> None:
    # decay (homeostasis) keeps the fast weights bounded — no runaway.
    e = PackEngine(_cfg(), seed=0)
    e.plasticity = 1.5
    for _ in range(500):
        e.step()
    assert np.all(np.isfinite(e.W_fast))
    assert np.abs(e.W_fast).max() < 50.0, "gated decay must keep fast weights bounded"


def test_freeze_plasticity_ablation() -> None:
    # the load-bearing test hook: freeze_plasticity keeps reading W_fast but stops learning it.
    e = PackEngine(_cfg(), seed=0, ablate="freeze_plasticity")
    e.plasticity = 1.0
    for _ in range(20):
        e.step()
    frozen = e.W_fast.copy()
    for _ in range(20):
        e.step()
    assert np.array_equal(e.W_fast, frozen), "freeze_plasticity must stop the fast weights learning"
