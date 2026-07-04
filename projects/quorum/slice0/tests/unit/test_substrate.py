"""Substrate tests — grid, agents, synchronous step semantics, toroidal wrap.

Invariants verified:

- I2 Synchrony — ``step()`` returns fresh arrays; input snapshot is untouched.
- I8 Replay determinism — ``init_state`` is a pure function of ``rng``.

Substrate-specific correctness:

- Placement respects capacity.
- Neighborhood windows honor toroidal wrap.
- MOVE_{N,S,E,W} shifts position by exactly one cell on a wrapped grid.
- STAY (Z) is a noop.
- Collisions: first agent wins the target cell; later agents fall back to STAY.
"""

from __future__ import annotations

import numpy as np
import pytest

from slice0 import substrate
from slice0.substrate import Agent, GRID_EMPTY, GRID_OCCUPIED


class TestInitState:
    def test_places_requested_number_of_agents(self):
        cells, agents = substrate.init_state(size=8, n_agents=12, rng=np.random.default_rng(42))
        assert len(agents) == 12
        assert int((cells != GRID_EMPTY).sum()) == 12

    def test_agent_positions_match_cells(self):
        cells, agents = substrate.init_state(size=8, n_agents=12, rng=np.random.default_rng(42))
        for a in agents:
            assert cells[a.row, a.col] == GRID_OCCUPIED

    def test_deterministic_with_same_seed(self):
        a_cells, a_agents = substrate.init_state(size=8, n_agents=12, rng=np.random.default_rng(42))
        b_cells, b_agents = substrate.init_state(size=8, n_agents=12, rng=np.random.default_rng(42))
        assert np.array_equal(a_cells, b_cells)
        assert [(a.id, a.row, a.col) for a in a_agents] == [(b.id, b.row, b.col) for b in b_agents]

    def test_different_seeds_diverge(self):
        a_cells, _ = substrate.init_state(size=8, n_agents=12, rng=np.random.default_rng(42))
        b_cells, _ = substrate.init_state(size=8, n_agents=12, rng=np.random.default_rng(43))
        assert not np.array_equal(a_cells, b_cells)

    def test_rejects_over_capacity(self):
        with pytest.raises(ValueError, match="exceeds"):
            substrate.init_state(size=3, n_agents=10, rng=np.random.default_rng(42))

    def test_rejects_bad_size(self):
        with pytest.raises(ValueError):
            substrate.init_state(size=0, n_agents=0, rng=np.random.default_rng(42))


class TestNeighborhoodToroidal:
    """Neighborhood counts wrap around the grid edges."""

    def test_agent_at_origin_sees_wrapped_neighbors(self):
        # Agent at (0, 0) on an 8×8 grid. Place another agent at (7, 7).
        # On a toroidal 3x3 window, (7,7) is diagonally adjacent to (0,0).
        cells = np.zeros((8, 8), dtype=np.int8)
        cells[0, 0] = GRID_OCCUPIED
        cells[7, 7] = GRID_OCCUPIED
        a = Agent(id=0, row=0, col=0)
        n_occ = substrate.neighborhood_occupancy(cells, a)
        assert n_occ == 1  # only the wrapped neighbor counts

    def test_interior_agent_normal_window(self):
        cells = np.zeros((8, 8), dtype=np.int8)
        cells[4, 4] = GRID_OCCUPIED
        cells[3, 3] = GRID_OCCUPIED
        cells[5, 5] = GRID_OCCUPIED
        a = Agent(id=0, row=4, col=4)
        assert substrate.neighborhood_occupancy(cells, a) == 2

    def test_no_neighbors_returns_zero(self):
        cells = np.zeros((8, 8), dtype=np.int8)
        cells[4, 4] = GRID_OCCUPIED
        a = Agent(id=0, row=4, col=4)
        assert substrate.neighborhood_occupancy(cells, a) == 0


class TestStepBasic:
    def test_stay_is_noop(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED
        agents = [Agent(id=0, row=1, col=1)]
        new_cells, new_agents = substrate.step(cells, agents, ["Z"])
        assert np.array_equal(new_cells, cells)
        assert (new_agents[0].row, new_agents[0].col) == (1, 1)

    @pytest.mark.parametrize(
        "action,expected",
        [("N", (0, 1)), ("S", (2, 1)), ("E", (1, 2)), ("W", (1, 0))],
    )
    def test_cardinal_moves_shift_by_one(self, action, expected):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED
        agents = [Agent(id=0, row=1, col=1)]
        new_cells, new_agents = substrate.step(cells, agents, [action])
        assert (new_agents[0].row, new_agents[0].col) == expected
        # The old cell is empty, new cell is occupied.
        assert new_cells[1, 1] == GRID_EMPTY
        assert new_cells[expected] == GRID_OCCUPIED

    def test_wrap_north_from_top_row(self):
        # Agent at row 0 moves N -> wraps to row H-1.
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 2] = GRID_OCCUPIED
        agents = [Agent(id=0, row=0, col=2)]
        new_cells, new_agents = substrate.step(cells, agents, ["N"])
        assert (new_agents[0].row, new_agents[0].col) == (3, 2)

    def test_wrap_south_from_bottom_row(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[3, 2] = GRID_OCCUPIED
        agents = [Agent(id=0, row=3, col=2)]
        new_cells, new_agents = substrate.step(cells, agents, ["S"])
        assert (new_agents[0].row, new_agents[0].col) == (0, 2)

    def test_wrap_east_from_right_column(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[2, 3] = GRID_OCCUPIED
        agents = [Agent(id=0, row=2, col=3)]
        new_cells, new_agents = substrate.step(cells, agents, ["E"])
        assert (new_agents[0].row, new_agents[0].col) == (2, 0)

    def test_wrap_west_from_left_column(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[2, 0] = GRID_OCCUPIED
        agents = [Agent(id=0, row=2, col=0)]
        new_cells, new_agents = substrate.step(cells, agents, ["W"])
        assert (new_agents[0].row, new_agents[0].col) == (2, 3)


class TestStepCollisions:
    def test_two_agents_target_same_cell_first_wins(self):
        """Two agents move to the same empty cell; the earlier agent claims it,
        the later one falls back to STAY. Preserves invariant: no two agents on
        the same cell."""
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[0, 1] = GRID_OCCUPIED  # agent 0 above target
        cells[2, 1] = GRID_OCCUPIED  # agent 1 below target
        agents = [
            Agent(id=0, row=0, col=1),
            Agent(id=1, row=2, col=1),
        ]
        # Both try to move to (1, 1) — agent 0 goes S, agent 1 goes N.
        new_cells, new_agents = substrate.step(cells, agents, ["S", "N"])
        assert (new_agents[0].row, new_agents[0].col) == (1, 1)  # first wins
        assert (new_agents[1].row, new_agents[1].col) == (2, 1)  # unchanged
        # Invariant: no overlap.
        positions = [(a.row, a.col) for a in new_agents]
        assert len(set(positions)) == len(positions)

    def test_move_into_currently_occupied_cell_stays(self):
        """An agent trying to move onto a cell currently occupied by a
        non-moving agent stays put (target is not vacated in state_t)."""
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED
        cells[1, 2] = GRID_OCCUPIED
        agents = [
            Agent(id=0, row=1, col=1),  # stays
            Agent(id=1, row=1, col=2),  # tries to move W into (1,1)
        ]
        new_cells, new_agents = substrate.step(cells, agents, ["Z", "W"])
        assert (new_agents[0].row, new_agents[0].col) == (1, 1)
        assert (new_agents[1].row, new_agents[1].col) == (1, 2)

    def test_swap_move_a_out_b_in_synchronous(self):
        """Agent A moves out of X, agent B tries to move into X. B's decision
        was made against state_t where X was still occupied by A — so B stays.
        This is the toy_v1's M1 lesson applied here from day one: no
        read-your-writes."""
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED  # A
        cells[1, 2] = GRID_OCCUPIED  # B
        agents = [
            Agent(id=0, row=1, col=1),  # A moves N out of (1,1)
            Agent(id=1, row=1, col=2),  # B tries to move W into (1,1)
        ]
        new_cells, new_agents = substrate.step(cells, agents, ["N", "W"])
        assert (new_agents[0].row, new_agents[0].col) == (0, 1)
        assert (new_agents[1].row, new_agents[1].col) == (1, 2), \
            "B chained on A's just-vacated cell — I2 violation"


class TestSynchrony:
    def test_input_arrays_not_mutated(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED
        agents = [Agent(id=0, row=1, col=1)]
        original_cells = cells.copy()
        original_agents = [(a.id, a.row, a.col) for a in agents]

        new_cells, new_agents = substrate.step(cells, agents, ["N"])

        assert np.array_equal(cells, original_cells), "step() mutated input cells"
        assert [(a.id, a.row, a.col) for a in agents] == original_agents, \
            "step() mutated input agents"
        assert new_cells is not cells


class TestStepValidation:
    def test_action_list_length_mismatch(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED
        agents = [Agent(id=0, row=1, col=1)]
        with pytest.raises(ValueError, match="length"):
            substrate.step(cells, agents, ["N", "S"])

    def test_unknown_action_rejected(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        cells[1, 1] = GRID_OCCUPIED
        agents = [Agent(id=0, row=1, col=1)]
        with pytest.raises(ValueError, match="unknown"):
            substrate.step(cells, agents, ["Q"])
