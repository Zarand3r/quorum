"""Rung 1, measured properly, with the metric validated before it is trusted.

The previous metric was `<r_head> - <r_tail>`, a difference of two mean radii. That estimator is
weak: it differences two large numbers so it is noisy, it presumes the aggregate is spherical and
centred, and when the cluster cutoff merges two separate micelles their shared centre of mass falls
between them and every radial quantity is scrambled. It also produced a "MICELLE" reading on a
six-molecule cluster that swung to the opposite extreme later in the same run.

Step 1 scores a HAND-BUILT micelle. A metric that cannot recognise a real micelle is not evidence
about anything, and the old one was never checked this way.
"""

import numpy as np

from bilayer3d import build
from micelle_probe import report


def plant_micelle(e, radius=2.6):
    """Heads out, tails to the centre: a micelle by construction."""
    mol = e._mol
    rng = np.random.default_rng(5)
    u = rng.standard_normal((len(mol), 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    for b in range(mol.shape[1]):
        e.X[mol[:, b], :3] = u * (radius - b * 0.9)
    e.X[e._wi, :3] = rng.uniform(-e.cfg.pos_bound, e.cfg.pos_bound, (len(e._wi), 3))
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:])
    e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest)
    e._write_radii(e.X[:, e.pd:])


if __name__ == "__main__":
    print("STEP 1 — validate the metric on a HAND-BUILT micelle (must score high, or it is useless)")
    e = build(seed=1, n_lip=24, bound=4.0, kt=0.0, speed=0.08, repel=12.0,
              k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=4)
    plant_micelle(e)
    report(e, "planted")

    print("\nSTEP 2 — the same metric on a DISORDERED start, relaxed")
    e2 = build(seed=1, n_lip=24, bound=4.0, kt=0.02, speed=0.08, repel=12.0,
               k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=4)
    report(e2, "t=0")
    for t in (20000, 40000, 60000):
        for _ in range(20000):
            e2.step()
        report(e2, f"t={t}")
