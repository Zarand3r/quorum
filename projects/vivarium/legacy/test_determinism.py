"""Step 1 (M0) — determinism (P4).

`(seed, drift schedule)` → byte-identical run. The one non-obvious hazard is
equal-distance k-NN ties: an unstable sort would pick different neighbours run
to run. We break ties by index, deterministically.
"""

from __future__ import annotations

import numpy as np

from block import neighbor_indices
from config import DEFAULTS, VivariumConfig
from engine import Engine


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_run_is_byte_identical() -> None:
    cfg = _cfg()
    a, b = Engine(cfg, seed=0), Engine(cfg, seed=0)
    for _ in range(50):
        a.step()
        b.step()
    assert a.t == b.t == 50
    assert a.X.tobytes() == b.X.tobytes(), "same seed must give a byte-identical run"


def test_different_seed_diverges() -> None:
    cfg = _cfg()
    a, b = Engine(cfg, seed=0), Engine(cfg, seed=1)
    for _ in range(10):
        a.step()
        b.step()
    assert a.X.tobytes() != b.X.tobytes()


def test_equal_distance_ties_break_by_index() -> None:
    # agent 0 at the origin is equidistant (=1) to agents 1, 2, 3.
    pos = np.array([[0.0, 0.0], [1.0, 0.0], [-1.0, 0.0], [0.0, 1.0]])
    idx = neighbor_indices(pos, k=2)
    assert idx[0, 0] == 0, "self (distance 0) is the nearest neighbour"
    assert idx[0, 1] == 1, "among equal-distance ties, the lowest index wins"
    # and it is reproducible.
    assert np.array_equal(idx, neighbor_indices(pos, k=2))
