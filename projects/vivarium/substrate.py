"""Substrate: initial state (dock-and-morph).

Channel views (`positions`, `morph_state`, `contour_coeffs`) live in `block.py`
next to the dynamics that use them; this module just seeds the initial dish.
"""

from __future__ import annotations

import numpy as np

from config import POS_DIM, VivariumConfig
from rng import base_rng


def init_state(cfg: VivariumConfig, seed: int) -> np.ndarray:
    """Initial embeddings: positions spread across the dish, morph channels small noise."""
    rng = base_rng(seed)
    X = np.zeros((cfg.N, cfg.d), dtype=np.float64)
    X[:, :POS_DIM] = rng.uniform(-0.5 * cfg.pos_bound, 0.5 * cfg.pos_bound, (cfg.N, POS_DIM))
    X[:, POS_DIM:] = rng.standard_normal((cfg.N, cfg.d - POS_DIM)) * 0.5
    return X
