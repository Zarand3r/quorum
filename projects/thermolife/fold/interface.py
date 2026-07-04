"""Grounded contour geometry (PLAN.md §4a, invariant J1).

A token's contour coefficients ``C = X·W_c`` are read as the Fourier coefficients
of a closed radial blob ``r(θ) = ρ₀ + Σ_k (a_k cos kθ + b_k sin kθ)``. By
Parseval, the L2 overlap of two such radial profiles equals the dot product of
their coefficient vectors — which is exactly the (pre-softmax) attention score
(J6). So the drawn shape *is* the query/key; nothing here reads anything but C.
"""

from __future__ import annotations

import numpy as np

from fold.config import FoldConfig
from fold.weights import FoldWeights


def contour_coeffs(x: np.ndarray, w: FoldWeights) -> np.ndarray:
    """[N,d] embeddings → [N,2K] contour coefficients (= attention query)."""
    return x @ w.W_c


def _angles_basis(cfg: FoldConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    theta = np.linspace(0.0, 2.0 * np.pi, cfg.contour_points, endpoint=False)
    kk = np.arange(1, cfg.k_harmonics + 1)
    ang = np.outer(theta, kk)  # [P, K]
    return theta, np.cos(ang), np.sin(ang)


def contour_radii(c: np.ndarray, cfg: FoldConfig, clamp: bool = True):
    """[N,2K] coeffs → (theta[P], r[N,P]) radial profile of each blob."""
    theta, cos, sin = _angles_basis(cfg)
    a = c[:, 0::2]  # [N,K] cos coeffs
    b = c[:, 1::2]  # [N,K] sin coeffs
    r = cfg.rho0 + cfg.amp * (a @ cos.T + b @ sin.T)  # [N,P]
    if clamp:
        r = np.maximum(r, cfg.r_min)
    return theta, r


def contour_polylines(c: np.ndarray, cfg: FoldConfig) -> np.ndarray:
    """[N,2K] coeffs → [N,P,2] blob outline points, relative to the token center."""
    theta, r = contour_radii(c, cfg)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.stack([x, y], axis=-1) * cfg.render_scale
