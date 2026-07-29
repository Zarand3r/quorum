"""`lamellar`: does each lipid put its HEAD farther from the midplane than its own TAILS?

The density profile shows tails forming a core at z=0 with heads pushed outside, which is the
defining bilayer architecture, but `nematic` reads +0.02 because it measures AXIS ALIGNMENT and the
lipids are splayed. This is a per-molecule yes/no, so it is robust to tilt and to a diffuse membrane.

Calibrated against BOTH controls before use (Finding 21): a planted bilayer must score ~1.0 and a
random configuration must score ~0.5.
"""
import numpy as np
from bilayer3d import build, metrics


def lamellar(e):
    mol = e._mol
    mid = e.X[mol.ravel(), 2].mean()
    hz = np.abs(e.X[mol[:, 0], 2] - mid)
    tz = np.abs(e.X[mol[:, 1:], 2] - mid).mean(axis=1)
    return float((hz > tz).mean())


KW = dict(seed=0, n_lip=231, bound=5.0, kt=0.0, speed=0.005, repel=12.0, k_bond=40.0,
          satt=0.30, spol=0.90, n_tail=2, head_q=0.0, rad_head=0.0, no_water=True,
          aniso=0.0, polarity=0.0, attract=0.30, bond_span=6.0)

pl = build(plant=True, **KW)
print(f"  POSITIVE control (planted bilayer): lamellar={lamellar(pl):.3f}  nematic={metrics(pl)[2]:+.3f}")
rn = build(plant=False, **{**KW, "seed": 7})
print(f"  NULL control (disordered start):    lamellar={lamellar(rn):.3f}  nematic={metrics(rn)[2]:+.3f}")

e = build(plant=True, **KW)
print("\n  relaxation at kT=0:")
prev = 0
for t in (0, 2000, 4000, 8000, 16000):
    for _ in range(t - prev):
        e.step()
    prev = t
    print(f"    t={t:6d}  lamellar={lamellar(e):.3f}  nematic={metrics(e)[2]:+.3f}", flush=True)
