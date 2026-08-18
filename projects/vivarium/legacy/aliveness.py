"""Aliveness — a measured, read-only, ungameable scoreboard (IMPLEMENTATION_PLAN.md Step 3).

Scores a window of the *live* run. It is wired **one-way**: it forks the engine and
rolls the fork, never touching the real engine (P5), and nothing here ever feeds back
into the update (P3 — invariant, grep-checked).

    aliveness = gate_finite · gate_spread · gate_motion · coherence · structure   ∈ [0, 1]

Hard-zero gates kill the degenerate regimes the design forbids:
  - gate_finite  : 0 on NaN/Inf (blow-up)
  - gate_spread  : 0 if the colony collapses to a point OR explodes
  - gate_motion  : 0 if frozen OR thrashing
Smooth factors reward *organised, non-random* motion:
  - coherence    : temporal — velocity is directed, not white noise
  - structure    : spatial  — neighbours move together (coordination), not independently

A twin-rollout Lyapunov exponent is reported alongside as an edge-of-chaos diagnostic
(≈0 = edge; <0 contracting/dead; >0 chaotic). It is NOT part of the score.
"""

from __future__ import annotations

import numpy as np

from block import neighbor_indices
from config import VivariumConfig

# regime bands (measured, never optimised).
_SPREAD_LO, _SPREAD_HI = 0.03, 8.0   # below → collapsed; above → blown up
_MOTION_LO, _MOTION_HI = 1e-3, 2.0   # below → frozen; above → thrashing


def rollout_states(engine, window: int) -> np.ndarray:
    """Fork the engine and roll it `window` steps, returning states (window+1, N, d).
    The real engine is untouched (P5)."""
    tw = engine.fork()
    states = [tw.X.copy()]
    for _ in range(window):
        tw.step()
        states.append(tw.X.copy())
    return np.stack(states)


def _cos_rows(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise cosine, 0 where either vector is ~0 (undefined direction)."""
    denom = np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1)
    dot = np.sum(a * b, axis=-1)
    return np.where(denom > 1e-12, dot / np.where(denom > 1e-12, denom, 1.0), 0.0)


def _coherence(V: np.ndarray) -> float:
    """Temporal: mean cosine between consecutive per-agent velocities (white noise → 0)."""
    if V.shape[0] < 2:
        return 0.0
    return float(np.clip(np.mean(_cos_rows(V[:-1], V[1:])), 0.0, 1.0))


def _structure(P: np.ndarray, V: np.ndarray, cfg: VivariumConfig, period=None) -> float:
    """Spatial: local organisation of the *relative* (drift-removed) velocity field.

    We subtract the global mean velocity per frame first, so a rigid coherent
    translation (all agents moving identically — the trivial "coherent drift" the
    rigor review flagged) has zero relative velocity and scores ~0. Only genuinely
    *differentiated* yet locally-aligned motion (counter-streams, vortices,
    clusters moving apart) scores high.

    (Known residual: a rigid-body *rotation* still shows differentiated velocity and
    scores high — removing rigid rotation too would need a Procrustes step; deferred.)"""
    k = min(cfg.n_neighbors, P.shape[1])
    vals = []
    for t in range(V.shape[0]):
        v = V[t] - V[t].mean(axis=0, keepdims=True)   # remove rigid translation
        idx = _neighbors_periodic(P[t], k, period)    # (N, k) — min-image on a torus
        mean_nbr_v = v[idx].mean(axis=1)              # (N, 2)
        vals.append(np.mean(_cos_rows(v, mean_nbr_v)))
    return float(np.clip(np.mean(vals), 0.0, 1.0)) if vals else 0.0


def _min_image(diff: np.ndarray, period) -> np.ndarray:
    """Wrap displacements to the nearest periodic image (no-op if period is None)."""
    if period is None:
        return diff
    return diff - period * np.round(diff / period)


def _neighbors_periodic(P_t: np.ndarray, k: int, period) -> np.ndarray:
    d = _min_image(P_t[:, None, :] - P_t[None, :, :], period)
    d2 = np.einsum("ijc,ijc->ij", d, d)
    return np.argsort(d2, axis=1, kind="stable")[:, :k]


def _deformation(P: np.ndarray, period=None) -> float:
    """Non-rigidity: how much the colony's *relative configuration* changes over the
    window. A rigid body (pure translation OR rotation) preserves all pairwise
    distances → 0. Genuine morphing/reconfiguration → > 0. This is the "morph" the
    life must actually do — and it closes the rigid-rotation loophole `_structure`
    leaves open."""
    T, N = P.shape[0], P.shape[1]
    if T < 2 or N < 2:
        return 0.0
    diff = P[:, :, None, :] - P[:, None, :, :]            # (T, N, N, 2)
    diff = _min_image(diff, period)                       # min-image on a torus (no-op if None)
    D = np.sqrt(np.einsum("tijc,tijc->tij", diff, diff) + 1e-12)  # (T, N, N) pairwise dists
    iu = np.triu_indices(N, k=1)
    pair = D[:, iu[0], iu[1]]                              # (T, P) each pair's distance over time
    cov = pair.std(axis=0) / (pair.mean(axis=0) + 1e-6)   # per-pair coefficient of variation
    return float(np.clip(np.mean(cov), 0.0, 1.0))


def score(states: np.ndarray, cfg: VivariumConfig, period=None) -> dict:
    """Score a (T, N, d) window. Pure — no engine, no side effects. `period` (the torus size L)
    makes velocities and pairwise distances min-image, so wrap-arounds don't register as
    spurious huge jumps — pass it for the periodic pack engine; leave None for clipped domains."""
    states = np.asarray(states, dtype=np.float64)
    if not np.all(np.isfinite(states)):
        return _report(0.0, gate_finite=0.0)

    P = states[:, :, :2]                          # positions (T, N, 2)
    V = _min_image(np.diff(P, axis=0), period)    # velocities (T-1, N, 2), min-image on a torus
    spread = float(np.mean(P.std(axis=1)))        # spatial spread (std over agents)
    motion = float(np.mean(np.linalg.norm(V, axis=2))) if V.size else 0.0

    gate_spread = 1.0 if _SPREAD_LO <= spread <= _SPREAD_HI else 0.0
    gate_motion = 1.0 if _MOTION_LO <= motion <= _MOTION_HI else 0.0
    coherence = _coherence(V)
    structure = _structure(P, V, cfg, period)
    deformation = _deformation(P, period)
    alive = 1.0 * gate_spread * gate_motion * coherence * structure * deformation
    return _report(
        alive,
        gate_finite=1.0,
        gate_spread=gate_spread,
        gate_motion=gate_motion,
        coherence=coherence,
        structure=structure,
        deformation=deformation,
        spread=spread,
        motion=motion,
    )


def lyapunov(engine, window: int, eps: float = 1e-4) -> float:
    """Twin-rollout largest-Lyapunov estimate: divergence rate of two forks that start
    eps apart. ≈0 edge-of-chaos, <0 contracting (dead), >0 chaotic. Diagnostic only."""
    a, b = engine.fork(), engine.fork()
    b.X = b.X.copy()
    b.X[0, 0] += eps
    for _ in range(window):
        a.step()
        b.step()
    dist = float(np.linalg.norm(a.X - b.X))
    if dist <= 0.0:
        return float("-inf")
    return float(np.log(dist / eps) / window)


def evaluate(engine, window: int = 40) -> dict:
    """Full read-only report for the engine's current regime."""
    period = getattr(engine, "L", None)   # periodic torus size for pack; None for clipped domains
    report = score(rollout_states(engine, window), engine.cfg, period)
    report["lyapunov"] = lyapunov(engine, window)
    return report


def _report(aliveness: float, **fields) -> dict:
    base = {
        "aliveness": float(aliveness),
        "gate_finite": 0.0,
        "gate_spread": 0.0,
        "gate_motion": 0.0,
        "coherence": 0.0,
        "structure": 0.0,
        "deformation": 0.0,
        "spread": 0.0,
        "motion": 0.0,
    }
    base.update(fields)
    return base
