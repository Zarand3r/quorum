"""The HK study — bounded-confidence attention vs global softmax, measured.

Two experiments, run from one CLI (results feed RESEARCH_HK.md):

  A. UNTRAINED DYNAMICS. Iterate random-weight folds and measure collapse:
     cluster count (single-linkage), effective rank (participation ratio),
     spread. Arms: global softmax; HK-dock (hard, τ sweep); HK-raw (hard,
     ε sweep); plus the two theory anchors with the transformer dressing
     stripped (pure averaging x←Ax): softmax must collapse to 1 cluster
     (Geshkovski/Dong), classic raw-HK must form ≥2 clusters for small ε
     (Hegselmann–Krause) — these validate the implementation, not the thesis.

  B. TRAINING WITHOUT DEEP SUPERVISION (decisive). M2's lock-and-key task,
     FINAL-STEP-ONLY loss, T=8: softmax is known to plateau near chance
     (rank collapse destroys the scene before T; M2 needed deep supervision).
     If HK-dock (sigmoid kernel) trains to high accuracy from final-step
     supervision alone, locality removes the crutch — mechanism-level evidence
     that bounded confidence is the right E1 operator. All four
     {softmax, hk} × {final, deep} arms are reported.

  bazel run //projects/thermolife:hk_study -- --exp A
  bazel run //projects/thermolife:hk_study -- --exp B --iters 800
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from fold.config import load_fold_config
from fold.hk import cluster_count, effective_rank, hk_block_step, spread
from fold.transformer import block_step
from fold.vocab import VocabConfig
from fold.weights import FoldWeights
from train.train import evaluate, train

_CFG = Path(__file__).resolve().parent.parent / "configs" / "fold.yaml"


# ---------------------------------------------------------------- experiment A

def _run_dynamics(arm: dict, cfg, n_tokens: int, t_iters: int, seed: int):
    rng = np.random.default_rng(seed)
    w = FoldWeights.random(cfg, seed)
    x = cfg.init_scale * rng.standard_normal((n_tokens, cfg.d))
    for _ in range(t_iters):
        if arm["op"] == "softmax":
            if arm.get("pure"):
                from fold.transformer import attention
                _, a = attention(x, w, cfg)
                x = a @ x
            else:
                x, _, _ = block_step(x, w, cfg)
        elif arm["op"] == "dist":
            x, _, _ = hk_block_step(x, w, cfg, space="dist", lam=arm["lam"])
        else:
            x, _, _ = hk_block_step(
                x, w, cfg, space=arm["space"], tau=arm["tau"],
                kernel="hard", use_ln=not arm.get("pure", False),
            )
    return x


def exp_a(n_tokens: int, t_iters: int, n_seeds: int, link_eps: float) -> None:
    cfg = load_fold_config(_CFG)
    arms = [
        # theory anchors (pure averaging — validate the implementation)
        {"name": "ANCHOR softmax pure",    "op": "softmax", "pure": True},
        {"name": "ANCHOR hk-raw pure e=1", "op": "hk", "space": "raw", "tau": -1.0, "pure": True},
        # the real comparison: full transformer dressing (residual+LN+MLP)
        {"name": "softmax (global)",       "op": "softmax"},
        {"name": "hk-dock t=-0.5",         "op": "hk", "space": "dock", "tau": -0.5},
        {"name": "hk-dock t=0.0",          "op": "hk", "space": "dock", "tau": 0.0},
        {"name": "hk-dock t=0.5",          "op": "hk", "space": "dock", "tau": 0.5},
        {"name": "hk-dock t=1.0",          "op": "hk", "space": "dock", "tau": 1.0},
        {"name": "hk-raw  e=1.0",          "op": "hk", "space": "raw", "tau": -1.0},
        # distance-penalized softmax (the smooth, trainable locality variant)
        {"name": "dist  lam=0.05",         "op": "dist", "lam": 0.05},
        {"name": "dist  lam=0.1",          "op": "dist", "lam": 0.1},
        {"name": "dist  lam=0.2",          "op": "dist", "lam": 0.2},
        {"name": "dist  lam=0.5",          "op": "dist", "lam": 0.5},
        {"name": "dist  lam=1.0",          "op": "dist", "lam": 1.0},
    ]
    print(f"EXP A — untrained dynamics: N={n_tokens} d={cfg.d} T={t_iters} "
          f"seeds={n_seeds} link_eps={link_eps}")
    print(f"{'arm':>22} {'clusters':>9} {'eff_rank':>9} {'spread':>8}")
    for arm in arms:
        cl, er, sp = [], [], []
        for s in range(n_seeds):
            x = _run_dynamics(arm, cfg, n_tokens, t_iters, seed=1000 + s)
            cl.append(cluster_count(x, link_eps))
            er.append(effective_rank(x))
            sp.append(spread(x))
        print(f"{arm['name']:>22} {np.mean(cl):>9.1f} {np.mean(er):>9.2f} "
              f"{np.mean(sp):>8.3f}")


# ---------------------------------------------------------------- experiment B

def exp_b(iters: int, t_steps: int, seed: int, tau: float, temp: float,
          hk_only: bool = False, lam: float = 0.1) -> None:
    cfg = load_fold_config(_CFG)
    vc = VocabConfig(n_pairs=cfg.n_tokens // 2, d=cfg.d,
                     noise_sigma=0.6, init_scale=cfg.init_scale)
    # (name, attn, deep)
    arms = [
        ("softmax final-only", "softmax", False),
        ("softmax deep",       "softmax", True),
        ("hk-dock final-only", "hk", False),
        ("dist final-only",    "dist", False),   # the trainable-locality test
        ("dist deep",          "dist", True),
    ]
    if hk_only:
        arms = [a for a in arms if a[1] in ("hk", "dist")]
    print(f"EXP B — M2 docking, T={t_steps}, iters={iters}, "
          f"tau={tau} temp={temp} lam={lam} seed={seed}")
    results = []
    for name, attn, deep in arms:
        print(f"--- arm: {name} ---")
        params, w0, _ = train(
            cfg, vc, t_steps=t_steps, iters=iters, batch=16, lr=3e-3, seed=seed,
            attn=attn, tau=tau, temp=temp, deep=deep, lam=lam,
            log=lambda s: print(f"  {s}"),
        )
        acc = evaluate(params, w0, vc, cfg, t_steps, n_scenes=200, seed=123_456,
                       attn=attn, tau=tau, temp=temp, lam=lam)
        results.append((name, acc))
        print(f"  FINAL held-out accuracy (200 scenes): {acc:.4f}")
    print("\nEXP B SUMMARY")
    for name, acc in results:
        print(f"  {name:>20}: {acc:.4f}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="HK bounded-confidence attention study")
    p.add_argument("--exp", choices=["A", "B"], required=True)
    p.add_argument("--n-tokens", type=int, default=64)
    p.add_argument("--t-iters", type=int, default=200)
    p.add_argument("--n-seeds", type=int, default=5)
    p.add_argument("--link-eps", type=float, default=0.5)
    p.add_argument("--iters", type=int, default=800)
    p.add_argument("--t-steps", type=int, default=8)
    p.add_argument("--tau", type=float, default=0.0)
    p.add_argument("--temp", type=float, default=0.1)
    p.add_argument("--lam", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--hk-only", action="store_true",
                   help="exp B: run only the hk arms (τ/temp follow-ups)")
    args = p.parse_args(argv)
    if args.exp == "A":
        exp_a(args.n_tokens, args.t_iters, args.n_seeds, args.link_eps)
    else:
        exp_b(args.iters, args.t_steps, args.seed, args.tau, args.temp,
              hk_only=args.hk_only, lam=args.lam)
    return 0


if __name__ == "__main__":
    sys.exit(main())
