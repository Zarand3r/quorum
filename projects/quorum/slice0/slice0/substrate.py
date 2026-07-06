"""Toroidal grid substrate for Slice 0.

32×32 by default (configurable via ``init_state``). Single "species" (Boids),
so agents carry only a position. Grid cells are int8 ∈ {EMPTY, OCCUPIED}.

Invariants (from PLAN.md §6):

- **I2 Synchrony** — ``step()`` returns fresh arrays; input snapshot untouched.
- **I8 Replay determinism** — every random choice takes its bits from an rng
  the caller supplies.

Collision policy (documented deliberately, tested directly):

- A MOVE whose target cell was occupied in ``state_t`` degrades to STAY. This
  includes cells occupied by an agent that *itself* moves out during this
  tick — because the moving agent's decision was made against ``state_t``,
  the target was still occupied at decision time (no read-your-writes,
  Slice 0 gets this right from day one; toy_v1's M1 review finding).
- Two agents whose actions would land them on the same currently-empty cell:
  the earlier-id agent claims it, the later degrades to STAY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from slice0 import actions

# Cell values. Single-species Boids, so only two states.
GRID_EMPTY: int = 0
GRID_OCCUPIED: int = 1


@dataclass(slots=True)
class Agent:
    """One agent's position. No color, no memory (single-persona Slice 0)."""

    id: int
    row: int
    col: int


def init_state(
    size: int,
    n_agents: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[Agent]]:
    """Place ``n_agents`` uniformly at random on a ``size × size`` grid.

    Returns the cells array + parallel agent list. Deterministic given ``rng``.
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if n_agents < 0:
        raise ValueError(f"n_agents must be non-negative, got {n_agents}")
    if n_agents > size * size:
        raise ValueError(
            f"n_agents={n_agents} exceeds grid capacity {size * size}"
        )

    cells = np.zeros((size, size), dtype=np.int8)
    positions = rng.choice(size * size, size=n_agents, replace=False)
    agents: list[Agent] = []
    for aid, p in enumerate(positions):
        r, c = int(p // size), int(p % size)
        cells[r, c] = GRID_OCCUPIED
        agents.append(Agent(id=aid, row=r, col=c))
    return cells, agents


def neighborhood_occupancy(
    cells: np.ndarray,
    agent: Agent,
    radius: int = 1,
) -> int:
    """Count the number of occupied cells in the agent's ``(2r+1) × (2r+1)``
    toroidal window, excluding the agent's own cell.

    Locality (I1) holds because the caller only gets the integer count — no
    coordinates, no per-cell values, no reference to any other agent.
    """
    H, W = cells.shape
    count = 0
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if dr == 0 and dc == 0:
                continue
            nr = (agent.row + dr) % H
            nc = (agent.col + dc) % W
            if int(cells[nr, nc]) == GRID_OCCUPIED:
                count += 1
    return count


def neighborhood_view(
    cells: np.ndarray,
    agent: Agent,
    radius: int = 1,
) -> np.ndarray:
    """Return the ``(2r+1) × (2r+1)`` toroidal window around the agent.

    Center is the agent's own cell (always ``GRID_OCCUPIED`` by construction).
    Values are cell states as int8 ``{GRID_EMPTY, GRID_OCCUPIED}``. Toroidal
    wrap on both axes.

    Locality (I1) holds because the view spans ONLY the declared window —
    same radius as ``neighborhood_occupancy``. No coordinates leak: the
    caller sees a grid-relative window, not any (row, col) tuples.
    """
    H, W = cells.shape
    side = 2 * radius + 1
    view = np.empty((side, side), dtype=np.int8)
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            nr = (agent.row + dr) % H
            nc = (agent.col + dc) % W
            view[dr + radius, dc + radius] = cells[nr, nc]
    return view


def step(
    cells: np.ndarray,
    agents: Sequence[Agent],
    action_labels: Sequence[str],
) -> tuple[np.ndarray, list[Agent]]:
    """Apply one tick's actions synchronously. Returns fresh state.

    All decisions are computed against the snapshot; no read-your-writes.
    """
    if len(action_labels) != len(agents):
        raise ValueError(
            f"actions length {len(action_labels)} != agents length {len(agents)}"
        )
    # Fail-fast on unknown labels before any writes.
    for i, label in enumerate(action_labels):
        try:
            _ = actions.to_delta(label)
        except ValueError as e:
            raise ValueError(f"unknown action {label!r} at index {i}") from e

    H, W = cells.shape
    new_cells = cells.copy()
    new_agents = [Agent(id=a.id, row=a.row, col=a.col) for a in agents]

    # I2 invariant: every decision is against state_t. So the "claimed" set
    # freezes the state_t occupancy for the whole tick — a mover CANNOT chain
    # into a just-vacated cell (that's read-your-writes; toy_v1's M1 review
    # finding, prevented here by construction).
    #
    # A move succeeds iff the target is not in `claimed`. On success, the
    # target is added to `claimed` (blocks later movers this tick). The
    # vacated cell stays in `claimed` — it was occupied in state_t and any
    # would-be chainer decided against state_t.
    claimed: set[tuple[int, int]] = {(a.row, a.col) for a in agents}

    for new_a, label in zip(new_agents, action_labels):
        dr, dc = actions.to_delta(label)
        if dr == 0 and dc == 0:
            continue  # Z: stay
        tr = (new_a.row + dr) % H
        tc = (new_a.col + dc) % W
        if (tr, tc) in claimed:
            continue  # target was occupied in state_t or already-taken → STAY
        claimed.add((tr, tc))
        # NOTE: (new_a.row, new_a.col) is *not* removed from `claimed`. See
        # the invariant comment above.
        new_cells[new_a.row, new_a.col] = GRID_EMPTY
        new_cells[tr, tc] = GRID_OCCUPIED
        new_a.row, new_a.col = tr, tc

    return new_cells, new_agents
