"""Re-run the 3-D micelle question on the CORRECTED molecule.

Every previous 3-D run had water, heads and tails at one steric radius, so it could not express the
packing parameter at all. With per-species sigma now reaching the contact distance, head_sigma is a
real lever again -- and micelles need a head WIDER than the tail (P < 1/3), which is head_sigma > 1.

Bands, all measured (planted references plus the random null, which was the control missing until
now):  bilayer 0.000   micelle 0.605   RANDOM 1.103
"""
import numpy as np
from bilayer3d import build
from harness import bond_stats, largest_cluster, measure

MOM, KB, SPEED = 0.30, 30.0, 0.001
assert SPEED * KB / (1 - MOM) < 0.05
FIG = dict(kt=0.02, speed=SPEED, repel=12.0, k_bond=KB, satt=0.55, spol=0.90, attract=1.0,
           polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)

print("  bands: bilayer 0.000 | micelle 0.605 | random 1.103", flush=True)
print(f"  {'head_sigma':>11}{'t':>8}{'splay':>7}{'pack':>7}{'align':>7}{'aggr':>7}{'bond':>7}  call",
      flush=True)
for hs in (1.0, 1.6, 2.2):
    e = build(3, n_lip=30, bound=4.5, plant=False, head_sigma=hs, **FIG)
    for t in (5000, 20000, 50000):
        while getattr(e, "_t", 0) < t:
            e.step(); e._t = getattr(e, "_t", 0) + 1
        m = measure(e); mean, _, _ = bond_stats(e)
        frac = len(largest_cluster(e)) / max(len(e._mol), 1)
        call = ("BILAYER" if m["splay"] < 0.30 else
                "MICELLE" if 0.45 <= m["splay"] <= 0.80 else
                "disordered" if m["splay"] > 0.95 else "partial")
        print(f"  {hs:>11.1f}{t:>8}{m['splay']:>7.3f}{m['packing']:>7.3f}{m['align']:>7.3f}"
              f"{frac:>7.2f}{mean:>7.3f}  {call} {'ok' if m['ok'] else m['why'][:14]}", flush=True)
