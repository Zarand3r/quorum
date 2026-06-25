"""Integration tests for the tick loop.

These exercise multiple modules together against a deterministic
``MockPolicy``, with no torch dependency:

- The I3 gate holds across the whole run (forward count = ticks).
- I8 replay determinism: two runs with the same seed produce a
  byte-identical trajectory of states and metrics.
- The runner cleanly handles the no-empty-cells case (population fully
  packed) without raising.
"""

from __future__ import annotations

import numpy as np

from toy_v1 import runner
from toy_v1.policy import MockPolicy


class TestSinglePassGateAcrossRun:
    def test_forward_count_equals_tick_count(self):
        """I3 (population scale): N forward calls over N ticks, regardless
        of how many agents are in the population."""
        cfg = runner.RunConfig(
            grid_size=8, n_agents=30, n_ticks=20, seed=42,
        )
        mock = MockPolicy(seed=cfg.seed)
        result = runner.run(cfg, mock)
        assert mock.forward_call_count == cfg.n_ticks
        assert len(result.metrics) == cfg.n_ticks

    def test_no_generate_calls_across_run(self):
        """I4: no autoregressive decode anywhere in the loop."""
        cfg = runner.RunConfig(grid_size=8, n_agents=30, n_ticks=20, seed=42)
        mock = MockPolicy(seed=cfg.seed)
        runner.run(cfg, mock)
        assert mock.generate_call_count == 0


class TestReplayDeterminism:
    def test_two_runs_with_same_seed_identical(self):
        """I8: same seed -> byte-identical trajectory across two runs."""
        cfg = runner.RunConfig(grid_size=8, n_agents=30, n_ticks=15, seed=42)
        r1 = runner.run(cfg, MockPolicy(seed=cfg.seed))
        r2 = runner.run(cfg, MockPolicy(seed=cfg.seed))
        # Metric history is byte-identical.
        assert r1.metrics == r2.metrics
        # Final state is byte-identical.
        assert np.array_equal(r1.final_cells, r2.final_cells)
        assert [(a.id, a.row, a.col, a.color) for a in r1.final_agents] == \
               [(a.id, a.row, a.col, a.color) for a in r2.final_agents]

    def test_different_seeds_diverge(self):
        cfg_a = runner.RunConfig(grid_size=8, n_agents=30, n_ticks=15, seed=42)
        cfg_b = runner.RunConfig(grid_size=8, n_agents=30, n_ticks=15, seed=43)
        a = runner.run(cfg_a, MockPolicy(seed=cfg_a.seed))
        b = runner.run(cfg_b, MockPolicy(seed=cfg_b.seed))
        assert a.metrics != b.metrics


class TestFullyPackedSubstrate:
    def test_no_empty_cells_loop_does_not_raise(self):
        """When every cell is occupied, MOVE actions degrade to STAY and
        the runner completes without error."""
        cfg = runner.RunConfig(grid_size=3, n_agents=9, n_ticks=5, seed=42)
        # Biased to always MOVE so the no-empty path is exercised every tick.
        mock = MockPolicy(seed=cfg.seed, p_stay=0.0)
        result = runner.run(cfg, mock)
        assert len(result.metrics) == cfg.n_ticks
        # With no empty cells, no agent actually moves; all metrics are
        # identical to the initial fraction.
        first_frac = result.metrics[0].same_color_fraction
        assert all(m.same_color_fraction == first_frac for m in result.metrics)


class TestMetricsShape:
    def test_each_tick_metric_has_fwd_pass_count(self):
        cfg = runner.RunConfig(grid_size=6, n_agents=18, n_ticks=4, seed=42)
        result = runner.run(cfg, MockPolicy(seed=cfg.seed))
        for m in result.metrics:
            assert m.fwd_passes == 1, "I3 per-tick gate violated"

    def test_movers_field_in_range(self):
        cfg = runner.RunConfig(grid_size=6, n_agents=18, n_ticks=4, seed=42)
        result = runner.run(cfg, MockPolicy(seed=cfg.seed))
        for m in result.metrics:
            assert 0 <= m.movers <= 18
