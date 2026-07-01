"""The tick loop.

Pulls together substrate + prompts + policy + step + metrics. Pure Python,
no torch. Drives a ``Policy`` (either ``MockPolicy`` for tests or
``LLMPolicy`` for the real run).

Per tick (PLAN.md §6 control flow):

1. Build per-agent prompts from local observations (I1, I11 via ``prompts``).
2. Call ``policy.step(prompts, rng)`` — ONE forward pass (I3).
3. Map action labels (``"S"`` / ``"M"``) to substrate verbs and apply
   synchronously (I2 via ``grid.step``).
4. Record a tick metric: same-color fraction, mover count, fwd-pass = 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from toy_v1 import actions, grid, metrics, prompts
from toy_v1.grid import Agent
from toy_v1.policy import Policy


@dataclass(slots=True)
class RunConfig:
    """One run's hyperparameters."""

    grid_size: int = 8
    n_agents: int = 30
    n_ticks: int = 40
    seed: int = 42


@dataclass(slots=True, frozen=True)
class TickMetric:
    """Per-tick observation row."""

    t: int
    same_color_fraction: float
    movers: int
    fwd_passes: int


@dataclass(slots=True)
class RunResult:
    """Trajectory of a single run."""

    config: RunConfig
    metrics: list[TickMetric] = field(default_factory=list)
    initial_cells: np.ndarray = field(default=None)  # type: ignore[assignment]
    initial_agents: list[Agent] = field(default_factory=list)
    final_cells: np.ndarray = field(default=None)  # type: ignore[assignment]
    final_agents: list[Agent] = field(default_factory=list)


def run(cfg: RunConfig, policy: Policy) -> RunResult:
    """Drive the tick loop for ``cfg.n_ticks`` ticks. Returns a ``RunResult``."""
    rng = np.random.default_rng(cfg.seed)

    cells, agents = grid.init_state(
        size=cfg.grid_size, n_agents=cfg.n_agents, rng=rng,
    )
    # Snapshot the initial state for the caller; the runner mutates copies
    # internally via grid.step (which itself never mutates its inputs).
    initial_cells = cells.copy()
    initial_agents = [Agent(id=a.id, row=a.row, col=a.col, color=a.color) for a in agents]

    tick_metrics: list[TickMetric] = []

    for t in range(cfg.n_ticks):
        # 1. Observe (locality enforced inside prompts.render_full → I1, I11)
        batch_prompts = [prompts.render_full(a, cells) for a in agents]

        # 2. Decide — ONE batched forward pass (I3, I4)
        labels = policy.step(batch_prompts, rng=rng)

        # 3. Apply — substrate semantics + synchronous step (I2)
        verbs = [actions.to_verb(L) for L in labels]
        cells, agents = grid.step(cells, agents, verbs, rng=rng)

        # 4. Metric
        tick_metrics.append(
            TickMetric(
                t=t,
                same_color_fraction=metrics.same_color_fraction(cells, agents),
                movers=sum(1 for v in verbs if v == "MOVE"),
                fwd_passes=1,
            )
        )

    return RunResult(
        config=cfg,
        metrics=tick_metrics,
        initial_cells=initial_cells,
        initial_agents=initial_agents,
        final_cells=cells,
        final_agents=agents,
    )
