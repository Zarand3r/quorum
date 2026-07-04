"""S0 fold mechanism — invariants J1–J6 (PLAN.md §6)."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from fold.config import load_fold_config
from fold.interface import contour_coeffs, contour_polylines, contour_radii
from fold.transformer import attention, block_step
from fold.weights import FoldWeights

_ROOT = Path(__file__).resolve().parent.parent
_CFG = _ROOT / "configs" / "fold.yaml"
_TOKEN_LOOP = re.compile(
    r"np\.ndindex|\.ndenumerate|for\s+\w+\s+in\s+range\([^)]*"
    r"(n_tokens|shape\[0\])",
)


def _setup(seed=0):
    cfg = load_fold_config(_CFG)
    w = FoldWeights.random(cfg, seed)
    rng = np.random.default_rng(seed + 10_000)
    x = rng.standard_normal((cfg.n_tokens, cfg.d)) * cfg.init_scale
    return cfg, w, x


def test_groundedness() -> None:
    """J1: the drawn contour uses the *same* C that is the attention query,
    and the renderer reads nothing but C."""
    cfg, w, x = _setup()
    c_iface = contour_coeffs(x, w)
    c_attn, _ = attention(x, w, cfg)
    assert np.array_equal(c_iface, c_attn)  # shape code == query
    # contour is a pure function of C (independent of anything else)
    assert np.array_equal(contour_polylines(c_iface, cfg), contour_polylines(c_iface.copy(), cfg))


def test_overlap_equals_attention_score() -> None:
    """J6: the geometric overlap of two blobs (i's contour vs j's π-rotated
    contour) equals amp²·π·(Q_i·K_j) — the pre-softmax attention score. This is
    the Parseval identity that makes 'fitting' == attention."""
    cfg, w, x = _setup(seed=2)
    c = contour_coeffs(x, w)
    theta, r = contour_radii(c, cfg, clamp=False)      # [P], [N,P]
    dtheta = 2.0 * np.pi / cfg.contour_points
    harm = r - cfg.rho0                                 # strip DC term
    key = c @ w.M                                       # analytic Q·K uses the same M
    half = cfg.contour_points // 2
    for i, j in [(0, 1), (2, 3), (1, 4)]:
        # j's contour rotated by π = shift the sampled profile by half a turn
        rj_rot = np.roll(harm[j], half)
        overlap_geom = float(np.sum(harm[i] * rj_rot) * dtheta)
        score = float(c[i] @ key[j])                    # Q_i · K_j
        assert np.isclose(overlap_geom, cfg.amp**2 * np.pi * score, rtol=1e-6, atol=1e-6)


def test_no_token_loop_in_mechanism() -> None:
    """J3: transformer + interface vectorize over tokens (no per-token loop)."""
    offenders = [
        f.name
        for f in [_ROOT / "fold" / "transformer.py", _ROOT / "fold" / "interface.py"]
        if _TOKEN_LOOP.search(f.read_text())
    ]
    assert not offenders, f"token loop in: {offenders}"


def test_synchrony() -> None:
    """J4: block_step reads X and returns a fresh X, mutating nothing."""
    cfg, w, x = _setup()
    before = x.copy()
    block_step(x, w, cfg)
    assert np.array_equal(x, before)


def test_bounded_over_long_fold() -> None:
    """J5: LayerNorm + residual keep embeddings finite over many iterations."""
    cfg, w, x = _setup(seed=7)
    for _ in range(500):
        x, _, _ = block_step(x, w, cfg)
    assert np.isfinite(x).all()
    assert np.abs(x).max() < 1e3


def test_determinism_of_map() -> None:
    """J2 (map level): same input+weights → identical step."""
    cfg, w, x = _setup()
    a1 = block_step(x, w, cfg)[0]
    a2 = block_step(x, w, cfg)[0]
    assert np.array_equal(a1, a2)
