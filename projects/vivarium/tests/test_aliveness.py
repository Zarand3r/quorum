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


def test_coordinated_motion_scores_positive() -> None:
    cfg = _cfg(N=32)
    rng = np.random.default_rng(4)
    P0 = rng.standard_normal((32, 2)) * 2.0
    v = np.array([0.1, 0.05])  # a shared, smooth drift (flock)
    P = np.stack([P0 + t * v for t in range(30)])
    s = score(_states(P, cfg), cfg)
    assert s["gate_spread"] == 1.0 and s["gate_motion"] == 1.0
    assert s["coherence"] > 0.9 and s["structure"] > 0.9
    assert s["aliveness"] > 0.5


def test_evaluate_is_read_only() -> None:
    # P3/P5: probing the engine must not change its state, time, or weights.
    e = Engine(_cfg(), seed=0)
    for _ in range(5):
        e.step()
    X0, t0 = e.X.copy(), e.t
    Wv0, Wp0 = e.weights.W_v.copy(), e.weights.W_p.copy()

    report = evaluate(e, window=20)

    assert np.array_equal(e.X, X0) and e.t == t0
    assert np.array_equal(e.weights.W_v, Wv0) and np.array_equal(e.weights.W_p, Wp0)
    assert set(report) >= {"aliveness", "gate_spread", "coherence", "structure", "lyapunov"}


def test_measure_not_rewarded_static() -> None:
    # P3: no update-path module may reference aliveness.
    import block
    import engine
    import plasticity
    import predict

    for mod in (plasticity, predict, block, engine):
        assert "aliveness" not in inspect.getsource(mod), f"{mod.__name__} touches aliveness"
