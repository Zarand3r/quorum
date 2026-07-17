"""Render / snapshot surface (IMPLEMENTATION_PLAN.md Step 1).

Strictly read-only (P5) and **grounded** (P8): `token_contours` reads the drawn
contour as `X·W_c` using the block's *own* `W_c` — the blob is the attention
query, not a decorative overlay. `snapshot` packages positions, contours, and
the local interaction edges for the viewer.
"""

from __future__ import annotations

import numpy as np

from block import Weights, neighbor_indices
from config import VivariumConfig
from substrate import contour_coeffs, positions


def idle_snapshot() -> dict:
    """A mode-agnostic empty snapshot (no agents yet)."""
    return {"status": "idle", "tick": 0, "n": 0, "tokens": [], "edges": []}


def token_contours(X: np.ndarray, w: Weights) -> np.ndarray:
    """The contour coefficients the renderer draws — `X·W_c`, the block's own `W_c` (P8)."""
    return contour_coeffs(X, w.W_c)


def snapshot(X: np.ndarray, w: Weights, cfg: VivariumConfig, tick: int) -> dict:
    """Read-only snapshot: positions + grounded contours + local edges."""
    pos = positions(X)
    C = token_contours(X, w)
    tokens = [
        {"x": float(pos[i, 0]), "y": float(pos[i, 1]), "c": C[i].tolist()}
        for i in range(cfg.N)
    ]
    idx = neighbor_indices(pos, cfg.n_neighbors)
    edges = [
        [int(i), int(j)]
        for i in range(cfg.N)
        for j in idx[i]
        if int(j) != i
    ]
    return {"status": "running", "tick": tick, "n": cfg.N, "tokens": tokens, "edges": edges}
