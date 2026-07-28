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


def pair(orientation, sep=1.1, n_wat=60, bound=3.0, head_q=1.2, n_tail=2, satt=0.55,
         rad_head=0.30):
    # species are drawn at random, so ask for more chain tokens than the two molecules we need and
    # use the first two; requesting exactly 6 sometimes yields only one molecule.
    nb = 1 + n_tail
    N = 6 * nb + n_wat
    cfg = VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": bound})
    e = PolarPackEngine(cfg, 0, water_frac=n_wat / N, chain_frac=(6 * nb) / N,
                        repel=12.0, attract=0.30, polarity=0.80, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=0.02, water_dipole=0.8, k_bond=8.0,
                        head_q=head_q, n_tail=n_tail, rad_head=rad_head)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, 0.90
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
        for bead in range(nb):
            P[m[bead]] = [x, 0.0, sgn * (nb - 1) / 2.0 - sgn * bead]
    if orientation == "tail-to-tail":       # tails facing each other across x
        for bead in range(nb):
            P[mol[0][bead]] = [-bead, 0.0, 0.0]
            P[mol[1][bead]] = [sep + bead, 0.0, 0.0]
    if orientation == "head-to-head":
        for bead in range(nb):
            P[mol[0][bead]] = [bead - (nb - 1), 0.0, 0.0]
            P[mol[1][bead]] = [sep + (nb - 1) - bead, 0.0, 0.0]
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
    seps = (1.1, 1.4, 1.8)
    import math
    print("  Rung 0 tracked TAIL FRACTION, which a WEAKER HEAD raises just as a longer tail does.")
    print("  If a 2-bead tail can pass with a weaker head, every lamellar structure shrinks by ~8x.\n")
    print("  %-6s %-10s %-12s %s" % ("tails", "rad_head", "signal", "tail-to-tail preferred"))
    for nt in (2, 3, 4):
        for rh in (0.30, 0.20, 0.12, 0.06):
            res = {}
            for o in ("tail-to-tail", "head-to-head"):
                res[o] = [pair(o, sep=s, n_tail=nt, rad_head=rh) for s in seps]
            tt, hh = res["tail-to-tail"], res["head-to-head"]
            sig = max(abs(a - b) / max(abs(a), abs(b), 1e-9) for a, b in zip(tt, hh))
            ok = all(a > b for a, b in zip(tt, hh))
            print("  %-6d %-10.2f %-12s %s"
                  % (nt, rh, "%.0f%%" % (100 * sig), "YES" if ok else "no"))
