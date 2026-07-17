"""Step 1 (M0) — boundedness (P7).

The block ends in LayerNorm, so state stays finite and bounded over a long
fixed-weight run. (At M0 the run may *converge* — non-convergence is an M1
property once drift + learning are on; here we only require it not blow up.)
"""

from __future__ import annotations

import numpy as np
import pytest

from config import DEFAULTS, VivariumConfig
from engine import Engine

_BOUND = 12.0  # LayerNorm output over d channels is ~≤ sqrt(d); 12 is generous for d≤64.


@pytest.mark.slow
def test_bounded_over_long_run() -> None:
    cfg = VivariumConfig(**DEFAULTS)
    e = Engine(cfg, seed=0)
    for _ in range(5000):
        e.step()
        assert np.all(np.isfinite(e.X)), f"non-finite state at tick {e.t}"
    assert np.abs(e.X).max() < _BOUND
