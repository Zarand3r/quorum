"""The damage is a TAIL, not bulk pressure: a saturating bond has a bounded max force, so once
steric push exceeds it the bond stretches freely. Raise that ceiling (k_bond) while holding the
integrator stability product speed*k_bond fixed, so the earlier blow-up cannot recur.
"""
from bicelle2d import build
from harness import bond_stats, measure

print(f"  {'k_bond':>7}{'speed':>9}{'prod':>7}{'bond':>7}{'max':>7}{'frac>1.25':>11}{'align':>8}", flush=True)
for kb, sp in ((20, 0.0006), (60, 0.0002), (120, 0.0001), (240, 0.00005)):
    e = build(0, n_lip=63, bound=11.0, kt=0.02, speed=sp, repel=6.0, k_bond=float(kb),
              satt=0.30, n_tail=2, attract=2.0, bond_span=2.0, polarity=0.0, head_q=0.0,
              hydrophobic=0.6, n_water=250, plant="clump")
    # hold total integrated time fixed: fewer steps at larger k means less physical time,
    # so scale step count by 1/speed to compare structures at the same point in their evolution.
    for _ in range(int(8000 * 0.0006 / sp)):
        e.step()
    mean, mx, frac = bond_stats(e)
    m = measure(e)
    print(f"  {kb:>7}{sp:>9.5f}{kb*sp:>7.3f}{mean:>7.3f}{mx:>7.2f}{frac:>11.2f}{m['align']:>8.3f}", flush=True)
