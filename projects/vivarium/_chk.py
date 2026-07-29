"""Slab or sphere? `lamellar` measured along z cannot tell them apart: a droplet also puts heads
outside. The discriminator is whether the structure is FLAT -- extended in two directions and thin in
the third -- which the eigenvalues of the position covariance answer directly, plus the density
profile along the thin axis.
"""
import numpy as np
from bilayer3d import build, lamellar, metrics


def shape(e):
    mol = e._mol
    X = e.X[mol.ravel(), :3]
    c = X - X.mean(0)
    ev = np.linalg.eigvalsh(c.T @ c / len(c))          # ascending L1<=L2<=L3
    return float(ev[0] / ev[2]), float(ev[1] / ev[2])   # (thin/long, mid/long)


def profile(e, tag):
    mol = e._mol
    n = np.linalg.eigh(np.cov((e.X[mol.ravel(), :3] - e.X[mol.ravel(), :3].mean(0)).T))[1][:, 0]
    hz = (e.X[mol[:, 0], :3] - e.X[mol.ravel(), :3].mean(0)) @ n
    tz = (e.X[mol[:, 1:].reshape(-1), :3] - e.X[mol.ravel(), :3].mean(0)) @ n
    bins = np.linspace(-5, 5, 17)
    ch, _ = np.histogram(hz, bins=bins); ct, _ = np.histogram(tz, bins=bins)
    mx = max(ch.max(), ct.max(), 1)
    a1, a2 = shape(e)
    print(f"\n  {tag}  lamellar={lamellar(e):.3f}  L1/L3={a1:.2f} L2/L3={a2:.2f}"
          f"  {'SLAB (bilayer)' if a1 < 0.45 and a2 > 0.6 else 'not a slab'}")
    print("   along the THIN axis:   HEAD                  TAIL")
    for i in range(len(ch)):
        z = 0.5 * (bins[i] + bins[i + 1])
        print(f"   {z:>5.1f}  {'#'*int(18*ch[i]/mx):<20} {'*'*int(18*ct[i]/mx):<20}")


KW = dict(n_lip=231, bound=5.0, kt=0.02, speed=0.005, repel=12.0, k_bond=40.0, satt=0.30,
          spol=0.90, n_tail=2, head_q=0.0, rad_head=0.0, no_water=True, aniso=0.0,
          polarity=0.0, attract=0.30, bond_span=6.0)
p = build(seed=0, plant=True, **KW); profile(p, "PLANTED control")
e = build(seed=0, plant=False, **KW)
for _ in range(30000): e.step()
profile(e, "SELF-ASSEMBLED t=30000")
