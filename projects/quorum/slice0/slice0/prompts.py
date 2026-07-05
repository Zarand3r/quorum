"""Slice 0 prompt renderer.

Two invariants live here (PLAN.md §6):

- **I1 Locality** — the per-agent suffix carries only ``(occupancy_count,)``
  from ``substrate.neighborhood_occupancy``. No coordinates, no per-cell
  values, no reference to any other agent.
- **I10 Shared prefix** — the system message + rules block is byte-identical
  across every agent in a tick (required for KV-cache prefix reuse).

The prefix explicitly states the flocking objective, correcting toy_v1's M5
review finding — a description-only prompt gives the LLM no basis to choose.
"""

from __future__ import annotations

import numpy as np

from slice0.substrate import Agent, neighborhood_occupancy


# I10 gate: this string is BYTE-IDENTICAL across the batch. Anything dynamic
# lives in the per-agent suffix below.
PREFIX: str = (
    "You are one agent in a 2D grid simulation. Every tick, all agents move "
    "simultaneously.\n"
    "\n"
    "You want to be near other agents (form a flock) but not on top of one — "
    "if the cell you would move into is already occupied, you cannot move "
    "into it this tick. Answer with exactly one character:\n"
    "  N — move one cell north\n"
    "  S — move one cell south\n"
    "  E — move one cell east\n"
    "  W — move one cell west\n"
    "  Z — stay in place\n"
    "\n"
    "You observe ONLY the eight cells immediately around you. Decide based "
    "only on what you can see. If the flock is close, staying may be right. "
    "If the flock is far, move toward it.\n"
    "\n"
)


def render(agent: Agent, cells: np.ndarray, radius: int = 1) -> tuple[str, str]:
    """Return ``(prefix, suffix)`` for a single agent.

    The prefix is I10-shared. The suffix carries only the neighborhood
    occupancy count — a single non-negative integer — and no coordinates
    or agent identifiers (I1, I11).
    """
    occ = neighborhood_occupancy(cells, agent, radius=radius)
    if occ == 0:
        window_line = "You see 0 agents in the 8 cells around you (the flock is far)."
    elif occ == 1:
        window_line = "You see 1 agent in the 8 cells around you."
    else:
        window_line = f"You see {occ} agents in the 8 cells around you."
    suffix = f"{window_line}\nAnswer with one character (N, S, E, W, Z):\n"
    return PREFIX, suffix


def render_full(agent: Agent, cells: np.ndarray, radius: int = 1) -> str:
    """Convenience: prefix + suffix."""
    prefix, suffix = render(agent, cells, radius=radius)
    return prefix + suffix
