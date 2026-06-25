"""Tests for the emergence metric."""

from __future__ import annotations

import numpy as np

from toy_v1 import metrics
from toy_v1.grid import Agent, RED, BLUE


class TestSameColorFraction:
    def test_isolated_agents_have_no_non_empty_neighbors_returns_zero(self):
        """If no agent has any non-empty neighbor, the metric is conventionally 0."""
        cells = np.zeros((10, 10), dtype=np.int8)
        cells[0, 0] = RED
        cells[9, 9] = BLUE
        agents = [
            Agent(id=0, row=0, col=0, color=RED),
            Agent(id=1, row=9, col=9, color=BLUE),
        ]
        assert metrics.same_color_fraction(cells, agents) == 0.0

    def test_uniform_color_cluster_returns_one(self):
        cells = np.zeros((4, 4), dtype=np.int8)
        # 2x2 block of RED in the corner.
        cells[0, 0] = RED
        cells[0, 1] = RED
        cells[1, 0] = RED
        cells[1, 1] = RED
        agents = [
            Agent(id=0, row=0, col=0, color=RED),
            Agent(id=1, row=0, col=1, color=RED),
            Agent(id=2, row=1, col=0, color=RED),
            Agent(id=3, row=1, col=1, color=RED),
        ]
        assert metrics.same_color_fraction(cells, agents) == 1.0

    def test_perfectly_mixed_returns_zero(self):
        # Single RED and BLUE adjacent: each sees only the other.
        cells = np.zeros((3, 3), dtype=np.int8)
        cells[0, 0] = RED
        cells[0, 1] = BLUE
        agents = [
            Agent(id=0, row=0, col=0, color=RED),
            Agent(id=1, row=0, col=1, color=BLUE),
        ]
        assert metrics.same_color_fraction(cells, agents) == 0.0

    def test_one_red_with_one_red_and_one_blue_neighbor_returns_half(self):
        cells = np.zeros((3, 3), dtype=np.int8)
        cells[1, 1] = RED   # the renderee
        cells[0, 0] = RED
        cells[2, 2] = BLUE
        agents = [
            Agent(id=0, row=1, col=1, color=RED),
        ]
        # Renderee's neighbors: 1 own (RED at 0,0), 1 other (BLUE at 2,2).
        # Same-color fraction = own/(own+other) = 1/2.
        assert metrics.same_color_fraction(cells, agents) == 0.5
