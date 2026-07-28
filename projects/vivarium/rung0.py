"""Rung 0: do TWO lipids prefer tail-to-tail contact?

The cheapest possible necessary condition. If two amphiphiles in water do not prefer to meet
tail-to-tail over head-to-head or head-to-tail, then no aggregate above them can be amphiphilic, and
every larger experiment is wasted. This runs in seconds and we never ran it.

Method: place two lipids in water at contact in each of the canonical relative orientations, take one
step, and read the force projected onto the separation axis. Negative means the pair is pulled
together in that orientation.
"""
import numpy as np

from config import DEFAULTS, VivariumConfig
from polar_pack import PolarPackEngine


def pair(orientation, sep=1.1, n_wat=60, bound=3.0, head_q=1.2):
    # species are drawn at random, so ask for more chain tokens than the two molecules we need and
    # use the first two; requesting exactly 6 sometimes yields only one molecule.
    N = 18 + n_wat
    cfg = VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": bound})
    e = PolarPackEngine(cfg, 0, water_frac=n_wat / N, chain_frac=18 / N,
                        repel=12.0, attract=0.30, polarity=0.80, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=0.02, water_dipole=0.8, k_bond=8.0,
                        head_q=head_q)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 0.55, 0.90
    e.repel_contact, e.rigidity, e.selectivity, e.temperature = 1.0, 0.0, 0.30, 0.0
    e.langevin = True
    mol = e._mol
    if len(mol) < 2:
        return None
    extra = mol[2:]          # park unused molecules far away so they cannot perturb the pair
    P = e.X[:, :3]
    # molecule A along +z at x=0; molecule B displaced along x, oriented per the case
    axes = {"tail-to-tail": (+1, -1), "head-to-head": (-1, +1),
            "head-to-tail": (+1, +1), "side-by-side ||": (+1, +1)}
    a, b = axes[orientation]
    for k, (m, sgn) in enumerate(zip(mol[:2], (a, b))):
        x = 0.0 if k == 0 else sep
        for bead, off in enumerate((1.0, 0.0, -1.0)):
            P[m[bead]] = [x, 0.0, sgn * off]
    if orientation == "tail-to-tail":       # tails facing each other across x
        for bead, off in enumerate((1.0, 0.0, -1.0)):
            P[mol[0][bead]] = [-off, 0.0, 0.0]
            P[mol[1][bead]] = [sep + off, 0.0, 0.0]
    if orientation == "head-to-head":
        for bead, off in enumerate((1.0, 0.0, -1.0)):
            P[mol[0][bead]] = [off, 0.0, 0.0]
            P[mol[1][bead]] = [sep - off, 0.0, 0.0]
    # water fills the rest, kept clear of the pair
    rng = np.random.default_rng(2)
    for j, m in enumerate(extra):
        for bead in range(mol.shape[1]):
            P[m[bead]] = [-bound + 0.3 * j, bound - 0.3, -bound + 0.3 * bead]
    w = rng.uniform(-bound, bound, (len(e._wi), 3))
    keep = np.abs(w[:, 1]) + np.abs(w[:, 2]) > 1.6
    w[~keep] += 2.0
    P[e._wi] = w
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:]); e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest); e._write_radii(e.X[:, e.pd:])
    e.step()
    f = e.vel          # from rest, one step gives vel = force exactly; do NOT divide by speed
    # net force on molecule A along +x (toward B). Negative = attraction.
    fx = float(f[mol[0]].sum(0)[0])
    return -fx      # report as "pull together"


if __name__ == "__main__":
    print("RUNG 0 — do two lipids prefer tail-to-tail? (kT=0, force along the separation axis)")
    print("  positive = the pair is PULLED TOGETHER in that orientation\n")
    seps = (1.1, 1.4, 1.8, 2.2)
    print("  %-18s" % "orientation" + "".join("%10s" % ("sep %.1f" % s) for s in seps))
    res = {}
    for o in ("tail-to-tail", "head-to-head", "head-to-tail"):
        row = [pair(o, sep=s) for s in seps]
        res[o] = row
        print("  %-18s" % o + "".join("%10.4f" % v for v in row))
    print()
    print("  amphiphilic ordering REQUIRES tail-to-tail > head-to-head at CONTACT separations.")
    for i, s in enumerate(seps):
        d = res["tail-to-tail"][i] - res["head-to-head"][i]
        print("    sep %.1f:  tail-tail - head-head = %+.4f   %s"
              % (s, d, "OK" if d > 0 else "FAILS"))
