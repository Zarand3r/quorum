"""Does a finite bilayer patch close when it is big enough? The edge-tension criterion.

WHY THIS AND NOT SPONTANEOUS CURVATURE
    `_patch_close.py` tested cone-shaped lipids (head_sigma > 1) and found they DISORDER the bilayer
    rather than bend it: align fell 0.856 -> 0.400 and the aggregate stayed filled. That is correct
    physics, not a failure. A symmetric bilayer gives both leaflets the same enlarged head, so the two
    spontaneous curvatures cancel; a cone curves a MONOLAYER. Closure of a bilayer is driven by the
    line tension of its exposed edge, where tails meet water.

THE CRITERION
    In 2-D a ribbon of contour length L pays a fixed edge cost 2*lambda to stay open, and a bending
    cost ~kappa/L to close into a circle of radius L/2pi. Closure wins when

        kappa / L  <  2 * lambda,

    so closure gets EASIER as the patch grows, and there is a critical size L* ~ kappa / (2 lambda).
    Both knobs are fundamental forces already in the engine: lambda is set by `hydrophobic` (the cost
    of exposing a tail to water), kappa by the steric core and the bond.

HYPOTHESIS     above some N, a finite ribbon closes into a hollow ring on its own, with no curvature
               term and no imported angular potential.
FALSIFICATION  if every N up to 160 stays `filled` at the strongest admissible edge tension, then
               2-D closure is not reachable from this force field and the milestone belongs in 3-D.

STERIC CALIBRATION NOTE
    `_steric.py` found repel=12 with a saturating core reaches 0.96 of contact, but it measured on a
    PLANTED FLAT SHEET -- the easy geometry: low coordination, no curvature stress. The same setting
    reads 0.13 on a condensed ribbon that has balled up, because a 2-D blob packs every bead against
    many more neighbours and cohesion wins. Excluded volume must be calibrated on the geometry that
    actually occurs, so `repel` is swept here rather than assumed.

Density is held FIXED across N -- a previous size sweep varied `bound` not at all while N changed, so
token density ran 0.39-0.82 and the largest rings were the most dilute. Here bound scales as
sqrt(tokens / rho) with rho pinned to the working configuration's 2.544.
"""
import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster, measure
from ring_assay import classify

RHO = 430.0 / (13.0 ** 2)          # tokens per unit area in the validated working configuration

BASE = dict(kt=0.02, speed=0.001, k_bond=120.0, satt=0.30, n_tail=2, bond_span=2.0,
            polarity=0.80, head_q=1.2, attract=1.5)

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    sizes = [int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "60,100,160").split(",")]
    phobs = [float(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "0.6").split(",")]
    repels = [float(v) for v in (sys.argv[4] if len(sys.argv) > 4 else "12,48,96").split(",")]
    print(f"finite ribbon, repel=12 sharp=8 k_bond=120, density fixed at {RHO:.3f}, {steps} steps",
          flush=True)
    for rp in repels:
      for hp in phobs:
        for n in sizes:
            nw = 4 * n
            bound = float(np.sqrt((3 * n + nw) / RHO))
            e = build(0, plant="ribbon", span_frac=0.55, repel=rp, sharp=8.0, head_sigma=1.0,
                      n_lip=n, n_water=nw, bound=bound, hydrophobic=hp, **BASE)
            e.curvature = 0.0
            for _ in range(steps):
                e.step()
            m = measure(e)
            v, d = classify(e)
            render(e, f"finite ribbon N={n} repel={rp} hydrophobic={hp} t={steps}",
                   f"edge_r{int(rp)}_h{int(hp*10)}_N{n}")
            print(f"repel={rp:>5.0f}  hydrophobic={hp:>4}  N={n:>4}  packing {m['packing']:.2f}"
                  f"  largest {len(largest_cluster(e)):>3}/{n}"
                  f"  bond {m['bond_mean']:.2f}  ring_assay {v:<10} lumen/bulk {d.get('lumen_ratio', 0):.2f}"
                  f"  align {m['align']:.3f}  {'ADMISSIBLE' if m['ok'] else m['why'][:24]}", flush=True)
