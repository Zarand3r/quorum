"""Heedless hyperparameter search for a LIVING morph (fold/morph.py).

Maximizes the ungameable aliveness score (train/aliveness.py) over the reaction–
diffusion knobs — no eyeballing SVGs. Random search with a cheap eval budget, then
re-scores the top candidates at the full budget so the winner isn't a short-rollout
fluke. Deterministic given --seed (the sampler RNG is fixed), so a run reproduces.

  bazel run //projects/thermolife:morph_search -- --samples 60
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

import numpy as np

from fold.config import load_fold_config
from fold.morph import MorphEngine, MorphParams, load_morph
from train.aliveness import evaluate

_CFG = Path(__file__).resolve().parent.parent / "configs" / "morph.yaml"

# search space: (log-)uniform ranges over the RD dynamics + embedding dim
_SPACE = {
    "d": [6, 8, 10, 12],
    "dt": (0.05, 0.13),
    "diffusion": (0.0, 0.30),
    "reaction": (0.15, 0.60),
    "omega": (0.3, 1.4),
    "lam": (1.0, 3.5),
    "jitter": (0.4, 0.9),
}


def _sample(rng: np.random.Generator) -> dict:
    s = {"d": int(rng.choice(_SPACE["d"]))}
    for k in ("dt", "diffusion", "reaction", "omega", "lam", "jitter"):
        lo, hi = _SPACE[k]
        s[k] = float(rng.uniform(lo, hi))
    return s


def _factory(base_cfg, base_p: MorphParams, s: dict):
    cfg = dataclasses.replace(base_cfg, d=s["d"])
    p = dataclasses.replace(base_p, dt=s["dt"], diffusion=s["diffusion"],
                            reaction=s["reaction"], omega=s["omega"], lam=s["lam"],
                            jitter=s["jitter"])
    return cfg, p


def search(samples: int, seed: int, log=print) -> list[dict]:
    base_cfg, base_p = load_morph(_CFG)
    rng = np.random.default_rng(seed)
    results = []
    for i in range(samples):
        s = _sample(rng)
        cfg, p = _factory(base_cfg, base_p, s)
        a = evaluate(lambda sd: MorphEngine(cfg, seed=sd, params=p),
                     seeds=(0, 1, 2), ticks=420, warmup=230, d=s["d"],
                     with_lyapunov=False)                    # cheap eval
        results.append({**s, "score": a.score, "spread": a.mean_spread,
                        "rank": a.mean_rank, "coher": a.coherence, "motion": a.mean_motion})
        if (i + 1) % 10 == 0:
            best = max(r["score"] for r in results)
            log(f"[search] {i+1}/{samples}  best_so_far={best:.3f}")
    results.sort(key=lambda r: -r["score"])
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="search morph RD params for aliveness")
    ap.add_argument("--samples", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--verify-top", type=int, default=5)
    args = ap.parse_args(argv)

    results = search(args.samples, args.seed)
    print(f"\n[search] top {args.verify_top} at FULL budget (seeds 0-3, 700 ticks):")
    base_cfg, base_p = load_morph(_CFG)
    print(f"  {'score':>6s} {'spread':>6s} {'rank':>5s} {'coher':>5s} {'lyap':>6s}  params")
    for r in results[:args.verify_top]:
        cfg, p = _factory(base_cfg, base_p, r)
        a = evaluate(lambda sd: MorphEngine(cfg, seed=sd, params=p),
                     seeds=(0, 1, 2, 3), ticks=700, warmup=300, d=r["d"])
        print(f"  {a.score:6.3f} {a.mean_spread:6.3f} {a.mean_rank:5.2f} {a.coherence:5.3f} "
              f"{a.lyapunov:6.3f}  d={r['d']} dt={r['dt']:.3f} D={r['diffusion']:.3f} "
              f"R={r['reaction']:.3f} Om={r['omega']:.3f} lam={r['lam']:.2f} jit={r['jitter']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
