"""Aliveness — a fixed, ungameable objective for "the simulation stays alive".

The morph (fold/morph.py) is a reaction–diffusion field; we want it to keep
moving and morphing without COLLAPSING (consensus), FREEZING (fixed point),
BLOWING UP (chaos), or degenerating into structureless NOISE. You cannot iterate
toward that by eye — so this is the scalar the search/training loop optimizes.

The score is MULTIPLICATIVE with hard gates, so every trivial fate is zeroed and
only sustained, structured, coherent dynamics survive (the same anti-gaming
discipline as the economy's P2 "no order reward" — here, "no trivial-motion
reward"). It is measured on the ASYMPTOTIC window (after a warmup), averaged over
fixed seeds, so transients don't flatter a system that later dies.

    score = gate_finite · gate_spread · gate_motion · (structure · coherence)

  gate_finite  : 0 if any NaN/Inf or motion exceeds the blow-up cap
  gate_spread  : 0 below S_MIN (collapsed to consensus) → ramps to 1
  gate_motion  : 0 below M_MIN (frozen) or above M_MAX (chaotic) → band in between
  structure    : spatial richness — normalized effective rank (many-D, not a line)
  coherence    : temporal richness — 1 − spectral flatness of a global readout
                 (white noise → flatness≈1 → coherence≈0; structured oscillation → high)

Also reports a LYAPUNOV estimate (twin-rollout divergence): a fixed point
contracts (<0), chaos explodes (≫0), life sits near 0⁺ — the edge-of-chaos
diagnostic. Reported, not yet folded into the scalar.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from fold.hk import cluster_count, effective_rank, spread

# --- thresholds (documented so the gates are auditable, not magic) ---------------
S_MIN = 0.15      # spread below this ⇒ collapsed to consensus
M_MIN = 0.008     # late motion below this ⇒ frozen (fixed point)
M_RAMP = 0.05     # motion is fully "alive" by here
M_MAX = 1.2       # late motion above this ⇒ too fast (approaching chaos)
BLOWUP = 2.5      # any motion above this (or non-finite) ⇒ dead


def _smoothstep(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = min(1.0, max(0.0, (x - lo) / (hi - lo)))
    return t * t * (3.0 - 2.0 * t)


def _motion_band(m: float) -> float:
    """1 inside the living band, ramping to 0 at the frozen and chaotic edges."""
    if m < M_MIN or m > M_MAX:
        return 0.0
    return _smoothstep(m, M_MIN, M_RAMP) * (1.0 - _smoothstep(m, 0.7 * M_MAX, M_MAX))


def _spectral_flatness(sig: np.ndarray) -> float:
    """Wiener entropy of a 1-D signal ∈ (0,1]: ≈1 white noise, →0 a pure tone."""
    sig = sig - sig.mean()
    if not np.all(np.isfinite(sig)) or np.allclose(sig, 0.0):
        return 1.0
    power = np.abs(np.fft.rfft(sig)) ** 2
    power = power[1:]                       # drop DC (mean already removed)
    power = power[power > 0]
    if power.size == 0:
        return 1.0
    return float(np.exp(np.mean(np.log(power))) / np.mean(power))


@dataclass(frozen=True)
class Aliveness:
    score: float
    mean_spread: float
    mean_motion: float
    mean_rank: float
    mean_clusters: float
    coherence: float
    lyapunov: float
    finite: bool


def rollout_records(engine, ticks: int, warmup: int, proj: np.ndarray) -> dict:
    """Step an engine and record asymptotic-window observables (read-only).

    proj is a FIXED unit vector (dim d) giving a scalar global readout g_t of the
    field — its time series is the temporal-coherence probe."""
    motion, sp, rk, cl, g = [], [], [], [], []
    finite = True
    for t in range(ticks):
        engine.step()
        x = engine.x
        if not np.all(np.isfinite(x)):
            finite = False
            break
        if t < warmup:
            continue
        m = engine.residual()
        motion.append(m)
        n = x.shape[0]
        sp.append(spread(x) if n > 1 else 0.0)
        rk.append(effective_rank(x))
        cl.append(float(cluster_count(x)) if n > 1 else 1.0)
        g.append(float((x @ proj).mean()))
    return {"motion": np.array(motion), "spread": np.array(sp), "rank": np.array(rk),
            "clusters": np.array(cl), "g": np.array(g), "finite": finite}


def score_records(rec: dict, d: int) -> tuple[float, dict]:
    """Reduce recorded observables to the scalar aliveness score + its parts."""
    if not rec["finite"] or rec["motion"].size == 0:
        return 0.0, {"reason": "non-finite / no window"}
    mean_motion = float(rec["motion"].mean())
    max_motion = float(rec["motion"].max())
    mean_spread = float(rec["spread"].mean())
    mean_rank = float(rec["rank"].mean())
    mean_clusters = float(rec["clusters"].mean())
    coherence = 1.0 - _spectral_flatness(rec["g"])

    gate_finite = 0.0 if (max_motion > BLOWUP) else 1.0
    gate_spread = _smoothstep(mean_spread, S_MIN, 2.0 * S_MIN)
    gate_motion = _motion_band(mean_motion)
    structure = float(np.clip((mean_rank - 1.0) / max(d - 1.0, 1e-9), 0.0, 1.0))
    score = gate_finite * gate_spread * gate_motion * structure * coherence
    parts = {"gate_finite": gate_finite, "gate_spread": round(gate_spread, 3),
             "gate_motion": round(gate_motion, 3), "structure": round(structure, 3),
             "coherence": round(coherence, 3), "mean_spread": round(mean_spread, 3),
             "mean_motion": round(mean_motion, 4), "mean_rank": round(mean_rank, 3),
             "mean_clusters": round(mean_clusters, 2)}
    return float(score), parts


def lyapunov(make_engine, seed: int, ticks: int, eps: float = 1e-6) -> float:
    """Twin-rollout divergence rate: perturb the seed field by eps, track the log
    growth of the field gap. <0 contracts (fixed point), ≫0 chaos, ~0⁺ = edge."""
    a, b = make_engine(seed), make_engine(seed)
    b.x = b.x + eps * np.random.default_rng([seed, 999]).standard_normal(b.x.shape)
    logs = []
    prev = eps * np.sqrt(a.x.size)
    for _ in range(ticks):
        a.step(); b.step()
        if a.x.shape != b.x.shape or not (np.all(np.isfinite(a.x)) and np.all(np.isfinite(b.x))):
            break
        gap = float(np.linalg.norm(a.x - b.x))
        if gap > 0 and prev > 0:
            logs.append(np.log(gap / prev))
        prev = max(gap, 1e-12)
    return float(np.mean(logs)) if logs else 0.0


def evaluate(make_engine, seeds=(0, 1, 2, 3), ticks: int = 700, warmup: int = 300,
             d: int = 6, with_lyapunov: bool = True) -> Aliveness:
    """THE fixed harness: mean aliveness over fixed seeds (deterministic). This is
    the scalar an unattended search / ES loop maximizes. Set ``with_lyapunov=False``
    to skip the (2× cost) twin-rollout during search."""
    proj = np.random.default_rng(12345).standard_normal(d)
    proj = proj / np.linalg.norm(proj)
    scores, sp, mo, rk, cl, co = [], [], [], [], [], []
    for s in seeds:
        rec = rollout_records(make_engine(s), ticks, warmup, proj)
        sc, parts = score_records(rec, d)
        scores.append(sc)
        if rec["finite"] and rec["motion"].size:
            sp.append(float(rec["spread"].mean())); mo.append(float(rec["motion"].mean()))
            rk.append(float(rec["rank"].mean())); cl.append(float(rec["clusters"].mean()))
            co.append(1.0 - _spectral_flatness(rec["g"]))
    lyap = (float(np.mean([lyapunov(make_engine, s, min(ticks, 200)) for s in seeds]))
            if with_lyapunov else 0.0)
    m = lambda v: float(np.mean(v)) if v else 0.0
    return Aliveness(score=m(scores), mean_spread=m(sp), mean_motion=m(mo),
                     mean_rank=m(rk), mean_clusters=m(cl), coherence=m(co),
                     lyapunov=lyap, finite=all(s >= 0 for s in scores))


def main(argv: list[str] | None = None) -> int:
    """Score the default morph config against ablated (collapsing) controls."""
    from fold.morph import MorphEngine, load_morph
    cfg, p = load_morph(Path(__file__).resolve().parent.parent / "configs" / "morph.yaml")

    def factory(params):
        return lambda s: MorphEngine(cfg, seed=s, params=params)

    arms = {
        "default (oscillatory local RD)": p,
        "no oscillator (omega=0)": replace(p, omega=0.0),
        "global attention (lam=0)": replace(p, lam=0.0),
        "high diffusion (D=1.0)": replace(p, diffusion=1.0),
    }
    print(f"{'arm':34s} {'score':>7s} {'spread':>7s} {'motion':>7s} "
          f"{'rank':>6s} {'coher':>6s} {'lyap':>7s}")
    for name, params in arms.items():
        a = evaluate(factory(params), d=cfg.d)
        print(f"{name:34s} {a.score:7.3f} {a.mean_spread:7.3f} {a.mean_motion:7.3f} "
              f"{a.mean_rank:6.2f} {a.coherence:6.3f} {a.lyapunov:7.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
