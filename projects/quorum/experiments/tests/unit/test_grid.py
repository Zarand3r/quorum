"""Tests for the substrate.

Verifies the discipline invariants the toy must hold (PLAN.md §6):

- I2 Synchrony — actions are computed from state_t and applied together to
  form state_{t+1}. Tested by snapshotting state before step() and confirming
  the snapshot is byte-identical afterward.
- I8 Replay determinism — init_state and step are pure functions of the RNG.

Plus the substrate's own correctness contract (neighbor counts; move semantics;
no-empty-cell fallback).
"""

from __future__ import annotations

import numpy as np
import pytest

from toy_v1 import grid
from toy_v1.grid import Agent, RED, BLUE, EMPTY


# ---------- init_state ----------


class TestInitState:
    def test_places_requested_number_of_agents(self):
        cells, agents = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(42))
        assert len(agents) == 30
        assert int((cells != EMPTY).sum()) == 30

    def test_agent_positions_match_cells(self):
        cells, agents = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(42))
        for a in agents:
            assert cells[a.row, a.col] == a.color

    def test_two_colors_present_in_typical_seed(self):
        cells, agents = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(42))
        colors = {a.color for a in agents}
        assert colors == {RED, BLUE}, "with N=30 the split should hit both colors"

    def test_deterministic_with_same_seed(self):
        a_cells, a_agents = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(42))
        b_cells, b_agents = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(42))
        assert np.array_equal(a_cells, b_cells)
        assert [(a.id, a.row, a.col, a.color) for a in a_agents] == \
               [(b.id, b.row, b.col, b.color) for b in b_agents]

    def test_different_seeds_diverge(self):
        a_cells, _ = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(42))
        b_cells, _ = grid.init_state(size=8, n_agents=30, rng=np.random.default_rng(43))
        assert not np.array_equal(a_cells, b_cells)

    def test_rejects_too_many_agents(self):
        with pytest.raises(ValueError, match="exceeds grid capacity"):
            grid.init_state(size=4, n_agents=20, rng=np.random.default_rng(42))

    def test_rejects_invalid_size(self):
        with pytest.raises(ValueError):
            grid.init_state(size=0, n_agents=1, rng=np.random.default_rng(42))


# ---------- neighbor_counts ----------


class TestNeighborCounts:
    def test_interior_agent_full_window(self):
        # Build a 5x5 grid with the agent at (2,2) and known neighbors.
        cells = np.zeros((5, 5), dtype=np.int8)
        cells[2, 2] = RED
        cells[1, 2] = RED   # own (above)
        cells[3, 2] = BLUE  # other (below)
        cells[2, 1] = BLUE  # other (left)
        cells[2, 3] = RED   # own (right)
        a = Agent(id=0, row=2, col=2, color=RED)
        own, other, empty = grid.neighbor_counts(cells, a)
        assert (own, other, empty) == (2, 2, 4)

    def test_corner_agent_off_grid_counted_as_empty(self):
        # Top-left corner; 5 of 8 neighbors are off-grid.
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 0] = RED
        cells[0, 1] = BLUE   # right
        cells[1, 0] = RED    # below
        cells[1, 1] = BLUE   # below-right
        a = Agent(id=0, row=0, col=0, color=RED)
        own, other, empty = grid.neighbor_counts(cells, a)
        # In-grid: 1 own (1,0), 2 other (0,1) and (1,1). Off-grid: 5 cells = empty.
        assert (own, other, empty) == (1, 2, 5)

    def test_all_empty_neighbors(self):
        cells = np.zeros((3, 3), dtype=np.int8)
        cells[1, 1] = RED
        a = Agent(id=0, row=1, col=1, color=RED)
        own, other, empty = grid.neighbor_counts(cells, a)
        assert (own, other, empty) == (0, 0, 8)

    def test_does_not_count_self(self):
        cells = np.zeros((3, 3), dtype=np.int8)
        cells[1, 1] = RED
        a = Agent(id=0, row=1, col=1, color=RED)
        own, other, empty = grid.neighbor_counts(cells, a)
        # Should be 8 empty (all neighbors), NOT 9 (would include self).
        assert own + other + empty == 8


# ---------- step ----------


class TestStep:
    def test_stay_is_noop(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 0] = RED
        agents = [Agent(id=0, row=0, col=0, color=RED)]
        new_cells, new_agents = grid.step(
            cells, agents, ["STAY"], rng=np.random.default_rng(42)
        )
        assert np.array_equal(new_cells, cells)
        assert (new_agents[0].row, new_agents[0].col) == (0, 0)

    def test_move_relocates_agent_to_empty_cell(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 0] = RED
        agents = [Agent(id=0, row=0, col=0, color=RED)]
        new_cells, new_agents = grid.step(
            cells, agents, ["MOVE"], rng=np.random.default_rng(42)
        )
        # Original cell empty, color appears somewhere else.
        assert new_cells[0, 0] == EMPTY
        assert int((new_cells == RED).sum()) == 1
        # The moved agent's coords now match where RED is.
        red_positions = list(zip(*np.where(new_cells == RED)))
        assert len(red_positions) == 1
        r, c = red_positions[0]
        assert (new_agents[0].row, new_agents[0].col) == (r, c)
        # And it's a different cell from where it started.
        assert (r, c) != (0, 0)

    def test_move_target_chosen_deterministically_by_seed(self):
        # Two identical grids + same seed should produce identical post-step state.
        def fresh():
            cells = np.zeros((4, 4), dtype=np.int8)
            cells[0, 0] = RED
            return cells, [Agent(id=0, row=0, col=0, color=RED)]

        a_cells, a_agents = fresh()
        b_cells, b_agents = fresh()
        a_new, a_new_ags = grid.step(a_cells, a_agents, ["MOVE"], rng=np.random.default_rng(42))
        b_new, b_new_ags = grid.step(b_cells, b_agents, ["MOVE"], rng=np.random.default_rng(42))
        assert np.array_equal(a_new, b_new)
        assert (a_new_ags[0].row, a_new_ags[0].col) == (b_new_ags[0].row, b_new_ags[0].col)

    def test_no_empty_cells_move_falls_back_to_stay(self):
        # Pack the grid full.
        cells = np.full((2, 2), RED, dtype=np.int8)
        agents = [
            Agent(id=0, row=0, col=0, color=RED),
            Agent(id=1, row=0, col=1, color=RED),
            Agent(id=2, row=1, col=0, color=RED),
            Agent(id=3, row=1, col=1, color=RED),
        ]
        new_cells, new_agents = grid.step(
            cells, agents, ["MOVE", "MOVE", "MOVE", "MOVE"],
            rng=np.random.default_rng(42),
        )
        # No empty cells -> all moves degrade to stay; cells unchanged.
        assert np.array_equal(new_cells, cells)
        assert [(a.row, a.col) for a in new_agents] == [(0, 0), (0, 1), (1, 0), (1, 1)]

    def test_synchronous_no_in_flight_state_visible(self):
        """I2 Synchrony: the input `cells` array must not be mutated. All
        actions are computed against the snapshot state_t and applied to a
        fresh state_{t+1}."""
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 0] = RED
        cells[3, 3] = BLUE
        agents = [
            Agent(id=0, row=0, col=0, color=RED),
            Agent(id=1, row=3, col=3, color=BLUE),
        ]
        original_cells = cells.copy()
        original_agent_state = [(a.id, a.row, a.col, a.color) for a in agents]

        new_cells, new_agents = grid.step(
            cells, agents, ["MOVE", "MOVE"], rng=np.random.default_rng(42)
        )

        # The input snapshot is untouched.
        assert np.array_equal(cells, original_cells), "step() mutated input cells"
        assert [(a.id, a.row, a.col, a.color) for a in agents] == original_agent_state, \
            "step() mutated input agents"
        # The output is a distinct array.
        assert new_cells is not cells

    def test_no_two_agents_end_up_on_the_same_cell(self):
        # Multiple movers should never collide on a single empty cell.
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 0] = RED
        cells[0, 1] = BLUE
        cells[0, 2] = RED
        cells[0, 3] = BLUE
        agents = [
            Agent(id=0, row=0, col=0, color=RED),
            Agent(id=1, row=0, col=1, color=BLUE),
            Agent(id=2, row=0, col=2, color=RED),
            Agent(id=3, row=0, col=3, color=BLUE),
        ]
        new_cells, new_agents = grid.step(
            cells, agents, ["MOVE", "MOVE", "MOVE", "MOVE"],
            rng=np.random.default_rng(7),
        )
        positions = [(a.row, a.col) for a in new_agents]
        assert len(set(positions)) == len(positions), "two agents share a cell"
        # And the agent count should still be 4.
        assert int((new_cells != EMPTY).sum()) == 4

    def test_action_list_length_must_match_agent_count(self):
        cells = np.zeros((2, 2), dtype=np.int8)
        cells[0, 0] = RED
        agents = [Agent(id=0, row=0, col=0, color=RED)]
        with pytest.raises(ValueError, match="actions"):
            grid.step(cells, agents, ["STAY", "MOVE"], rng=np.random.default_rng(42))

    def test_unknown_action_rejected(self):
        cells = np.zeros((2, 2), dtype=np.int8)
        cells[0, 0] = RED
        agents = [Agent(id=0, row=0, col=0, color=RED)]
        with pytest.raises(ValueError, match="unknown action"):
            grid.step(cells, agents, ["JUMP"], rng=np.random.default_rng(42))
