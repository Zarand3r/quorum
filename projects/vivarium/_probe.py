"""Uniform force scaling was a time rescaling and bought nothing (align 0.111 -> 0.116 for 4x more
force). The real signal was that a SOFT bond ordered better than a stiff one (0.225 at k_bond 60 vs
0.111 at 240), which points at kinetic trapping rather than insufficient force. So sweep the two
knobs that control annealing: temperature, and bond flexibility.
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure, unwrap

BASE = dict(n_lip=63, bound=16.0, satt=0.30, n_tail=2, bond_span=2.0, polarity=0.0,
            head_q=0.0, hydrophobic=0.6, n_water=250, repel=192.0, attract=8.0, speed=0.00005)
print(f"  {'kT':>7}{'kbond':>7}{'pack':>6}{'bad':>6}{'align':>7}{'clust':>7}{'span':>7}  verdict",
      flush=True)
for kt in (0.02, 0.10, 0.40):
    for kb in (30.0, 60.0):
        e = build(0, kt=kt, k_bond=kb, plant="clump", **BASE)
        for _ in range(96000):
            e.step()
        m = measure(e)
        ext = unwrap(e, np.where(e.species != 0)[0])[:, :2]
        span = max(np.ptp(ext[:, 0]), np.ptp(ext[:, 1]))
        mean, mx, frac = bond_stats(e)
        print(f"  {kt:>7.2f}{kb:>7.0f}{m['packing']:>6.2f}{frac:>6.2f}{m['align']:>7.3f}"
              f"{m['cluster_frac']:>7.2f}{span:>7.1f}  {'OK' if m['ok'] else m['why'][:30]}", flush=True)
