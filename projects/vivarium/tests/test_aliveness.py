"""Step 3 — aliveness harness: gates fire + read-only + measure-not-rewarded (P3).

The score is ungameable-by-construction: the degenerate regimes (freeze, collapse,
blow-up, white noise) each trip a hard zero; only organised, coordinated motion
scores > 0. And nothing about computing it can influence the dynamics (P3).
"""

from __future__ import annotations

import inspect

import numpy as np

from aliveness import evaluate, score
from config import DEFAULTS, VivariumConfig
from engine import Engine


def _cfg(**over) -> VivariumConfig:
    return VivariumConfig(**{**DEFAULTS, **over})


def _states(P: np.ndarray, cfg: VivariumConfig) -> np.ndarray:
    """Embed a (T, N, 2) position track into (T, N, d) finite states."""
    T, N, _ = P.shape
    X = np.zeros((T, N, cfg.d))
    X[:, :, :2] = P
    return X


def test_frozen_scores_zero() -> None:
    cfg = _cfg(N=16)
    base = np.random.default_rng(0).standard_normal((16, 2)) * 2.0  # only for a fixture
    P = np.repeat(base[None], 30, axis=0)  # no motion
    s = score(_states(P, cfg), cfg)
    assert s["gate_motion"] == 0.0 and s["aliveness"] == 0.0


def test_collapsed_scores_zero() -> None:
    cfg = _cfg(N=16)
    P = np.zeros((30, 16, 2))  # everyone at one point
    P += np.linspace(0, 0.3, 30)[:, None, None]  # moving, but no spread
    s = score(_states(P, cfg), cfg)
    assert s["gate_spread"] == 0.0 and s["aliveness"] == 0.0


def test_blowup_scores_zero() -> None:
    cfg = _cfg(N=16)
    X = _states(np.random.default_rng(1).standard_normal((30, 16, 2)), cfg)
    X[15, 0, 0] = np.inf
    assert score(X, cfg)["aliveness"] == 0.0
    # also: excessive spread trips gate_spread.
    P_big = np.random.default_rng(2).standard_normal((30, 16, 2)) * 1e3
    assert score(_states(P_big, cfg), cfg)["gate_spread"] == 0.0


def test_white_noise_scores_low() -> None:
    cfg = _cfg(N=32)
    rng = np.random.default_rng(3)
    P = rng.standard_normal((30, 32, 2)) * 2.0  # independent each frame → no coherence
    s = score(_states(P, cfg), cfg)
    assert s["coherence"] < 0.3
    assert s["aliveness"] < 0.2


def test_rigid_drift_scores_low() -> None:
    # R2 fix: a shared rigid translation (coherent drift) is TRIVIAL — it must NOT
    # score as alive, even though it is smooth and moving.
    cfg = _cfg(N=32)
    rng = np.random.default_rng(4)
    P0 = rng.standard_normal((32, 2)) * 2.0
    v = np.array([0.1, 0.05])  # everyone moves identically
    P = np.stack([P0 + t * v for t in range(30)])
    s = score(_states(P, cfg), cfg)
    assert s["gate_motion"] == 1.0        # it IS moving...
    assert s["structure"] < 0.1           # ...but has no relative structure
    assert s["aliveness"] < 0.15          # so it is (correctly) not alive


def test_rigid_rotation_scores_low() -> None:
    # A rigid-body rotation has differentiated velocity (structure high) but preserves
    # all pairwise distances → NOT morphing → deformation ~0 → not alive.
    cfg = _cfg(N=32)
    rng = np.random.default_rng(6)
    P0 = rng.standard_normal((32, 2)) * 2.0
    th = 0.12
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    P = [P0]
    for _ in range(29):
        P.append(P[-1] @ R.T)
    s = score(_states(np.stack(P), cfg), cfg)
    assert s["deformation"] < 0.05        # rigid → relative config preserved
    assert s["aliveness"] < 0.1           # so a spinning rigid blob is NOT alive


def test_nonrigid_flow_scores_above_trivial() -> None:
    # A shear flow: horizontal speed ∝ vertical position. Neighbours (similar height)
    # move alike (structure high), but the configuration genuinely deforms
    # (deformation high) — non-rigid, organised motion. It must score clearly above
    # every trivial case (rigid drift, rigid rotation ≈ 0).
    cfg = _cfg(N=48)
    rng = np.random.default_rng(5)
    P0 = rng.standard_normal((48, 2)) * 2.0
    shear = 0.05
    P = np.stack([P0 + t * np.stack([shear * P0[:, 1], np.zeros(48)], axis=1) for t in range(30)])
    s = score(_states(P, cfg), cfg)

    assert s["gate_motion"] == 1.0
    assert s["structure"] > 0.5       # locally aligned relative motion
    assert s["deformation"] > 0.1     # genuinely non-rigid (unlike rotation/translation)

    # the discriminating claim: non-rigid organised flow ≫ trivial motions.
    rigid = np.stack([P0 + t * np.array([0.1, 0.05]) for t in range(30)])
    assert s["aliveness"] > 5.0 * score(_states(rigid, cfg), cfg)["aliveness"] + 0.05


def test_evaluate_is_read_only() -> None:
    # P3/P5: probing the engine must not change its state, time, or weights.
    e = Engine(_cfg(), seed=0)
    for _ in range(5):
        e.step()
    X0, t0 = e.X.copy(), e.t
    Wv0 = e.weights.W_v.copy()

    report = evaluate(e, window=20)

    assert np.array_equal(e.X, X0) and e.t == t0
    assert np.array_equal(e.weights.W_v, Wv0)
    assert set(report) >= {"aliveness", "gate_spread", "coherence", "structure", "deformation", "lyapunov"}


def test_measure_not_rewarded_static() -> None:
    # P3: no dynamics module may reference aliveness (measured, never fed back).
    import block
    import engine

    for mod in (block, engine):
        assert "aliveness" not in inspect.getsource(mod), f"{mod.__name__} touches aliveness"
