"""E1 — the transformer interaction operator (IMPLEMENTATION_PLAN.md Step 7).

Replaces the hand-forager: each tick, tokens interact through **bounded-confidence
dock attention** (fold/hk.py — the operator chosen by the HK study, RESEARCH_HK.md:
in this gradient-free regime collapse-resistance is what a living population needs)
and an MLP head decodes the three actions (move / harvest / transfer).

Groundedness (P7): a token's interface coefficients are C_i = x_i·W_c + g_i·G_c —
the **gene modulates the binding surface**. The same C is (a) what a renderer draws
as the token's contour blob and (b) the Q/K that decides who interacts with whom.
Selection acting on g literally reshapes the drawn surface and the interaction graph
together.

θ (all matrices here) is FIXED at construction from a seed — the shared chemistry.
Genes g are per-token state and evolve by reproduction-mutation (E3); θ never does.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from eco.config import EcoConfig
from eco.state import EcoState
from fold.hk import distance_penalized_scores, dock_scores, hk_attention


@dataclass
class EcoWeights:
    """Fixed chemistry: interface readout + value + action head."""
    W_c: np.ndarray   # [d, 2K]    embedding → contour coeffs (query/ligand)
    G_c: np.ndarray   # [d_g, 2K]  gene → contour bias (the evolvable surface)
    M: np.ndarray     # [2K, 2K]   complementarity metric (π-rotation, fixed)
    W_v: np.ndarray   # [d, d]     value (what a token communicates)
    W1: np.ndarray    # [3d+d_g+2, H]  action MLP (own + message + senses)
    b1: np.ndarray    # [H]
    W2: np.ndarray    # [H, d+2]   → (dx[d], harvest logit, transfer logit)
    b2: np.ndarray    # [d+2]

    @staticmethod
    def random(cfg: EcoConfig, k_harmonics: int, hidden: int, seed: int) -> "EcoWeights":
        rng = np.random.Generator(np.random.PCG64(seed))
        d, dg, k = cfg.d, cfg.d_g, k_harmonics
        s = 1.0 / np.sqrt(d)
        signs = np.array([(-1.0) ** i for i in range(1, k + 1)])
        in_dim = 3 * d + dg + 2
        return EcoWeights(
            W_c=rng.standard_normal((d, 2 * k)) * s,
            G_c=rng.standard_normal((dg, 2 * k)) * (1.0 / np.sqrt(dg)),
            M=np.diag(np.repeat(signs, 2)),
            W_v=rng.standard_normal((d, d)) * s,
            W1=rng.standard_normal((in_dim, hidden)) * (1.0 / np.sqrt(in_dim)),
            b1=np.zeros(hidden),
            W2=rng.standard_normal((hidden, d + 2)) * (1.0 / np.sqrt(hidden)),
            b2=np.zeros(d + 2),
        )


def interface_coeffs(x: np.ndarray, g: np.ndarray, w: EcoWeights) -> np.ndarray:
    """Grounded, gene-modulated binding surface: C = x·W_c + g·G_c (P7)."""
    return x @ w.W_c + g @ w.G_c


def _softmax(s: np.ndarray) -> np.ndarray:
    s = s - s.max(axis=1, keepdims=True)
    e = np.exp(s)
    return e / e.sum(axis=1, keepdims=True)


def interaction_graph(
    x: np.ndarray, g: np.ndarray, w: EcoWeights, cfg: EcoConfig, mode: str = "dist"
) -> np.ndarray:
    """The interaction operator (RESEARCH_HK.md decision).

    mode="dist" (DEFAULT): distance-penalized softmax A = softmax(dock − λ‖Δx‖²)
    — smooth physical locality, collapse-resistant AND gradient-trainable.
    mode="softmax": global softmax (ablation arm, collapse-prone).
    mode="hk": hard bounded-confidence (measured control only — untrainable)."""
    c = interface_coeffs(x, g, w)
    if mode == "dist":
        return _softmax(distance_penalized_scores(c, x, w.M, cfg.dist_lambda))
    if mode == "softmax":
        return _softmax(dock_scores(c, w.M))
    if mode == "hk":
        return hk_attention(dock_scores(c, w.M), tau=cfg.hk_tau, kernel="hard")
    raise ValueError(f"unknown interaction mode: {mode}")


def decode_actions(
    state: EcoState, a: np.ndarray, w: EcoWeights, cfg: EcoConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MLP head over (own state ‖ attention-aggregated message) → actions.

    Returns (dx [N,d], harvest gate [N] in [0,1], transfer matrix T [N,N] ≥ 0)
    where T[i,j] is energy sent i→j this tick, T row sums ≤ e_i (no overdraw:
    the sender fraction is bounded by transfer_frac_max < 1), diag(T) = 0.

    Senses (the plan's "resource it can sense locally"): each token reads its
    LOCAL access weight w_i and its gradient ∇w (chemotaxis) — without this
    channel no policy, learned or evolved, could ever forage; with a random θ
    it is merely noise-mixed. Tokens never read μ directly (no global oracle).
    """
    msg = a @ (state.x @ w.W_v)                                     # [N, d]
    diff = state.mu[None, :] - state.x                              # [N, d]
    sense = np.exp(-np.sum(diff * diff, axis=1) /
                   (2.0 * cfg.sigma_r * cfg.sigma_r))               # [N] local field
    sense_grad = (sense[:, None] * diff) / (cfg.sigma_r * cfg.sigma_r)  # [N, d] ∇w
    feat = np.concatenate(
        [state.x, msg, state.g, state.e[:, None],
         sense[:, None], sense_grad], axis=1)                       # [N, 3d+dg+2]
    hidden = np.maximum(0.0, feat @ w.W1 + w.b1)
    out = hidden @ w.W2 + w.b2                                      # [N, d+2]
    d = cfg.d
    dx = cfg.max_step * np.tanh(out[:, :d])                         # bounded step
    gate = 1.0 / (1.0 + np.exp(-out[:, d]))                         # harvest ∈ (0,1)
    frac = cfg.transfer_frac_max / (1.0 + np.exp(-out[:, d + 1]))   # send ∈ (0, max)
    # route the sent energy along the sender's OFF-DIAGONAL attention shares
    share = a * (1.0 - np.eye(a.shape[0]))
    row = share.sum(axis=1, keepdims=True)
    share = np.divide(share, row, out=np.zeros_like(share), where=row > 0)
    t = (frac * state.e)[:, None] * share                           # [N, N], row i ≤ frac·e_i
    return dx, gate, t


def make_attention_policy(
    cfg: EcoConfig, *, k_harmonics: int = 4, hidden: int = 16, seed: int = 0,
    mode: str = "dist",
):
    """Build the E1 policy: fixed random θ, distance-penalized interaction.

    mode: "dist" (default) | "softmax" | "hk" | "freeze_attention" |
    "shuffle_edges" | "remove_transfer" — the ablation arms are wrapped by the
    matched-compute harness in eco/ablations.py."""
    w = EcoWeights.random(cfg, k_harmonics, hidden, seed)
    ablation_rng = np.random.Generator(np.random.PCG64(seed + 777))

    def policy(state: EcoState, _cfg: EcoConfig):
        n = state.n
        if n == 0:
            z = np.zeros((0, cfg.d))
            return z, np.zeros(0), np.zeros((0, 0))
        base_mode = mode if mode in ("dist", "softmax", "hk") else "dist"
        a = interaction_graph(state.x, state.g, w, cfg, mode=base_mode)
        if mode == "freeze_attention":
            a = np.eye(n)                       # no interaction: pure self-loop
        elif mode == "shuffle_edges":
            perm = ablation_rng.permutation(n)  # break who-talks-to-whom, keep mass
            a = a[:, perm]
        dx, gate, t = decode_actions(state, a, w, cfg)
        if mode == "remove_transfer":
            t = np.zeros_like(t)
        policy.last_attention = a               # read-only observable (P2)
        return dx, gate, t

    policy.weights = w
    policy.last_attention = None
    return policy
