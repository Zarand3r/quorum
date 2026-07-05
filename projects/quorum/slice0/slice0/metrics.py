"""Slice 0 metrics.

- ``mean_nearest_neighbor_distance``: the success signal from PLAN.md §15.1.
  Chebyshev distance on the toroidal grid — smaller ⇒ flocking. The Slice 0
  merge gate compares this under the LLM population vs the uniform-random
  baseline (Mann-Whitney U over ≥ 10 seeds).

- ``action_decorrelation``: normalized entropy of the per-tick action
  distribution over the 5-symbol vocab. Feeds the R2 herding check
  (PLAN.md §5, I5). 1.0 = uniform over the vocab, 0.0 = every agent picks
  the same action.
"""

from __future__ import annotations

import math
from typing import Sequence

from slice0 import actions as _actions
from slice0.substrate import Agent


def _toroidal_chebyshev(a: Agent, b: Agent, size: int) -> int:
    """Chebyshev distance on a toroidal ``size × size`` grid."""
    dr = abs(a.row - b.row)
    dc = abs(a.col - b.col)
    # Wrap: the shorter of the two spans around the torus.
    dr = min(dr, size - dr)
    dc = min(dc, size - dc)
    return max(dr, dc)


def mean_nearest_neighbor_distance(agents: Sequence[Agent], size: int) -> float:
    """Mean over all agents of the Chebyshev distance to that agent's
    nearest neighbor on a ``size × size`` toroidal grid.

    Returns 0.0 for a population of one (no neighbor to measure against).
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if len(agents) <= 1:
        return 0.0

    nn_distances: list[int] = []
    for i, a in enumerate(agents):
        best = None
        for j, b in enumerate(agents):
            if i == j:
                continue
            d = _toroidal_chebyshev(a, b, size)
            if best is None or d < best:
                best = d
                if best == 0:  # can't get closer; skip the rest
                    break
        assert best is not None  # unreachable given len >= 2
        nn_distances.append(best)
    return float(sum(nn_distances) / len(nn_distances))


def action_decorrelation(action_labels: Sequence[str]) -> float:
    """Normalized Shannon entropy over ``LABELS``, in ``[0, 1]``.

    1.0 = uniform over the vocab (max decorrelation).
    0.0 = every agent picks the same action.

    Undefined for an empty batch; returns 0.0 by convention.
    """
    if not action_labels:
        return 0.0
    counts: dict[str, int] = {lbl: 0 for lbl in _actions.LABELS}
    for lbl in action_labels:
        if lbl in counts:
            counts[lbl] += 1
        # Silently ignore unknown labels — the caller is responsible for
        # validation and typically already fed these to substrate.step()
        # which raises on unknown.
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c == 0:
            continue
        p = c / total
        h -= p * math.log(p)
    # Normalize by the entropy of the uniform distribution over LABELS.
    max_h = math.log(len(_actions.LABELS))
    return h / max_h if max_h > 0 else 0.0
