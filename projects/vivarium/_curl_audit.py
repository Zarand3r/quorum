"""PRIORITY 4: is each deterministic Vivarium force actually the gradient of a scalar?

Newton's third law (F_ij = -F_ji) buys momentum conservation, NOT conservativeness. A force can be
perfectly antisymmetric and still not be the gradient of any scalar. The test that decides it is the
symmetry of the Jacobian:

    J_ab = dF_a / dx_b,     conservative  <=>  J = J^T

reported as

    eta_curl = ||J - J^T||_F / ||J||_F.

Each deterministic term is isolated by zeroing the others, on a small configuration held away from
cutoffs and minimum-image discontinuities. Langevin noise is disabled -- it is not part of the
deterministic field and would swamp the finite differences.

This determines whether an energy-model refactor must touch every force family or only a subset.
"""

import sys

import numpy as np

from bicelle2d import build

CFG = dict(n_lip=6, bound=6.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
           n_tail=2, bond_span=2.0, n_water=10, polarity=0.80, head_q=1.2,
           hydrophobic=0.6, attract=1.0)

# knob -> the value that turns that term ON, with everything else off
TERMS = [
    ("repel",     dict(repel=12.0)),
    ("attract",   dict(attract=1.0)),
    ("polarity",  dict(polarity=0.80)),
    ("cohesion",  dict(cohesion=0.30)),
    ("nematic",   dict(nematic=0.50)),
    ("curvature", dict(curvature=0.20)),
]
OFF = dict(repel=0.0, attract=0.0, polarity=0.0, cohesion=0.0, nematic=0.0, curvature=0.0)


def deterministic_force(e):
    """The force field alone: freeze the state, disable noise, and read what step() would apply."""
    e.langevin = False
    e.temperature = 0.0
    x0 = e.X.copy()
    v0 = e.vel.copy() if hasattr(e, "vel") else None
    e.X = x0.copy()
    if v0 is not None:
        e.vel = np.zeros_like(v0)
    before = e.X[:, :e.pd].copy()
    e.step()
    after = e.X[:, :e.pd].copy()
    d = after - before
    d -= e.L * np.round(d / e.L)
    e.X = x0
    if v0 is not None:
        e.vel = v0
    return d                      # proportional to force for one overdamped step from rest


def jacobian(e, h=1e-5):
    n, pd = e.X.shape[0], e.pd
    m = n * pd
    J = np.zeros((m, m))
    for b in range(m):
        i, c = divmod(b, pd)
        e.X[i, c] += h
        fp = deterministic_force(e).ravel()
        e.X[i, c] -= 2 * h
        fm = deterministic_force(e).ravel()
        e.X[i, c] += h
        J[:, b] = (fp - fm) / (2 * h)
    return J


def eta_curl(J):
    a = np.linalg.norm(J - J.T)
    b = np.linalg.norm(J)
    return float(a / max(b, 1e-30))


if __name__ == "__main__":
    print("eta_curl = ||J - J^T|| / ||J||   (0 = conservative; ~1 = not a gradient field)")
    print(f"{'term':>12}{'eta_curl':>12}{'||J||':>12}   verdict")
    for name, on in TERMS:
        kw = dict(CFG)
        e = build(0, plant="clump", **{**kw, **{k: v for k, v in OFF.items() if k in kw}})
        for k, v in OFF.items():
            if hasattr(e, k):
                setattr(e, k, v)
        for k, v in on.items():
            setattr(e, k, v)
        e.langevin = False
        e.temperature = 0.0
        J = jacobian(e)
        nj = float(np.linalg.norm(J))
        if nj < 1e-12:
            print(f"{name:>12}{'--':>12}{nj:>12.2e}   term inactive in this configuration")
            continue
        ec = eta_curl(J)
        verdict = ("conservative" if ec < 1e-3 else
                   "mildly non-conservative" if ec < 0.1 else "NOT a gradient field")
        print(f"{name:>12}{ec:>12.4f}{nj:>12.2e}   {verdict}")
