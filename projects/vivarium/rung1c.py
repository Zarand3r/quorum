"""Rung 1 measured for the shape the aggregate actually has: a CYLINDER.

At 24 lipids a spherical micelle is not available. A sphere of radius equal to the molecule length
needs ~231 four-bead lipids (Finding 19), so with 24 the only micellar phase with enough material is
the cylindrical one, which is a real lyotropic phase and sits at packing parameter 1/3 to 1/2.

`outward` is measured from the centroid and therefore under-reads a cylinder: the molecules near the
two end caps point radially along the LONG axis, and their head-out order does not register. `cyl`
measures the same alignment in the plane perpendicular to the long axis, which is where a cylindrical
micelle puts its heads.

STEP 1 validates `cyl` on a hand-built cylinder. A metric that cannot recognise the structure it was
written for is not evidence, which is how three earlier claims in this project went wrong.
"""

import numpy as np

from bilayer3d import build
from micelle_probe import report


def plant_cylinder(e, radius=2.2):
    """Heads out in the perpendicular plane, tails on the axis: a cylindrical micelle by construction."""
    mol = e._mol
    rng = np.random.default_rng(5)
    n = len(mol)
    ax = np.array([0.0, 0.0, 1.0])
    th = rng.uniform(0, 2 * np.pi, n)
    z = np.linspace(-e.cfg.pos_bound * 0.7, e.cfg.pos_bound * 0.7, n)
    rhat = np.stack([np.cos(th), np.sin(th), np.zeros(n)], axis=1)
    for b in range(mol.shape[1]):
        p = rhat * (radius - b * 0.9)
        p[:, 2] = z
        e.X[mol[:, b], :3] = p
    e.head_u = rhat.copy()
    e.X[e._wi, :3] = rng.uniform(-e.cfg.pos_bound, e.cfg.pos_bound, (len(e._wi), 3))
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:])
    e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest)
    e._write_radii(e.X[:, e.pd:])


if __name__ == "__main__":
    kw = dict(seed=1, n_lip=24, bound=4.0, speed=0.08, repel=12.0,
              k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=4)
    print("STEP 1 - validate `cyl` on a HAND-BUILT cylindrical micelle (must score high)")
    e = build(kt=0.0, **kw)
    plant_cylinder(e)
    report(e, "planted")

    print("\nSTEP 2 - the same metric on a DISORDERED start, relaxed")
    e2 = build(kt=0.02, **kw)
    report(e2, "t=0")
    for t in (20000, 40000, 60000, 80000):
        for _ in range(20000):
            e2.step()
        report(e2, f"t={t}")
