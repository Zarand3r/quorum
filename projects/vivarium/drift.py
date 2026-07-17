"""The season: a slow deterministic external field (IMPLEMENTATION_PLAN.md Step 2).

`s(t)` is the gentle drive `J` — a slowly rotating field that shifts what the
neighbourhood "should" look like, so the prediction target is perpetually
non-stationary and the colony never fully predicts (never settles). Deterministic
in `t` (part of the P4 contract): no wall-clock, no RNG.
"""

from __future__ import annotations

import numpy as np

_PERIOD = 500.0  # ticks per full turn of the season (slow relative to the dynamics)
_OMEGA = 2.0 * np.pi / _PERIOD


def season(t: int, m: int, rate: float) -> np.ndarray:
    """An m-vector field at tick t: a slow rotation in the first two (position) slots."""
    s = np.zeros(m)
    s[0] = rate * np.cos(_OMEGA * t)
    if m > 1:
        s[1] = rate * np.sin(_OMEGA * t)
    return s
