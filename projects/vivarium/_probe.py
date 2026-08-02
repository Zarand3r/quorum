"""The head_sigma sweep never reached the lamellar band, but 30 lipids CANNOT form a 3-D bilayer:
a patch of radius R needs ~pi*R^2/a0 lipids PER LEAFLET, so even a minimal R=3 patch needs ~56 total.
The structure was below its own existence threshold, so that sweep could not have found it whatever
the head size did.

Lipids are cheap next to solvent -- N 626 -> ~800 is 1.5x, against the L^6 wall that makes a bigger
BOX unaffordable -- so raise the lipid count instead and keep the box fixed.

Scored on `splay` (the lamellar criterion). Bands: bilayer 0.000 | micelle 0.605 | random 1.103.
"""
import numpy as np
from bilayer3d import build
from harness import bond_stats, largest_cluster, measure
from references import clump_start
from xsection import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
FIG = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.55, spol=0.90, attract=1.0,
           polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)
assert 0.001 * 30.0 / (1 - 0.30) < 0.05

print(f"  {'n_lip':>6}{'head_sig':>9}{'N':>6}{'t':>7}{'splay':>7}{'enrich':>8}{'pack':>7}"
      f"{'aggr':>6}  reading", flush=True)
for n_lip in (70, 110):
    for hs in (0.65, 0.85):
        e = clump_start(build(3, n_lip=n_lip, bound=4.5, plant=False, head_sigma=hs, **FIG))
        for t in (5000, 18000):
            while getattr(e, "_t", 0) < t:
                e.step(); e._t = getattr(e, "_t", 0) + 1
            m = measure(e); mean, _, _ = bond_stats(e)
            frac = len(largest_cluster(e)) / max(len(e._mol), 1)
            reading = ("LAMELLAR" if m["splay"] < 0.35 else
                       "part-lamellar" if m["splay"] < 0.60 else
                       "micelle" if m["head_enrich"] > 2.5 else
                       "inverted" if m["head_enrich"] < 1.0 else "partial")
            print(f"  {n_lip:>6}{hs:>9.2f}{len(e.X):>6}{t:>7}{m['splay']:>7.3f}"
                  f"{m['head_enrich']:>8.2f}{m['packing']:>7.3f}{frac:>6.2f}  {reading}"
                  f"{'' if m['ok'] else '  [' + m['why'][:14] + ']'}", flush=True)
        cross_section(e, f"{OUT}/big_{n_lip}_{str(hs).replace('.','p')}",
                      title=f"3-D, {n_lip} lipids, head_sigma {hs}, t=18000",
                      sub=f"splay {m['splay']:.3f} (bilayer 0.00)  enrich {m['head_enrich']:.2f}  "
                          f"packing {m['packing']:.3f}")
