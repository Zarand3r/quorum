"""Step 0 — deterministic RNG helpers (IMPLEMENTATION_PLAN.md Step 0).

P4 (Determinism) rests on `rng_for(seed, tick)` being a *pure* function of its
arguments: identical `(seed, tick)` → identical stream, and no dependence on
wall-clock or global state. These tests pin that before any dynamics exist.
"""

from __future__ import annotations

import numpy as np

from rng import base_rng, rng_for


def test_rng_for_is_pure_and_reproducible() -> None:
    a = rng_for(1, 2).standard_normal(16)
    b = rng_for(1, 2).standard_normal(16)
    assert np.array_equal(a, b), "same (seed, tick) must give the same stream"


def test_rng_for_varies_with_tick() -> None:
    a = rng_for(1, 2).standard_normal(16)
    b = rng_for(1, 3).standard_normal(16)
    assert not np.array_equal(a, b), "different tick must decorrelate the stream"


def test_rng_for_varies_with_seed() -> None:
    a = rng_for(1, 2).standard_normal(16)
    b = rng_for(2, 2).standard_normal(16)
    assert not np.array_equal(a, b), "different seed must decorrelate the stream"


def test_base_rng_is_pure() -> None:
    a = base_rng(7).standard_normal(16)
    b = base_rng(7).standard_normal(16)
    assert np.array_equal(a, b), "base_rng(seed) must be reproducible"


def test_returns_fresh_generators() -> None:
    # Two calls return independent Generator objects (no shared cursor), yet —
    # being seeded identically — they yield the same first draw.
    g1, g2 = rng_for(3, 4), rng_for(3, 4)
    assert g1 is not g2
    assert g1.standard_normal() == g2.standard_normal()
