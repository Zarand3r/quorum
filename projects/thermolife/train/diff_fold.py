"""Differentiable twin of the fold (M2). Same math as ``fold/transformer.py``,
written against ``autograd.numpy`` so we can backprop through the unrolled
iterations. A parity test (tests/test_m2_parity.py) pins the two implementations
together — if the mechanism and this twin ever drift, the gate fails.

Trainable params (a dict, autograd differentiates through it):
    W_c [d,2K]  grounded contour readout (= query; the "genome" of shape)
    W_v [d,d]   value
    W1,b1,W2,b2 pointwise MLP
    e_types [2K_pairs*2, d]  the vocabulary's base embeddings
Fixed: the complementarity metric M (π-rotation) — high Q·K must keep meaning
*complementary*, not identical; and the render projection P (display only).
"""

from __future__ import annotations

import autograd.numpy as anp

from fold.config import FoldConfig
from fold.weights import FoldWeights


def params_from_weights(w: FoldWeights, e_types) -> dict:
    return {
        "W_c": w.W_c.copy(), "W_v": w.W_v.copy(),
        "W1": w.W1.copy(), "b1": w.b1.copy(),
        "W2": w.W2.copy(), "b2": w.b2.copy(),
        "e_types": anp.array(e_types),
    }


def _layernorm(x, eps: float = 1e-5):
    mu = anp.mean(x, axis=1, keepdims=True)
    var = anp.mean((x - mu) ** 2, axis=1, keepdims=True)
    return (x - mu) / anp.sqrt(var + eps)


def _softmax_rows(s):
    s = s - anp.max(s, axis=1, keepdims=True)
    e = anp.exp(s)
    return e / anp.sum(e, axis=1, keepdims=True)


def diff_block_step(x, params: dict, m_metric, cfg: FoldConfig):
    """One fold iteration; mirrors fold.transformer.block_step exactly."""
    c = x @ params["W_c"]
    key = c @ m_metric
    a = _softmax_rows((c @ key.T) / anp.sqrt(c.shape[1]))
    x1 = _layernorm(x + a @ (x @ params["W_v"]))
    if cfg.use_mlp:
        hidden = anp.maximum(0.0, x1 @ params["W1"] + params["b1"])
        x1 = _layernorm(x1 + hidden @ params["W2"] + params["b2"])
    return x1, a


def fold_forward(x0, params: dict, m_metric, cfg: FoldConfig, t_steps: int):
    """Unroll T iterations; return (final X, final attention A)."""
    x, a = x0, None
    for _ in range(t_steps):
        x, a = diff_block_step(x, params, m_metric, cfg)
    return x, a


def fold_forward_all(x0, params: dict, m_metric, cfg: FoldConfig, t_steps: int):
    """Unroll T iterations; return (final X, [A_1..A_T])."""
    x, attns = x0, []
    for _ in range(t_steps):
        x, a = diff_block_step(x, params, m_metric, cfg)
        attns.append(a)
    return x, attns


def scene_loss(
    params: dict, types, partner, noise, sigma: float, m_metric, cfg: FoldConfig, t_steps: int
):
    """Lock-and-key retrieval loss: −mean log A[i, partner(i)] on the FINAL
    attention. The readout is the attention structure, not a token. Collapse is
    self-defeating: identical embeddings ⇒ uniform A ⇒ loss pinned at log N.

    X0 is assembled here from params["e_types"] so the vocabulary itself learns.

    DEEP SUPERVISION: the loss averages over every iteration's attention, not
    just the last. A weight-tied untrained fold washes the scene out by ~T
    (rank collapse), so a final-step-only loss plateaus near chance; supervising
    all steps teaches docking to form early and *persist*.
    """
    x0 = params["e_types"][types] + sigma * noise
    _, attns = fold_forward_all(x0, params, m_metric, cfg, t_steps)
    idx = anp.arange(len(partner))
    total = 0.0
    for a in attns:
        total = total - anp.mean(anp.log(a[idx, partner] + 1e-12))
    return total / len(attns)


def batch_loss(params: dict, scenes, sigma, m_metric, cfg: FoldConfig, t_steps: int):
    """Mean scene_loss over a list of (types, partner, noise) scenes."""
    total = 0.0
    for types, partner, noise in scenes:
        total = total + scene_loss(
            params, types, partner, noise, sigma, m_metric, cfg, t_steps
        )
    return total / len(scenes)
