"""Policies map state → actions (IMPLEMENTATION_PLAN.md Steps 5, 7).

A policy returns ``(dx, gate, transfer)``:
  - ``dx`` [N, d]      : requested displacement this tick (costs c_move·||dx||²)
  - ``gate`` [N]       : harvest intent in [0, 1]
  - ``transfer`` [N,N] : energy sent i→j this tick (row sums ≤ e_i, diag 0)

E0 ships ``hand_forager`` (greedy, no interaction) and ``frozen`` (the starvation
control). E1's attention policy lives in eco/interaction.py; the hand-forager
survives as the E2 baseline/control.
"""

from __future__ import annotations

import numpy as np

from eco.config import EcoConfig
from eco.state import EcoState


def hand_forager(state: EcoState, cfg: EcoConfig):
    """Greedy chase: step toward the source, clipped to ``max_step``; always harvest."""
    step = cfg.forager_gain * (state.mu[None, :] - state.x)      # [N, d] toward source
    norm = np.linalg.norm(step, axis=1, keepdims=True)           # [N, 1]
    scale = np.minimum(1.0, cfg.max_step / np.maximum(norm, 1e-12))
    dx = step * scale
    gate = np.ones(state.n, dtype=np.float64)
    return dx, gate, np.zeros((state.n, state.n))


def frozen(state: EcoState, cfg: EcoConfig):
    """Control policy: never move, always harvest — starves under any drift (P8)."""
    dx = np.zeros((state.n, cfg.d), dtype=np.float64)
    gate = np.ones(state.n, dtype=np.float64)
    return dx, gate, np.zeros((state.n, state.n))
