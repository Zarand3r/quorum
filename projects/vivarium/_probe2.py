"""Cross-sections with the cut axis chosen from the structure, not fixed at z."""
import numpy as np
from bilayer3d import build
from harness import measure
from references import clump_start, micelle_3d, relax, spanning_bilayer_3d
from render import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
FIG = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.55, spol=0.90, attract=1.0,
           polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)

def shot(e, tag, title):
    m = measure(e)
    sub = (f"splay {m['splay']:.3f} (bilayer 0.00 | micelle 0.605 | random 1.103)   "
           f"packing {m['packing']:.3f}")
    p = cross_section(e, f"{OUT}/{tag}", title=title, sub=sub, thickness=2.0)
    print(f"  {title:<44} splay {m['splay']:.3f} -> {p}", flush=True)

shot(spanning_bilayer_3d(build, bound=3.4, **FIG),
     "xs_ref_bilayer0", "REFERENCE: planted 3-D bilayer, t=0 (pristine)")
shot(relax(spanning_bilayer_3d(build, bound=3.4, **FIG), 500),
     "xs_ref_bilayer", "REFERENCE: planted 3-D bilayer, relaxed 500")
e = clump_start(build(3, n_lip=30, bound=4.5, plant=False, head_sigma=1.0, **FIG))
for _ in range(8000):
    e.step()
shot(e, "xs_run_hs1", "RUN: 3-D self-assembly, head_sigma 1.0, t=8000")
