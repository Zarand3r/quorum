"""Step 1 — World contract (IMPLEMENTATION_PLAN.md Step 1)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from env import fields as F
from env.config import load_world_config

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _cfg():
    return load_world_config(_CONFIG, scenario="static_gradient")


def test_shapes_and_dtypes() -> None:
    cfg = _cfg()
    w = F.from_config(cfg, seed=42)
    assert w.fields.shape == (64, 64, F.N_FIELDS)
    assert w.fields.dtype == F.DTYPE
    assert w.energy.shape == (64, 64)
    assert w.alive.shape == (64, 64)
    assert w.tick == 0
    # heat starts at ambient, other fields at zero.
    assert np.all(w.fields[:, :, F.Field.HEAT] == cfg.fields["heat"].ambient)
    assert np.all(w.fields[:, :, F.Field.NUTRIENT] == 0.0)


def test_exactly_one_forager() -> None:
    w = F.from_config(_cfg(), seed=42)
    assert w.alive.sum() == 1.0
    assert w.energy.sum() > 0.0


def test_state_hash_deterministic_across_construction() -> None:
    a = F.from_config(_cfg(), seed=42)
    b = F.from_config(_cfg(), seed=42)
    assert a.state_hash() == b.state_hash()


def test_state_hash_changes_with_state() -> None:
    w = F.from_config(_cfg(), seed=42)
    h0 = w.state_hash()
    w2 = w.copy()
    w2.fields[0, 0, F.Field.NUTRIENT] += 1.0
    assert w2.state_hash() != h0
    # tick is part of the hash.
    w3 = w.copy()
    w3.tick = 1
    assert w3.state_hash() != h0


def test_copy_is_independent() -> None:
    w = F.from_config(_cfg(), seed=42)
    c = w.copy()
    c.energy[0, 0] += 5.0
    assert w.energy[0, 0] == 0.0  # original untouched
