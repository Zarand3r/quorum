"""Rung 2 in 2-D: can a FINITE bilayer ribbon (the 2-D bicelle) form and stay flat?

Why 2-D is not merely cheaper but thermodynamically easier. A bicelle is a finite piece of bilayer,
and what destroys it is the RIM: tails exposed along the edge. In 3-D that rim is a whole
circumference, which is why both vivarium and the Cooke-Deserno control relaxed finite aggregates
into cylinders (2026-07-29c). In 2-D the same structure is a double ROW and its rim is just the TWO
end molecules, so the edge penalty is far smaller and a finite ribbon may be stable with a single
species.

The 2-D bilayer is a double row: heads out on both sides, tails meeting along the midline. A 2-D
bicelle is a SHORT such row -- extended, two-layered, and not closed into a circle.

Every metric is calibrated against BOTH controls before it is read, per the rule this project has
relearned three times (see docs/RESEARCH_LOG.md):

    lamellar   fraction of lipids whose HEAD is farther from the ribbon midline than its OWN tails.
               Planted ribbon ~1.0, random ~0.5. Robust to tilt, and it does not care whether the
               ribbon is straight or gently curved.
    aspect     L1/L2 of the lipid position covariance. A RIBBON is elongated (low); a compact
               micelle is round (near 1).
    thick      separation of the two head rows along the ribbon's thin axis. A double row is ~2
               molecule lengths; a single row or a filled blob is ~1.

    bazel run //projects/vivarium:bicelle2d -- --lipids 60 --steps 40000
"""

from __future__ import annotations

import argparse
import math

import numpy as np

from config import DEFAULTS, VivariumConfig
from polar_pack import BOND_REST, PolarPackEngine


def build(seed, n_lip, bound, kt, speed, repel, k_bond, satt, plant=False, n_tail=2,
          head_sigma=1.0, attract=0.30, bond_span=6.0, aniso=0.0, walls=False, span_frac=1.0):
    nb = 1 + n_tail
    n_tok = nb * n_lip
    cfg = VivariumConfig(**{**DEFAULTS, "N": n_tok, "pos_dim": 2, "n_harmonics": 3,
                            "pos_bound": bound})
    # Solvent-free, no electrostatics: the recipe the 3-D work converged on. Cohesion is tail-tail
    # only (rad_head=0 zeroes the head's dispersion while leaving its excluded volume), and
    # polarity=0 takes the early-out that skips ~half the step cost.
    e = PolarPackEngine(cfg, seed, water_frac=0.0, chain_frac=1.0, repel=repel, attract=attract,
                        polarity=0.0, cohesion=0.0, skew=0.0, morph=0.70, momentum=0.30,
                        speed=speed, k_bond=k_bond, head_q=0.0, n_tail=n_tail, rad_head=0.0,
                        aniso=aniso, bond_span=bond_span, head_sigma=head_sigma)
    e.conservative = True
    # sink_polarity must stay non-zero even though polarity=0 disables the head, because
    # min_image_margin() takes the max over ALL sink ranges and exp(-0*d^2)=1 would report a bogus
    # margin of 1.0 (the gate is <0.01) for a head that is not even active.
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, 0.90
    e.repel_contact, e.rigidity, e.selectivity, e.temperature = 1.0, 0.0, 0.30, kt
    e.langevin = True
    e.wall_axes = (1,) if walls else ()

    mol, B = e._mol, bound
    rng = np.random.default_rng(seed + 11)
    if plant == "ribbon" or plant is True:
        # plant == "ribbon": a double ROW along x: heads out along ±y, tails meeting at y=0. Innermost tails start
        # exactly at contact (sigma_i+sigma_j), not overlapping -- the 3-D version of this planted
        # geometry began with a 20% steric clash and tore itself apart (2026-07-28c).
        # Spacing must equal the contact distance. Planting n_lip/2 lipids across the FULL box
        # regardless of count starts the row over-compressed -- 30 lipids across a box of 12 gives
        # 0.4 spacing against a contact distance of 1.0, and the row collapses immediately. Here the
        # row is laid out at unit spacing and span_frac < 1 leaves the rest of the box EMPTY, which is
        # what makes the ribbon FINITE (a bicelle) rather than spanning (a bilayer).
        per = len(mol) // 2
        width = min(2 * B * span_frac, per * BOND_REST)
        xs = (np.arange(per) - (per - 1) / 2.0) * (width / max(per - 1, 1))
        for leaf, sgn in ((0, +1.0), (1, -1.0)):
            idx = mol[leaf * per:(leaf + 1) * per]
            for bead in range(nb):
                off = 0.5 + (nb - 1 - bead) * BOND_REST
                e.X[idx[:, bead], 0] = xs[:len(idx)]
                e.X[idx[:, bead], 1] = sgn * off
    elif plant == "micelle":
        # a 2-D circular micelle: tails to the centre, heads on the perimeter. The competing phase.
        n = len(mol)
        th = (np.arange(n) + 0.5) / n * 2 * np.pi
        rhat = np.stack([np.cos(th), np.sin(th)], axis=1)
        for bead in range(nb):
            e.X[mol[:, bead], :2] = rhat * (0.5 + (nb - 1 - bead) * BOND_REST)
        e.head_phi[:] = th
    else:
        cen = rng.uniform(-B, B, (len(mol), 2))
        th = rng.uniform(0, 2 * np.pi, len(mol))
        ax = np.stack([np.cos(th), np.sin(th)], axis=1)
        half = (nb - 1) / 2.0
        for bead in range(nb):
            e.X[mol[:, bead], :2] = cen + (half - bead) * BOND_REST * ax
        e.head_phi[:] = th
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest)
    e._write_radii(e.X[:, e.pd:])
    return e


def _axes(e):
    """(long, thin) unit vectors of the aggregate, from the position covariance."""
    X = e.X[e._mol.ravel(), :2]
    c = X - X.mean(0)
    ev, evec = np.linalg.eigh(c.T @ c / len(c))
    return evec[:, 1], evec[:, 0], float(ev[0] / max(ev[1], 1e-9))


def metrics(e):
    mol = e._mol
    long_ax, thin_ax, aspect = _axes(e)
    mid = e.X[mol.ravel(), :2].mean(0)
    # signed distance along the THIN axis = "which side of the midline"
    h = (e.X[mol[:, 0], :2] - mid) @ thin_ax
    t = ((e.X[mol[:, 1:], :2] - mid) @ thin_ax).mean(axis=1)
    lamellar = float((np.abs(h) > np.abs(t)).mean())
    up = h > 0
    thick = float(h[up].mean() - h[~up].mean()) if up.any() and not up.all() else 0.0
    return lamellar, aspect, thick


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--lipids", type=int, default=60)
    p.add_argument("--steps", type=int, default=40000)
    p.add_argument("--every", type=int, default=10000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--bound", type=float, default=6.0)
    p.add_argument("--kt", type=float, default=0.02)
    p.add_argument("--speed", type=float, default=0.005)
    p.add_argument("--repel", type=float, default=12.0)
    p.add_argument("--kbond", type=float, default=40.0)
    p.add_argument("--satt", type=float, default=0.30)
    p.add_argument("--tails", type=int, default=2)
    p.add_argument("--headsigma", type=float, default=1.0)
    p.add_argument("--span", type=float, default=6.0)
    p.add_argument("--attract", type=float, default=0.30)
    p.add_argument("--spanfrac", type=float, default=1.0,
                   help="fraction of the box the planted row occupies. 1.0 = spanning (a bilayer); "
                        "less than 1 leaves empty box around it, so the ribbon is FINITE and has two "
                        "exposed ends -- that is the bicelle, and whether it stays flat or curls up is "
                        "the whole question.")
    p.add_argument("--walls", action="store_true", help="confine y only (a 2-D slit)")
    p.add_argument("--plant", default="", choices=["", "ribbon", "micelle"],
                   help="plant a candidate phase instead of starting disordered. Relaxing a PLANTED "
                        "structure at low kT answers 'is this phase stable' for a tiny fraction of the "
                        "cost of waiting for it to nucleate -- and nucleation, not stability, is what "
                        "has failed in every 3-D attempt.")
    a = p.parse_args(argv)

    kw = dict(n_lip=a.lipids, bound=a.bound, kt=a.kt, speed=a.speed, repel=a.repel,
              k_bond=a.kbond, satt=a.satt, n_tail=a.tails, head_sigma=a.headsigma,
              attract=a.attract, bond_span=a.span, walls=a.walls, span_frac=a.spanfrac)
    pl = build(a.seed, plant="ribbon", **kw)
    rn = build(a.seed + 99, plant=False, **kw)
    lp, ap, tp = metrics(pl)
    lr, ar, tr = metrics(rn)
    print(f"  CONTROLS  planted ribbon: lamellar {lp:.3f}  aspect {ap:.3f}  thick {tp:.2f}")
    print(f"            random start  : lamellar {lr:.3f}  aspect {ar:.3f}  thick {tr:.2f}")
    e = build(a.seed, plant=(a.plant or False), **kw)
    print(f"  N={e.cfg.N} lipids={len(e._mol)} tails={a.tails} box={2*a.bound:.0f} "
          f"{'PLANTED' if a.plant else 'DISORDERED'}  margin={e.min_image_margin():.4f}")
    print("   step  lamellar  aspect  thick   verdict")
    for t in range(0, a.steps + 1, a.every):
        lam, asp, th = metrics(e)
        v = "RIBBON (2-D bicelle)" if (lam > 0.85 and asp < 0.35 and th > 1.5) else (
            "partial" if lam > 0.7 else "no lamellar order")
        print(f"  {t:6d}   {lam:.3f}   {asp:.3f}  {th:5.2f}   {v}", flush=True)
        if t < a.steps:
            for _ in range(a.every):
                e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
