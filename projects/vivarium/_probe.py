"""3-D micelle question on the corrected molecule, from a CLUMP start.

Clump supplies proximity and NOT order (random positions in a ball, random orientations), which
separates "can dispersed molecules find each other" -- diffusion, slow, and what dominated the
previous 3-D runs at 25% aggregated after 5000 steps -- from "can molecules already together
ORDER", the actual question.

head_sigma is a real lever again now that per-species radius reaches the contact distance, and
micelles need a head WIDER than the tail (P < 1/3), i.e. head_sigma > 1.

Bands, all measured, including the random nulls that were missing until today:
    3-D:  bilayer 0.000 | micelle 0.605 | random 1.103
"""
import numpy as np
from bilayer3d import build
from harness import bond_stats, largest_cluster, measure
from references import clump_start

MOM, KB, SPEED = 0.30, 30.0, 0.001
assert SPEED * KB / (1 - MOM) < 0.05, "timestep violates the stability limit"
FIG = dict(kt=0.02, speed=SPEED, repel=12.0, k_bond=KB, satt=0.55, spol=0.90, attract=1.0,
           polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)

print("  bands: bilayer 0.000 | micelle 0.605 | random 1.103", flush=True)
print(f"  {'head_sig':>9}{'t':>7}{'splay':>7}{'pack':>7}{'align':>7}{'aggr':>6}{'bond':>7}  call",
      flush=True)
for hs in (1.0, 1.6, 2.2):
    e = clump_start(build(3, n_lip=30, bound=4.5, plant=False, head_sigma=hs, **FIG))
    for t in (2000, 8000, 20000):
        while getattr(e, "_t", 0) < t:
            e.step(); e._t = getattr(e, "_t", 0) + 1
        m = measure(e); mean, _, _ = bond_stats(e)
        frac = len(largest_cluster(e)) / max(len(e._mol), 1)
        call = ("BILAYER" if m["splay"] < 0.30 else
                "MICELLE" if 0.45 <= m["splay"] <= 0.80 else
                "disordered" if m["splay"] > 0.95 else "partial")
        print(f"  {hs:>9.1f}{t:>7}{m['splay']:>7.3f}{m['packing']:>7.3f}{m['align']:>7.3f}"
              f"{frac:>6.2f}{mean:>7.3f}  {call}", flush=True)
