"""LOOK at the spanning-but-disordered structure. The small box reaches spanning 0.90 with splay
0.54, and those numbers alone cannot say whether it is a bilayer with defects, a stripe that is too
thick, or something else -- exactly the ambiguity that has misled this session three times.

Renders the small-box run beside a planted spanning bilayer in the SAME box, so the comparison is on
identical axes rather than against a remembered number.
"""
from bicelle2d import build
from harness import bond_stats, measure
from references import relax, spanning_bilayer_2d
from xsection import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
DENS = 382 / (22.0 ** 2)
BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, repel=24.0)

def shot(e, tag, title):
    m = measure(e); mean, _, _ = bond_stats(e)
    sub = (f"splay {m['splay']:.3f} (bilayer <0.30)  spanning {m['spanning']:.2f} (need >0.80)  "
           f"packing {m['packing']:.3f}  bond {mean:.3f}")
    cross_section(e, f"{OUT}/{tag}", title=title, sub=sub)
    print(f"  {title:<44} splay {m['splay']:.3f}  span {m['spanning']:.2f}", flush=True)

B = 5.0
n_lip = int(round(2 * (2 * B)))
n_water = max(8, int(round(DENS * (2 * B) ** 2 - 3 * n_lip)))

# the reference, in the SAME box: what success looks like here
ref = relax(spanning_bilayer_2d(build, bound=B, n_water=n_water, **BASE), 2000)
shot(ref, "sb_ref", f"PLANTED spanning bilayer, box {2*B:.0f}, relaxed")

# the self-assembled run that reaches spanning 0.90
e = build(7, bound=B, n_lip=n_lip, n_water=n_water, plant="clump", **BASE)
for _ in range(60000):
    e.step()
shot(e, "sb_run", f"SELF-ASSEMBLED, box {2*B:.0f}, {n_lip} lipids, t=60000")
