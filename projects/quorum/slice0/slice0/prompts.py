"""Slice 0 prompt renderer.

Two invariants live here (PLAN.md §6):

- **I1 Locality** — the per-agent suffix carries only the agent's own
  ``(2r+1)×(2r+1)`` window, rendered as per-direction occupancy. No
  coordinates, no per-cell (row, col), no reference to any other agent.
- **I10 Shared prefix** — the system message + rules block is byte-identical
  across every agent in a tick (required for KV-cache prefix reuse).

The prefix explicitly states the flocking objective, correcting toy_v1's M5
review finding — a description-only prompt gives the LLM no basis to choose.

**Why per-direction and not a scalar count.** Slice 0's first pass rendered
only the total occupancy count in the suffix. That kept I1/I10/I11 strict
but was directionally symmetric — every action looked equally good from a
prompt with only "you see N agents around you," so the LLM couldn't steer
toward density. The §15.1 merge gate under Qwen 2.5 1.5B on that suffix
produced treatment MNND > baseline MNND (p=0.977). Rendering the 8
neighbor cells as "N=<0|1> NE=... NW=<0|1>" preserves I1 (same declared
radius, still no coordinates) but gives the LLM a directional signal.
"""

from __future__ import annotations

import numpy as np

from slice0.substrate import Agent, GRID_OCCUPIED, neighborhood_view


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
    "You observe ONLY the eight cells immediately around you. Each cell is "
    "reported as 0 (empty) or 1 (occupied by another agent). Decide based "
    "only on what you can see: move toward occupied cells to join the flock, "
    "stay put if you already have neighbors on multiple sides.\n"
    "\n"
)


# radius-1 directional labels in (dr, dc) → label order. Matches the
# (row, col)-major layout returned by ``neighborhood_view``.
_DIR_LABELS: tuple[tuple[int, int, str], ...] = (
    (-1, -1, "NW"),
    (-1,  0, "N"),
    (-1,  1, "NE"),
    ( 0, -1, "W"),
    ( 0,  1, "E"),
    ( 1, -1, "SW"),
    ( 1,  0, "S"),
    ( 1,  1, "SE"),
)


def render(agent: Agent, cells: np.ndarray, radius: int = 1) -> tuple[str, str]:
    """Return ``(prefix, suffix)`` for a single agent.

    The prefix is I10-shared. The suffix carries the agent's own local
    window as per-direction occupancy. It never names another agent, never
    describes the agent's own (row, col), and never reaches outside the
    declared radius (I1, I11).
    """
    if radius != 1:
        raise NotImplementedError(
            "render currently supports only radius=1; "
            "extend _DIR_LABELS to widen."
        )
    view = neighborhood_view(cells, agent, radius=radius)
    parts: list[str] = []
    total = 0
    for dr, dc, label in _DIR_LABELS:
        val = 1 if int(view[dr + radius, dc + radius]) == GRID_OCCUPIED else 0
        parts.append(f"{label}={val}")
        total += val
    window_line = "Neighbors: " + " ".join(parts) + f" (total {total} agents)"
    suffix = f"{window_line}\nAnswer with one character (N, S, E, W, Z):\n"
    return PREFIX, suffix


def render_full(agent: Agent, cells: np.ndarray, radius: int = 1) -> str:
    """Convenience: prefix + suffix."""
    prefix, suffix = render(agent, cells, radius=radius)
    return prefix + suffix
