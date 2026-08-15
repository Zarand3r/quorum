"""Is the self-assembled slab kinetically trapped, or is it the equilibrium state?

At repel=48 a PLANTED bilayer holds align 0.862, but self-assembly from a ribbon reaches only
0.44-0.60 regardless of polarity (0.8, 2.4) or hydrophobic (0.6, 1.8, 3.6). A planted sheet starts
segregated and only has to hold; assembly has to get there against a core that is now 4x stronger,
which slows every rearrangement.

Two readings, and they demand opposite responses:
  KINETIC        align still rising at 20k steps -> run longer, or anneal from a hotter start.
  THERMODYNAMIC  align flat since ~5k steps      -> the mixed slab IS this force field's preferred
                 state, and no amount of running will produce a bilayer.

DISCRIMINATOR  align(t) sampled through 100k steps, plus a hot-start arm at 4x temperature cooled to
               the working kT. If the hot arm ends materially higher than the cold arm at the same
               step count, the cold arm was trapped.
"""
import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster, measure

RHO = 430.0 / (13.0 ** 2)
BASE = dict(speed=0.001, k_bond=120.0, satt=0.30, n_tail=2, bond_span=2.0, head_q=1.2,
            attract=1.5, repel=48.0, sharp=8.0, head_sigma=1.0, polarity=0.80, hydrophobic=0.6)

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    n, nw = 60, 240
    bound = float(np.sqrt((3 * n + nw) / RHO))
    for arm in ("cold", "annealed"):
        e = build(0, plant="ribbon", span_frac=0.55, n_lip=n, n_water=nw, bound=bound,
                  kt=0.02, **BASE)
        e.curvature = 0.0
        print(f"\n[{arm}] N={n} repel=48 -- planted-sheet reference align 0.862", flush=True)
        every = max(steps // 10, 1)
        for t in range(steps):
            if arm == "annealed":
                # hot start, cooled linearly to the working temperature over the first half
                frac = min(t / (0.5 * steps), 1.0)
                e.temperature = 0.08 * (1.0 - frac) + 0.02 * frac
            e.step()
            if (t + 1) % every == 0:
                m = measure(e)
                print(f"  t={t + 1:>7}  align {m['align']:.3f}  packing {m['packing']:.2f}  "
                      f"largest {len(largest_cluster(e)):>3}/{n}  bond {m['bond_mean']:.2f}",
                      flush=True)
        render(e, f"{arm} N={n} repel=48 t={steps}", f"anneal_{arm}")
