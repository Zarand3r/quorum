"""Restore head/tail segregation after the steric correction.

At the calibrated steric point (repel=48, sharp=8, k_bond=120) a self-assembled ribbon packs correctly
-- packing 0.99, bond 1.00, 60/60 connected, ADMISSIBLE -- but it does NOT segregate: heads sit
scattered through the interior instead of on the two faces, align 0.577 against the 0.862 the same
repel gives on a PLANTED sheet. The planted sheet starts segregated and merely has to hold; assembly
has to achieve segregation against a repulsion that is now 4x stronger.

This is the third instance of the same coupling. `repel` was raised to fix excluded volume, and it then
overpowered `k_bond` (fixed), and now `polarity` and `hydrophobic`, both of which were balanced against
the weak core. Vivarium's knobs are independent multipliers with no shared length scale, so correcting
one requires re-balancing the rest -- which is exactly why a single oracle fact cannot be imported.

HYPOTHESIS     scaling the segregating forces with the steric core recovers a clean self-assembled
               bilayer, align >= 0.80 at packing >= 0.9.
FALSIFICATION  if no (polarity, hydrophobic) in this range gets align above ~0.7 while staying
               admissible, segregation and excluded volume are not simultaneously satisfiable here, and
               the force field, not the parameters, is the problem.
"""
import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster, measure
from ring_assay import classify

RHO = 430.0 / (13.0 ** 2)
BASE = dict(kt=0.02, speed=0.001, k_bond=120.0, satt=0.30, n_tail=2, bond_span=2.0,
            head_q=1.2, attract=1.5, repel=48.0, sharp=8.0, head_sigma=1.0)

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    nw = 4 * n
    bound = float(np.sqrt((3 * n + nw) / RHO))
    print(f"N={n} bound={bound:.1f} repel=48 sharp=8 k_bond=120, {steps} steps "
          f"(planted-sheet reference align 0.862)", flush=True)
    for pol in (0.8, 2.4):
        for hp in (0.6, 1.8, 3.6):
            e = build(0, plant="ribbon", span_frac=0.55, n_lip=n, n_water=nw, bound=bound,
                      polarity=pol, hydrophobic=hp, **BASE)
            e.curvature = 0.0
            for _ in range(steps):
                e.step()
            m = measure(e)
            v, d = classify(e)
            render(e, f"N={n} polarity={pol} hydrophobic={hp} t={steps}",
                   f"reb_p{int(pol*10)}_h{int(hp*10)}")
            print(f"polarity={pol:>4}  hydrophobic={hp:>4}  packing {m['packing']:.2f}  "
                  f"largest {len(largest_cluster(e)):>3}/{n}  bond {m['bond_mean']:.2f}  "
                  f"align {m['align']:.3f}  ring_assay {v:<10} "
                  f"{'ADMISSIBLE' if m['ok'] else m['why'][:26]}", flush=True)
