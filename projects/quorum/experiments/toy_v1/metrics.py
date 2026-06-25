"""Emergence metric: Schelling same-color-neighbor fraction.

Used as the runtime signal that the population is segregating (or not).
Convention: an agent with zero non-empty neighbors contributes nothing to
the mean — the metric is computed over the subset of agents that have at
least one same- or different-color neighbor.

If no agent has any non-empty neighbor (degenerate sparse case), the
metric is 0.0.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from toy_v1.grid import Agent, neighbor_counts


def same_color_fraction(cells: np.ndarray, agents: Sequence[Agent]) -> float:
    """Mean fraction of same-color neighbors among each agent's non-empty
    neighbors. Returns 0.0 if no agent has any non-empty neighbor."""
    fracs: list[float] = []
    for a in agents:
        own, other, _ = neighbor_counts(cells, a)
        if own + other == 0:
            continue
        fracs.append(own / (own + other))
    return float(np.mean(fracs)) if fracs else 0.0
