"""Which way do the forces point on a PERFECT planted bilayer at kT=0?

If the planted state were a local minimum the net force would be ~0 everywhere. It is not, so the
question is which species is pushed which way. One step from rest gives displacement proportional to
force, and signing by leaflet turns "z" into "outward from the midplane".
"""
import numpy as np
from bilayer3d import build

for span, tag in ((2.0, "floppy chain"), (6.0, "rigid chain")):
    e = build(seed=0, n_lip=231, bound=5.0, kt=0.0, speed=0.005, repel=12.0, k_bond=8.0,
              satt=0.30, spol=0.90, plant=True, n_tail=2, head_q=0.0, rad_head=0.0,
              no_water=True, aniso=0.0, bond_span=span)
    mol = e._mol
    X0 = e.X[:, :3].copy()
    e.step()
    d = e.X[:, :3] - X0
    d -= e.L * np.round(d / e.L)
    sgn = np.sign(X0[:, 2])                      # +1 upper leaflet, -1 lower
    outward = d[:, 2] * sgn                      # >0 means pushed AWAY from the midplane
    print(f"\n--- span={span} ({tag})")
    for name, idx in (("head", mol[:, 0]), ("tail1", mol[:, 1]), ("tail2 (inner)", mol[:, 2])):
        o = outward[idx]
        lat = np.linalg.norm(d[idx][:, :2], axis=1).mean()
        print(f"  {name:>14}  outward={o.mean():+.3e}  |lateral|={lat:.3e}")
    print(f"  {'TOTAL |disp|':>14}  {np.linalg.norm(d, axis=1).mean():.3e}")
