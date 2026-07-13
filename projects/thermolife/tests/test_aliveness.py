"""The aliveness objective must ZERO every trivial fate and reward only sustained,
structured, coherent dynamics — the ungameable target for heedless iteration."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fold.morph import MorphEngine, load_morph
from train.aliveness import BLOWUP, evaluate, score_records

_CFG = Path(__file__).resolve().parent.parent / "configs" / "morph.yaml"
_D = 6


def _rec(spread, motion, rank, g, clusters=3.0, finite=True, n=300):
    return {
        "motion": np.full(n, motion), "spread": np.full(n, spread),
        "rank": np.full(n, rank), "clusters": np.full(n, clusters),
        "g": np.asarray(g), "finite": finite,
    }


def _alive_signal(n=400):
    t = np.arange(n)
    return np.sin(2 * np.pi * t / 50.0) + 0.4 * np.sin(2 * np.pi * t / 23.0)


def test_alive_records_score_positive() -> None:
    sc, _ = score_records(_rec(0.5, 0.1, 3.0, _alive_signal()), _D)
    assert sc > 0.0


def test_collapse_scores_zero() -> None:
    """Spatial consensus (spread below floor) is death, however much it moves."""
    sc, _ = score_records(_rec(0.03, 0.1, 3.0, _alive_signal()), _D)
    assert sc == 0.0


def test_freeze_scores_zero() -> None:
    """A fixed point (no late motion) is death, however spread out."""
    sc, _ = score_records(_rec(0.5, 0.0005, 3.0, _alive_signal()), _D)
    assert sc == 0.0


def test_blowup_scores_zero() -> None:
    rec = _rec(0.5, 0.1, 3.0, _alive_signal())
    rec["motion"][10] = BLOWUP + 1.0            # one chaotic spike ⇒ dead
    sc, _ = score_records(rec, _D)
    assert sc == 0.0


def test_nonfinite_scores_zero() -> None:
    sc, _ = score_records(_rec(0.5, 0.1, 3.0, _alive_signal(), finite=False), _D)
    assert sc == 0.0


def test_white_noise_scores_below_structured() -> None:
    """Same spatial stats, but a WHITE-NOISE global signal (structureless) must
    score strictly below a coherent oscillation — 'no trivial-motion reward'."""
    rng = np.random.default_rng(0)
    white = _rec(0.5, 0.1, 3.0, rng.standard_normal(400))
    structured = _rec(0.5, 0.1, 3.0, _alive_signal())
    assert score_records(white, _D)[0] < score_records(structured, _D)[0]


def test_score_bounded_unit() -> None:
    sc, _ = score_records(_rec(0.9, 0.1, 6.0, _alive_signal()), _D)
    assert 0.0 <= sc <= 1.0


def test_global_attention_collapses_more_than_local() -> None:
    """End-to-end wiring: global attention (lam=0) spatially collapses the field
    harder than the local default — the RD locality claim, measured through the
    real engine (short rollout to keep the suite fast)."""
    import dataclasses
    cfg, p = load_morph(_CFG)
    a_local = evaluate(lambda s: MorphEngine(cfg, seed=s, params=p),
                       seeds=(0, 1), ticks=200, warmup=120, d=cfg.d)
    a_global = evaluate(lambda s: MorphEngine(cfg, seed=s, params=dataclasses.replace(p, lam=0.0)),
                        seeds=(0, 1), ticks=200, warmup=120, d=cfg.d)
    # global attention diffuses without limit → the field homogenizes harder;
    # local (distance-penalized) attention keeps more of it spread apart.
    assert a_global.mean_spread < a_local.mean_spread
