"""The dock-and-morph block (substrate).

`forward(X, θ, cfg)` is a **pure function**. It splits each agent's embedding into
position `p` (first two channels) and a morphing sub-embedding `z` (the rest), and
advances them by two coupled but distinct mechanisms:

  * **Motion** — position moves by **neighbour forces**: attract toward
    complementary (attention-weighted) neighbours, repel at short range. With no
    neighbours (the identity ablation) there is **no force**, so an agent does not
    move — interaction is load-bearing for the dynamics *by construction* (P6).
  * **Morph** — the sub-embedding `z` (shape + hidden) is updated by the transformer
    block (message + MLP + LayerNorm): induced-fit conformational change. The drawn
    contour `C = z·W_c` is the attention query, so the blob *is* the interaction (P8).

Attention is local (k-NN by position) and grounded (dock = contour overlap
`⟨C_i, C_j·M⟩`); k-NN ties break by index (P4). Positions are clipped to the dish
(P7). No learning here — the rule is fixed on the fast clock.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import POS_DIM, VivariumConfig
from rng import base_rng, rng_for

_MLP_HIDDEN_FACTOR = 2
_LN_EPS = 1e-5
_REPEL_EPS = 1e-3  # softening so coincident agents don't produce infinite repulsion


@dataclass(frozen=True)
class Weights:
    """The block's fixed parameters θ (all structural / fixed on the fast clock)."""

    W_c: np.ndarray  # (z_dim, 2K) selection: extracts z's shape channels → contour = query
    M: np.ndarray    # (2K, 2K) fixed π-rotation complementarity metric (diagonal ±1)
    W_v: np.ndarray  # (z_dim, z_dim) value projection (morph message)
    W1: np.ndarray   # (z_dim, h) MLP in
    b1: np.ndarray   # (h,)
    W2: np.ndarray   # (h, z_dim) MLP out
    b2: np.ndarray   # (z_dim,)
    J_spin: np.ndarray  # (z_dim, z_dim) fixed skew-symmetric → non-settling morph rotation

    @staticmethod
    def array_names() -> tuple[str, ...]:
        return ("W_c", "M", "W_v", "W1", "b1", "W2", "b2", "J_spin")


def make_weights(cfg: VivariumConfig, seed: int) -> Weights:
    rng = base_rng(seed + 1)
    z, twoK, h = cfg.z_dim, cfg.shape_dim, _MLP_HIDDEN_FACTOR * cfg.z_dim

    # W_c selects z's shape channels (the first 2K of z): C = z·W_c = z[:, :2K].
    W_c = np.zeros((z, twoK), dtype=np.float64)
    W_c[:twoK, :] = np.eye(twoK)

    signs = np.array([(-1.0) ** (k + 1) for k in range(cfg.n_harmonics) for _ in range(2)])
    M = np.diag(signs)

    W_v = rng.standard_normal((z, z)) / np.sqrt(z)
    W1 = rng.standard_normal((z, h)) / np.sqrt(z)
    b1 = np.zeros(h)
    W2 = rng.standard_normal((h, z)) / np.sqrt(h)
    b2 = np.zeros(z)
    # skew-symmetric ⇒ non-gradient rotation on z: the morph never settles (Helmholtz).
    J_raw = rng.standard_normal((z, z)) / np.sqrt(z)
    J_spin = J_raw - J_raw.T
    return Weights(W_c=W_c, M=M, W_v=W_v, W1=W1, b1=b1, W2=W2, b2=b2, J_spin=J_spin)


# --- channel views ------------------------------------------------------------
def positions(X: np.ndarray) -> np.ndarray:
    return X[:, :POS_DIM]


def morph_state(X: np.ndarray) -> np.ndarray:
    """The morphing sub-embedding z = shape + hidden (everything but position)."""
    return X[:, POS_DIM:]


def contour_coeffs(z: np.ndarray, W_c: np.ndarray) -> np.ndarray:
    """Grounded contour C = z·W_c — the attention query and the drawn blob."""
    return z @ W_c


# --- attention (attract graph) ------------------------------------------------
def neighbor_indices(pos: np.ndarray, k: int) -> np.ndarray:
    diff = pos[:, None, :] - pos[None, :, :]
    d2 = np.einsum("ijc,ijc->ij", diff, diff)
    return np.argsort(d2, axis=1, kind="stable")[:, :k]


def _softmax_masked(score: np.ndarray) -> np.ndarray:
    m = np.max(score, axis=1, keepdims=True)
    e = np.exp(score - m)
    return e / e.sum(axis=1, keepdims=True)


def attention_matrix(X: np.ndarray, w: Weights, cfg: VivariumConfig) -> np.ndarray:
    """Row-stochastic local complementarity attention `A` (N, N); zero off the k-NN support."""
    pos = positions(X)
    C = contour_coeffs(morph_state(X), w.W_c)
    Kmat = C @ w.M
    dock = (C @ Kmat.T) / np.sqrt(cfg.shape_dim)
    diff = pos[:, None, :] - pos[None, :, :]
    d2 = np.einsum("ijc,ijc->ij", diff, diff)
    score = dock - cfg.dist_lambda * d2
    idx = neighbor_indices(pos, cfg.n_neighbors)
    mask = np.zeros_like(score, dtype=bool)
    np.put_along_axis(mask, idx, True, axis=1)
    return _softmax_masked(np.where(mask, score, -np.inf))


def ablate_attention(A: np.ndarray, mode: str, seed: int, tick: int) -> np.ndarray:
    """P6 control arms: none / identity (self only → no neighbour forces) / shuffle."""
    if mode == "none":
        return A
    if mode == "identity":
        return np.eye(A.shape[0])
    if mode == "shuffle":
        perm = rng_for(seed, tick).permutation(A.shape[0])
        return A[:, perm]
    raise ValueError(f"unknown ablation mode: {mode!r}")


# --- forces (motion) ----------------------------------------------------------
def position_force(pos: np.ndarray, A: np.ndarray, cfg: VivariumConfig) -> np.ndarray:
    """Neighbour force on each agent: attract toward complementary neighbours + short-range
    repel. Both derive from the interaction graph `A`, so with no neighbours (A = I) the
    force is zero (P6). (N, 2)."""
    # attract: toward attention-weighted neighbour centroid — (A − I)·p.
    attract = A @ pos - pos
    # repel: short-range (1/d²) push, over the attention support only (so identity ⇒ none).
    diff = pos[:, None, :] - pos[None, :, :]            # (N, N, 2) = p_i − p_j
    d2 = np.einsum("ijc,ijc->ij", diff, diff) + _REPEL_EPS
    support = (A > 0.0).astype(np.float64)
    np.fill_diagonal(support, 0.0)                       # never repel from self
    weight = support / d2                                # (N, N)
    repel = np.einsum("ij,ijc->ic", weight, diff)
    return cfg.force_attract * attract + cfg.force_repel * repel


# --- morph --------------------------------------------------------------------
def _layernorm(Z: np.ndarray) -> np.ndarray:
    mu = Z.mean(axis=1, keepdims=True)
    var = Z.var(axis=1, keepdims=True)
    return (Z - mu) / np.sqrt(var + _LN_EPS)


def _mlp(Z: np.ndarray, w: Weights) -> np.ndarray:
    return np.tanh(Z @ w.W1 + w.b1) @ w.W2 + w.b2


def forward_verbose(
    X: np.ndarray,
    w: Weights,
    cfg: VivariumConfig,
    ablate: str = "none",
    seed: int = 0,
    tick: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """One dock-and-morph step. Returns (X_next, A). Pure."""
    A = ablate_attention(attention_matrix(X, w, cfg), ablate, seed, tick)
    p, z = positions(X), morph_state(X)

    # motion: position by neighbour forces, clipped to the dish (P7).
    p_next = np.clip(p + position_force(p, A, cfg), -cfg.pos_bound, cfg.pos_bound)

    # morph: z updated by the block (message + MLP + LayerNorm), with a skew rotation so
    # the shape never settles → complementarity C keeps shifting → forces keep driving motion.
    spin = cfg.morph_spin * (z @ w.J_spin) if cfg.morph_spin > 0.0 else 0.0
    msg = A @ (z @ w.W_v)
    z1 = _layernorm(z + msg + spin)
    z2 = _layernorm(z1 + _mlp(z1, w))

    return np.concatenate([p_next, z2], axis=1), A


def forward(X: np.ndarray, w: Weights, cfg: VivariumConfig) -> np.ndarray:
    return forward_verbose(X, w, cfg)[0]
