"""Substrate: state layout + channel readouts (IMPLEMENTATION_PLAN.md Step 1).

The dish is the set of `N` agent embeddings `X ∈ ℝ^{N×d}`. Channels split into
position (first two — where the agent sits, used by the distance penalty and the
renderer), shape (the grounded contour `C = X·W_c`, drawn as a blob and *equal to*
the attention query), and hidden (working memory). `W_c` is a fixed selection
matrix (see block.make_weights), so `contour_coeffs` literally returns the shape
channels — grounding is structural, not a coincidence of a shared matrix.
"""

from __future__ import annotations

import numpy as np

from config import POS_DIM, VivariumConfig
from rng import base_rng


def init_state(cfg: VivariumConfig, seed: int) -> np.ndarray:
    """Initial embeddings. Positions are spread; other channels are small noise."""
    rng = base_rng(seed)
    X = rng.standard_normal((cfg.N, cfg.d)).astype(np.float64)
    X[:, :POS_DIM] *= 2.0  # spread the initial layout so neighbourhoods are meaningful
    return X


def positions(X: np.ndarray) -> np.ndarray:
    """The 2-D position channels (a view of the first two columns)."""
    return X[:, :POS_DIM]


def contour_coeffs(X: np.ndarray, W_c: np.ndarray) -> np.ndarray:
    """The grounded contour coefficients `C = X·W_c` — the attention query and the
    drawn blob, one and the same array."""
    return X @ W_c
