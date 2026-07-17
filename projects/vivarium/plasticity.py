"""Route A local predictive plasticity (IMPLEMENTATION_PLAN.md Step 2).

One clock: every tick advances state *and* nudges θ from a **local, one-step**
prediction error — no autograd, no backprop-through-time. Each agent predicts the
attention-weighted next observable of its neighbourhood from the message it just
formed; the error drives a hand-derived delta rule on the value projection `W_v`
(so the *interaction* adapts) and the readout `W_p`.

Locality: `msg_i` and the aggregate `(A·X)_i` involve only agent i's neighbours
(A is zero off the k-NN support), and `target_i = (A·obs_next)_i` likewise — so the
update for agent i reads only its neighbourhood. Attention routing `A` is treated
as fixed context for the plasticity (we differentiate the message, not the
softmax), which keeps the credit assignment a single linear layer — the delta
(Widrow–Hoff) rule, i.e. the one-step gradient of the local surprise.

A small L2 decay keeps the learned weights bounded (P7); LayerNorm bounds the
state independently.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from block import Weights
from config import VivariumConfig
from drift import season
from predict import obs_dim, observe

_WEIGHT_DECAY = 1e-2  # ridge pull-back → bounded W_v, W_p at the plasticity fixed point


def local_error(
    w: Weights,
    A: np.ndarray,
    msg: np.ndarray,
    X_next: np.ndarray,
    t: int,
    cfg: VivariumConfig,
) -> np.ndarray:
    """Per-agent one-step prediction error `e_i = pred_i − target_i` (N, m).

    target_i = (A · obs(X_next))_i + s(t)   — the neighbourhood's next observable,
    plus the season; pred_i = msg_i · W_p."""
    m = obs_dim(cfg)
    target = A @ observe(X_next, cfg) + season(t, m, cfg.drift_rate)
    pred = msg @ w.W_p
    return pred - target


def learn(
    w: Weights,
    X: np.ndarray,
    A: np.ndarray,
    msg: np.ndarray,
    X_next: np.ndarray,
    t: int,
    cfg: VivariumConfig,
) -> tuple[Weights, float]:
    """Apply the local delta rule; return (updated θ, mean surprise)."""
    e = local_error(w, A, msg, X_next, t, cfg)  # (N, m)
    n = X.shape[0]
    loss = 0.5 * float(np.mean(np.sum(e * e, axis=1)))

    # msg = (A·X)·W_v, so agg = A·X is the pre-W_v activity feeding the message.
    agg = A @ X                                  # (N, d)
    g_Wp = msg.T @ e / n                          # (d, m)   dL/dW_p
    g_Wv = agg.T @ (e @ w.W_p.T) / n              # (d, d)   dL/dW_v via the message

    # Option 1 — local anti-collapse (M2). Reward each agent's message for deviating from
    # its attention-weighted neighbourhood, so the plasticity is pushed away from homogenising.
    # da = (I − A)·agg is the local deviation; d = da·W_v; the diversity-reward gradient
    # −(β/n)·(daᵀda)·W_v is linear in W_v (still a hand-derived one-step delta, still local).
    if cfg.anticollapse > 0.0:
        da = agg - A @ agg                        # (N, d)  deviation from neighbourhood
        g_Wv = g_Wv - (cfg.anticollapse / n) * (da.T @ da) @ w.W_v

    W_p = w.W_p - cfg.lr * (g_Wp + _WEIGHT_DECAY * w.W_p)
    W_v = w.W_v - cfg.lr * (g_Wv + _WEIGHT_DECAY * w.W_v)
    return replace(w, W_p=W_p, W_v=W_v), loss
