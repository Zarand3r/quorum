"""HK bounded-confidence attention — correctness, theory anchors, parity.

Three layers of rigor:
  1. operator invariants (row-stochastic, self-inclusion, kernel semantics);
  2. theory anchors — the implementation reproduces known dynamics
     (classic HK freezes multiple clusters; global softmax averaging contracts);
  3. mechanism/diff-twin parity for the trainable sigmoid variant (the same
     pin that gates the softmax fold, extended to HK).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fold.config import load_fold_config
from fold.hk import (
    cluster_count,
    distance_penalized_scores,
    dock_scores,
    effective_rank,
    hk_attention,
    hk_block_step,
    raw_scores,
    spread,
)
from fold.interface import contour_coeffs
from fold.weights import FoldWeights

_CFG = Path(__file__).resolve().parent.parent / "configs" / "fold.yaml"


def _cfg():
    return load_fold_config(_CFG)


# ---- operator invariants -------------------------------------------------


def test_hk_attention_row_stochastic_all_kernels() -> None:
    rng = np.random.default_rng(0)
    s = rng.standard_normal((16, 16))
    for kernel in ("hard", "soft", "sigmoid"):
        a = hk_attention(s, tau=0.3, kernel=kernel)
        assert np.allclose(a.sum(axis=1), 1.0), kernel
        assert np.all(a >= 0.0), kernel


def test_hk_self_never_excluded() -> None:
    """Even a token with no partners keeps itself — no empty confidence set."""
    s = np.full((4, 4), -10.0)  # nothing passes any reasonable τ
    for kernel in ("hard", "soft", "sigmoid"):
        a = hk_attention(s, tau=0.0, kernel=kernel)
        assert np.all(np.diag(a) > 0.0), kernel
        assert np.allclose(a.sum(axis=1), 1.0), kernel
    # hard kernel: isolated tokens attend ONLY to themselves (classic HK freeze)
    a_hard = hk_attention(s, tau=0.0, kernel="hard")
    assert np.allclose(a_hard, np.eye(4))


def test_hk_hard_kernel_is_uniform_average() -> None:
    """Classic HK semantics: uniform weight over the confidence set."""
    s = np.array([[9.0, 1.0, -1.0],
                  [1.0, 9.0, 1.0],
                  [-1.0, 1.0, 9.0]])
    a = hk_attention(s, tau=0.0, kernel="hard")
    assert np.allclose(a[0], [0.5, 0.5, 0.0])       # {0,1}
    assert np.allclose(a[1], [1 / 3, 1 / 3, 1 / 3])  # {0,1,2}


def test_sigmoid_kernel_matches_soft_at_low_temp() -> None:
    """The trainable relaxation converges to the masked softmax as temp → 0.

    Caveat this test controls for: the two kernels differ ON THE DIAGONAL when a
    token's self-score < τ (soft forces self fully in; sigmoid only floors the
    self gate at 1e-3). With self-compatible diagonals the semantics coincide."""
    rng = np.random.default_rng(1)
    s = rng.standard_normal((12, 12)) * 2.0 + 5.0 * np.eye(12)  # self-score > τ
    a_soft = hk_attention(s, tau=0.2, kernel="soft")
    a_sig = hk_attention(s, tau=0.2, kernel="sigmoid", temp=1e-4)
    assert np.allclose(a_soft, a_sig, atol=1e-3)


# ---- theory anchors --------------------------------------------------------


def test_anchor_classic_hk_freezes_clusters() -> None:
    """Hegselmann–Krause: pure averaging with a small confidence radius
    converges to ≥2 frozen clusters (opinions ≤ ε merge; gaps > ε persist)."""
    rng = np.random.default_rng(2)
    x = rng.uniform(0.0, 10.0, size=(50, 1))       # 1-D opinions on [0, 10]
    eps = 1.0
    for _ in range(100):
        a = hk_attention(raw_scores(x), tau=-eps * eps, kernel="hard")
        x = a @ x
    n_clusters = cluster_count(x, link_eps=0.5)
    assert n_clusters >= 2                          # no global consensus
    # converged: one more step changes nothing
    a = hk_attention(raw_scores(x), tau=-eps * eps, kernel="hard")
    assert np.allclose(a @ x, x, atol=1e-8)


def test_anchor_classic_hk_consensus_at_large_eps() -> None:
    """With ε larger than the opinion range, HK = global averaging → consensus."""
    rng = np.random.default_rng(3)
    x = rng.uniform(0.0, 10.0, size=(50, 1))
    for _ in range(50):
        a = hk_attention(raw_scores(x), tau=-1e6, kernel="hard")
        x = a @ x
    assert cluster_count(x, link_eps=0.5) == 1


def test_anchor_softmax_averaging_contracts() -> None:
    """Row-stochastic global averaging contracts the token cloud and merges
    tokens into clusters (Dong et al. / Geshkovski et al.). NOTE the honest
    shape of the claim: collapse to ONE point is an infinite-time limit with
    exponentially long metastable multi-cluster trapping (arXiv:2410.06833) —
    so the finite-horizon assertion is contraction + merging, not consensus."""
    cfg = _cfg()
    rng = np.random.default_rng(4)
    w = FoldWeights.random(cfg, 4)
    x = cfg.init_scale * rng.standard_normal((32, cfg.d))
    s0 = spread(x)
    for _ in range(50):
        from fold.transformer import attention
        _, a = attention(x, w, cfg)
        x = a @ x
    assert spread(x) < 0.95 * s0                    # cloud strictly contracted
    assert cluster_count(x, link_eps=0.25) < 32     # tokens began merging


def test_dressed_hk_dock_preserves_more_spread_than_softmax() -> None:
    """THE STUDY'S HEADLINE, as a permanent regression gate: with full
    transformer dressing, bounded-confidence dock attention (τ=0.5) retains
    far more token spread than global softmax — ON AVERAGE ACROSS SEEDS (the
    honest form: individual seeds can still collapse under either operator;
    Exp A measured ~0.64 vs ~0.02 mean spread over 5 seeds)."""
    cfg = _cfg()
    from fold.transformer import block_step

    sp_sm, sp_hk = [], []
    for s in range(5):
        rng = np.random.default_rng(1000 + s)
        w = FoldWeights.random(cfg, 1000 + s)
        x_sm = cfg.init_scale * rng.standard_normal((64, cfg.d))
        x_hk = x_sm.copy()
        for _ in range(200):
            x_sm, _, _ = block_step(x_sm, w, cfg)
            x_hk, _, _ = hk_block_step(x_hk, w, cfg, space="dock", tau=0.5,
                                       kernel="hard")
        sp_sm.append(spread(x_sm))
        sp_hk.append(spread(x_hk))
    assert np.mean(sp_hk) > 5.0 * np.mean(sp_sm), (sp_hk, sp_sm)


# ---- groundedness (J1/J6 carried) -----------------------------------------


def test_hk_dock_scores_are_grounded() -> None:
    """The confidence set lives in the SAME contour-overlap metric the blobs
    render: perturbing an embedding moves its contour and its score row together."""
    cfg = _cfg()
    rng = np.random.default_rng(6)
    w = FoldWeights.random(cfg, 6)
    x = rng.standard_normal((8, cfg.d))
    c0, s0 = contour_coeffs(x, w), dock_scores(contour_coeffs(x, w), w.M)
    x2 = x.copy()
    x2[3] += 0.5
    c2, s2 = contour_coeffs(x2, w), dock_scores(contour_coeffs(x2, w), w.M)
    assert not np.allclose(c0[3], c2[3])            # blob changed
    assert not np.allclose(s0[3], s2[3])            # its confidence row changed
    others = [i for i in range(8) if i != 3]
    assert np.allclose(c0[others], c2[others])      # only token 3's contour moved


# ---- mechanism / diff-twin parity ------------------------------------------


def test_distance_penalty_localizes_attention() -> None:
    """The λ‖Δx‖² cost makes a token attend to a physically-near token over an
    equally-complementary far one (soft locality, no threshold)."""
    cfg = _cfg()
    rng = np.random.default_rng(20)
    w = FoldWeights.random(cfg, 20)
    # token 0 at origin; tokens 1 (near) and 2 (far) with identical contours
    x = np.zeros((3, cfg.d))
    x[1] = 0.2 * rng.standard_normal(cfg.d)
    x[2] = 5.0 + 0.2 * rng.standard_normal(cfg.d)
    c = np.zeros((3, 2 * cfg.k_harmonics)) + 0.3   # identical complementarity
    s_plain = dock_scores(c, w.M)
    s_dist = distance_penalized_scores(c, x, w.M, lam=0.5)
    # plain: near/far scores equal; dist: far is penalized below near
    assert abs(s_plain[0, 1] - s_plain[0, 2]) < 1e-9
    assert s_dist[0, 1] > s_dist[0, 2] + 1.0


def test_dist_softmax_preserves_spread_vs_softmax() -> None:
    """Exp-A regression gate for the trainable variant — reproduces the reported
    row (seeds 1000–1004): distance-penalized softmax (λ=0.5) retains far more
    spread than plain softmax. NOTE (honest): collapse is seed-DEPENDENT for the
    dressed fold — residual+LN+MLP prevent it on some seeds (Wu et al. 2024) — so
    this is an average-over-the-reported-seeds claim, not a per-seed guarantee."""
    cfg = _cfg()
    from fold.transformer import block_step

    sp_sm, sp_d = [], []
    for s in range(5):
        rng = np.random.default_rng(1000 + s)
        w = FoldWeights.random(cfg, 1000 + s)
        x_sm = cfg.init_scale * rng.standard_normal((64, cfg.d))
        x_d = x_sm.copy()
        for _ in range(200):
            x_sm, _, _ = block_step(x_sm, w, cfg)
            x_d, _, _ = hk_block_step(x_d, w, cfg, space="dist", lam=0.5)
        sp_sm.append(spread(x_sm))
        sp_d.append(spread(x_d))
    assert np.mean(sp_d) > 5.0 * np.mean(sp_sm), (sp_d, sp_sm)


def test_dist_parity_mechanism_vs_diff() -> None:
    """Mechanism dist fold and its autograd twin are the same math (1e-12)."""
    import autograd.numpy as anp

    from train.diff_fold import diff_block_step, params_from_weights

    cfg = _cfg()
    rng = np.random.default_rng(21)
    w = FoldWeights.random(cfg, 21)
    x = rng.standard_normal((cfg.n_tokens, cfg.d))
    params = params_from_weights(w, np.zeros((2, cfg.d)))
    xm, _, am = hk_block_step(x, w, cfg, space="dist", lam=0.4)
    xd, ad = diff_block_step(anp.array(x), params, w.M, cfg, attn="dist", lam=0.4)
    assert np.max(np.abs(xm - np.asarray(xd))) < 1e-12
    assert np.max(np.abs(am - np.asarray(ad))) < 1e-12


def test_hk_sigmoid_parity_mechanism_vs_diff() -> None:
    """The trainable diff twin and the mechanism HK fold are the same math."""
    import autograd.numpy as anp

    from train.diff_fold import diff_block_step, params_from_weights

    cfg = _cfg()
    rng = np.random.default_rng(7)
    w = FoldWeights.random(cfg, 7)
    x = rng.standard_normal((cfg.n_tokens, cfg.d))
    params = params_from_weights(w, np.zeros((2, cfg.d)))

    xm, _, am = hk_block_step(x, w, cfg, space="dock", tau=0.3,
                              kernel="sigmoid", temp=0.2)
    xd, ad = diff_block_step(anp.array(x), params, w.M, cfg,
                             attn="hk", tau=0.3, temp=0.2)
    assert np.max(np.abs(xm - np.asarray(xd))) < 1e-12
    assert np.max(np.abs(am - np.asarray(ad))) < 1e-12


# ---- metrics sanity ---------------------------------------------------------


def test_cluster_count_two_blobs() -> None:
    rng = np.random.default_rng(8)
    a = rng.normal(0.0, 0.05, size=(20, 3))
    b = rng.normal(5.0, 0.05, size=(20, 3))
    assert cluster_count(np.vstack([a, b]), link_eps=0.5) == 2


def test_effective_rank_bounds() -> None:
    rng = np.random.default_rng(9)
    collapsed = np.ones((30, 4)) + 1e-9 * rng.standard_normal((30, 4))
    iso = rng.standard_normal((5000, 4))
    assert effective_rank(collapsed) < 1.5
    assert effective_rank(iso) > 3.5


def test_spread_zero_on_identical() -> None:
    assert spread(np.ones((10, 4))) == 0.0
