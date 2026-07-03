"""Step 5 — the Slice-0 headline gate (PLAN.md §15.2) + golden path §A.

The forager survives on the static gradient and DIES within a bounded window
after the source is removed, with conservation holding throughout.
"""

from __future__ import annotations

from pathlib import Path

from env.config import load_world_config
from sim.runner import run

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"
_WINDOW = 1000  # ticks after removal within which the forager must die


def test_slice0_gate_and_conservation() -> None:
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    removal = cfg.scenario.removal_tick
    assert removal is not None
    res = run(cfg, seed=42, ticks=removal + _WINDOW)

    # (stakes) alive while the gradient is fed …
    assert res.alive_history[removal - 1] == 1
    # … and dead within the window after the source is removed (§15.2).
    assert res.alive_history[-1] == 0
    # (P1) conservation residual bounded the whole run.
    assert res.residual_max < 1e-6


def test_forager_does_not_die_while_source_is_on() -> None:
    # Control: with no removal, the forager stays alive indefinitely.
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    # A run shorter than removal_tick keeps the source on throughout.
    res = run(cfg, seed=42, ticks=2000)
    assert all(a == 1 for a in res.alive_history)
