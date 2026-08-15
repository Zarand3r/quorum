"""Calibrate the curl audit on a force that is PROVABLY a gradient before trusting any verdict.

The audit reported eta_curl = 0.91 for the curvature term, which was separately verified against
its own scalar to 2.2e-9. Both cannot be true, so the instrument is on trial here, not the physics.
"""
import numpy as np
from bicelle2d import build

CFG = dict(n_lip=6, bound=6.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
           n_tail=2, bond_span=2.0, n_water=10, polarity=0.80, head_q=1.2,
           hydrophobic=0.6, attract=1.0)


def eta(J):
    return float(np.linalg.norm(J - J.T) / max(np.linalg.norm(J), 1e-30))


e = build(0, plant="clump", **CFG)
e.curvature, e.bend = 0.20, 1.0
n, pd = e.X.shape[0], e.pd
m = n * pd
h = 1e-5

# (1) the curvature force taken DIRECTLY from its analytic implementation -- known conservative
J = np.zeros((m, m))
for b in range(m):
    i, c = divmod(b, pd)
    e.X[i, c] += h
    fp = e._curvature_pot_and_force()[1].ravel()
    e.X[i, c] -= 2 * h
    fm = e._curvature_pot_and_force()[1].ravel()
    e.X[i, c] += h
    J[:, b] = (fp - fm) / (2 * h)
print(f"curvature force, read directly from its analytic form:  eta_curl = {eta(J):.6f}")
print("   (must be ~0: this force is -grad of a scalar, verified at 2.2e-9)")

# (2) the same quantity as the audit measured it: one step() displacement
def disp():
    e.langevin = False
    e.temperature = 0.0
    x0 = e.X.copy()
    before = e.X[:, :pd].copy()
    e.step()
    after = e.X[:, :pd].copy()
    d = after - before
    d -= e.L * np.round(d / e.L)
    e.X = x0
    return d

J2 = np.zeros((m, m))
for b in range(m):
    i, c = divmod(b, pd)
    e.X[i, c] += h
    fp = disp().ravel()
    e.X[i, c] -= 2 * h
    fm = disp().ravel()
    e.X[i, c] += h
    J2[:, b] = (fp - fm) / (2 * h)
print(f"one-step displacement, as the audit measured it:          eta_curl = {eta(J2):.6f}")
