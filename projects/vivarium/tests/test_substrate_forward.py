"""Step 1 (M0) — locality of interaction + block purity (P1, and the P9/P2 seed).

The forward block is a *pure function* of (X, θ): it never mutates the weights.
Attention is *local*: each agent's row is supported only on its k nearest
neighbours (by position), with self always included.
"""

from __future__ import annotations

import numpy as np

from block import attention_matrix, forward, make_weights
from config import DEFAULTS, VivariumConfig
from substrate import init_state


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_attention_is_local(  ) -> None:
    cfg = _cfg(N=40, n_neighbors=6)
    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    A = attention_matrix(X, w, cfg)

    assert A.shape == (cfg.N, cfg.N)
    # rows are proper distributions.
    assert np.allclose(A.sum(axis=1), 1.0)
    # at most k nonzero entries per row.
    assert np.all((A > 0).sum(axis=1) <= cfg.n_neighbors)

    # the support is exactly a subset of the k nearest neighbours by position.
    pos = X[:, :2]
    for i in range(cfg.N):
        d2 = ((pos - pos[i]) ** 2).sum(axis=1)
        nearest = set(np.argsort(d2, kind="stable")[: cfg.n_neighbors].tolist())
        active = set(np.nonzero(A[i] > 0)[0].tolist())
        assert active.issubset(nearest)
        assert i in active  # self is always a neighbour (distance 0)


def test_forward_shape_and_finite() -> None:
    cfg = _cfg()
    X = init_state(cfg, seed=1)
    w = make_weights(cfg, seed=1)
    Y = forward(X, w, cfg)
    assert Y.shape == X.shape
    assert np.all(np.isfinite(Y))


def test_forward_does_not_mutate_weights() -> None:
    # P9/P2 seed: M0 forward writes no weights (byte-identical θ across a step).
    cfg = _cfg()
    w = make_weights(cfg, seed=2)
    before = {name: getattr(w, name).copy() for name in w.array_names()}
    X = init_state(cfg, seed=2)
    _ = forward(X, w, cfg)
    for name in w.array_names():
        assert getattr(w, name).tobytes() == before[name].tobytes(), f"{name} mutated"


def test_forward_does_not_mutate_input_state() -> None:
    cfg = _cfg()
    X = init_state(cfg, seed=3)
    w = make_weights(cfg, seed=3)
    X_ref = X.copy()
    _ = forward(X, w, cfg)
    assert np.array_equal(X, X_ref), "forward must not mutate its input X in place"
