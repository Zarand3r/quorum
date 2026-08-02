"""The 2-D lamellar phase IS stable at repel 24 -- a planted spanning bilayer holds and ORDERS,
splay 0.197 -> 0.121 -> 0.098 with packing 0.87. Every earlier 2-D run used repel 12, inside the
collapse regime, so stage 3 was blocked by force balance rather than thermodynamics.

That makes self-assembly a KINETIC question: the target phase exists, so the only remaining issue is
whether disorder can reach it. Run it from a clump start (proximity supplied, order NOT) at the
ratio that works.

Stage 3 criterion, all three at once:
    splay < 0.30   AND   spanning > 0.8   AND   packing > 0.35
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, largest_cluster, measure
from xsection import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6)

def spanning_frac(e):
    comp = largest_cluster(e)
    if len(comp) < 3:
        return 0.0
    x = np.mod(e.X[e._mol[comp].ravel(), 0] + e.cfg.pos_bound, 2 * e.cfg.pos_bound)
    nb = max(8, int(2 * e.cfg.pos_bound))
    return float(len(np.unique((x / (2 * e.cfg.pos_bound) * nb).astype(int))) / nb)

print("  stage 3 needs splay<0.30 AND spanning>0.8 AND packing>0.35, together", flush=True)
print(f"  {'repel':>6}{'n_lip':>6}{'t':>7}{'splay':>7}{'span':>6}{'pack':>7}{'align':>7}"
      f"{'clust':>7}  STAGE 3?", flush=True)
for rp in (24.0, 48.0):
    for n_lip in (44, 63):
        e = build(7, n_lip=n_lip, bound=11.0, repel=rp, n_water=250, plant="clump", **BASE)
        for t in (5000, 20000, 60000):
            while getattr(e, "_t", 0) < t:
                e.step(); e._t = getattr(e, "_t", 0) + 1
            m = measure(e); sf = spanning_frac(e); mean, _, _ = bond_stats(e)
            ok = m["splay"] < 0.30 and sf > 0.8 and m["packing"] > 0.35
            print(f"  {rp:>6.0f}{n_lip:>6}{t:>7}{m['splay']:>7.3f}{sf:>6.2f}{m['packing']:>7.3f}"
                  f"{m['align']:>7.3f}{m['cluster_frac']:>7.2f}  {'*** YES ***' if ok else 'no'}",
                  flush=True)
        cross_section(e, f"{OUT}/s3_{int(rp)}_{n_lip}",
                      title=f"2-D self-assembly, repel {rp:.0f}, {n_lip} lipids, t=60000",
                      sub=f"splay {m['splay']:.3f}  spanning {sf:.2f}  packing {m['packing']:.3f}")
