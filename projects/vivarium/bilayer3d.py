"""3-D lipid self-assembly experiment: can a bilayer form, and can we tell?

Sized from the geometry rather than by guesswork. A bilayer that spans a periodic box of side L
needs 2·L²/a lipids, where a ≈ 0.87 is the area a lipid occupies in a packed leaflet — at L=6 that
is ~83 lipids, and with fewer than that there is simply not enough material to close a sheet, so
the system stays a micelle by necessity rather than by physics.

All order parameters are ORIENTATION-AGNOSTIC (no assumed bilayer normal), so a vesicle, a tilted
sheet or a disc all register:

    burial     of a TAIL bead's close neighbours, the fraction that are not water.
    hydration  of a HEAD bead's close neighbours, the fraction that ARE water.
    nematic    <2(u_i·u_j)² − 1> over neighbouring lipid pairs. In 3-D the ISOTROPIC baseline is
               −1/3, not 0 (verified numerically), so the scale runs −0.33 (random) → +1 (aligned).
               Reading 0 as "disordered" understates how much residual order a value near −0.2 has.
    opposed    of neighbouring lipid pairs, the fraction pointing OPPOSITE ways. THIS is what
               separates a bilayer from a micelle: a bilayer has two leaflets meeting tail-to-tail,
               so close neighbours are frequently antiparallel. In a micelle every lipid points
               outward along the radius, so close neighbours are nearly parallel and this stays low.
    cells      occupancy of a 4×4×4 grid — a collapse detector, since a globally condensed blob
               also scores high burial and is the classic false positive.

    bazel run //projects/vivarium:bilayer3d -- --lipids 83 --steps 200000
    bazel run //projects/vivarium:bilayer3d -- --plant     # reference: a hand-built bilayer
"""

from __future__ import annotations

import argparse
import math

import numpy as np

from config import DEFAULTS, VivariumConfig
from polar_pack import WATER, PolarPackEngine

BOND_REST_Z = 1.0        # matches polar_pack.BOND_REST
APL = math.sqrt(3) / 2.0     # area a lipid occupies in a packed leaflet (hex, diameter 1)
LIP_LEN = 2.0                # head -> far tail
NEAR = 1.6


def build(seed, n_lip, bound, kt, speed, repel, k_bond, satt, spol, plant=False, attract=0.30,
          polarity=0.80,
          head_q=1.2, n_tail=2, rad_head=None, no_water=False, aniso=0.95, bond_span=2.0, bend_frac=1.0, head_sigma=1.0, wall_axes=()):
    side = 2.0 * bound
    # water fills whatever the lipids do not, at roughly liquid packing
    nb = 1 + n_tail
    lip_vol = nb * n_lip * (4 / 3) * math.pi * 0.5 ** 3
    n_wat = 0 if no_water else int(max(40.0, (0.45 * side ** 3 - lip_vol) / ((4 / 3) * math.pi * 0.5 ** 3)))
    N = nb * n_lip + n_wat
    cfg = VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": bound})
    e = PolarPackEngine(cfg, seed, water_frac=n_wat / N, chain_frac=nb * n_lip / N,
                        repel=repel, attract=attract, polarity=polarity, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=speed, water_dipole=0.8, k_bond=k_bond,
                        head_q=head_q, n_tail=n_tail, rad_head=rad_head, aniso=aniso, bond_span=bond_span, bend_frac=bend_frac,
                        head_sigma=head_sigma)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, spol
    e.repel_contact, e.rigidity, e.selectivity, e.temperature = 1.0, 0.0, 0.30, kt
    e.langevin = True
    e.wall_axes = wall_axes

    mol, B = e._mol, bound
    rng = np.random.default_rng(seed + 11)
    if plant:                       # reference bilayer normal to z, tails meeting at z=0
        per = len(mol) // 2
        k = int(math.ceil(math.sqrt(per)))
        xs = (np.arange(k) + 0.5) / k * side - B
        gx, gy = np.meshgrid(xs, xs, indexing="ij")
        flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
        hu = np.zeros((len(e._hi), 3))
        for leaf, sgn in ((0, +1.0), (1, -1.0)):
            idx = mol[leaf * per:(leaf + 1) * per]
            pts = flat[:len(idx)]
            # 1.0 spacing to match BOND_REST, and 2.0 head-to-far-tail to match BOND_SPAN. The
            # previous offsets (2.0, 1.2, 0.4) gave 0.8 spacing, so every bond started 20%
            # compressed and the bond force tore the planted lattice apart before the pair forces
            # could be judged at all.
            # (2.5, 1.5, 0.5), NOT (2.4, 1.4, 0.4). The chain spacing is 1.0 either way, matching
            # BOND_REST, but the INNERMOST tails of the two leaflets sit at +off and -off, so their
            # separation is 2*off. At off=0.4 that is 0.8 against a contact distance of
            # sigma_i+sigma_j = 1.0, i.e. the planted bilayer starts with a 20% steric CLASH at the
            # midplane. The repulsion tears the leaflets apart at ANY temperature, which is what
            # every previous "the planted bilayer melts even at kT=0" result was actually measuring.
            # At off=0.5 the opposing tails start exactly at contact.
            nb = mol.shape[1]
            for bead in range(nb):
                off = 0.5 + (nb - 1 - bead) * BOND_REST_Z
                e.X[idx[:, bead], 0] = pts[:, 0]
                e.X[idx[:, bead], 1] = pts[:, 1]
                e.X[idx[:, bead], 2] = sgn * off
            hu[leaf * per:(leaf + 1) * per, 2] = sgn
        e.head_u = hu
        z = rng.uniform(3.0, B, len(e._wi)) * rng.choice([-1.0, 1.0], len(e._wi))
        e.X[e._wi, 0] = rng.uniform(-B, B, len(e._wi))
        e.X[e._wi, 1] = rng.uniform(-B, B, len(e._wi))
        e.X[e._wi, 2] = z
    else:                           # disordered: molecules extended along random axes
        cen = rng.uniform(-B, B, (len(mol), 3))
        ax = rng.standard_normal((len(mol), 3))
        ax /= np.linalg.norm(ax, axis=1, keepdims=True)
        half = (mol.shape[1] - 1) / 2.0
        for bead in range(mol.shape[1]):
            e.X[mol[:, bead], :3] = cen + (half - bead) * ax
        e.head_u = ax.copy()
        e.X[e._wi, :3] = rng.uniform(-B, B, (len(e._wi), 3))
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:])
    e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest)
    e._write_radii(e.X[:, e.pd:])
    return e


def lamellar(e):
    """Fraction of lipids whose HEAD sits farther from the membrane midplane than its own TAILS.

    This is the bilayer's defining architecture: a hydrophobic tail core with heads on the outside.
    `nematic` measures something different, axis ALIGNMENT, and a FLUID membrane splays its lipids,
    so nematic decays to ~0 while the lamellar organisation is untouched. Reading nematic alone
    reports a stable bilayer as a failure, which is exactly what happened here for most of a day.

    Per-molecule yes/no, so it is robust to tilt and to a diffuse membrane. Calibrated against BOTH
    controls: a planted bilayer scores 0.996 and a disordered start scores 0.463 (null = 0.5).
    """
    mol = e._mol
    mid = e.X[mol.ravel(), 2].mean()
    hz = np.abs(e.X[mol[:, 0], 2] - mid)
    tz = np.abs(e.X[mol[:, 1:], 2] - mid).mean(axis=1)
    return float((hz > tz).mean())


def molecule_ok(e):
    """(mean bond length, mean 1-3 span). RULE 0: every order parameter here is computed from head and
    tail POSITIONS, so a deformed lipid makes all of them meaningless. bond_span=6.0 stretched bonds to
    2.4x their rest length in every 4-bead-tail run before this was checked, so it now prints on every
    line. Rest length is 1.0 and a straight 1-3 span is 2.0."""
    mol = e._mol
    if not mol.size:
        return 0.0, 0.0
    b = np.linalg.norm(e.X[mol[:, 0], :3] - e.X[mol[:, 1], :3], axis=1)
    r13 = np.linalg.norm(e.X[mol[:, 0], :3] - e.X[mol[:, 2], :3], axis=1)
    return float(b.mean()), float(r13.mean())


def shape(e):
    """(L1/L3, L2/L3) of the lipid position covariance, ascending eigenvalues.

    `lamellar` cannot tell a bilayer from a cylinder: a rod also puts heads outside along its thin
    axis, and it scored 0.827 on one. A SLAB needs TWO long axes, so L2/L3 high with L1/L3 low.
    Planted bilayer reads (0.34, 0.85); a self-assembled cylinder read (0.18, 0.31).
    """
    X = e.X[e._mol.ravel(), :3]
    c = X - X.mean(0)
    ev = np.linalg.eigvalsh(c.T @ c / len(c))
    return float(ev[0] / max(ev[2], 1e-9)), float(ev[1] / max(ev[2], 1e-9))


def metrics(e):
    _, d2 = e._periodic_delta()
    near = d2 < NEAR ** 2
    np.fill_diagonal(near, False)
    sp = e.species
    is_w = sp == WATER

    def frac(idx, want_water):
        out = [(is_w[np.where(near[i])[0]] == want_water).mean()
               for i in idx if near[i].any()]
        return float(np.mean(out)) if out else 0.0

    burial, hydration = frac(e._ti, False), frac(e._hi, True)

    u = e.chain_axis()
    cen = e.X[e._mol[:, 1], :e.pd]
    dc = cen[:, None, :] - cen[None, :, :]
    if not e.wall_axes:
        dc = dc - e.L * np.round(dc / e.L)
    # 3.2, not 2.8: the planted leaflets sit EXACTLY 2.8 apart centre-to-centre, so a strict `< 2.8`
    # excludes every cross-leaflet pair by one epsilon and `opposed` reads 0.000 on a PERFECT planted
    # bilayer. That is the same class of defect as Finding 21: a metric that fails its own positive
    # control. 3.2 clears the leaflet spacing with margin while staying well inside the box.
    pair = np.einsum("ijc,ijc->ij", dc, dc) < 3.2 ** 2
    np.fill_diagonal(pair, False)
    dot = u @ u.T
    nem = float(np.mean(2.0 * dot[pair] ** 2 - 1.0)) if pair.any() else 0.0
    opp = float(np.mean(dot[pair] < -0.5)) if pair.any() else 0.0

    b = e.cfg.pos_bound
    g = np.floor((e.X[:, :3] + b) / (2 * b) * 4).clip(0, 3).astype(int)
    return burial, hydration, nem, opp, len(set(map(tuple, g.tolist())))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--lipids", type=int, default=83)
    p.add_argument("--bound", type=float, default=3.0)
    p.add_argument("--steps", type=int, default=200000)
    p.add_argument("--every", type=int, default=25000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--kt", type=float, default=0.02)
    p.add_argument("--speed", type=float, default=0.08)
    p.add_argument("--repel", type=float, default=12.0)
    p.add_argument("--kbond", type=float, default=8.0)
    p.add_argument("--satt", type=float, default=0.55)
    p.add_argument("--spol", type=float, default=0.90)
    p.add_argument("--headq", type=float, default=1.2)
    p.add_argument("--radhead", type=float, default=None,
                   help="head DISPERSION radius. eps=tanh(rad^2/0.25), so ~0.05 gives a head that "
                        "has excluded volume but does NOT attract, which is the Cooke-Deserno "
                        "structure: cohesion is tail-tail ONLY.")
    p.add_argument("--nowater", action="store_true",
                   help="solvent-free, as Cooke-Deserno. Tail-tail cohesion replaces water.")
    p.add_argument("--tails", type=int, default=2)
    p.add_argument("--span", type=float, default=2.0,
                   help="1-3 rest length. 2.0 = the straight length (zero tension, floppy chain). Above 2.0 the spring is permanently stretched, the Cooke-Deserno rigid-rod trick.")
    p.add_argument("--slit", action="store_true",
                   help="walls on z ONLY, periodic in x,y: the standard membrane geometry. Removes "
                        "periodic self-interaction across the membrane NORMAL while leaving the sheet "
                        "infinite laterally, so it has no edges to curl at. A fully walled box is "
                        "worse than either, since lipids just coat all six faces.")
    p.add_argument("--walls", action="store_true", help="confine ALL axes (mostly a control)")
    p.add_argument("--headsigma", type=float, default=1.0,
                   help="head steric radius as a fraction of the tail's. THE packing-parameter knob: "
                        "P = v/(a0*l) is a cylinder for 1/3..1/2 and a BILAYER for 1/2..1, and shrinking "
                        "the head shrinks a0. Cooke-Deserno uses 0.95.")
    p.add_argument("--polarity", type=float, default=0.80,
                   help="electrostatic head strength. Profiling shows _extra_force is 52%% of every "
                        "step (spherical harmonics + pair basis + attention). With head_q=0 that work "
                        "contributes NOTHING, and polarity=0 takes the early-out. Cooke-Deserno has no "
                        "electrostatics at all, so 0 is also the faithful setting for the port.")
    p.add_argument("--attract", type=float, default=0.30,
                   help="vdW cohesion amplitude. Never swept before: the default 0.30 sits against repel=12, a 1:40 ratio. This is the term that must hold a membrane together.")
    p.add_argument("--bendfrac", type=float, default=1.0,
                   help="1-3 straightener stiffness as a fraction of k_bond. Must be < 1 or the two "
                        "saturating tanh forces cancel and the molecule stretches without restoring "
                        "force. Cooke-Deserno uses bond 30 vs bend 10.")
    p.add_argument("--aniso", type=float, default=0.95,
                   help="how strongly the contour deforms EXCLUDED VOLUME. At the 0.95 default the "
                        "contact distance swings over [0.05, 1.95] instead of sitting at 1.0, which "
                        "stretches a bonded pair well past BOND_REST. Cooke-Deserno beads are "
                        "spheres; 0.0 reproduces that.")
    p.add_argument("--plant", action="store_true")
    a = p.parse_args(argv)

    e = build(a.seed, a.lipids, a.bound, a.kt, a.speed, a.repel, a.kbond, a.satt, a.spol,
              a.plant, attract=a.attract, polarity=a.polarity, head_q=a.headq, n_tail=a.tails, rad_head=a.radhead, no_water=a.nowater,
              aniso=a.aniso, bond_span=a.span, bend_frac=a.bendfrac, head_sigma=a.headsigma,
              wall_axes=(0, 1, 2) if a.walls else ((2,) if a.slit else ()))
    side = 2 * a.bound
    need = 2 * side * side / APL
    print(f"N={e.cfg.N}  lipids={len(e._mol)}  water={len(e._wi)}  box={side:.1f}  "
          f"{'PLANTED' if a.plant else 'DISORDERED'}")
    print(f"  a spanning bilayer needs ~{need:.0f} lipids; solvent slab {(side - 2*LIP_LEN)/2:.1f} per side")
    print(f"  min-image margin {e.min_image_margin():.4f} (gate < 0.01)")
    print("   step  lamellar  L1/L3  L2/L3  shape      nematic  cells   bond  r13   [bond 1.0, r13 2.0]")
    print("         [lamellar: 0.5 random, 1.0 = every head outside its own tails -- THE bilayer test]")
    for t in range(0, a.steps + 1, a.every):
        b, h, n, o, c = metrics(e)
        a1, a2 = shape(e)
        kind = "SLAB" if (a1 < 0.45 and a2 > 0.60) else ("rod" if a2 < 0.45 else "blob")
        bo, r13 = molecule_ok(e)
        warn = "" if abs(bo - 1.0) < 0.25 else "  <-- LIPID STRETCHED"
        print(f"  {t:6d}   {lamellar(e):.3f}  {a1:.2f}   {a2:.2f}   {kind:<9} {n:+.3f}   {c}/64  "
              f"{bo:.2f}  {r13:.2f}{warn}", flush=True)
        if t < a.steps:
            for _ in range(a.every):
                e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
