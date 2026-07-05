"""Metric tests.

- ``mean_nearest_neighbor_distance`` on a toroidal grid: the Slice 0 success
  signal (PLAN.md §15.1). Lower under LLM population than under uniform-random
  baseline ⇒ flocking. Property-tested (lattice → 1; scattered → analytic).
- ``action_decorrelation``: how "not-herding" the population's actions are
  in a single tick. High when actions are diverse across agents (per-agent
  seeds working); low when the population marches in lockstep.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, strategies as st

from slice0 import metrics
from slice0.substrate import Agent


class TestMeanNearestNeighborDistance:
    def test_single_agent_returns_zero(self):
        """A single agent has no neighbors; convention is 0.0."""
        agents = [Agent(id=0, row=0, col=0)]
        assert metrics.mean_nearest_neighbor_distance(agents, size=8) == 0.0

    def test_two_adjacent_agents_have_distance_one(self):
        agents = [Agent(id=0, row=0, col=0), Agent(id=1, row=0, col=1)]
        assert metrics.mean_nearest_neighbor_distance(agents, size=8) == 1.0

    def test_toroidal_wrap_two_corners(self):
        """Agent at (0,0) and (7,7) on an 8-grid are diagonally 1 step apart
        (toroidal Chebyshev distance)."""
        agents = [Agent(id=0, row=0, col=0), Agent(id=1, row=7, col=7)]
        assert metrics.mean_nearest_neighbor_distance(agents, size=8) == 1.0

    def test_two_agents_at_opposite_ends(self):
        """On an 8-grid, (0, 0) and (4, 4) are 4 steps apart (Chebyshev)."""
        agents = [Agent(id=0, row=0, col=0), Agent(id=1, row=4, col=4)]
        assert metrics.mean_nearest_neighbor_distance(agents, size=8) == 4.0

    def test_full_2x2_lattice_returns_one(self):
        """Four agents on a 2×2 lattice — each nearest neighbor is 1 step
        away. Toroidal, so wrap distances tie: still 1."""
        agents = [
            Agent(id=0, row=0, col=0),
            Agent(id=1, row=0, col=1),
            Agent(id=2, row=1, col=0),
            Agent(id=3, row=1, col=1),
        ]
        assert metrics.mean_nearest_neighbor_distance(agents, size=8) == 1.0

    def test_flocking_reduces_mnnd(self):
        """A tight cluster has lower MNND than a scattered population."""
        clustered = [
            Agent(id=i, row=i // 3, col=i % 3) for i in range(9)
        ]  # 3x3 block in the corner
        scattered = [Agent(id=i, row=i * 3, col=i * 3) for i in range(9)]
        cl = metrics.mean_nearest_neighbor_distance(clustered, size=32)
        sc = metrics.mean_nearest_neighbor_distance(scattered, size=32)
        assert cl < sc, f"clustered {cl} >= scattered {sc}"

    @given(size=st.integers(min_value=4, max_value=32))
    def test_full_grid_lattice_is_exactly_one(self, size):
        """Property: with EVERY cell occupied on a size×size grid, every
        agent's nearest neighbor is exactly 1 step away (Chebyshev)."""
        agents = [
            Agent(id=r * size + c, row=r, col=c)
            for r in range(size)
            for c in range(size)
        ]
        assert metrics.mean_nearest_neighbor_distance(agents, size=size) == 1.0

    def test_rejects_bad_size(self):
        agents = [Agent(id=0, row=0, col=0)]
        with pytest.raises(ValueError):
            metrics.mean_nearest_neighbor_distance(agents, size=0)


class TestActionDecorrelation:
    def test_all_agents_same_action_low_decorrelation(self):
        """Everyone stays: correlation = 1, decorrelation = 0."""
        actions_ = ["N"] * 10
        assert metrics.action_decorrelation(actions_) == pytest.approx(0.0)

    def test_uniform_actions_high_decorrelation(self):
        """Actions uniformly split across the 5-vocab: max decorrelation.

        With 100 agents evenly split (20 per label), the normalized entropy
        equals 1.0.
        """
        actions_ = (["N"] * 20 + ["S"] * 20 + ["E"] * 20 + ["W"] * 20 + ["Z"] * 20)
        assert metrics.action_decorrelation(actions_) == pytest.approx(1.0, abs=1e-6)

    def test_two_actions_50_50_partial(self):
        """50/50 across two of the five labels — decorrelation is
        log(2)/log(5)."""
        actions_ = ["N"] * 10 + ["S"] * 10
        expected = math.log(2) / math.log(5)
        assert metrics.action_decorrelation(actions_) == pytest.approx(expected, abs=1e-9)

    def test_empty_action_list_returns_zero(self):
        assert metrics.action_decorrelation([]) == 0.0

    def test_output_range(self):
        # Fuzz over random action mixes; result must be in [0, 1].
        rng = np.random.default_rng(0)
        for _ in range(50):
            actions_ = [rng.choice(("N", "S", "E", "W", "Z")) for _ in range(rng.integers(1, 100))]
            d = metrics.action_decorrelation(actions_)
            assert 0.0 <= d <= 1.0 + 1e-9
