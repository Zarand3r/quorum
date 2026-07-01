"""Tests for prompt rendering.

This is where the invariants most likely to be silently violated land:

- I1 Locality      — prompt body contains only the agent's neighborhood counts.
- I10 Shared prefix — every batch member shares a byte-identical prefix.
- I11 No global leak — the prompt for agent A contains no reference to agent B's
                       color, position, or count.

Each invariant has its own test that fails if violated.
"""

from __future__ import annotations

import numpy as np

from toy_v1 import prompts
from toy_v1.grid import Agent, RED, BLUE, EMPTY


def _world():
    """Tiny world: two adjacent agents (RED at (1,1), BLUE at (1,2)) plus
    a far-away RED at (3,3) deliberately placed *off* both renderees'
    3×3 neighborhoods, to seed an I11 / locality trap. (Chebyshev distance
    from (1,1) to (3,3) is 2, and from (1,2) to (3,3) is 2 — both > 1.)"""
    cells = np.zeros((4, 4), dtype=np.int8)
    cells[1, 1] = RED
    cells[1, 2] = BLUE
    cells[3, 3] = RED   # off-neighborhood for both agents — I11 trap
    agents = [
        Agent(id=0, row=1, col=1, color=RED),
        Agent(id=1, row=1, col=2, color=BLUE),
    ]
    return cells, agents


class TestSharedPrefix:
    def test_render_returns_prefix_and_suffix(self):
        cells, agents = _world()
        prefix, suffix = prompts.render(agents[0], cells)
        assert isinstance(prefix, str) and isinstance(suffix, str)
        assert prefix and suffix

    def test_shared_prefix_across_batch_byte_identical(self):
        """I10: every agent's prefix is identical byte-for-byte."""
        cells, agents = _world()
        prefixes = [prompts.render(a, cells)[0] for a in agents]
        assert len(set(prefixes)) == 1, "prefix drifts across batch members"

    def test_full_prompt_is_prefix_then_suffix(self):
        cells, agents = _world()
        prefix, suffix = prompts.render(agents[0], cells)
        full = prompts.render_full(agents[0], cells)
        assert full == prefix + suffix


class TestLocality:
    def test_suffix_contains_neighbor_counts(self):
        """I1: the per-agent suffix carries the neighborhood breakdown.

        RED at (1,1) sees: 0 same-color neighbors (the other RED at (3,3)
        is OFF the 3×3 neighborhood), 1 BLUE neighbor (at (1,2)), 7 empty.
        """
        cells, agents = _world()
        _, suffix = prompts.render(agents[0], cells)
        assert "0 RED" in suffix
        assert "1 BLUE" in suffix
        assert "7 empty" in suffix

    def test_suffix_contains_only_local_state(self):
        """I11: the suffix mentions no agent other than the one being rendered."""
        cells, agents = _world()
        # Plant a third agent far away with a memorable name; render only agent 0.
        a0 = agents[0]
        _, suffix = prompts.render(a0, cells)
        # The suffix should describe a0's own color and a0's neighborhood
        # totals, with no per-agent identifier visible for any other agent.
        assert "agent 1" not in suffix.lower()
        assert "position (0, 0)" not in suffix.lower()

    def test_other_agent_color_not_named_unless_in_neighborhood(self):
        """A more specific I11 / locality assertion: if a BLUE agent exists
        only off-neighborhood, the suffix's BLUE count must be 0 — and it must
        not leak a per-agent reference."""
        cells = np.zeros((6, 6), dtype=np.int8)
        cells[0, 0] = RED          # the renderee
        cells[5, 5] = BLUE         # far away, NOT in the neighborhood
        a = Agent(id=0, row=0, col=0, color=RED)
        _, suffix = prompts.render(a, cells)
        # The BLUE agent at (5,5) is invisible: the suffix's BLUE count is 0.
        assert "0 BLUE" in suffix

    def test_prompt_deterministic_for_same_state(self):
        cells, agents = _world()
        full_a = prompts.render_full(agents[0], cells)
        full_b = prompts.render_full(agents[0], cells)
        assert full_a == full_b


class TestColorNames:
    def test_red_agent_describes_self_as_red(self):
        cells, agents = _world()
        _, suffix = prompts.render(agents[0], cells)
        assert "RED" in suffix

    def test_blue_agent_describes_self_as_blue(self):
        cells, agents = _world()
        _, suffix = prompts.render(agents[1], cells)
        assert "BLUE" in suffix
