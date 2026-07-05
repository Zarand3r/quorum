"""Slice 0 tick loop.

Same shape as toy_v1's runner. Per tick:

1. Observe — build one prompt per agent from the neighborhood window
   (locality I1 / I11 enforced by ``prompts.render_full``).
2. Decide — ONE batched forward pass via ``policy.step`` (I3, I4).
3. Apply — synchronous substrate step (I2).
4. Record — MNND + decorrelation + fwd-pass=1 metric row.

The whole trajectory is retained in ``RunResult.cells_history`` so the
merge gate can replay + diff without re-running.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from slice0 import metrics as _metrics
from slice0 import prompts as _prompts
from slice0 import substrate
from slice0.policy import Policy
from slice0.substrate import Agent


@dataclass(slots=True)
class RunConfig:
    """One run's knobs. Defaults match PLAN.md §15.1 Slice 0."""

    grid_size: int = 32
    n_agents: int = 64
    n_ticks: int = 100
    seed: int = 42


@dataclass(slots=True, frozen=True)
class TickMetric:
    """Per-tick metrics row."""

    t: int
    mean_nn_distance: float
    decorrelation: float
    movers: int
    fwd_passes: int


@dataclass(slots=True)
class RunResult:
    """Trajectory + metrics of one run."""

    config: RunConfig
    metrics: list[TickMetric] = field(default_factory=list)
    initial_cells: np.ndarray = field(default=None)  # type: ignore[assignment]
    initial_agents: list[Agent] = field(default_factory=list)
    final_cells: np.ndarray = field(default=None)  # type: ignore[assignment]
    final_agents: list[Agent] = field(default_factory=list)
    cells_history: list[np.ndarray] = field(default_factory=list)


def run(cfg: RunConfig, policy: Policy) -> RunResult:
    """Drive ``cfg.n_ticks`` ticks. Returns a full trajectory."""
    rng = np.random.default_rng(cfg.seed)
    cells, agents = substrate.init_state(cfg.grid_size, cfg.n_agents, rng)

    initial_cells = cells.copy()
    initial_agents = [Agent(id=a.id, row=a.row, col=a.col) for a in agents]

    cells_history: list[np.ndarray] = [initial_cells.copy()]
    metric_rows: list[TickMetric] = []

    for t in range(cfg.n_ticks):
        # 1. Observe (I1, I11 inside prompts.render_full via neighborhood_occupancy)
        batch_prompts = [_prompts.render_full(a, cells) for a in agents]
        batch_obs = [
            {"occupancy": substrate.neighborhood_occupancy(cells, a)}
            for a in agents
        ]

        # 2. Decide — ONE batched forward pass (I3, I4)
        labels = policy.step(batch_prompts, rng=rng, observations=batch_obs)

        # 3. Apply — synchronous (I2, enforced inside substrate.step)
        cells, agents = substrate.step(cells, agents, labels)

        # 4. Record
        movers = sum(1 for lbl in labels if lbl != "Z")
        metric_rows.append(
            TickMetric(
                t=t,
                mean_nn_distance=_metrics.mean_nearest_neighbor_distance(agents, cfg.grid_size),
                decorrelation=_metrics.action_decorrelation(labels),
                movers=movers,
                fwd_passes=1,
            )
        )
        cells_history.append(cells.copy())

    return RunResult(
        config=cfg,
        metrics=metric_rows,
        initial_cells=initial_cells,
        initial_agents=initial_agents,
        final_cells=cells,
        final_agents=agents,
        cells_history=cells_history,
    )
