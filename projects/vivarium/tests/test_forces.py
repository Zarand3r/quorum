"""Motion from neighbour forces → P6 by construction.

Position moves only by attract/repel forces from neighbours. Under the identity
ablation there are no neighbours, so the force is exactly zero and positions never
move — interaction is load-bearing for the *dynamics* by construction (not merely
seed-dependent, as the earlier prediction substrate was).
"""

from __future__ import annotations

import numpy as np

from block import make_weights, position_force, positions
from config import DEFAULTS, VivariumConfig
from engine import Engine
from substrate import init_state


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def test_identity_force_is_exactly_zero() -> None:
    cfg = _cfg()
    p = positions(init_state(cfg, seed=0))
    F = position_force(p, np.eye(cfg.N), cfg)
    assert np.allclose(F, 0.0), "no neighbours (A=I) ⇒ no attract, no repel ⇒ no motion"


def test_identity_ablation_freezes_positions() -> None:
    # P6 by construction: with interaction ablated, positions never move.
    e = Engine(_cfg(), seed=0, ablate="identity")
    p0 = positions(e.X).copy()
    for _ in range(50):
        e.step()
    assert np.allclose(p0, positions(e.X)), "identity ablation must freeze positions"


def test_real_interaction_moves_positions() -> None:
    e = Engine(_cfg(), seed=0)  # ablate="none"
    p0 = positions(e.X).copy()
    for _ in range(50):
        e.step()
    assert not np.allclose(p0, positions(e.X)), "neighbour forces must move positions"


def test_forces_are_local() -> None:
    # An agent's force depends only on its k-NN support (P1): a distant non-neighbour's
    # position does not enter its force.
    cfg = _cfg(N=40, n_neighbors=6)
    from block import attention_matrix

    X = init_state(cfg, seed=0)
    w = make_weights(cfg, seed=0)
    A = attention_matrix(X, w, cfg)
    p = positions(X)
    F0 = position_force(p, A, cfg)

    i = 0
    nbrs = set(np.nonzero(A[i] > 0)[0].tolist())
    j = next(x for x in range(cfg.N) if x not in nbrs)  # non-neighbour of i
    p2 = p.copy()
    p2[j] += np.array([3.0, 3.0])  # move a non-neighbour far
    # recompute force with the SAME graph A (isolate the force's position dependence).
    F1 = position_force(p2, A, cfg)
    assert np.allclose(F0[i], F1[i]), "a non-neighbour must not affect agent i's force"
