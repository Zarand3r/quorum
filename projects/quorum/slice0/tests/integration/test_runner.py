"""Integration tests for the Slice 0 tick loop.

- I3 across a run: forward_call_count == n_ticks (independent of N).
- I4 across a run: generate_call_count stays 0.
- I8 replay: two runs with same seed → byte-identical trajectory + metrics.
- The runner returns a coherent RunResult (cells_history length == n_ticks+1).
- Uniform-random baseline over 100 ticks completes in well under a second.
"""

from __future__ import annotations

import time

import numpy as np

from slice0 import runner
from slice0.policy import UniformRandomPolicy


class TestI3AcrossRun:
    def test_forward_count_equals_tick_count(self):
        cfg = runner.RunConfig(grid_size=16, n_agents=32, n_ticks=25, seed=42)
        pol = UniformRandomPolicy(seed=cfg.seed)
        result = runner.run(cfg, pol)
        assert pol.forward_call_count == cfg.n_ticks
        assert len(result.metrics) == cfg.n_ticks

    def test_forward_count_independent_of_population(self):
        pol_a = UniformRandomPolicy(seed=0)
        pol_b = UniformRandomPolicy(seed=0)
        runner.run(runner.RunConfig(grid_size=16, n_agents=8, n_ticks=10, seed=42), pol_a)
        runner.run(runner.RunConfig(grid_size=16, n_agents=128, n_ticks=10, seed=42), pol_b)
        assert pol_a.forward_call_count == pol_b.forward_call_count == 10


class TestI4AcrossRun:
    def test_no_generate_calls(self):
        cfg = runner.RunConfig(grid_size=16, n_agents=32, n_ticks=10, seed=42)
        pol = UniformRandomPolicy(seed=cfg.seed)
        runner.run(cfg, pol)
        assert pol.generate_call_count == 0


class TestI8Replay:
    def test_two_runs_same_seed_identical(self):
        cfg = runner.RunConfig(grid_size=16, n_agents=32, n_ticks=20, seed=42)
        r1 = runner.run(cfg, UniformRandomPolicy(seed=cfg.seed))
        r2 = runner.run(cfg, UniformRandomPolicy(seed=cfg.seed))
        # Metrics identical.
        assert r1.metrics == r2.metrics
        # Final state identical.
        assert np.array_equal(r1.final_cells, r2.final_cells)
        assert [(a.id, a.row, a.col) for a in r1.final_agents] == \
               [(a.id, a.row, a.col) for a in r2.final_agents]
        # Every frame identical.
        assert len(r1.cells_history) == len(r2.cells_history)
        for c1, c2 in zip(r1.cells_history, r2.cells_history):
            assert np.array_equal(c1, c2)

    def test_different_seeds_diverge(self):
        r1 = runner.run(runner.RunConfig(16, 32, 20, seed=1), UniformRandomPolicy(seed=1))
        r2 = runner.run(runner.RunConfig(16, 32, 20, seed=2), UniformRandomPolicy(seed=2))
        assert r1.metrics != r2.metrics


class TestRunResultShape:
    def test_cells_history_length(self):
        """N ticks → N+1 frames (state_0 + state_1 … state_N)."""
        cfg = runner.RunConfig(grid_size=8, n_agents=4, n_ticks=7, seed=42)
        result = runner.run(cfg, UniformRandomPolicy(seed=42))
        assert len(result.cells_history) == cfg.n_ticks + 1

    def test_agent_count_preserved_every_tick(self):
        cfg = runner.RunConfig(grid_size=16, n_agents=32, n_ticks=20, seed=42)
        result = runner.run(cfg, UniformRandomPolicy(seed=42))
        for i, cells in enumerate(result.cells_history):
            n_occ = int((cells != 0).sum())
            assert n_occ == cfg.n_agents, f"frame {i}: {n_occ} agents, expected {cfg.n_agents}"

    def test_metrics_populated_per_tick(self):
        cfg = runner.RunConfig(grid_size=16, n_agents=32, n_ticks=15, seed=42)
        result = runner.run(cfg, UniformRandomPolicy(seed=42))
        for m in result.metrics:
            assert m.fwd_passes == 1
            assert 0 <= m.movers <= cfg.n_agents
            assert m.mean_nn_distance >= 1.0  # any Chebyshev NN ≥ 1


class TestPerformance:
    def test_baseline_100_ticks_completes_fast(self):
        """The runner must not have quadratic-in-N-and-T hot paths hiding
        somewhere. 100 ticks × 64 agents on 32×32 should be < 3 s even in
        a bazel sandbox."""
        cfg = runner.RunConfig(grid_size=32, n_agents=64, n_ticks=100, seed=42)
        start = time.monotonic()
        runner.run(cfg, UniformRandomPolicy(seed=42))
        elapsed = time.monotonic() - start
        assert elapsed < 3.0, f"baseline 100-tick run took {elapsed:.2f}s"
