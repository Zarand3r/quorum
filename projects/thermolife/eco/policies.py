"""Policies map state → actions (IMPLEMENTATION_PLAN.md Step 5).

A policy returns ``(dx, gate)``:
  - ``dx`` [N, d]  : requested displacement this tick (costs c_move·||dx||²)
  - ``gate`` [N]   : harvest intent in [0, 1]

E0 ships ``hand_forager`` — greedy, vectorized, no learning. E1 (Step 7) swaps in an
attention policy with the same signature; the hand-forager survives as a baseline/control.
"""

from __future__ import annotations

import numpy as np

from eco.config import EcoConfig
from eco.state import EcoState


def hand_forager(state: EcoState, cfg: EcoConfig) -> tuple[np.ndarray, np.ndarray]:
    """Greedy chase: step toward the source, clipped to ``max_step``; always harvest."""
    step = cfg.forager_gain * (state.mu[None, :] - state.x)      # [N, d] toward source
    norm = np.linalg.norm(step, axis=1, keepdims=True)           # [N, 1]
    scale = np.minimum(1.0, cfg.max_step / np.maximum(norm, 1e-12))
    dx = step * scale
    gate = np.ones(state.n, dtype=np.float64)
    return dx, gate


def frozen(state: EcoState, cfg: EcoConfig) -> tuple[np.ndarray, np.ndarray]:
    """Control policy: never move, always harvest — starves under any drift (P8)."""
    dx = np.zeros((state.n, cfg.d), dtype=np.float64)
    gate = np.ones(state.n, dtype=np.float64)
    return dx, gate
