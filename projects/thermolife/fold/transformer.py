"""The weight-tied attention block — one fold iteration (PLAN.md §4c).

Fully vectorized over the N tokens (batched matmuls, no per-token loop, J3) and
synchronous (reads X, returns a fresh X, J4). The query/key come from the
grounded contour readout, so attention is literally contour overlap.
"""

from __future__ import annotations

import numpy as np

from fold.config import FoldConfig
from fold.interface import contour_coeffs
from fold.weights import FoldWeights


def _softmax_rows(s: np.ndarray) -> np.ndarray:
    s = s - s.max(axis=1, keepdims=True)
    e = np.exp(s)
    return e / e.sum(axis=1, keepdims=True)


def _layernorm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mu = x.mean(axis=1, keepdims=True)
    var = x.var(axis=1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps)


def attention(x: np.ndarray, w: FoldWeights, cfg: FoldConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return (C[N,2K] contour coeffs = query, A[N,N] softmax attention)."""
    c = contour_coeffs(x, w)          # ligand / query
    key = c @ w.M                     # receptor / key (π-rotated contour)
    scores = (c @ key.T) / np.sqrt(c.shape[1])
    return c, _softmax_rows(scores)


def block_step(
    x: np.ndarray, w: FoldWeights, cfg: FoldConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One fold iteration. Returns (new_X, C used, A used)."""
    c, a = attention(x, w, cfg)
    value = x @ w.W_v
    x1 = _layernorm(x + a @ value)
    if cfg.use_mlp:
        hidden = np.maximum(0.0, x1 @ w.W1 + w.b1)
        x1 = _layernorm(x1 + hidden @ w.W2 + w.b2)
    return x1, c, a
