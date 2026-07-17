"""Step 2 (M1) — locality of the learning signal (P1, learning half).

An agent's one-step error reads only its neighbourhood: perturbing a *non-neighbour's*
next observable leaves that agent's error untouched (its attention row is zero there),
while the perturbed agent's own error does move.
"""

from __future__ import annotations

import numpy as np

from block import forward_verbose, make_weights
from config import DEFAULTS, VivariumConfig
from plasticity import local_error
from substrate import init_state


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_error_depends_only_on_neighbours() -> None:
    cfg = _cfg(N=30, n_neighbors=5)
    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    X_next, A, msg = forward_verbose(X, w, cfg)

    e0 = local_error(w, A, msg, X_next, t=0, cfg=cfg)

    i = 0
    neighbours = set(np.nonzero(A[i] > 0)[0].tolist())
    j = next(x for x in range(cfg.N) if x not in neighbours)  # a non-neighbour of i
    assert A[i, j] == 0.0

    # perturb only agent j's *next* observable.
    Xn = X_next.copy()
    Xn[j, : cfg.pos_dim + cfg.shape_dim] += 1.0
    e1 = local_error(w, A, msg, Xn, t=0, cfg=cfg)

    assert np.allclose(e0[i], e1[i]), "a non-neighbour must not affect agent i's error"
    assert not np.allclose(e0[j], e1[j]), "agent j's own error must move (self is a neighbour)"
