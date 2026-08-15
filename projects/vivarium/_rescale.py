"""If the failure is scale separation, rescaling the WHOLE parameter vector should fix it.

At repel=48 the steric core carries energy scale 48 while the chemistry that distinguishes head from
tail carries 0.6-3.6. Head/tail identity is then a small perturbation on a hard-sphere packing problem,
and the system packs densely while ignoring which bead is which -- align 0.577 from assembly against
0.862 for a planted sheet, stationary over 60000 steps and unchanged by annealing.

Raising polarity and hydrophobic ALONE cannot fix that, and the sweep confirms it did not. The
prediction is sharper: since `repel` went up 4x, every other interaction must go up 4x TOO, so that the
ratios that made the original configuration work are restored at the new steric strength.

HYPOTHESIS     the working configuration is a set of RATIOS, not of values. Scale attract, polarity,
               hydrophobic, satt and head_q by the same 4x that repel took, and self-assembly returns
               to a clean bilayer (align >= 0.8).
FALSIFICATION  if the fully rescaled vector still lands near 0.58, the failure is not scale separation,
               and the head/tail chemistry itself cannot compete with excluded volume at any scale.

The x1 arm is the control: original ratios at the ORIGINAL repel=12, which is where the historical
bilayers and micelles came from. It must reproduce them, or the comparison means nothing.
"""
import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster, measure
from ring_assay import classify

RHO = 430.0 / (13.0 ** 2)
# the historical working vector, at repel=12
BASE1 = dict(repel=12.0, k_bond=30.0, attract=1.5, polarity=0.80, hydrophobic=0.6, satt=0.30,
             head_q=1.2)

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    n, nw = 60, 240
    bound = float(np.sqrt((3 * n + nw) / RHO))
    print(f"N={n} bound={bound:.1f}, {steps} steps. Every interaction scaled together by lam; "
          f"lam=1 is the historical vector.", flush=True)
    print(f"{'lam':>5}{'repel':>7}{'attract':>9}{'polar':>7}{'phobic':>8}{'k_bond':>8}"
          f"{'packing':>9}{'align':>7}   ring_assay / admissibility", flush=True)
    for lam in (1.0, 4.0):
        kw = {k: v * lam for k, v in BASE1.items()}
        e = build(0, plant="ribbon", span_frac=0.55, n_lip=n, n_water=nw, bound=bound,
                  kt=0.02, speed=0.001, sharp=8.0, head_sigma=1.0, n_tail=2, bond_span=2.0, **kw)
        e.curvature = 0.0
        for _ in range(steps):
            e.step()
        m = measure(e)
        v, d = classify(e)
        render(e, f"all interactions x{lam:g}, t={steps}", f"rescale_x{int(lam)}")
        print(f"{lam:>5.0f}{kw['repel']:>7.0f}{kw['attract']:>9.1f}{kw['polarity']:>7.1f}"
              f"{kw['hydrophobic']:>8.1f}{kw['k_bond']:>8.0f}{m['packing']:>9.2f}{m['align']:>7.3f}"
              f"   {v:<10} {len(largest_cluster(e))}/{n} "
              f"{'ADMISSIBLE' if m['ok'] else m['why'][:26]}", flush=True)
