"""The interaction block: one weight-tied transformer block (IMPLEMENTATION_PLAN.md Step 1).

`forward(X, θ, cfg)` is a **pure function** — it reads the weights, never writes
them (P9/P2). Attention is **local** (k-NN by position) and **grounded** (the dock
score is contour overlap `⟨C_i, C_j·M⟩`, exactly the drawn shapes). The distance
penalty `−λ‖Δp‖²` makes locality physical; k-NN ties break by index (P4).

    C = X·W_c ;  Q = C ;  K = C·M ;  V = X·W_v
    s_ij = ⟨Q_i, K_j⟩/√(2K) − λ‖p_i − p_j‖²   (masked to i's k-NN)
    X ← LN(X + softmax(s)·V) ; X ← LN(X + MLP(X))
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import POS_DIM, VivariumConfig
from rng import base_rng
from substrate import contour_coeffs, positions

_MLP_HIDDEN_FACTOR = 2  # MLP hidden width = factor · d
_LN_EPS = 1e-5


@dataclass(frozen=True)
class Weights:
    """The block's parameters θ. `W_c` and `M` are fixed structural maps; `W_v`
    and the MLP are random. At M0 nothing updates them; M1 will."""

    W_c: np.ndarray  # (d, 2K) selection: extracts the shape channels → contour = query
    M: np.ndarray    # (2K, 2K) fixed π-rotation complementarity metric (diagonal ±1)
    W_v: np.ndarray  # (d, d) value projection
    W1: np.ndarray   # (d, h) MLP in
    b1: np.ndarray   # (h,)
    W2: np.ndarray   # (h, d) MLP out
    b2: np.ndarray   # (d,)

    @staticmethod
    def array_names() -> tuple[str, ...]:
        return ("W_c", "M", "W_v", "W1", "b1", "W2", "b2")


def make_weights(cfg: VivariumConfig, seed: int) -> Weights:
    # a weight stream decorrelated from the state-init stream (base_rng(seed)).
    rng = base_rng(seed + 1)
    d, twoK, h = cfg.d, cfg.shape_dim, _MLP_HIDDEN_FACTOR * cfg.d

    # W_c selects the shape channels: C = X·W_c = X[:, pos:pos+2K].
    W_c = np.zeros((d, twoK), dtype=np.float64)
    W_c[POS_DIM : POS_DIM + twoK, :] = np.eye(twoK)

    # M: π-rotation → harmonic k's (cos, sin) pair scaled by (−1)^k (a bump meets a pocket).
    signs = np.array([(-1.0) ** (k + 1) for k in range(cfg.n_harmonics) for _ in range(2)])
    M = np.diag(signs)

    W_v = rng.standard_normal((d, d)) / np.sqrt(d)
    W1 = rng.standard_normal((d, h)) / np.sqrt(d)
    b1 = np.zeros(h)
    W2 = rng.standard_normal((h, d)) / np.sqrt(h)
    b2 = np.zeros(d)
    return Weights(W_c=W_c, M=M, W_v=W_v, W1=W1, b1=b1, W2=W2, b2=b2)


def neighbor_indices(pos: np.ndarray, k: int) -> np.ndarray:
    """(N, k) indices of each agent's k nearest neighbours by position, self included,
    with **index-stable tie-breaking** (P4)."""
    diff = pos[:, None, :] - pos[None, :, :]
    d2 = np.einsum("ijc,ijc->ij", diff, diff)  # (N, N) squared distances
    return np.argsort(d2, axis=1, kind="stable")[:, :k]


def _squared_dists(pos: np.ndarray) -> np.ndarray:
    diff = pos[:, None, :] - pos[None, :, :]
    return np.einsum("ijc,ijc->ij", diff, diff)


def _softmax_masked(score: np.ndarray) -> np.ndarray:
    # rows always contain self (a finite entry), so the row-max is finite.
    m = np.max(score, axis=1, keepdims=True)
    e = np.exp(score - m)  # masked -inf entries → 0
    return e / e.sum(axis=1, keepdims=True)


def attention_matrix(X: np.ndarray, w: Weights, cfg: VivariumConfig) -> np.ndarray:
    """Row-stochastic local attention `A` (N, N): zero off the k-NN support."""
    pos = positions(X)
    C = contour_coeffs(X, w.W_c)          # Q
    Kmat = C @ w.M                         # K = C·M
    dock = (C @ Kmat.T) / np.sqrt(cfg.shape_dim)
    d2 = _squared_dists(pos)
    score = dock - cfg.dist_lambda * d2

    idx = neighbor_indices(pos, cfg.n_neighbors)
    mask = np.zeros_like(score, dtype=bool)
    np.put_along_axis(mask, idx, True, axis=1)
    score = np.where(mask, score, -np.inf)
    return _softmax_masked(score)


def _layernorm(X: np.ndarray) -> np.ndarray:
    mu = X.mean(axis=1, keepdims=True)
    var = X.var(axis=1, keepdims=True)
    return (X - mu) / np.sqrt(var + _LN_EPS)


def _mlp(X: np.ndarray, w: Weights) -> np.ndarray:
    return np.tanh(X @ w.W1 + w.b1) @ w.W2 + w.b2


def forward(X: np.ndarray, w: Weights, cfg: VivariumConfig) -> np.ndarray:
    """One block application. Pure: returns a new array, mutates neither X nor θ."""
    A = attention_matrix(X, w, cfg)
    msg = A @ (X @ w.W_v)
    X1 = _layernorm(X + msg)
    X2 = _layernorm(X1 + _mlp(X1, w))
    return X2
