"""Step 5 — hand-coded forager climbs the gradient (IMPLEMENTATION_PLAN.md Step 5)."""

from __future__ import annotations

import math
from pathlib import Path

from env.config import load_world_config
from env.fields import from_config
from env.transactions import TransactionLedger
from sim.forager import forager_position
from sim.tick import tick

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def test_forager_climbs_and_survives() -> None:
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    w = from_config(cfg, seed=42)
    ledger = TransactionLedger()
    start = forager_position(w)
    assert start is not None

    for _ in range(400):
        tick(w, cfg, ledger)

    end = forager_position(w)
    assert end is not None  # survived on the gradient
    src = (int(cfg.scenario.source["cx"]), int(cfg.scenario.source["cy"]))
    # climbed toward the source (never further than it started)
    assert _dist(end, src) <= _dist(start, src)
    # energy stayed above the lethal floor
    assert w.energy[end] > cfg.energy.e_lethal
