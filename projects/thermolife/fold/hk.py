"""Bounded-confidence (Hegselmann–Krause) attention variants — the HK study.

Replaces global row-softmax with LOCAL interaction: each token aggregates only
over a *confidence set* of others, selected by a score threshold. Variants along
two axes:

  space:  where the confidence set lives
    - "dock": the complementarity metric — s_ij = ⟨C_i, C_j·M⟩/√2K, the SAME
      grounded docking score the softmax fold uses (J1/J6 preserved). τ = 0 is
      the principled default: interact iff net-complementary.
    - "raw" : classic HK similarity — s_ij = −‖x_i − x_j‖², threshold −ε².
      Included as the literature-faithful control; note it clusters *identical*
      tokens, which fights the ligand/receptor thesis.

  kernel: how the set aggregates
    - "hard"    : classic HK — uniform average over the confidence set
                  (self always included ⇒ no empty rows).
    - "soft"    : softmax restricted to the confidence set (masked softmax).
    - "sigmoid" : differentiable relaxation — g_ij = σ((s_ij−τ)/temp) gates
                  exp(s); trainable (no dead gradients at the boundary), and
                  → "soft" as temp → 0. This is the training variant.

All fully vectorized (J3), synchronous (J4).
"""

from __future__ import annotations

import numpy as np

from fold.config import FoldConfig
from fold.interface import contour_coeffs
from fold.weights import FoldWeights


def dock_scores(c: np.ndarray, m_metric: np.ndarray) -> np.ndarray:
    """Grounded complementarity scores s_ij = ⟨C_i, C_j·M⟩/√2K (= softmax fold's)."""
    key = c @ m_metric
    return (c @ key.T) / np.sqrt(c.shape[1])


def raw_scores(x: np.ndarray) -> np.ndarray:
    """Classic-HK similarity scores: negative squared distance in state space."""
    d2 = np.sum(x * x, axis=1, keepdims=True)
    return -(d2 + d2.T - 2.0 * (x @ x.T))


def hk_attention(
    scores: np.ndarray,
    tau: float,
    kernel: str = "hard",
    temp: float = 0.1,
) -> np.ndarray:
    """Row-stochastic interaction matrix from scores under a confidence rule.

    Self is always in the confidence set (diagonal forced) so no row is empty —
    a token with no partners simply keeps its own state (classic HK convention).
    """
    n = scores.shape[0]
    eye = np.eye(n, dtype=bool)
    if kernel == "hard":
        mask = (scores > tau) | eye
        a = mask.astype(np.float64)
        return a / a.sum(axis=1, keepdims=True)
    if kernel == "soft":
        mask = (scores > tau) | eye
        s = np.where(mask, scores, -np.inf)
        s = s - s.max(axis=1, keepdims=True)
        e = np.exp(s)
        return e / e.sum(axis=1, keepdims=True)
    if kernel == "sigmoid":
        gate = 1.0 / (1.0 + np.exp(-(scores - tau) / temp))
        gate = np.where(eye, np.maximum(gate, 1e-3), gate)  # self never fully gated out
        s = scores - scores.max(axis=1, keepdims=True)
        e = gate * np.exp(s)
        return e / e.sum(axis=1, keepdims=True)
    raise ValueError(f"unknown kernel: {kernel}")


def hk_block_step(
    x: np.ndarray,
    w: FoldWeights,
    cfg: FoldConfig,
    *,
    space: str = "dock",
    tau: float = 0.0,
    kernel: str = "hard",
    temp: float = 0.1,
    use_ln: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One fold iteration with bounded-confidence attention.

    Mirrors fold.transformer.block_step (residual + LN + optional MLP) with A
    swapped for the HK variant. use_ln=False additionally strips residual+LN+MLP
    down to pure averaging x ← A·x — the literal Hegselmann–Krause update, kept
    as the theoretical sanity anchor.
    """
    c = contour_coeffs(x, w)
    if space == "dock":
        s = dock_scores(c, w.M)
    elif space == "raw":
        s = raw_scores(x)
    else:
        raise ValueError(f"unknown space: {space}")
    a = hk_attention(s, tau, kernel=kernel, temp=temp)

    if not use_ln:                      # classic HK: consensus averaging, no dressing
        return a @ x, c, a

    from fold.transformer import _layernorm  # same normalization as the softmax fold

    x1 = _layernorm(x + a @ (x @ w.W_v))
    if cfg.use_mlp:
        hidden = np.maximum(0.0, x1 @ w.W1 + w.b1)
        x1 = _layernorm(x1 + hidden @ w.W2 + w.b2)
    return x1, c, a


# ---- dynamics metrics (measured, never rewarded — E2/P2 discipline) ----------


def cluster_count(x: np.ndarray, link_eps: float = 0.5) -> int:
    """Single-linkage cluster count: connected components of the ε-proximity
    graph, by boolean transitive closure (vectorized; fine for N ≤ a few hundred)."""
    d2 = np.sum(x * x, axis=1, keepdims=True)
    adj = (d2 + d2.T - 2.0 * (x @ x.T)) < link_eps * link_eps
    reach = adj
    for _ in range(int(np.ceil(np.log2(max(x.shape[0], 2))))):
        reach = reach | (reach @ reach)
    # rows with identical reachability sets belong to one component
    return int(np.unique(reach, axis=0).shape[0])


def effective_rank(x: np.ndarray, var_tol: float = 1e-6) -> float:
    """Participation ratio of covariance eigenvalues: (Σλ)²/Σλ² ∈ [1, d].

    PR alone measures *directional* structure, not magnitude — a cloud collapsed
    to a point with isotropic numerical residue would score ≈ d. So a cloud whose
    total variance is below ``var_tol`` is reported as rank 1 (collapsed); above
    it, PR measures how many directions the spread genuinely occupies."""
    xc = x - x.mean(axis=0, keepdims=True)
    lam = np.maximum(np.linalg.eigvalsh(np.cov(xc.T)), 0.0)
    s = lam.sum()
    if s < var_tol:
        return 1.0
    return float(s * s / np.sum(lam * lam))


def spread(x: np.ndarray) -> float:
    """Mean pairwise distance (0 under total collapse)."""
    d2 = np.sum(x * x, axis=1, keepdims=True)
    dist2 = np.maximum(d2 + d2.T - 2.0 * (x @ x.T), 0.0)
    n = x.shape[0]
    off = ~np.eye(n, dtype=bool)
    return float(np.sqrt(dist2[off]).mean())
