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

APL = math.sqrt(3) / 2.0     # area a lipid occupies in a packed leaflet (hex, diameter 1)
LIP_LEN = 2.0                # head -> far tail
NEAR = 1.6


def build(seed, n_lip, bound, kt, speed, repel, k_bond, satt, spol, plant=False,
          head_q=1.2, n_tail=2):
    side = 2.0 * bound
    # water fills whatever the lipids do not, at roughly liquid packing
    nb = 1 + n_tail
    lip_vol = nb * n_lip * (4 / 3) * math.pi * 0.5 ** 3
    n_wat = int(max(40.0, (0.45 * side ** 3 - lip_vol) / ((4 / 3) * math.pi * 0.5 ** 3)))
    N = nb * n_lip + n_wat
    cfg = VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": bound})
    e = PolarPackEngine(cfg, seed, water_frac=n_wat / N, chain_frac=nb * n_lip / N,
                        repel=repel, attract=0.30, polarity=0.80, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=speed, water_dipole=0.8, k_bond=k_bond,
                        head_q=head_q, n_tail=n_tail)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, spol
    e.repel_contact, e.rigidity, e.selectivity, e.temperature = 1.0, 0.0, 0.30, kt
    e.langevin = True

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
            for bead, off in enumerate((2.4, 1.4, 0.4)):
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
    p.add_argument("--plant", action="store_true")
    a = p.parse_args(argv)

    e = build(a.seed, a.lipids, a.bound, a.kt, a.speed, a.repel, a.kbond, a.satt, a.spol,
              a.plant, a.headq)
    side = 2 * a.bound
    need = 2 * side * side / APL
    print(f"N={e.cfg.N}  lipids={len(e._mol)}  water={len(e._wi)}  box={side:.1f}  "
          f"{'PLANTED' if a.plant else 'DISORDERED'}")
    print(f"  a spanning bilayer needs ~{need:.0f} lipids; solvent slab {(side - 2*LIP_LEN)/2:.1f} per side")
    print(f"  min-image margin {e.min_image_margin():.4f} (gate < 0.01)")
    print("   step   burial  hydration  nematic  opposed  cells   [nematic: -0.33 random, +1 aligned]")
    for t in range(0, a.steps + 1, a.every):
        b, h, n, o, c = metrics(e)
        print(f"  {t:6d}   {b:.3f}     {h:.3f}   {n:+.3f}   {o:.3f}   {c}/64", flush=True)
        if t < a.steps:
            for _ in range(a.every):
                e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
