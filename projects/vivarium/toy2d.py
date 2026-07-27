"""Small, fast 2-D testbed for lipid self-assembly.

In 2-D a bilayer is a DOUBLE ROW of lipids: heads out to either side, tails meeting in the middle.
The point of working here is iteration speed — a 2-D box needs far fewer particles for the same
areal coverage, so a run is seconds rather than minutes.

The order parameters are deliberately ORIENTATION-AGNOSTIC. The 3-D toy measured order about the z
axis, which is only meaningful for a bilayer that was planted flat: it would score a vesicle, a
tilted sheet or a micelle as zero. Everything below is computed from local neighbour relations, so
it registers structure wherever and however it forms:

    burial     — of a TAIL bead's close neighbours, the fraction that are not water.
                 High only if tails are buried away from water. Micelle or bilayer both qualify.
    hydration  — of a HEAD bead's close neighbours, the fraction that ARE water.
                 High only if heads are solvated.
    nematic    — 2-D nematic order <2(u_i·u_j)² − 1> over NEIGHBOURING lipid pairs. 1 = axes locally
                 aligned (lamellar), 0 = random. A spherical micelle splays its axes radially and so
                 scores low; a bilayer scores high. This is what separates the two.
    opposed    — of neighbouring lipid pairs that are aligned, the fraction pointing OPPOSITE ways.
                 A bilayer has two leaflets, so it should be substantial; a monolayer has none.

    bazel run //projects/vivarium:toy2d -- --plant     # stability of a planted bilayer
    bazel run //projects/vivarium:toy2d                # self-assembly from disorder
"""

from __future__ import annotations

import argparse

import numpy as np

from config import DEFAULTS, VivariumConfig
from polar_pack import MOL_HEAD, MOL_TAIL, WATER, PolarPackEngine

NEAR = 1.5
BOND_R = 1.0


def build(seed, n_mol=24, n_water=90, bound=5.0, kt=0.05, k_bond=80.0, plant=False,
          satt=1.0, repel=40.0, speed=1.20, maxvel=0.25, langevin=False):
    n_tok = 3 * n_mol + n_water
    cfg = VivariumConfig(**{**DEFAULTS, "N": n_tok, "pos_dim": 2, "n_harmonics": 3,
                            "pos_bound": bound})
    e = PolarPackEngine(cfg, seed, water_frac=n_water / n_tok, chain_frac=3 * n_mol / n_tok,
                        repel=repel, attract=0.30, polarity=1.0, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=speed, maxvel=maxvel, water_dipole=0.8,
                        aniso=0.0, k_bond=k_bond)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, 0.25
    e.repel_contact, e.rigidity, e.selectivity = 1.0, 0.0, 0.30
    e.temperature = kt
    e.langevin = langevin

    mol, B = e._mol, bound
    rng = np.random.default_rng(seed + 5)
    if plant:
        # two rows, tails meeting at x = 0, heads pointing out along ±x
        per = len(mol) // 2
        ys = (np.arange(per) + 0.5) / per * (2 * B) - B
        for leaf, sgn in ((0, +1.0), (1, -1.0)):
            idx = mol[leaf * per:(leaf + 1) * per]
            for bead, off in enumerate((1.45, 0.90, 0.35)):
                b = idx[:, bead]
                e.X[b, 0] = sgn * off
                e.X[b, 1] = ys[:len(idx)]
            e.head_phi[leaf * per:(leaf + 1) * per] = 0.0 if sgn > 0 else np.pi
        wi = e._wi
        e.X[wi, 0] = rng.uniform(1.9, B, len(wi)) * rng.choice([-1.0, 1.0], len(wi))
        e.X[wi, 1] = rng.uniform(-B, B, len(wi))
    else:
        cen = rng.uniform(-B, B, (len(mol), 2))
        th = rng.uniform(0, 2 * np.pi, len(mol))
        ax = np.stack([np.cos(th), np.sin(th)], axis=1)
        for bead, off in enumerate((1.0, 0.0, -1.0)):
            e.X[mol[:, bead], :2] = cen + off * BOND_R * ax
        e.head_phi[:] = th
        e.X[e._wi, :2] = rng.uniform(-B, B, (len(e._wi), 2))
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
        out = []
        for i in idx:
            nb = np.where(near[i])[0]
            if nb.size:
                out.append((is_w[nb] == want_water).mean())
        return float(np.mean(out)) if out else 0.0

    burial = frac(e._ti, False)          # tails should NOT see water
    hydration = frac(e._hi, True)        # heads SHOULD see water

    u = e.chain_axis()
    cen = e.X[e._mol[:, 1], :e.pd]       # middle bead = molecular centre
    dc = cen[:, None, :] - cen[None, :, :]
    dc = dc - e.L * np.round(dc / e.L)
    md2 = np.einsum("ijc,ijc->ij", dc, dc)
    pair = md2 < (1.8 ** 2)
    np.fill_diagonal(pair, False)
    dot = u @ u.T
    if pair.any():
        nem = float(np.mean(2.0 * dot[pair] ** 2 - 1.0))          # 2-D nematic, orientation-free
        aligned = pair & (np.abs(dot) > 0.7)
        opposed = float(np.mean(dot[aligned] < 0)) if aligned.any() else 0.0
    else:
        nem, opposed = 0.0, 0.0
    # occupancy of an 8x8 grid: distinguishes genuine amphiphilic assembly (system still fills the
    # box, lipids segregate WITHIN it) from global COLLAPSE (everything crushed into one blob, which
    # also scores high burial and is the classic false positive).
    B = e.cfg.pos_bound
    g = np.floor((e.X[:, :2] + B) / (2 * B) * 8).clip(0, 7).astype(int)
    occ = len(set(map(tuple, g.tolist())))
    return burial, hydration, nem, opposed, occ


def report(e, tag):
    b, h, n, o, occ = metrics(e)
    print(f"{tag:>8s}  burial={b:.3f}  hydration={h:.3f}  nematic={n:+.3f}  opposed={o:.3f}"
          f"  cells={occ}/64")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=4000)
    p.add_argument("--every", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mol", type=int, default=24)
    p.add_argument("--water", type=int, default=90)
    p.add_argument("--bound", type=float, default=5.0)
    p.add_argument("--kt", type=float, default=0.05)
    p.add_argument("--kbond", type=float, default=80.0)
    p.add_argument("--satt", type=float, default=1.0)
    p.add_argument("--repel", type=float, default=40.0)
    p.add_argument("--speed", type=float, default=1.20,
                   help="effective timestep. speed*maxvel is the max displacement per step; "
                        "at the default that is 0.3 sigma, which is a huge MD step.")
    p.add_argument("--maxvel", type=float, default=0.25)
    p.add_argument("--langevin", action="store_true",
                   help="FDT-satisfying inertial Langevin, no velocity cap")
    p.add_argument("--plant", action="store_true", help="start from a planted bilayer")
    a = p.parse_args(argv)

    e = build(a.seed, n_mol=a.mol, n_water=a.water, bound=a.bound, kt=a.kt,
              k_bond=a.kbond, plant=a.plant, satt=a.satt, repel=a.repel,
              speed=a.speed, maxvel=a.maxvel, langevin=a.langevin)
    print(f"2-D: {a.mol} lipids ({3 * a.mol} beads) + {a.water} water, box {2 * a.bound:.0f}, "
          f"kT={a.kt} k_bond={a.kbond} satt={a.satt} dx_max={a.speed*a.maxvel:.3f} {'LANGEVIN ' if a.langevin else ''}{'PLANTED' if a.plant else 'DISORDERED'}")
    print("  burial=tails hidden from water · hydration=heads in water · "
          "nematic=local axis alignment · opposed=two-leaflet signature")
    report(e, "t=0")
    for t in range(a.every, a.steps + 1, a.every):
        for _ in range(a.every):
            e.step()
        report(e, f"t={t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
