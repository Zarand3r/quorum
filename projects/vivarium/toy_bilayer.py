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
from polar_pack import AMPHI, WATER, PolarPackEngine

NEAR = 1.6          # neighbour cutoff, same as the benchmark
LEAFLET_Z = 0.55    # half the hydrophobic core thickness
WATER_GAP = 1.15    # water starts beyond this |z|


def build(seed, n_side=6, aniso=0.95, temperature=0.03):
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
                        morph=0.70, momentum=0.30, speed=1.20, water_dipole=0.8, aniso=aniso)
    e.conservative = True
    e.sink_repel, e.sink_attract, e.sink_polarity = 6.0, 1.0, 0.55
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

def nematic_S(e):
    """S = <(3cos²θ − 1)/2> of the head axes about the bilayer normal (z). 1 = perfectly aligned
    along the normal, 0 = isotropic. A bilayer is orientationally ordered ALONG its normal even
    though the two leaflets point opposite ways, so this uses cos² and ignores the sign."""
    c = e.amphi_head()[:, 2]
    return float(np.mean(1.5 * c * c - 0.5))


def leaflet_correctness(e):
    """Fraction of amphiphiles whose head points AWAY from the midplane — i.e. toward water. This
    is the defining property of a bilayer as opposed to any other dense lipid aggregate."""
    z = e.X[e._ai, 2]
    h = e.amphi_head()[:, 2]
    return float(np.mean(np.sign(z) * h > 0))


def core_dryness(e):
    """Fraction of particles inside the hydrophobic core (|z| < LEAFLET_Z) that are NOT water. A
    real bilayer core excludes water almost completely."""
    z = e.X[:, 2]
    core = np.abs(z) < LEAFLET_Z
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
    a = p.parse_args(argv)

    e = build(a.seed, aniso=a.aniso, temperature=a.kt)
    print(f"planted bilayer: N={e.cfg.N} amphiphiles={len(e._ai)} water={len(e._wi)} "
          f"aniso={a.aniso} kT={a.kt}")
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
