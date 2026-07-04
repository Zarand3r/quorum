"""Windowed neighbor attention — the coupling operator (M2.1, PLAN.md §9.4/§10.5).

Every cell emits a ligand (query) and receptor (key) per direction and a value.
Compatibility κ between cell i's ligand toward direction d and the neighbor's
receptor pointing back gives softmax weights α over the 4 neighbors; the message
m aggregates neighbor values. Toroidal grid via ``np.roll`` (periodic), so the
same weights drive conserved advection (M2.2) with no boundary loss.

The only loop is over the 4 directions (a constant, O(1) in grid size) — each
iteration is a whole-grid vectorized op, so there is no per-cell loop (I6/Q4).
"""

from __future__ import annotations

import numpy as np

from model.config import ModelConfig
from model.genome import Genome

# von-Neumann offsets: 0=up 1=down 2=left 3=right, and the opposite-direction map.
DIRS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
OPP: tuple[int, ...] = (1, 0, 3, 2)


def _gather(field: np.ndarray, off: tuple[int, int]) -> np.ndarray:
    """Value of the neighbor in direction ``off`` brought to each cell (periodic)."""
    return np.roll(field, shift=(-off[0], -off[1]), axis=(0, 1))


def interface_heads(
    hidden: np.ndarray, g: Genome
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ligand[H,W,D,F], receptor[H,W,D,F], value[H,W,C]) from the hidden field."""
    ligand = np.einsum("hwc,cdf->hwdf", hidden, g.W_lig)
    receptor = np.einsum("hwc,cdf->hwdf", hidden, g.W_rec)
    value = np.einsum("hwc,ce->hwe", hidden, g.W_val)
    return ligand, receptor, value


def neighbor_attention(
    ligand: np.ndarray, receptor: np.ndarray, value: np.ndarray, cfg: ModelConfig
) -> tuple[np.ndarray, np.ndarray]:
    """Return (alpha[H,W,D] softmax over directions, message[H,W,C])."""
    h, w, d, _ = ligand.shape
    kappa = np.empty((h, w, d))
    value_nb = np.empty((h, w, d, value.shape[-1]))
    for k in range(d):
        off = DIRS[k]
        receptor_back = _gather(receptor[:, :, OPP[k], :], off)  # neighbor's key toward i
        diff = ligand[:, :, k, :] - receptor_back
        kappa[:, :, k] = (cfg.bind_bias - np.sum(diff * diff, axis=-1)) / cfg.bind_temperature
        value_nb[:, :, k, :] = _gather(value, off)

    kappa -= kappa.max(axis=-1, keepdims=True)  # softmax over directions (stable)
    ex = np.exp(kappa)
    alpha = ex / ex.sum(axis=-1, keepdims=True)
    message = np.einsum("hwd,hwde->hwe", alpha, value_nb)
    return alpha, message
