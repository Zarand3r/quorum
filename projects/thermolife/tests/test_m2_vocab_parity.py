"""M2.0/M2.1 — vocabulary + differentiable-fold parity gates."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fold.config import load_fold_config
from fold.transformer import block_step
from fold.vocab import VocabConfig, init_type_embeddings, sample_scene, scene_embed
from fold.weights import FoldWeights
from train.diff_fold import fold_forward, params_from_weights, scene_loss

_CFG = Path(__file__).resolve().parent.parent / "configs" / "fold.yaml"


def _vocab_cfg(d=4):
    return VocabConfig(n_pairs=4, d=d, noise_sigma=0.6, init_scale=1.5)


def test_vocab_scene_structure() -> None:
    vc = _vocab_cfg()
    e = init_type_embeddings(vc, seed=0)
    assert e.shape == (8, 4)
    rng = np.random.default_rng(1)
    types, partner, noise = sample_scene(vc, rng)
    x0 = scene_embed(e, types, noise, vc.noise_sigma)
    assert x0.shape == (8, 4)
    assert sorted(types) == list(range(8))          # every type exactly once
    # partnering is a symmetric, self-free pairing
    for i in range(8):
        j = partner[i]
        assert j != i and partner[j] == i
        assert types[j] == (types[i] ^ 1)           # scene partner is the type partner
    # determinism: same rng seed → same scene
    t2, p2, n2 = sample_scene(vc, np.random.default_rng(1))
    assert np.array_equal(types, t2) and np.array_equal(noise, n2)


def test_diff_fold_parity_with_mechanism() -> None:
    """The autograd twin computes EXACTLY the mechanism fold (J-parity).
    If train-time and view-time dynamics drift apart, this gate fails."""
    cfg = load_fold_config(_CFG)
    w = FoldWeights.random(cfg, seed=3)
    rng = np.random.default_rng(7)
    x = rng.standard_normal((cfg.n_tokens, cfg.d))
    params = params_from_weights(w, np.zeros((8, cfg.d)))

    xm = x.copy()
    for _ in range(12):
        xm, _, am = block_step(xm, w, cfg)
    xd, ad = fold_forward(x, params, w.M, cfg, t_steps=12)

    assert np.allclose(xm, xd, atol=1e-12)
    assert np.allclose(am, ad, atol=1e-12)


def test_scene_loss_gradient_flows() -> None:
    """autograd produces finite, nonzero gradients through the unrolled fold."""
    from autograd import grad

    cfg = load_fold_config(_CFG)
    w = FoldWeights.random(cfg, seed=0)
    vc = _vocab_cfg(cfg.d)
    e = init_type_embeddings(vc, seed=0)
    params = params_from_weights(w, e)
    rng = np.random.default_rng(0)
    types, partner, noise = sample_scene(vc, rng)

    g = grad(
        lambda p: scene_loss(p, types, partner, noise, vc.noise_sigma, w.M, cfg, t_steps=8)
    )(params)
    for k in ("W_c", "W_v", "W1", "e_types"):
        assert np.isfinite(g[k]).all()
        assert np.abs(g[k]).max() > 0.0
