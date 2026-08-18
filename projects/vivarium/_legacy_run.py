"""Run the PRE-ORACLE vivarium as an independent implementation, for a three-way comparison.

The pre-oracle engine is recovered verbatim from tag `vivarium-pre-oracle` (commit 3a70fce) into
`legacy/`, so it is not affected by any subsequent edit to `pack.py`. That matters: the current
`pack.py` has had a curvature term added and removed, its admissibility floor raised, and species-pair
matrices introduced, and comparing against it would not be comparing against what actually produced
the historical phenotypes.

WHAT IS COMPARED, AND WHAT IS NOT
    `align` is deliberately NOT the headline. It reads 0.837 on the historical configuration whose
    beads sit at 0.15 of contact, because it is computed from DIRECTIONS, which stay well defined at
    any density. The comparison is on physically meaningful quantities: median nearest non-bonded
    separation over contact (does matter occupy space), and the largest connected aggregate.

This is one rung of the bridge experiment: the old engine at its own recorded configuration, so its
historical phenotype can be reproduced before any like-for-like comparison is attempted.
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import largest_cluster
from harness import measure, packing

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    attract = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
    n_lip = int(sys.argv[3]) if len(sys.argv) > 3 else 63

    e = build(0, n_lip=n_lip, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
              satt=0.30, plant="clump", n_tail=2, attract=attract, bond_span=2.0,
              n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)
    print(f"PRE-ORACLE vivarium (tag vivarium-pre-oracle), n_lip={n_lip}, attract={attract}, "
          f"{steps} steps", flush=True)
    print(f"{'step':>8}{'packing':>9}{'largest':>9}{'align':>8}   admissible", flush=True)
    every = max(steps // 5, 1)
    for t in range(steps + 1):
        if t % every == 0:
            m = measure(e)
            print(f"{t:>8}{packing(e):>9.3f}{len(largest_cluster(e)):>6}/{n_lip:<3}"
                  f"{m['align']:>8.3f}   {'yes' if m['ok'] else m['why'][:34]}", flush=True)
        e.step()
