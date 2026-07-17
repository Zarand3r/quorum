"""Step 2 (M1) — one clock (P2) + single module (P9).

A single step() advances state AND weights. The learned weights are W_v (the
interaction) and W_p (the readout); the structural maps W_c, M, MLP stay fixed.
There is no separate train()/fit() phase.
"""

from __future__ import annotations

import inspect

import numpy as np

from block import Weights
from config import DEFAULTS, VivariumConfig
from engine import Engine


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_step_updates_weights_one_clock() -> None:
    e = Engine(_cfg(), seed=0)
    before = {n: getattr(e.weights, n).copy() for n in Weights.array_names()}
    e.step()
    # learned weights changed...
    assert not np.array_equal(e.weights.W_v, before["W_v"]), "W_v (interaction) must adapt"
    assert not np.array_equal(e.weights.W_p, before["W_p"]), "W_p (readout) must adapt"
    # ...structural weights did not.
    for n in ("W_c", "M", "W1", "b1", "W2", "b2"):
        assert np.array_equal(getattr(e.weights, n), before[n]), f"{n} must stay fixed at M1"


def test_no_separate_train_phase() -> None:
    # P2: the only way weights change is step(); there is no train()/fit().
    assert not hasattr(Engine, "train")
    assert not hasattr(Engine, "fit")
    src = inspect.getsource(Engine)
    assert "def step" in src
    assert "for epoch" not in src


def test_prediction_is_a_readout_not_a_network() -> None:
    # P9: exactly one weight bundle (θ); W_p lives in it; predict.py has no network.
    assert "W_p" in Weights.array_names()
    import predict

    src = inspect.getsource(predict)
    for forbidden in ("nn.", "Linear(", "Sequential(", "class "):
        assert forbidden not in src, f"predictor must be a readout, found {forbidden!r}"
