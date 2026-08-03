"""Measure R_crit: below what radius does a closed 2-D loop stop being stable?

Closure trades edge energy against bending -- G_edge = 2*pi*R*gamma falls as R shrinks while bending
cost rises -- so below some radius a loop springs open. That radius decides whether the finite
ribbons this model already makes (12-20 lipids, splay 0.253, stable 130k steps) can ever close into
a vesicle, which is the project's actual target and does NOT depend on the periodic box the way a
spanning bilayer does.

A loop that HOLDS reads: edge -> 0 (no exposed tails), splay low (locally lamellar), enclosed finite
(solvent trapped inside). A loop that opens reads rising edge and falling enclosed.
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure
from references import closed_loop_2d, relax

BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, repel=24.0, n_water=250)

print(f"  {'R':>5}{'n_lip':>6}{'box':>6}{'t':>7}{'splay':>7}{'edge':>7}{'encl':>7}{'pack':>7}"
      f"{'aspect':>8}  verdict", flush=True)
for R in (3.0, 4.0, 5.5):
    try:
        e = closed_loop_2d(build, R=R, **BASE)
    except ValueError as err:
        print(f"  R={R}: {err}", flush=True); continue
    n_lip, bound = len(e._mol), e.cfg.pos_bound
    for t in (0, 2000, 10000, 40000):
        if t:
            relax(e, t - getattr(e, "_t", 0)); e._t = t
        m = measure(e); mean, _, _ = bond_stats(e)
        verdict = ("HOLDS" if m["edge"] < 0.15 and m["packing"] > 0.35 else
                   "collapsed" if m["packing"] < 0.35 else "opened")
        print(f"  {R:>5.1f}{n_lip:>6}{2*bound:>6.0f}{t:>7}{m['splay']:>7.3f}{m['edge']:>7.3f}"
              f"{m['enclosed']:>7.3f}{m['packing']:>7.3f}{m['aspect']:>8.3f}  {verdict}", flush=True)
