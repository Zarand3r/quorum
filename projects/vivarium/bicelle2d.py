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
          n_water=0, polarity=0.0, head_q=0.0, water_dipole=0.8, spol=0.90,
          head_sigma=1.0, attract=0.30, bond_span=6.0, aniso=0.0, walls=False, span_frac=1.0, sharp=0.0, branched=False):
    nb = 1 + n_tail
    n_tok = nb * n_lip + max(0, n_water)
    cfg = VivariumConfig(**{**DEFAULTS, "N": n_tok, "pos_dim": 2, "n_harmonics": 3,
                            "pos_bound": bound})
    # Solvent-free, no electrostatics: the recipe the 3-D work converged on. Cohesion is tail-tail
    # only (rad_head=0 zeroes the head's dispersion while leaving its excluded volume), and
    # polarity=0 takes the early-out that skips ~half the step cost.
    wf = 0.0 if n_water <= 0 else n_water / n_tok
    e = PolarPackEngine(cfg, seed, water_frac=wf, chain_frac=1.0 - wf, repel=repel,
                        attract=attract, polarity=polarity, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, water_dipole=water_dipole,
                        speed=speed, k_bond=k_bond, head_q=head_q, n_tail=n_tail, rad_head=0.0,
                        aniso=aniso, bond_span=bond_span, head_sigma=head_sigma,
                        branched=branched)
    e.conservative = True
    e.repel_sharp = sharp   # >0 = saturating tanh core: bounded, but HARD near contact
    # sink_polarity must stay non-zero even though polarity=0 disables the head, because
    # min_image_margin() takes the max over ALL sink ranges and exp(-0*d^2)=1 would report a bogus
    # margin of 1.0 (the gate is <0.01) for a head that is not even active.
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, spol
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
    elif plant == "clump":
        # A COMPACT but fully disordered clump in the middle of a large box. This separates two
        # different questions that a dilute random start conflates: whether dispersed molecules can
        # FIND each other (ordinary diffusion, and hopeless at the density a finite ribbon needs -- at
        # box 44 the density is 0.056 and nothing ever aggregates), versus whether molecules that are
        # already together can ORDER into a ribbon. The second is the physics under test.
        n = len(mol)
        rad = math.sqrt(n * nb * 0.9 / math.pi)     # just dense enough to be in contact
        ang = rng.uniform(0, 2 * np.pi, n)
        rr = rad * np.sqrt(rng.random(n))
        cen = np.stack([rr * np.cos(ang), rr * np.sin(ang)], axis=1)
        th = rng.uniform(0, 2 * np.pi, n)
        ax = np.stack([np.cos(th), np.sin(th)], axis=1)
        half = (nb - 1) / 2.0
        for bead in range(nb):
            e.X[mol[:, bead], :2] = cen + (half - bead) * BOND_REST * ax
        e.head_phi[:] = th
    else:
        cen = rng.uniform(-B, B, (len(mol), 2))
        th = rng.uniform(0, 2 * np.pi, len(mol))
        ax = np.stack([np.cos(th), np.sin(th)], axis=1)
        if branched and n_tail >= 2 and n_tail % 2 == 0:
            perp = np.stack([-ax[:, 1], ax[:, 0]], axis=1)
            arm = n_tail // 2
            e.X[mol[:, 0], :2] = cen
            for a_ in range(2):
                off = (2 * a_ - 1) * 0.45 * perp
                for k in range(arm):
                    e.X[mol[:, 1 + a_ * arm + k], :2] = cen + off - (k + 1) * BOND_REST * ax
        else:
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


def edge_frac(e):
    """Fraction of lipids whose TAIL beads still touch water: L_edge, the quantity the pathway trades.

    stage 2 BICELLE  flat with a rim      -> edge > 0
    stage 3 CUP      rim shrinking         -> edge falling
    stage 4 VESICLE  sealed                -> edge ~ 0
    Requires explicit solvent: with none, gamma = 0 and closure cannot happen at any size.
    """
    wi = e._wi
    mol = e._mol
    if not wi.size or not mol.size:
        return float("nan")
    # The DEEPEST tail bead only. A lipid with a damp tip is not a rim lipid: in a bilayer the tips
    # meet at the midplane and are the driest point, so wetting THERE is what marks a genuine exposed
    # edge. Counting any wet tail bead reported edge=1.00 even at perfect lamellar order, because a
    # 4-bead branched lipid gives a membrane only ~4 thick and a 1.4 contact range penetrates from
    # both faces.
    tips = mol[:, -1]
    d = e.X[tips, :2][:, None, :] - e.X[wi, :2][None, :, :]
    d -= e.L * np.round(d / e.L)
    return float((np.einsum("ijc,ijc->ij", d, d) < 1.2 ** 2).any(axis=1).mean())


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
    p.add_argument("--water", type=int, default=0,
                   help="explicit solvent tokens. gamma (line tension) comes from tail-water contact, and gamma=0 makes R_crit infinite, so closure is impossible without it.")
    p.add_argument("--headq", type=float, default=0.0)
    p.add_argument("--waterdipole", type=float, default=0.8,
                   help="WATER SELF-ATTRACTION, the hydrogen-bond analogue. This is the actual driver of "
                        "the hydrophobic effect: water cages a tail because it would rather bond to other "
                        "water. Our water has dispersion eps 0.09 against tail-tail 0.99, i.e. nearly an "
                        "ideal gas, so solvating a tail costs almost nothing and the aggregate never "
                        "develops a dry core.")
    p.add_argument("--spol", type=float, default=0.90, help="range of the electrostatic head")
    p.add_argument("--polarity", type=float, default=0.0)
    p.add_argument("--branched", action="store_true",
                   help="TWO tails branching from one head, as in a real phospholipid. A linear "
                        "head-tail-tail chain is a single-tailed SURFACTANT, and single-tailed "
                        "surfactants form MICELLES -- which is what this project kept producing. Two "
                        "tails double v at fixed a0, moving P = v/(a0*l) from the micelle regime into "
                        "the bilayer regime. An architecture change, not a parameter.")
    p.add_argument("--anneal", type=float, default=0.0,
                   help="starting kT for a cooling schedule, linearly ramped down to --kt over the run. "
                        "Every run so far has been at FIXED kT, and the droplet is a kinetic trap: the "
                        "planted ribbon is stable but never nucleates. Cooling is the standard way out of "
                        "a trap -- hot enough to stay mobile, then slow enough for the ordered phase to "
                        "form. 0 disables it.")
    p.add_argument("--sharp", type=float, default=0.0,
                   help="saturating tanh excluded-volume core. The linear ramp lets beads "
                        "interpenetrate, so a molecule is not a well-defined rod and an aggregate can be a "
                        "round blob with heads and tails mixed. Cooke-Deserno uses a 1/r^12 hard core and "
                        "DOES elongate from a clump; this is the bounded equivalent. Rung 0 said a sharp "
                        "core hurts, but that was a TWO-molecule test where shape is not the mechanism.")
    p.add_argument("--spanfrac", type=float, default=1.0,
                   help="fraction of the box the planted row occupies. 1.0 = spanning (a bilayer); "
                        "less than 1 leaves empty box around it, so the ribbon is FINITE and has two "
                        "exposed ends -- that is the bicelle, and whether it stays flat or curls up is "
                        "the whole question.")
    p.add_argument("--walls", action="store_true", help="confine y only (a 2-D slit)")
    p.add_argument("--plant", default="", choices=["", "ribbon", "micelle", "clump"],
                   help="plant a candidate phase instead of starting disordered. Relaxing a PLANTED "
                        "structure at low kT answers 'is this phase stable' for a tiny fraction of the "
                        "cost of waiting for it to nucleate -- and nucleation, not stability, is what "
                        "has failed in every 3-D attempt.")
    a = p.parse_args(argv)

    kw = dict(n_lip=a.lipids, bound=a.bound, kt=a.kt, speed=a.speed, repel=a.repel,
              k_bond=a.kbond, satt=a.satt, n_tail=a.tails, head_sigma=a.headsigma,
              attract=a.attract, bond_span=a.span, walls=a.walls, span_frac=a.spanfrac,
              sharp=a.sharp, branched=a.branched, n_water=a.water, polarity=a.polarity,
              head_q=a.headq, water_dipole=a.waterdipole, spol=a.spol)
    pl = build(a.seed, plant="ribbon", **kw)
    rn = build(a.seed + 99, plant=False, **kw)
    lp, ap, tp = metrics(pl)
    lr, ar, tr = metrics(rn)
    print(f"  CONTROLS  planted ribbon: lamellar {lp:.3f}  aspect {ap:.3f}  thick {tp:.2f}")
    print(f"            random start  : lamellar {lr:.3f}  aspect {ar:.3f}  thick {tr:.2f}")
    e = build(a.seed, plant=(a.plant or False), **kw)
    print(f"  N={e.cfg.N} lipids={len(e._mol)} tails={a.tails} box={2*a.bound:.0f} "
          f"{'PLANTED' if a.plant else 'DISORDERED'}  margin={e.min_image_margin():.4f}")
    if a.anneal > 0.0:
        print(f"  annealing: kT {a.anneal} -> {a.kt} linearly over {a.steps} steps")
    print("   step  lamellar  aspect  thick   edge   verdict   [edge->0 = sealed vesicle]")
    for t in range(0, a.steps + 1, a.every):
        lam, asp, th = metrics(e)
        v = "RIBBON (2-D bicelle)" if (lam > 0.85 and asp < 0.35 and th > 1.5) else (
            "partial" if lam > 0.7 else "no lamellar order")
        ef = edge_frac(e)
        print(f"  {t:6d}   {lam:.3f}   {asp:.3f}  {th:5.2f}  {ef:5.2f}   {v}", flush=True)
        if t < a.steps:
            for k in range(a.every):
                if a.anneal > 0.0:                      # linear cool from --anneal down to --kt
                    frac = (t + k) / max(a.steps, 1)
                    e.temperature = a.anneal + (a.kt - a.anneal) * frac
                e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
