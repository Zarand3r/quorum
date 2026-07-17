"""Step 2 (M1) — boundedness under learning (P7).

State stays bounded via LayerNorm; the learned weights stay bounded via the L2
decay in the plasticity rule. Neither blows up over a long one-clock run.
"""

from __future__ import annotations

import numpy as np
import pytest

from block import Weights
from config import DEFAULTS, VivariumConfig
from engine import Engine

_STATE_BOUND = 12.0
_WEIGHT_BOUND = 50.0


@pytest.mark.slow
def test_bounded_under_learning() -> None:
    e = Engine(VivariumConfig(**DEFAULTS), seed=0)
    for _ in range(2000):
        e.step()
        assert np.all(np.isfinite(e.X)), f"non-finite state at tick {e.t}"
    assert np.abs(e.X).max() < _STATE_BOUND

    for n in Weights.array_names():
        arr = getattr(e.weights, n)
        assert np.all(np.isfinite(arr)), f"non-finite {n}"
        assert np.abs(arr).max() < _WEIGHT_BOUND, f"{n} grew unbounded"
