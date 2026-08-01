"""Does a DOUBLE-TAILED lipid hold a bilayer where the single-tailed one melts? The single-tailed
screen retained 28% of planted order by t=6000 and shrinking the head only caused collapse, so the
remaining lever is the second tail: it doubles v at fixed a0 and l, moving P from the micelle range
(<1/3) into the bilayer range (1/2..1).
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure
from references import relax, spanning_bilayer_2d, spanning_bilayer_2d_branched

FIG = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30, attract=1.0,
           bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)

print(f"  {'lipid':<22}{'t':>7}{'packing':>9}{'align':>7}{'bond':>7}{'bad':>6}  retained", flush=True)
for name, mk in (("single tail (n=2)", lambda: spanning_bilayer_2d(build, n_tail=2, **FIG)),
                 ("DOUBLE tail (n=4)", lambda: spanning_bilayer_2d_branched(build, n_tail=4, **FIG))):
    e = mk()
    a0 = measure(e)["align"]
    m0 = measure(e); mean0, _, frac0 = bond_stats(e)
    print(f"  {name:<22}{0:>7}{m0['packing']:>9.3f}{a0:>7.3f}{mean0:>7.3f}{frac0:>6.2f}  planted",
          flush=True)
    for t, step in ((500, 500), (2000, 1500), (6000, 4000), (20000, 14000)):
        relax(e, step)
        m = measure(e); mean, _, frac = bond_stats(e)
        print(f"  {name:<22}{t:>7}{m['packing']:>9.3f}{m['align']:>7.3f}{mean:>7.3f}{frac:>6.2f}"
              f"  {m['align']/max(a0,1e-9):.0%}", flush=True)
