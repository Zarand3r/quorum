"""Deterministic RNG factory (IMPLEMENTATION_PLAN.md Step 0; invariant P4).

Every stochastic draw in vivarium comes from here, keyed by an explicit
`(seed, tick)` pair rather than a mutable global generator. This makes a run a
*pure function* of `(seed, drift schedule)`: replaying the same seed reproduces
the byte-identical trajectory the golden-path spine (§A) pins.

`np.random.SeedSequence` mixes the integer key into a high-quality state, so
adjacent ticks/seeds are decorrelated without us hand-rolling a hash.
"""

from __future__ import annotations

import numpy as np


def rng_for(seed: int, tick: int) -> np.random.Generator:
    """A fresh generator that is a pure function of ``(seed, tick)``."""
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(tick)]))


def base_rng(seed: int) -> np.random.Generator:
    """A fresh generator for one-time init (weights, initial layout), keyed by seed."""
    return np.random.default_rng(np.random.SeedSequence([int(seed)]))
