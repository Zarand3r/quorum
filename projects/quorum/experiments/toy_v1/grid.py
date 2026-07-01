"""Substrate: 2D grid of agents.

The grid is a numpy int8 array, ``cells[r, c]`` ∈ {EMPTY, RED, BLUE}. Agents
are addressed by id and carry their own (row, col, color) so the runner can
build prompts without scanning the grid.

Invariants enforced here (PLAN.md §6):

- **I2 Synchrony**: ``step()`` returns *new* arrays without mutating the
  input snapshot. The whole tick's actions are computed against ``state_t``
  and applied together to form ``state_{t+1}``.
- **Locality (I1)** is enforced at observation time by ``neighbor_counts``,
  which returns only the 8-neighbor breakdown for a single agent — never
  a window onto the global grid.

All randomness is taken from a caller-supplied ``np.random.Generator`` so
the runner can wire one RNG through the whole tick for replay determinism
(I8).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

EMPTY: int = 0
RED:   int = 1
BLUE:  int = 2

VALID_ACTIONS: frozenset[str] = frozenset({"STAY", "MOVE"})


@dataclass(slots=True)
class Agent:
    """One agent's position + color.

    Mutable on purpose: ``step()`` returns a list of fresh ``Agent`` instances
    (so the input list is never mutated, preserving I2), but the runner that
    holds the list may rebind fields like ``row``/``col`` within a single
    tick if it wants to. For now no internal code does this; the field is
    settable to keep the option open.
    """

    id: int
    row: int
    col: int
    color: int


def init_state(
    size: int,
    n_agents: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[Agent]]:
    """Build a ``size × size`` grid with ``n_agents`` agents placed uniformly
    at random and with colors drawn ~50/50 from {RED, BLUE}.

    Returns the ``cells`` array and a parallel list of ``Agent`` records.
    Deterministic given ``rng``.
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
    colors = rng.choice([RED, BLUE], size=n_agents)

    agents: list[Agent] = []
    for aid, (p, c) in enumerate(zip(positions, colors)):
        r, k = int(p // size), int(p % size)
        cells[r, k] = int(c)
        agents.append(Agent(id=aid, row=r, col=k, color=int(c)))
    return cells, agents


def neighbor_counts(
    cells: np.ndarray,
    agent: Agent,
) -> tuple[int, int, int]:
    """Return ``(own, other, empty)`` over the agent's 8 neighbors.

    Off-grid neighbors count as empty. The agent's own cell is excluded.

    This is the ONLY function that builds an observation for an agent; the
    locality invariant (I1) holds because the output is the (own, other,
    empty) tuple, with no other cells visible to the caller.
    """
    own = other = empty = 0
    H, W = cells.shape
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = agent.row + dr, agent.col + dc
            if 0 <= nr < H and 0 <= nc < W:
                v = int(cells[nr, nc])
                if v == EMPTY:
                    empty += 1
                elif v == agent.color:
                    own += 1
                else:
                    other += 1
            else:
                empty += 1  # off-grid → empty
    return own, other, empty


def step(
    cells: np.ndarray,
    agents: Sequence[Agent],
    actions: Sequence[str],
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[Agent]]:
    """Apply one tick's actions synchronously. Returns fresh state.

    I2 Synchrony: the input ``cells`` array and ``agents`` list are NOT
    mutated. The function computes everything against the snapshot, then
    returns new objects.

    MOVE semantics: relocate to a random empty cell. The selection uses
    ``rng`` (so replays are deterministic). Movers are processed in agent-id
    order; if two movers would land on the same empty cell, the earlier
    agent claims it.

    If no empty cells remain (or run out during the tick), subsequent MOVE
    actions degrade to STAY rather than raising — fail-soft on environment
    capacity, fail-loud on caller bugs (unknown actions; wrong list length).
    """
    if len(actions) != len(agents):
        raise ValueError(
            f"actions has length {len(actions)} but there are {len(agents)} agents"
        )
    for i, act in enumerate(actions):
        if act not in VALID_ACTIONS:
            raise ValueError(f"unknown action {act!r} at index {i}")

    new_cells = cells.copy()
    new_agents = [Agent(id=a.id, row=a.row, col=a.col, color=a.color) for a in agents]

    # Build the empty-cell pool against the SNAPSHOT (state_t).
    H, W = cells.shape
    empties: list[tuple[int, int]] = [
        (r, c) for r in range(H) for c in range(W) if cells[r, c] == EMPTY
    ]
    # Shuffle so movers land on a uniformly random empty cell rather than
    # always the lexicographically smallest one.
    rng.shuffle(empties)

    for new_a, act in zip(new_agents, actions):
        if act == "STAY":
            continue
        # MOVE: take the next empty cell, if any.
        if not empties:
            continue  # no empty cells left → fall back to STAY
        nr, nc = empties.pop()
        new_cells[new_a.row, new_a.col] = EMPTY
        new_cells[nr, nc] = new_a.color
        # Make the vacated cell available to later movers in this tick.
        empties.insert(0, (new_a.row, new_a.col))
        new_a.row, new_a.col = nr, nc

    return new_cells, new_agents
