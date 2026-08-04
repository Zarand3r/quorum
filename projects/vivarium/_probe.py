"""Can 2-D ribbons close into a vesicle?

The geometry says why they never have: a closed loop of radius R needs n = 4*pi*R lipids -- 50 at
R=4, 69 at R=5.5 -- while the ribbons this model makes hold 12-20. They were never within reach of
closing, so "ribbons do not close" was never actually tested.

Two questions, in the order that makes the second interpretable:

  1. DOES A PLANTED LOOP PERSIST? If closure is not even stable when handed over, self-assembly
     cannot produce it and the lipid count is beside the point. Tracked with `encloses`, the
     topological partition test -- planted loops read 0.030-0.032, sheets and droplets 0.001-0.009.
  2. DOES SELF-ASSEMBLY REACH IT, given enough lipids and a box that can hold the loop?
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure
from references import closed_loop_2d, relax
from xsection import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, repel=24.0)

def shot(e, tag, title):
    m = measure(e); mean, _, _ = bond_stats(e)
    sub = (f"encloses {m['encloses']:.4f} (loop 0.030, sheet 0.009)  splay {m['splay']:.3f}  "
           f"packing {m['packing']:.3f}  aspect {m['aspect']:.3f}")
    cross_section(e, f"{OUT}/{tag}", title=title, sub=sub)
    return m

print("  --- 1. does a PLANTED loop persist? ---", flush=True)
print(f"  {'R':>5}{'t':>8}{'encloses':>10}{'splay':>7}{'aspect':>8}{'pack':>7}  verdict", flush=True)
for R in (4.0, 5.5):
    e = closed_loop_2d(build, R=R, n_water=int(0.55 * (2 * 2.2 * (R + 2.5)) ** 2 / 2), **BASE)
    for t in (0, 5000, 20000):
        if t:
            relax(e, t - getattr(e, "_t", 0)); e._t = t
        m = measure(e)
        v = "SEALED" if m["encloses"] > 0.02 else "open"
        print(f"  {R:>5.1f}{t:>8}{m['encloses']:>10.4f}{m['splay']:>7.3f}{m['aspect']:>8.3f}"
              f"{m['packing']:>7.3f}  {v}", flush=True)
    shot(e, f"loop_R{str(R).replace('.','p')}", f"PLANTED loop R={R}, t=20000")

print("  --- 2. does SELF-ASSEMBLY reach it? enough lipids, box that fits ---", flush=True)
R = 4.0
bound = 2.2 * (R + 2.5)
n_lip = int(round(4 * np.pi * R))
n_water = int(0.55 * (2 * bound) ** 2 / 2)
print(f"  box {2*bound:.0f}, {n_lip} lipids (loop needs 4*pi*R), {n_water} water", flush=True)
e = build(7, n_lip=n_lip, bound=bound, n_water=n_water, plant="clump", **BASE)
for t in (10000, 40000, 100000):
    while getattr(e, "_t", 0) < t:
        e.step(); e._t = getattr(e, "_t", 0) + 1
    m = measure(e)
    v = "*** SEALED ***" if m["encloses"] > 0.02 else "open"
    print(f"  t={t:<7} encloses {m['encloses']:.4f}  splay {m['splay']:.3f}  "
          f"aspect {m['aspect']:.3f}  pack {m['packing']:.3f}  {v}", flush=True)
shot(e, "selfasm_loop", f"SELF-ASSEMBLY, {n_lip} lipids, box {2*bound:.0f}, t=100000")
