"""Vivarium's lipid geometry, measured the way the oracle's was — the numbers that decided everything there.

On the oracle side, morphology was fully determined by what the particle count could AFFORD:

    spanning sheet   L^2 / a          (3-D)      2L / s        (2-D, two leaflets)
    spanning tube    2 pi r L / a     (3-D)      --
    closed vesicle   4 pi R^2 / a     (3-D)      4 pi R / s    (2-D ring, two leaflets)

with a = 1.50 sigma^2 measured on a spanning slab. Only when sheet AND tube were both unaffordable
did a finite aggregate close. Those three numbers have never been computed for Vivarium's lipid, and
every Vivarium run has used 63 lipids simply because the historical configuration did.

This measures, from a planted FLAT bilayer relaxed under the current force field:
  * s, the linear spacing per lipid along one leaflet (the 2-D analogue of area per lipid);
  * d, the head-to-head membrane thickness;
  * the head and tail steric widths, hence the 2-D packing parameter P = v / (a0 * l).

P places the lipid in a phase band: below ~1/3 micelles, ~1/2 to 1 bilayers. Every planted ring in
the matched-density sweep collapsed to a FILLED MICELLE at every size, which is the signature of a
lipid sitting in the micelle band. If P lands there, no curvature term can rescue a ring, and the
oracle would have predicted exactly what was observed.
"""

import sys

import numpy as np

from bicelle2d import build
from polar_pack import BOND_REST

CFG = dict(n_lip=40, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
           n_tail=2, bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2,
           hydrophobic=0.6, attract=1.5)


def plant_flat(e):
    """A double row spanning x: heads out along +/-y, tails meeting at y=0."""
    mol, nb = e._mol, e._mol.shape[1]
    per = len(mol) // 2
    xs = (np.arange(per) - (per - 1) / 2.0) * BOND_REST
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(nb):
            off = 0.5 + (nb - 1 - bead) * BOND_REST
            e.X[idx[:len(idx), bead], 0] = xs[:len(idx)]
            e.X[idx[:len(idx), bead], 1] = sgn * off


def geometry(e):
    mol, nb = e._mol, e._mol.shape[1]
    P = e.X[:, :e.pd]
    head, tail = P[mol[:, 0]], P[mol[:, 1:]].mean(axis=1)
    upper = head[:, 1] > tail[:, 1]
    # spacing: nearest in-leaflet neighbour distance along the membrane (x)
    s_vals = []
    for sel in (upper, ~upper):
        xs = np.sort(head[sel][:, 0])
        if len(xs) > 2:
            s_vals.append(np.median(np.diff(xs)))
    spacing = float(np.mean(s_vals)) if s_vals else float("nan")
    thickness = float(head[upper][:, 1].mean() - head[~upper][:, 1].mean())
    return spacing, thickness


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    e = build(0, plant=False, **CFG)
    e.curvature = 0.0
    plant_flat(e)
    s0, d0 = geometry(e)
    for _ in range(steps):
        e.step()
    s1, d1 = geometry(e)
    sig = getattr(e, "sigma", None)
    print(f"planted   spacing s = {s0:.3f}   thickness d = {d0:.3f}")
    print(f"relaxed   spacing s = {s1:.3f}   thickness d = {d1:.3f}   (after {steps} steps)")

    s, d = s1, abs(d1)
    print()
    print("2-D affordability with the RELAXED spacing (two leaflets):")
    print(f"{'':4}{'L or R':>9}{'spanning bilayer':>19}{'closed ring':>14}")
    for L in (11.0, 16.0, 22.0):
        print(f"{'':4}{L:>9.1f}{2 * L / s:>19.0f}{'':>14}")
    for R in (4.0, 6.0, 8.0, 10.0):
        print(f"{'':4}{R:>9.1f}{'':>19}{4 * np.pi * R / s:>14.0f}")

    print()
    print("packing parameter, 2-D form P = v / (a0 * l):")
    n_tail = CFG["n_tail"]
    l = n_tail * BOND_REST                       # tail length
    v = n_tail * BOND_REST * s                   # tail 'area' occupied per lipid in 2-D
    a0 = s                                       # head width along the membrane
    P = v / (a0 * l)
    print(f"    tail length l  = {l:.2f}")
    print(f"    head width a0  = {a0:.2f}   (= measured spacing)")
    print(f"    P = {P:.2f}    (micelle < 0.33, bilayer 0.5-1.0)")
    print()
    print("    NOTE: with a0 taken as the measured spacing this P is 1 by construction, which means")
    print("    the assay cannot see the head/tail asymmetry. The steric widths must come from the")
    print("    engine's own per-species sigma, not from the packing that results.")
    if sig is not None:
        print(f"    engine sigma present: {np.unique(np.round(sig, 3))[:6]}")
    else:
        print("    engine exposes no per-token sigma (self.sigma is None) -- head and tail widths")
        print("    are then set by repel_contact alone and are IDENTICAL, i.e. P = 1 structurally.")
