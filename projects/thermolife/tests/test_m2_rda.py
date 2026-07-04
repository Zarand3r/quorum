"""M2.3 — the full RDA tick (M2.3). Gates Q4 (no cell loop), Q5 (synchrony)."""

from __future__ import annotations

import re
import time
from pathlib import Path

import numpy as np

from model.config import load_model_config
from model.genome import Genome
from model.rda import rda_step
from model.state import NCAState

_ROOT = Path(__file__).resolve().parent.parent
_MODEL = _ROOT / "configs" / "model.yaml"
_GRID_LOOP = re.compile(
    r"np\.ndindex|\.ndenumerate|for\s+\w+\s+in\s+range\([^)]*"
    r"(height|width|shape\[0\]|shape\[1\])",
)


def _cfg():
    return load_model_config(_MODEL)


def test_no_grid_loop_in_model() -> None:
    """Q4: the RDA path vectorizes — no loop over grid cells (direction loops ok)."""
    offenders = [
        f.name
        for f in (_ROOT / "model").glob("*.py")
        if _GRID_LOOP.search(f.read_text())
    ]
    assert not offenders, f"grid loop in: {offenders}"


def test_step_does_not_mutate_input() -> None:
    """Q5: synchrony — the step reads state_t and writes fresh arrays."""
    cfg = _cfg()
    g = Genome.random(cfg, seed=2)
    s = NCAState.seed(32, 32, cfg, seed=2)
    hidden_before = s.hidden.copy()
    mass_before = s.mass.copy()
    rda_step(s, g, cfg)
    assert np.array_equal(s.hidden, hidden_before)
    assert np.array_equal(s.mass, mass_before)


def test_bounded_and_conserved_over_long_run() -> None:
    cfg = _cfg()
    g = Genome.random(cfg, seed=11)
    s = NCAState.seed(48, 48, cfg, seed=11)
    total0 = s.mass.sum()
    for _ in range(1000):
        s, _ = rda_step(s, g, cfg)
    assert np.isfinite(s.hidden).all()
    assert np.abs(s.hidden).max() < 1e3          # no blow-up with fixed θ
    assert np.isclose(s.mass.sum(), total0, atol=1e-9)  # advection conserves


def test_throughput_budget() -> None:
    cfg = _cfg()
    g = Genome.random(cfg, seed=1)
    s = NCAState.seed(64, 64, cfg, seed=1)
    t0 = time.perf_counter()
    for _ in range(500):
        s, _ = rda_step(s, g, cfg)
    assert time.perf_counter() - t0 < 15.0
