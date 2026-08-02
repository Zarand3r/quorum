"""Did 2-D fail for the same reason 3-D did?

The 3-D bilayer was being CRUSHED, not melted: at attract/repel = 1/12 packing fell to 0.24, and
raising repel to 96 held packing at 0.90 and showed the melting was real. Every 2-D run in this
project also used repel=12 with attract=1.0 -- the same 1/12 ratio -- and the 2-D planted bilayer
degrades on BOTH axes at once (packing 1.000 -> 0.484, align 0.883 -> 0.275), which is the same
signature. 2-D was never run above repel 12.

If the 2-D bilayer HOLDS at higher repel, then stage 3 in 2-D was a collapse artifact all along.
Bands (2-D): splay bilayer 0.00-0.21 | micelle 0.52 | random 0.60-0.70.
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure
from references import spanning_bilayer_2d

BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)

print("  2-D bands: splay bilayer 0.00-0.21 | micelle 0.52 | random 0.60-0.70", flush=True)
print(f"  {'repel':>6}{'ratio':>8}{'t':>7}{'splay':>7}{'pack':>7}{'align':>7}{'bond':>7}  verdict",
      flush=True)
for rp in (12.0, 24.0, 48.0, 96.0):
    e = spanning_bilayer_2d(build, bound=11.0, repel=rp, **BASE)
    for t in (500, 2000, 8000, 20000):
        while getattr(e, "_t", 0) < t:
            e.step(); e._t = getattr(e, "_t", 0) + 1
        m = measure(e); mean, _, _ = bond_stats(e)
        verdict = ("HOLDS" if m["splay"] < 0.30 and m["packing"] > 0.35 else
                   "collapsed" if m["packing"] < 0.35 else
                   "degrading" if m["splay"] < 0.50 else "melted")
        print(f"  {rp:>6.0f}{1.0/rp:>8.3f}{t:>7}{m['splay']:>7.3f}{m['packing']:>7.3f}"
              f"{m['align']:>7.3f}{mean:>7.3f}  {verdict}", flush=True)
