"""Step 2/M2 — non-degenerate signalling target + a correct local descent rule.

The pivoted objective predicts each neighbourhood's next observable **relative to
self**, `target_i = ((A − I)·obs)_i`. Two M1-scoped claims:

  1. The target is a *real* problem: it has non-trivial magnitude at a fresh state
     (there is relative structure to model), and it is **drift-invariant** and **≡ 0
     under the identity ablation** (interaction load-bearing by construction — the P6
     property, unit-checked here; the dynamical P6 test lives at M2).
  2. The local delta rule is a correct descent: one step reduces the tick's error.
"""

from __future__ import annotations

import numpy as np

from block import forward_verbose, make_weights
from config import DEFAULTS, VivariumConfig
from engine import Engine
from plasticity import learn, local_error
from predict import observe
from substrate import init_state


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_target_has_relative_structure() -> None:
    e = Engine(_cfg(), seed=0)
    X_next, A, msg = forward_verbose(e.X, e.weights, e.cfg)
    obs = observe(X_next, e.cfg)
    target = A @ obs - obs
    assert float(np.mean(np.sum(target**2, axis=1))) > 1e-3, "no relative structure to model"


def test_target_is_drift_invariant() -> None:
    # a uniform shift of every observable leaves the relative target unchanged.
    cfg = _cfg()
    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    X_next, A, msg = forward_verbose(X, w, cfg)
    e0 = local_error(w, A, msg, X_next, t=0, cfg=cfg)

    shift = np.zeros_like(X_next)
    shift[:, : cfg.pos_dim + cfg.shape_dim] = np.array([1.7, -0.9] + [0.3] * cfg.shape_dim)
    e1 = local_error(w, A, msg, X_next + shift, t=0, cfg=cfg)
    assert np.allclose(e0, e1), "target must be invariant to a uniform observable shift"


def test_identity_ablation_makes_target_zero() -> None:
    # P6 by construction: no neighbours ⇒ (A−I)=0 ⇒ nothing to model.
    cfg = _cfg()
    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    X_next, A_id, msg = forward_verbose(X, w, cfg, ablate="identity")
    obs = observe(X_next, cfg)
    target = A_id @ obs - obs
    assert np.allclose(target, 0.0), "identity coupling must trivialise the target"


def test_local_delta_rule_descends_surprise() -> None:
    e = Engine(_cfg(), seed=0)
    cfg = e.cfg
    X = e.X
    X_next, A, msg = forward_verbose(X, e.weights, cfg)

    e0 = local_error(e.weights, A, msg, X_next, t=0, cfg=cfg)
    L0 = 0.5 * float(np.mean(np.sum(e0 * e0, axis=1)))

    w2, _ = learn(e.weights, X, A, msg, X_next, t=0, cfg=cfg)

    obs = observe(X_next, cfg)
    target = A @ obs - obs
    e1 = (msg @ w2.W_p) - target
    L1 = 0.5 * float(np.mean(np.sum(e1 * e1, axis=1)))
    assert L1 < L0, "the local delta rule must reduce the tick's prediction error"
