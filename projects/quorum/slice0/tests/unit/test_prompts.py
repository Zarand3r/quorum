"""Prompt tests — the invariants that are silently violable without them.

- I1  Locality: prompt suffix contains only the neighborhood window observation.
- I10 Shared prefix: system message + rules bytes are IDENTICAL across the batch.
- I11 No global-view leak: no reference to any other agent's coordinates / id.
- Also: the prompt explicitly states the flocking objective (M5 lesson from
  toy_v1 — don't ship a description-only prompt; state what the agent WANTS).
"""

from __future__ import annotations

import numpy as np

from slice0 import prompts
from slice0.substrate import Agent, GRID_OCCUPIED


def _world():
    """Two adjacent agents at (1,1) and (1,2) on a 4×4 toroidal grid, plus
    a far-away agent at (3,3) that is OUTSIDE the (1,1) window when
    radius=1 (toroidal Chebyshev distance from (1,1) to (3,3) is 2)."""
    cells = np.zeros((4, 4), dtype=np.int8)
    cells[1, 1] = GRID_OCCUPIED
    cells[1, 2] = GRID_OCCUPIED
    cells[3, 3] = GRID_OCCUPIED  # off-window trap
    agents = [
        Agent(id=0, row=1, col=1),
        Agent(id=1, row=1, col=2),
        Agent(id=2, row=3, col=3),
    ]
    return cells, agents


class TestSharedPrefix:
    def test_prefix_and_suffix_returned(self):
        cells, agents = _world()
        prefix, suffix = prompts.render(agents[0], cells)
        assert prefix and suffix

    def test_shared_prefix_across_batch_byte_identical(self):
        """I10: every agent's prefix is the identical byte sequence."""
        cells, agents = _world()
        prefixes = [prompts.render(a, cells)[0] for a in agents]
        assert len(set(prefixes)) == 1

    def test_prefix_states_flocking_objective(self):
        """Toy v1's M5 review: prompt must say what the agent WANTS.

        Without an objective, the LLM has no basis to choose. Slice 0 has
        this from day one.
        """
        cells, agents = _world()
        prefix, _ = prompts.render(agents[0], cells)
        low = prefix.lower()
        # Look for flocking-shaped language.
        assert "near" in low or "flock" in low or "close" in low, (
            "prefix does not state a flocking objective — see PLAN.md §22 "
            "and toy_v1 M5 review"
        )

    def test_prefix_lists_all_five_actions(self):
        cells, agents = _world()
        prefix, _ = prompts.render(agents[0], cells)
        for lbl in ("N", "S", "E", "W", "Z"):
            assert lbl in prefix, f"prefix does not mention action {lbl!r}"


class TestLocalitySuffix:
    def test_suffix_contains_local_count(self):
        """I1: the suffix carries the neighborhood occupancy count."""
        cells, agents = _world()
        # Agent 0 at (1,1) has one neighbor (agent 1 at (1,2)). Agent 2 at
        # (3,3) is toroidal-Chebyshev distance 2 from (1,1) — OUTSIDE the
        # radius=1 window.
        _, suffix = prompts.render(agents[0], cells)
        assert "1 neighbor" in suffix or "1 agents" in suffix or " 1 " in suffix

    def test_suffix_no_mention_of_other_agent_ids(self):
        """I11: agent 0's suffix names no other agent."""
        cells, agents = _world()
        _, suffix = prompts.render(agents[0], cells)
        for other in ("agent 1", "agent 2", "agent id"):
            assert other not in suffix.lower(), f"suffix leaks {other!r}"

    def test_suffix_no_absolute_position_leak(self):
        """The suffix must not describe the agent's own row/col directly —
        that's a global-view signal (which corner of the world we're in)."""
        cells, agents = _world()
        _, suffix = prompts.render(agents[0], cells)
        # These would only appear if we accidentally rendered the agent's
        # own (row, col). Instead the prompt should describe the local
        # neighborhood only.
        assert "row 1" not in suffix.lower()
        assert "col 1" not in suffix.lower()
        assert "(1, 1)" not in suffix

    def test_off_window_agent_not_named(self):
        """The far-away agent (3,3) is outside agent 0's window. The suffix
        cannot describe its position or existence directly."""
        cells, agents = _world()
        _, suffix = prompts.render(agents[0], cells)
        assert "3, 3" not in suffix and "(3, 3)" not in suffix

    def test_prompt_deterministic_for_same_state(self):
        cells, agents = _world()
        full1 = prompts.render_full(agents[0], cells)
        full2 = prompts.render_full(agents[0], cells)
        assert full1 == full2


class TestRenderFull:
    def test_full_is_prefix_plus_suffix(self):
        cells, agents = _world()
        prefix, suffix = prompts.render(agents[0], cells)
        assert prompts.render_full(agents[0], cells) == prefix + suffix
