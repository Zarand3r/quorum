"""TOY: plant a bilayer by hand and ask whether the force field can hold it.

Self-assembly is two questions welded together, and they have opposite fixes:

  (1) Is a bilayer a STABLE structure under these forces?   — a force-field question
  (2) If so, will the system FIND it from a random start?   — a nucleation/kinetics question

Waiting for spontaneous assembly cannot distinguish them. So: build a perfect bilayer, then relax
it. If it melts, no amount of patience or tuning of the initial condition will help and the force
field is wrong. If it holds, the force field is fine and the problem is nucleation.

It also audits the BENCHMARK METRIC, which is the quieter risk: `emergence_score` is a local
composition excess, not a bilayer detector. Scored against a hand-built perfect bilayer it should
be strongly positive. If it is not, we could already be producing partial structure and recording
it as nothing.

    bazel run //projects/vivarium:toy_bilayer
    bazel run //projects/vivarium:toy_bilayer -- --steps 3000 --aniso 0.95
"""

from __future__ import annotations

import argparse

import numpy as np

from config import DEFAULTS, VivariumConfig
from polar_pack import AMPHI, MOL_HEAD, MOL_TAIL, WATER, PolarPackEngine

NEAR = 1.6          # neighbour cutoff, same as the benchmark
LEAFLET_Z = 0.55    # half the hydrophobic core thickness
WATER_GAP = 1.15    # water starts beyond this |z|


BOND_R = 1.0


def build_chain(seed, n_side=4, temperature=0.03, k_bond=1.5, scramble=False):
    """A planted bilayer of THREE-BEAD lipids: head outermost, then two tail beads reaching into the
    midplane. This is the geometry a single bead cannot express — head repulsion and tail attraction
    now act at DIFFERENT points, and tail-tail contact area is doubled."""
    n_mol = 2 * n_side * n_side
    n_chain_tok = 3 * n_mol
    n_water = 2 * n_side * n_side + 6 * n_side
    N = n_chain_tok + n_water
    cfg = VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": 3.0})
    e = PolarPackEngine(cfg, seed, water_frac=n_water / N, chain_frac=n_chain_tok / N,
                        repel=40.0, attract=0.30, polarity=1.0, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=1.20, water_dipole=0.8,
                        aniso=0.0, k_bond=k_bond)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 1.0, 0.55
    e.repel_contact, e.rigidity, e.selectivity = 1.0, 0.0, 0.30
    e.temperature = temperature
    B = cfg.pos_bound
    mol = e._mol
    per = len(mol) // 2
    side = int(np.ceil(np.sqrt(per)))
    xs = (np.arange(side) + 0.5) / side * (2 * B) - B
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    hu = np.zeros((len(e._hi), 3))
    for leaf, sign in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        pts = flat[:len(idx)]
        for bead, zoff in enumerate((1.45, 0.90, 0.35)):   # head outermost -> tails at the midplane
            b = idx[:, bead]
            e.X[b, 0], e.X[b, 1] = pts[:, 0], pts[:, 1]
            e.X[b, 2] = sign * zoff
        hu[leaf * per:(leaf + 1) * per, 2] = sign          # head dipole points out into water
    e.head_u = hu
    r = np.random.default_rng(seed + 17)
    wi = e._wi
    e.X[wi, 0] = r.uniform(-B, B, len(wi))
    e.X[wi, 1] = r.uniform(-B, B, len(wi))
    e.X[wi, 2] = r.uniform(1.75, B, len(wi)) * r.choice([-1.0, 1.0], len(wi))
    if scramble:
        # SELF-ASSEMBLY test: throw the same molecules in at random and see whether a bilayer forms
        # on its own. Each lipid is still laid out extended along a random axis (its bonds fix that),
        # but molecular positions and orientations are disordered and water is mixed throughout.
        rr = np.random.default_rng(seed + 91)
        cen = rr.uniform(-B, B, (len(mol), 3))
        ax = rr.standard_normal((len(mol), 3))
        ax /= np.linalg.norm(ax, axis=1, keepdims=True)
        for bead, off in enumerate((1.0, 0.0, -1.0)):
            e.X[mol[:, bead], :3] = cen + off * BOND_R * ax
        e.head_u = ax.copy()
        e.X[e._wi, :3] = rr.uniform(-B, B, (len(e._wi), 3))
    e.vel[:] = 0.0
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:])
    e._write_chain(e.X[:, e.pd:])
    e._write_chain(e.c_rest)
    e._write_radii(e.X[:, e.pd:])
    return e


def build(seed, n_side=6, aniso=0.95, temperature=0.03, satt=1.0, q=2.0):
    """A planted bilayer: two leaflets in the x-y plane, tails meeting at z=0, heads pointing out
    into water. The box is periodic in z as well, so the water slab is continuous through the
    boundary — the standard membrane-simulation setup."""
    n_amphi = 2 * n_side * n_side
    # water fills the two slabs outside the membrane; pick a count that keeps liquid density
    n_water = 2 * n_side * n_side + 4 * n_side
    cfg = VivariumConfig(**{**DEFAULTS, "N": n_amphi + n_water, "pos_dim": 3,
                            "n_harmonics": 2, "pos_bound": 3.0})
    # species fractions are assigned by a random draw inside the engine, so ask for the split we
    # want and then OVERWRITE positions/orientations below.
    e = PolarPackEngine(cfg, seed, water_frac=n_water / cfg.N, amphi_frac=n_amphi / cfg.N,
                        repel=40.0, attract=0.30, polarity=1.0, cohesion=0.0, skew=0.0,
                        morph=0.70, momentum=0.30, speed=1.20, water_dipole=0.8, aniso=aniso,
                        amphi_charge=q)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, satt, 0.55
    e.repel_contact, e.rigidity, e.selectivity = 1.0, 0.0, 0.30
    e.temperature = temperature

    B = cfg.pos_bound
    ai, wi = e._ai, e._wi
    # --- amphiphiles: two square lattices, heads pointing AWAY from the midplane ---
    per = len(ai) // 2
    side = int(np.ceil(np.sqrt(per)))
    xs = (np.arange(side) + 0.5) / side * (2 * B) - B
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    u = np.zeros((len(ai), 3))
    for leaf, sign in ((0, +1.0), (1, -1.0)):
        idx = ai[leaf * per:(leaf + 1) * per]
        pts = flat[:len(idx)]
        e.X[idx, 0], e.X[idx, 1] = pts[:, 0], pts[:, 1]
        e.X[idx, 2] = sign * LEAFLET_Z
        u[leaf * per:(leaf + 1) * per, 2] = sign          # head points out toward water
    if len(ai) % 2:                                        # odd leftover: park it in the core
        e.X[ai[-1], :3] = 0.0
        u[-1, 2] = 1.0
    e.amphi_u = u
    # --- water: fill the slabs outside the membrane ---
    r = np.random.default_rng(seed + 17)
    zs = r.uniform(WATER_GAP, B, len(wi)) * r.choice([-1.0, 1.0], len(wi))
    e.X[wi, 0] = r.uniform(-B, B, len(wi))
    e.X[wi, 1] = r.uniform(-B, B, len(wi))
    e.X[wi, 2] = zs
    e.vel[:] = 0.0
    e._write_amphi(e.c_rest)
    e.X[:, e.pd:e.pd + e.tK] = 0.0
    e._write_water(e.X[:, e.pd:])
    e._write_amphi(e.X[:, e.pd:])
    e._write_radii(e.X[:, e.pd:])
    return e


# ---------------------------------------------------------------- bilayer order parameters

def _axes(e):
    """Per-molecule head->tail axis. For a chain that is the real molecular axis; for a single-bead
    amphiphile it is the stored head vector."""
    if getattr(e, "_mol", np.zeros((0, 3))).size:
        h, t = e.X[e._mol[:, 0], :3], e.X[e._mol[:, 2], :3]
        v = h - t
        v = v - e.L * np.round(v / e.L)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9), e.X[e._mol[:, 1], 2]
    return e.amphi_head(), e.X[e._ai, 2]


def nematic_S(e):
    """S = <(3cos²θ − 1)/2> of the head axes about the bilayer normal (z). 1 = perfectly aligned
    along the normal, 0 = isotropic. A bilayer is orientationally ordered ALONG its normal even
    though the two leaflets point opposite ways, so this uses cos² and ignores the sign."""
    c = _axes(e)[0][:, 2]
    return float(np.mean(1.5 * c * c - 0.5))


def leaflet_correctness(e):
    """Fraction of amphiphiles whose head points AWAY from the midplane — i.e. toward water. This
    is the defining property of a bilayer as opposed to any other dense lipid aggregate."""
    u, z = _axes(e)
    return float(np.mean(np.sign(z) * u[:, 2] > 0))


def core_dryness(e):
    """Fraction of particles inside the hydrophobic core (|z| < LEAFLET_Z) that are NOT water. A
    real bilayer core excludes water almost completely."""
    z = e.X[:, 2]
    core = np.abs(z) < 0.75
    if not core.any():
        return 0.0
    return float(np.mean(e.species[core] != WATER))


def emergence_score(e):
    """The BENCHMARK's metric, recomputed here so the toy can audit it: head-side water excess plus
    tail-side amphiphile excess, each against the local composition baseline."""
    ai = e._ai
    delta, d2 = e._periodic_delta()
    near = d2 < NEAR ** 2
    np.fill_diagonal(near, False)
    sp, head = e.species, e.amphi_head()
    out = []
    for k, i in enumerate(ai):
        nb = np.where(near[i])[0]
        if not nb.size:
            continue
        v = -delta[i, nb]
        v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        side = v @ head[k]
        hs, ts = nb[side > 0], nb[side <= 0]
        bw, ba = (sp[nb] == WATER).mean(), (sp[nb] == AMPHI).mean()
        hw = (sp[hs] == WATER).mean() - bw if hs.size else 0.0
        td = (sp[ts] == AMPHI).mean() - ba if ts.size else 0.0
        out.append(hw + td)
    return float(np.mean(out)) if out else 0.0


def report(e, tag):
    print(f"{tag:>10s}  S={nematic_S(e):+.3f}  leaflet={leaflet_correctness(e):.3f}  "
          f"dry_core={core_dryness(e):.3f}  emergence={emergence_score(e):+.4f}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--every", type=int, default=500)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--aniso", type=float, default=0.95)
    p.add_argument("--kt", type=float, default=0.03)
    p.add_argument("--chain", action="store_true", help="use 3-BEAD bonded lipids")
    p.add_argument("--scramble", action="store_true",
                   help="start DISORDERED — tests self-assembly rather than stability")
    p.add_argument("--kbond", type=float, default=1.5)
    p.add_argument("--q", type=float, default=2.0,
                   help="amphiphile head charge. The belt carries -q/4 (an unavoidable artefact of "
                        "truncating at l=2), so lateral repulsion scales as q^2 while vdW is fixed.")
    p.add_argument("--satt", type=float, default=1.0,
                   help="vdW decay lambda; range ~ 1/sqrt(lambda). Literature says the RANGE, "
                        "not the depth, is load-bearing: 1-2 sigma gives NO self-assembly, 3 sigma does.")
    a = p.parse_args(argv)

    e = (build_chain(a.seed, temperature=a.kt, k_bond=a.kbond, scramble=a.scramble) if a.chain
         else build(a.seed, aniso=a.aniso, temperature=a.kt, satt=a.satt, q=a.q))
    n_units = len(e._mol) if a.chain else len(e._ai)
    print(f"planted bilayer: N={e.cfg.N} lipids={n_units} water={len(e._wi)} chain={a.chain} "
          f"aniso={a.aniso} kT={a.kt} q={a.q} satt={a.satt} (range~{1/a.satt**0.5:.1f} sigma)")
    print("  S = nematic order about the bilayer normal (1 = aligned)")
    print("  leaflet = fraction with the head pointing out toward water (1 = correct bilayer)")
    print("  dry_core = fraction of the hydrophobic core that is NOT water (1 = correct)")
    print("  emergence = the BENCHMARK metric — should be strongly positive on a real bilayer\n")
    report(e, "t=0")
    for t in range(a.every, a.steps + 1, a.every):
        for _ in range(a.every):
            e.step()
        report(e, f"t={t}")
    print("\nreading: if S and leaflet stay high the force field SUPPORTS a bilayer and the problem "
          "is nucleation.\nIf they decay to ~0 the bilayer is not stable and the force field is "
          "wrong.\nIf they stay high but `emergence` is near 0, the BENCHMARK METRIC is blind.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
