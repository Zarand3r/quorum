"""The null controls that were never run. The 2-D stage-2 claim rests on splay 0.253 = "BILAYER",
but the 2-D RANDOM null was never measured -- only the 3-D one. If random reads near 0.3, that claim
is not supported. Same for `packing`, which has structure references but no null.
"""
import numpy as np
from bicelle2d import build
from harness import measure, packing, solvation, splay
from references import micelle_2d, relax, spanning_bilayer_2d

FIG = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0,
           bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)

print(f"  {'2-D structure':<34}{'splay':>8}{'packing':>9}{'solvation':>11}{'align':>8}", flush=True)

def row(label, e):
    m = measure(e)
    print(f"  {label:<34}{m['splay']:>8.3f}{m['packing']:>9.3f}{m['solvation']:>11.2f}"
          f"{m['align']:>8.3f}", flush=True)

bil = spanning_bilayer_2d(build, **FIG)
row("planted bilayer (t=0)", bil)
row("planted bilayer (relaxed)", relax(bil, 500))
mic = micelle_2d(build, n_lip=20, **FIG)
row("planted micelle (relaxed)", relax(mic, 500))

# THE MISSING CONTROL: random positions, random orientations, no aggregation
for seed in (5, 17):
    e = build(seed, n_lip=63, bound=11.0, plant=False, **FIG)
    row(f"RANDOM NULL t=0 (seed {seed})", e)

# and the claim under test
e = build(7, n_lip=63, bound=11.0, plant=False, **FIG)
for _ in range(20000):
    e.step()
row("the stage-2 ribbons (t=20k)", e)
