"""Pointwise reaction F_θ — the difference-amplifying term (M2.3, PLAN.md §10.5).

A small per-cell MLP mapping ``concat(hidden, message, mass)`` → Δhidden. This is
the nonlinear local transformation that morphs a cell's state (and, being
nonlinear, is the analogue of Gray-Scott autocatalysis `+uv²` that can *amplify*
rather than smooth). Applied identically at every cell (shared genome), fully
vectorized.
"""

from __future__ import annotations

import numpy as np

from model.config import ModelConfig
from model.genome import Genome


def reaction(
    hidden: np.ndarray, message: np.ndarray, mass: np.ndarray, g: Genome, cfg: ModelConfig
) -> np.ndarray:
    """Δhidden[H,W,C] from the per-cell reaction MLP."""
    x = np.concatenate([hidden, message, mass[..., None]], axis=-1)  # [H,W,2C+1]
    hidden1 = np.tanh(x @ g.W1 + g.b1)                                # [H,W,M]
    delta = hidden1 @ g.W2 + g.b2                                     # [H,W,C]
    return cfg.reaction_scale * delta
