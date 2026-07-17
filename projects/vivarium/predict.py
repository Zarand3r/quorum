"""Prediction readout (IMPLEMENTATION_PLAN.md Step 2; invariant P9).

The "prediction" is a **linear readout of the block's own message** — not a
separate network. `observe` extracts the observable channels (position + shape:
what an agent can see about its neighbours; hidden channels stay private, which
is what makes the one-step target non-degenerate). No classes, no `nn`, no
auxiliary weights beyond `W_p ∈ θ`.
"""

from __future__ import annotations

import numpy as np

from config import VivariumConfig


def obs_dim(cfg: VivariumConfig) -> int:
    """Observable width: position + shape channels (hidden is private)."""
    return cfg.pos_dim + cfg.shape_dim


def observe(X: np.ndarray, cfg: VivariumConfig) -> np.ndarray:
    """The observable channels of each agent (position + shape)."""
    return X[:, : obs_dim(cfg)]


def predict(msg: np.ndarray, W_p: np.ndarray) -> np.ndarray:
    """Predict the neighbourhood's next observable from the message: a linear readout."""
    return msg @ W_p
