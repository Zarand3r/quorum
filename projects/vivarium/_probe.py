"""scale 4 held (packing 0.80, align 0.225); scale 16 failed on BONDS, not collapse -- repel/attract
went to 768/32 while k_bond stayed at 60, so the saturating bond lost to external force. Scale
k_bond with everything else and the ceiling moves with the load.
"""
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure, unwrap

BASE = dict(n_lip=63, bound=16.0, kt=0.02, satt=0.30, n_tail=2, bond_span=2.0,
            polarity=0.0, head_q=0.0, hydrophobic=0.6, n_water=250)
print(f"  {'scale':>6}{'repel':>7}{'attr':>6}{'kbond':>7}{'pack':>6}{'bad':>6}{'align':>7}"
      f"{'clust':>7}{'span':>7}  verdict", flush=True)
for sc in (4.0, 16.0):
    rp, at, kb, sp = 48.0 * sc, 2.0 * sc, 60.0 * sc, 0.0002 / sc
    e = build(0, repel=rp, attract=at, k_bond=kb, speed=sp, plant="clump", **BASE)
    for _ in range(int(24000 * sc)):
        e.step()
    m = measure(e)
    ext = unwrap(e, np.where(e.species != 0)[0])[:, :2]
    span = max(np.ptp(ext[:, 0]), np.ptp(ext[:, 1]))
    mean, mx, frac = bond_stats(e)
    print(f"  {sc:>6.0f}{rp:>7.0f}{at:>6.0f}{kb:>7.0f}{m['packing']:>6.2f}{frac:>6.2f}"
          f"{m['align']:>7.3f}{m['cluster_frac']:>7.2f}{span:>7.1f}  "
          f"{'OK' if m['ok'] else m['why'][:30]}", flush=True)
