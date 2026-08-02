"""Self-assembly at the ratio where the phase is PROVEN stable, with annealing.

Established: a planted 2-D bilayer at repel 48 reaches splay 0.071 and holds it to 20k steps at
packing 0.95. So the target exists and the only remaining question is whether disorder can REACH it.
First clump-start runs at repel 24 gave one consolidated aggregate at 64-68% spanning but splay 0.61
-- condensed and not lamellar, which is a nucleation problem.

Annealing is the standard escape from a kinetic trap, it has been implemented in bicelle2d for
months, and it has never been used in any run. Temperature is ramped linearly from `hot` down to the
production kT over the first 60% of the run, then held, so the structure orders while cold.

Stage 3 criterion, all three together:
    splay < 0.30   AND   spanning > 0.8   AND   packing > 0.35
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, largest_cluster, measure
from xsection import cross_section

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
KT = 0.02
BASE = dict(kt=KT, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, repel=48.0)

def spanning_frac(e):
    comp = largest_cluster(e)
    if len(comp) < 3:
        return 0.0
    x = np.mod(e.X[e._mol[comp].ravel(), 0] + e.cfg.pos_bound, 2 * e.cfg.pos_bound)
    nb = max(8, int(2 * e.cfg.pos_bound))
    return float(len(np.unique((x / (2 * e.cfg.pos_bound) * nb).astype(int))) / nb)

TOTAL = 60000
print("  repel 48 (phase proven stable: planted holds at splay 0.071)", flush=True)
print(f"  {'hot kT':>7}{'n_lip':>6}{'t':>7}{'kT':>7}{'splay':>7}{'span':>6}{'pack':>7}"
      f"{'align':>7}  STAGE 3?", flush=True)
for hot in (0.02, 0.20, 0.60):
    for n_lip in (44,):
        e = build(7, n_lip=n_lip, bound=11.0, n_water=250, plant="clump", **BASE)
        for step in range(TOTAL):
            frac = min(1.0, step / (0.6 * TOTAL))          # cool over the first 60%, then hold
            e.temperature = hot + (KT - hot) * frac
            e.step()
            if step + 1 in (20000, 40000, TOTAL):
                m = measure(e); sf = spanning_frac(e)
                ok = m["splay"] < 0.30 and sf > 0.8 and m["packing"] > 0.35
                print(f"  {hot:>7.2f}{n_lip:>6}{step+1:>7}{e.temperature:>7.3f}{m['splay']:>7.3f}"
                      f"{sf:>6.2f}{m['packing']:>7.3f}{m['align']:>7.3f}"
                      f"  {'*** YES ***' if ok else 'no'}", flush=True)
        cross_section(e, f"{OUT}/anneal_{str(hot).replace('.','p')}",
                      title=f"2-D self-assembly, repel 48, anneal kT {hot} -> {KT}, t={TOTAL}",
                      sub=f"splay {m['splay']:.3f} (bilayer <0.30)  spanning {sf:.2f}  "
                          f"packing {m['packing']:.3f}")
