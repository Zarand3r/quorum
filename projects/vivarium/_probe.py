"""Re-run the head-size stability screen where packing HOLDS.

The first screen ran at repel=12, inside the collapse regime: packing fell to 0.24-0.32, below the
0.35 floor, so "the bilayer melted" was confounded with "the bilayer was crushed". Raising repel
separates them -- at repel 96 packing stays at 0.90 with no interpenetration at all -- and only then
does the melting mean what it appears to.

head_sigma is a fraction of the tail radius, so < 1 is a NARROW head (raises P toward the bilayer
window) and > 1 is a WIDE head (lowers P toward micelles).
"""
import numpy as np
from bilayer3d import build
from harness import bond_stats, measure
from references import spanning_bilayer_3d

MOM, KB, SPEED = 0.30, 30.0, 0.001
assert SPEED * KB / (1 - MOM) < 0.05
BASE = dict(kt=0.02, speed=SPEED, k_bond=KB, satt=0.55, spol=0.90, attract=1.0, repel=96.0,
            polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)

print("  repel=96 (packing holds ~0.90).  splay: 0.000 lamellar | 0.605 micelle | 1.103 random",
      flush=True)
print(f"  {'head_sig':>9}{'t':>7}{'splay':>7}{'pack':>7}{'align':>7}{'bond':>7}  verdict", flush=True)
for hs in (0.5, 0.7, 1.0, 1.4):
    e = spanning_bilayer_3d(build, bound=3.4, head_sigma=hs, **BASE)
    for t in (500, 2000, 8000):
        while getattr(e, "_t", 0) < t:
            e.step(); e._t = getattr(e, "_t", 0) + 1
        m = measure(e); mean, _, _ = bond_stats(e)
        verdict = ("HOLDS" if m["splay"] < 0.35 and m["packing"] > 0.35 else
                   "collapsed" if m["packing"] < 0.35 else
                   "degrading" if m["splay"] < 0.60 else "melted")
        print(f"  {hs:>9.2f}{t:>7}{m['splay']:>7.3f}{m['packing']:>7.3f}{m['align']:>7.3f}"
              f"{mean:>7.3f}  {verdict}", flush=True)
