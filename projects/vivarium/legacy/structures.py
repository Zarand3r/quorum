"""Score candidate structures directly, without running dynamics.

Simulating and eyeballing is slow and it is what produced a false micelle claim. If a target
structure is not a mechanical equilibrium of the force field, no amount of simulation will find it,
and that is a STATIC question: build the structure, evaluate the forces, and look at how hard the
field pushes on it.

    RMS force   how hard the field pushes the structure away from itself. Near zero = equilibrium.
    drift       how far the structure actually moves in a short relaxation. Small = it holds.

Comparing candidates (dispersed / blob / micelle / bilayer) tells you which one the field prefers in
seconds rather than hours.

    bazel run //projects/vivarium:structures
"""
import math

import numpy as np

from config import DEFAULTS, VivariumConfig
from polar_pack import PolarPackEngine


def make(n_lip, n_tail, bound, seed=0):
    n_bead = 1 + n_tail
    n_wat = 120
    N = n_bead * n_lip + n_wat
    cfg = VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": bound})
    e = PolarPackEngine(cfg, seed, water_frac=n_wat / N, chain_frac=n_bead * n_lip / N,
                        repel=12.0, attract=0.30, polarity=0.80, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=0.02, water_dipole=0.8, k_bond=8.0)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 0.55, 0.90
    e.repel_contact, e.rigidity, e.selectivity, e.temperature = 1.0, 0.0, 0.30, 0.0
    e.langevin = True
    return e


def place(e, kind, bound, rng):
    """Lay the lipids out in a candidate structure. Beads sit at the bond rest length."""
    mol, P = e._mol, e.X[:, :3]
    n = len(mol)
    if kind == "micelle":                       # heads out, tails to a common centre
        u = rng.standard_normal((n, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        for b in range(mol.shape[1]):
            P[mol[:, b]] = u * (2.4 - b * 1.0)          # head furthest out
    elif kind == "bilayer":                     # two flat leaflets, tails meeting at z=0
        per = n // 2
        k = int(math.ceil(math.sqrt(per)))
        xs = (np.arange(k) + 0.5) / k * 2 * bound - bound
        gx, gy = np.meshgrid(xs, xs, indexing="ij")
        flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
        for leaf, sgn in ((0, 1.0), (1, -1.0)):
            idx = mol[leaf * per:(leaf + 1) * per]
            pts = flat[:len(idx)]
            for b in range(mol.shape[1]):
                P[idx[:, b], 0], P[idx[:, b], 1] = pts[:, 0], pts[:, 1]
                P[idx[:, b], 2] = sgn * (2.4 - b * 1.0)
    elif kind == "blob":                        # compact, random orientations
        c = rng.standard_normal((n, 3)) * 0.7
        u = rng.standard_normal((n, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        for b in range(mol.shape[1]):
            P[mol[:, b]] = c + u * (1.0 - b * 1.0)
    else:                                       # dispersed
        c = rng.uniform(-bound, bound, (n, 3))
        u = rng.standard_normal((n, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        for b in range(mol.shape[1]):
            P[mol[:, b]] = c + u * (1.0 - b * 1.0)
    P[e._wi] = rng.uniform(-bound, bound, (len(e._wi), 3))
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:]); e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest); e._write_radii(e.X[:, e.pd:])


def score(e, steps=400):
    start = e.X[:, :3].copy()
    e.step()
    f = e.vel / max(e.speed, 1e-9)
    rms = float(np.sqrt((f ** 2).sum(1).mean()))
    for _ in range(steps):
        e.step()
    d = e.X[:, :3] - start
    d -= e.L * np.round(d / e.L)
    return rms, float(np.sqrt((d ** 2).sum(1).mean()))


if __name__ == "__main__":
    print("Which structure does the force field actually prefer? (kT = 0, so this is pure mechanics)")
    for n_tail in (2, 3, 4):
        print(f"\n  tail beads per lipid = {n_tail}")
        print("    %-11s %10s %10s" % ("structure", "RMS force", "drift"))
        for kind in ("dispersed", "blob", "micelle", "bilayer"):
            e = make(40, n_tail, 3.6)
            place(e, kind, 3.6, np.random.default_rng(7))
            rms, drift = score(e)
            print("    %-11s %10.3f %10.3f" % (kind, rms, drift), flush=True)
