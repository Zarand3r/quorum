"""Prompt rendering for the toy.

This module is where the locality / no-global-leak / shared-prefix invariants
land. Specifically:

- **I1 Locality**  — the suffix carries only the agent's neighborhood counts,
  built via ``grid.neighbor_counts`` which itself reads only the 3×3 window.
- **I10 Shared prefix** — every agent's prompt starts with the same byte-
  identical prefix (system message + format rules). KV-cache prefix reuse
  depends on this, and it's tested directly in ``test_prompts.py``.
- **I11 No global view leakage** — the suffix names no other agent and
  exposes no per-cell state outside the renderee's neighborhood.
"""

from __future__ import annotations

import numpy as np

from toy_v1.grid import Agent, RED, BLUE, neighbor_counts


# The shared system prompt is BYTE-IDENTICAL across the whole batch (I10).
# Anything dynamic goes into the per-agent suffix below.
PREFIX: str = (
    "You are one agent in a 2D grid simulation. You observe ONLY your 8 "
    "immediate neighbors. Answer with exactly one character:\n"
    "  S = stay where you are\n"
    "  M = move to a random empty cell\n"
    "Decide based only on what you can see.\n\n"
)


_COLOR_NAME: dict[int, str] = {RED: "RED", BLUE: "BLUE"}
_OTHER_NAME: dict[int, str] = {RED: "BLUE", BLUE: "RED"}


def render(agent: Agent, cells: np.ndarray) -> tuple[str, str]:
    """Return ``(prefix, suffix)`` for the given agent.

    The prefix is byte-identical across all agents in a batch (I10). The
    suffix is the agent's local observation, formatted as a short natural-
    language sentence. The locality invariant (I1, I11) holds because the
    suffix's only state-derived content is the (own, other, empty) triple
    returned by ``neighbor_counts``.
    """
    own, other, empty = neighbor_counts(cells, agent)
    self_color = _COLOR_NAME[agent.color]
    other_color = _OTHER_NAME[agent.color]
    suffix = (
        f"You are a {self_color} agent. "
        f"Among your 8 neighbors: {own} {self_color}, "
        f"{other} {other_color}, {empty} empty. "
        f"Answer:"
    )
    return PREFIX, suffix


def render_full(agent: Agent, cells: np.ndarray) -> str:
    """Convenience: prefix + suffix."""
    prefix, suffix = render(agent, cells)
    return prefix + suffix
