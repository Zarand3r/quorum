"""Broad cheap search in 2-D for ANY configuration showing the bicelle signature at once.

Signs of life first. A bicelle needs three things SIMULTANEOUSLY, and so far each has been reachable
alone but never together:

    lamellar > 0.85    heads out, tails in
    aspect   < 0.50    flat ribbon, not a round droplet
    edge     < 0.50    a genuinely dry hydrophobic core, only the ends exposed

2-D with explicit water is ~10x cheaper per lipid than 3-D, and water is mandatory: gamma comes from
tail-water contact, and gamma = 0 makes closure impossible at any size.

    bazel run //projects/vivarium:search2d -- --iters 40
"""

from __future__ import annotations

import argparse
import json
import random

import numpy as np
from bicelle2d import build, edge_frac, metrics

SPACE = {
    "attract": [2.0, 5.0, 8.0, 14.0, 22.0],
    "repel": [3.0, 8.0, 12.0, 25.0],
    "headsigma": [0.6, 1.0, 1.5, 2.0],
    "tails": [2, 4, 6],
    "kt": [0.01, 0.02, 0.05],
    "lipids": [40, 80, 140],
    "waterper": [4, 6, 10],
    "satt": [0.3, 0.55, 0.9],
    "branched": [True, False],
}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--iters", type=int, default=40)
    p.add_argument("--steps", type=int, default=14000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="/tmp/vivarium_search2d.tsv")
    a = p.parse_args(argv)
    rng = random.Random(a.seed)
    with open(a.out, "w") as fh:
        fh.write("iter\tlamellar\taspect\tedge\thit\tconfig\n")

    best, best_cfg, hits = 1e9, None, 0
    for i in range(a.iters):
        c = {k: rng.choice(v) for k, v in SPACE.items()}
        if c["branched"] and c["tails"] % 2:
            c["tails"] = 4
        try:
            e = build(a.seed, n_lip=c["lipids"], bound=11.0 if c["lipids"] <= 40 else 16.0,
                      kt=c["kt"], speed=0.004, repel=c["repel"], k_bond=80.0, satt=c["satt"],
                      plant="clump", n_tail=c["tails"], head_sigma=c["headsigma"],
                      attract=c["attract"], bond_span=2.0, branched=c["branched"],
                      n_water=c["lipids"] * c["waterper"], polarity=0.80, head_q=1.2)
            for _ in range(a.steps):
                e.step()
            lam, asp, th = metrics(e)
            ed = edge_frac(e)
            mol = e._mol
            bb = np.isclose(e._bond_r0, 1.0)
            d = e.X[e._bond_i[bb], :2] - e.X[e._bond_j[bb], :2]
            d -= e.L * np.round(d / e.L)
            bond = float(np.linalg.norm(d, axis=1).mean())
        except Exception as exc:
            print(f"  [{i:3d}] CRASH {type(exc).__name__}", flush=True)
            continue
        if bond > 1.25:
            print(f"  [{i:3d}] REJECT molecule deformed (bond {bond:.2f})", flush=True)
            continue
        hit = lam > 0.85 and asp < 0.50 and ed < 0.50
        # distance from the target corner, for ranking near-misses
        score = max(0, 0.85 - lam) + max(0, asp - 0.50) + max(0, ed - 0.50)
        if score < best:
            best, best_cfg = score, c
        hits += hit
        print(f"  [{i:3d}] lam={lam:.3f} asp={asp:.3f} edge={ed:.3f} bond={bond:.2f}"
              f"{'   <<< HIT' if hit else ''}{'   <-- closest' if score == best and not hit else ''}",
              flush=True)
        with open(a.out, "a") as fh:
            fh.write(f"{i}\t{lam:.4f}\t{asp:.4f}\t{ed:.4f}\t{int(hit)}\t{json.dumps(c)}\n")
    print(f"\n  {hits} hits / {a.iters}.  closest miss score={best:.3f}")
    print(f"  config: {json.dumps(best_cfg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
