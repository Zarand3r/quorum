"""Planted reference structures WITH SOLVENT, and the calibration they exist to provide.

Every reference in the test suite was solvent-free, so no number in this project was ever calibrated
in the regime the experiments actually run in. That gap is what made the four-micelle figure
unjudgeable: `packing` read 0.441 with nothing to compare it against, and the one available
reference (a dry 3-D bilayer at 1.000) came from a different regime entirely.

Two rules these builders exist to enforce, both learned the hard way:

  1. THE LIPID COUNT FOLLOWS THE BOX, never the reverse. A spanning bilayer needs exactly
     box_width / contact molecules per leaflet. Planting 63 across a width of 22 gives 0.71 spacing,
     i.e. a structure over-crowded BY CONSTRUCTION, which then measures as though the physics had
     crushed it. This defect has now appeared four times.
  2. A REFERENCE MUST BE RELAXED BEFORE IT IS READ. Freshly planted solvent is random and sits inside
     the membrane; it takes a few hundred steps to move out. Reading at t=0 measures the planting,
     not the structure.
"""

from __future__ import annotations

import numpy as np

from harness import BOND_REST

__all__ = ["spanning_bilayer_2d", "micelle_2d", "relax"]


def _lipids_per_leaflet(bound):
    """Molecules that tile one leaflet across the periodic box at CONTACT spacing."""
    return int(round(2.0 * bound / BOND_REST))


def spanning_bilayer_2d(build, bound=11.0, **kw):
    """A rimless bilayer spanning the periodic box: the target structure in 2-D.

    Rimless is the point. A finite patch pays edge energy 2*pi*R*gamma along its exposed rim and
    closes into a vesicle to escape it, which is why bulk water makes vesicles rather than sheets.
    A periodic box removes the rim, so the flat phase becomes reachable -- this is exactly why
    coarse-grained membrane simulations plant spanning bilayers.
    """
    per = _lipids_per_leaflet(bound)
    e = build(0, n_lip=2 * per, bound=bound, plant="clump", **kw)
    mol, nb = e._mol, e._mol.shape[1]
    B = e.cfg.pos_bound
    xs = -B + (np.arange(per) + 0.5) * (2.0 * B / per)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(nb):
            e.X[idx[:, bead], 0] = xs[:len(idx)]
            e.X[idx[:, bead], 1] = sgn * (0.5 + (nb - 1 - bead) * BOND_REST)
    return e


def micelle_2d(build, n_lip=20, bound=11.0, **kw):
    """A single 2-D micelle: a DISC of radially oriented lipids, tails in, heads out.

    In 2-D the aggregation number is set by the head ring, not by a core volume: n heads on a circle
    of radius r sit 2*pi*r/n apart, so r >= n*contact/(2*pi). The tails must also reach the centre,
    which caps n -- exactly the packing-parameter argument, in the geometry that applies here rather
    than the spherical one.
    """
    e = build(0, n_lip=n_lip, bound=bound, plant="clump", **kw)
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    r_head = max(n * BOND_REST / (2.0 * np.pi), (nb - 1) * BOND_REST + 0.5)
    th = 2.0 * np.pi * (np.arange(n) + 0.5) / n
    u = np.stack([np.cos(th), np.sin(th)], axis=1)
    for bead in range(nb):
        e.X[mol[:, bead], :2] = u * (r_head - bead * BOND_REST)
    return e


def relax(e, steps=500):
    """Let freshly planted solvent move out of the structure before anything is read."""
    for _ in range(steps):
        e.step()
    return e


def spanning_bilayer_2d_branched(build, bound=11.0, n_tail=4, **kw):
    """A spanning bilayer of DOUBLE-TAILED lipids: head out, two arms side by side pointing in.

    This is the geometry that separates a bilayer former from a micelle former. The packing parameter
    P = v/(a0*l) needs 1/2 to 1 for a bilayer and under 1/3 for a micelle, and a second tail doubles v
    while leaving a0 and l alone -- which is why single-tailed surfactants micellize and double-tailed
    phospholipids build membranes.

    That doubling shows up directly in the planting: two tails side by side occupy ~2.0 of lateral
    width where the head needs only 1.0, so the LATERAL SPACING is set by the tails, not the head, and
    the leaflet holds half as many molecules as a single-tailed one across the same box.

    Topology is head -> arm0 -> arm1, both arms bonded from bead 0 (polar_pack builds it this way), so
    the first bead of each arm sits at dy = sqrt(contact^2 - dx^2) below the head rather than a full
    contact below it -- otherwise every head-arm bond starts stretched.
    """
    half = n_tail // 2
    pitch = 2.0 * BOND_REST                     # two tails abreast
    per = max(2, int(round(2.0 * bound / pitch)))
    e = build(0, n_lip=2 * per, bound=bound, n_tail=n_tail, branched=True, plant="clump", **kw)
    mol = e._mol
    B = e.cfg.pos_bound
    xs = -B + (np.arange(per) + 0.5) * (2.0 * B / per)
    dx = 0.5 * BOND_REST
    dy0 = float(np.sqrt(max(BOND_REST ** 2 - dx ** 2, 1e-9)))
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        x = xs[:len(idx)]
        y_head = 0.5 + dy0 + (half - 1) * BOND_REST
        e.X[idx[:, 0], 0] = x
        e.X[idx[:, 0], 1] = sgn * y_head
        for arm in range(2):
            for k in range(half):
                b = 1 + arm * half + k
                e.X[idx[:, b], 0] = x + (dx if arm else -dx)
                e.X[idx[:, b], 1] = sgn * (y_head - dy0 - k * BOND_REST)
    return e


def _fib_sphere(n):
    """n directions spread evenly over a sphere. Same reason as the 2-D case: normalised Gaussians
    are Poisson-random and CLUMP, which put the planted shells at 0.59 of contact no matter how the
    radii were chosen."""
    k = np.arange(n) + 0.5
    z = 1.0 - 2.0 * k / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    th = np.pi * (1.0 + 5.0 ** 0.5) * k
    return np.stack([r * np.cos(th), r * np.sin(th), z], axis=1)


def spanning_bilayer_3d(build, bound=3.4, **kw):
    """A rimless bilayer spanning the periodic box in 3-D: a SHEET, not a row.

    This is the object the 2-D runs only approximate. A 2-D "bilayer" is a double ROW whose edge is
    two endpoints at constant cost; a 3-D bilayer is a SHEET whose rim costs 2*pi*R*gamma and grows
    with size. The periodic box removes the rim in both cases, but the structures are not the same
    dimensionality of thing, which is why the 2-D result cannot be assumed to transfer.

    LIPID COUNT FOLLOWS THE BOX, in two dimensions here rather than one: per leaflet =
    (box_width / contact)^2. The existing 3-D planted bilayer used 48 lipids in a box of width 6.8,
    i.e. a 4.9 x 4.9 grid at 1.39 spacing, and measured packing 1.360 -- BEYOND contact, so it was
    never a properly built reference.
    """
    per_side = max(2, int(round(2.0 * bound / BOND_REST)))
    per = per_side * per_side
    e = build(0, n_lip=2 * per, bound=bound, plant=False, **kw)
    mol, nb = e._mol, e._mol.shape[1]
    B = e.cfg.pos_bound
    xs = -B + (np.arange(per_side) + 0.5) * (2.0 * B / per_side)
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        n = len(idx)
        for bead in range(nb):
            e.X[idx[:, bead], 0] = flat[:n, 0]
            e.X[idx[:, bead], 1] = flat[:n, 1]
            e.X[idx[:, bead], 2] = sgn * (0.5 + (nb - 1 - bead) * BOND_REST)
    return e


def micelle_3d(build, n_lip=30, bound=6.0, **kw):
    """A single 3-D micelle: a BALL of radially oriented lipids, tails in, heads out.

    Aggregation number is capped by geometry from both sides, and both caps matter. The head shell of
    n points at radius r spaces them ~2r*sqrt(pi/n) apart, needing r >= sqrt(n/(4*pi)) * contact; and
    the tails must REACH the centre, needing r <= (nb-1)*contact. Those cross at n ~ 4*pi*l^2, about
    50 lipids for a 2-bead tail -- so a larger "micelle" than that is not a micelle.

    Molecule CENTRES are staggered through the ball as ((m+0.5)/n)^(1/3) rather than placed on
    concentric shells. Shells put every tail END on one tiny inner sphere: the old 3-D reference had
    60 tail ends at radius 0.6, i.e. 0.32 of contact, an impossible core that calibrated `hollow` and
    `enclosed` for weeks before `packing` existed to reject it.
    """
    e = build(0, n_lip=n_lip, bound=bound, plant=False, **kw)
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    u = _fib_sphere(n)
    r_out = max(float(np.sqrt(n / (4.0 * np.pi))) * BOND_REST, (nb - 1) * BOND_REST + 0.5)
    r_mid = r_out * ((np.arange(n) + 0.5) / n) ** (1.0 / 3.0)
    for bead in range(nb):
        off = (nb - 1) / 2.0 - bead      # head radially OUTWARD of its own tails
        e.X[mol[:, bead], :3] = u * (r_mid + off * BOND_REST)[:, None]
    return e
