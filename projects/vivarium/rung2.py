"""Rung 2 — push the aggregate from a rod toward a DISC (a bicelle).

We already produce elongated aggregates with heads out, which is a cylindrical micelle. A bicelle is
the same thing flattened: two long principal axes and one short. The packing parameter is what
selects between them, so this sweeps the head size, which is the term Cooke uses explicitly to set
an effective cylindrical lipid shape.

Validated instrument first, per the rule that cost us three claims.
"""
import numpy as np

from bilayer3d import build
from micelle_probe import report


def plant_disc(e, radius=3.0):
    """A bicelle by construction: two flat leaflets in a circular patch, tails meeting at z=0."""
    mol = e._mol
    n = len(mol)
    rng = np.random.default_rng(4)
    per = n // 2
    pts = []
    k = 1
    while len(pts) < per:
        for a in np.linspace(0, 2 * np.pi, max(1, 6 * k), endpoint=False):
            pts.append((0.9 * k * np.cos(a), 0.9 * k * np.sin(a)))
        k += 1
    pts = np.array(pts[:per])
    nb = mol.shape[1]
    for leaf, sgn in ((0, 1.0), (-1, -1.0)):
        idx = mol[:per] if leaf == 0 else mol[per:2 * per]
        p = pts[:len(idx)]
        for b in range(nb):
            e.X[idx[:, b], 0], e.X[idx[:, b], 1] = p[:, 0], p[:, 1]
            e.X[idx[:, b], 2] = sgn * ((nb - 1) * 0.9 - b * 0.9 + 0.4)
    e.X[e._wi, :3] = rng.uniform(-e.cfg.pos_bound, e.cfg.pos_bound, (len(e._wi), 3))
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:]); e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest); e._write_radii(e.X[:, e.pd:])


if __name__ == "__main__":
    import sys
    print("STEP 1 — validate the DISC classifier on a hand-built bicelle")
    e = build(seed=2, n_lip=28, bound=4.0, kt=0.0, speed=0.08, repel=12.0,
              k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=4)
    plant_disc(e)
    report(e, "planted")

    print("\nSTEP 2 — self-assembly, sweeping head charge (sets the packing parameter)")
    for hq in (1.2, 2.4):
        e2 = build(seed=2, n_lip=28, bound=4.0, kt=0.02, speed=0.08, repel=12.0,
                   k_bond=8.0, satt=0.55, spol=0.90, plant=False, head_q=hq, n_tail=4)
        print(f"  head_q={hq}")
        for t in (30000, 60000):
            for _ in range(30000):
                e2.step()
            report(e2, f"t={t}")
