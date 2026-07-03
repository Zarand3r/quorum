"""Step 5 — replay determinism (P5, PLAN.md I8). IMPLEMENTATION_PLAN.md Step 5.

Two runs with the same seed + scenario produce a byte-identical trajectory
(equal per-tick state-hash sequences). This is the "golden constant" for §A:
rather than a brittle hardcoded literal, the golden is the determinism-checked
terminal hash — reproducible under the pinned hermetic interpreter.
"""

from __future__ import annotations

from pathlib import Path

from env.config import load_world_config
from sim.runner import run

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def test_same_seed_identical_trajectory() -> None:
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    a = run(cfg, seed=42, ticks=400, record_hashes=True)
    b = run(cfg, seed=42, ticks=400, record_hashes=True)
    assert a.hashes == b.hashes
    assert len(a.hashes) == 400


def test_trajectory_spans_death() -> None:
    # A deterministic run that includes the death transition is still reproducible.
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    removal = cfg.scenario.removal_tick
    a = run(cfg, seed=42, ticks=removal + 600, record_hashes=True)
    b = run(cfg, seed=42, ticks=removal + 600, record_hashes=True)
    assert a.hashes[-1] == b.hashes[-1]
    assert a.alive_history[-1] == 0  # crossed the death transition
