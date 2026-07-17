"""Step 2 (M1) — non-degenerate target + a correct local descent rule.

Two M1-scoped claims (sustained non-collapse is an M2 deliverable, NOT asserted here):

  1. The one-step prediction target is a *real* problem: at a fresh state a null
     "predict-identity" baseline (predict neighbours' next observable by your own
     current observable) carries non-trivial error — partial observation (hidden
     channels + drift) makes it non-degenerate.
  2. The local delta rule is a correct descent: for the tick's message and (detached)
     target, applying the update reduces the readout's prediction error.

KNOWN M1 LIMITATION (see report / DECISIONS): at default settings the colony
*collapses* under predictive plasticity — surprise is minimized the trivial way, by
homogenising, until only the un-trackable drift remains. Preventing that collapse
(sustained non-convergence) is M2's explicit tuning deliverable.
"""

from __future__ import annotations

import numpy as np

from block import forward_verbose
from config import DEFAULTS, VivariumConfig
from drift import season
from engine import Engine
from plasticity import learn, local_error
from predict import obs_dim, observe


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_target_is_nondegenerate_at_a_fresh_state() -> None:
    e = Engine(_cfg(), seed=0)
    X_next, A, msg = forward_verbose(e.X, e.weights, e.cfg)
    m = obs_dim(e.cfg)
    target = A @ observe(X_next, e.cfg) + season(e.t, m, e.cfg.drift_rate)
    identity = observe(e.X, e.cfg)
    L_identity = 0.5 * float(np.mean(np.sum((identity - target) ** 2, axis=1)))
    assert L_identity > 1e-3, "the prediction target must not be trivially the current obs"


def test_local_delta_rule_descends_surprise() -> None:
    e = Engine(_cfg(), seed=0)
    cfg = e.cfg
    X = e.X
    X_next, A, msg = forward_verbose(X, e.weights, cfg)

    e0 = local_error(e.weights, A, msg, X_next, t=0, cfg=cfg)
    L0 = 0.5 * float(np.mean(np.sum(e0 * e0, axis=1)))

    w2, _ = learn(e.weights, X, A, msg, X_next, t=0, cfg=cfg)

    # Re-evaluate the readout against the SAME (detached) message + target the rule
    # descended: only W_p moved here, so this is a clean check that the step reduces error.
    m = obs_dim(cfg)
    target = A @ observe(X_next, cfg) + season(0, m, cfg.drift_rate)
    e1 = (msg @ w2.W_p) - target
    L1 = 0.5 * float(np.mean(np.sum(e1 * e1, axis=1)))

    assert L1 < L0, "the local delta rule must reduce the tick's prediction error"
