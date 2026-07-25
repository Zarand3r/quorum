"""FROZEN benchmark: does membrane-like structure EMERGE from Pauli + vdW + electrostatics alone?

*** THIS FILE IS THE HARNESS. DO NOT EDIT IT DURING AN AUTO-RESEARCH RUN. ***
Editing it invalidates every row of results.tsv, because scores stop being comparable.

The mutable surface is the FORCE MODEL (pack.py / polar_pack.py). This harness only constructs a
fixed scenario, steps it, and measures. It computes its own order parameters from a deliberately
small engine interface — positions, `species`, `amphi_head()`, `_periodic_delta()` — so it stays
valid across force-model changes (including a move to 3D).

PRIMARY metric — `emergence_score` (higher is better).
    Amphiphile self-assembly excess, the definition of a micelle/bilayer: tails buried together
    AND heads facing water, each measured against the local composition baseline so it cannot be
    faked by simply clumping everything.

        head_water = P(neighbour on the HEAD side is water)      − baseline
        tail_dry   = P(neighbour on the TAIL side is amphiphile) − baseline
        emergence_score = mean over amphiphiles and seeds of (head_water + tail_dry)

    0 = randomly mixed/oriented (today's behaviour). >0 = real amphiphile ordering.

SECONDARY — `demix_excess` (higher is better): the hydrophobic effect that must precede assembly.
    Water/oil like-fraction rescaled so 0 = fully mixed, 1 = fully demixed. Reported every run and
    used ONLY as a tiebreak while `emergence_score` sits at 0 (it is the upstream driver).

GATES (any failure disqualifies the run regardless of score) — printed as `gate_*`:
    gate_base_identity : PolarPackEngine with polarity=0, no water still reduces to PackEngine.
    gate_occupancy     : water stays space-filling (no collapse to a droplet), ≥ 55 of 64 cells.

Run:  bazel run //projects/vivarium:bench_emergence
"""

from __future__ import annotations

import numpy as np

from config import DEFAULTS, POS_DIM, VivariumConfig
from pack import PackEngine
from polar_pack import AMPHI, OIL, WATER, PolarPackEngine

# ---- the fixed scenario. These numbers define the benchmark; they never change. ----
N = 190                 # ≈ full-box packing for pos_bound 6 → dense liquid, no free volume
STEPS = 1800            # long enough for structure to form, short enough to iterate on
SEEDS = (0, 1)          # averaged, to keep the score out of the single-seed noise floor
NEAR = 1.6              # neighbour cutoff (≈ 1.6 particle diameters)
WATER_FRAC_AMPHI = 0.70  # assembly scenario: 70% water, 30% amphiphile
AMPHI_FRAC = 0.30
WATER_FRAC_DEMIX = 0.50  # hydrophobic scenario: 50/50 water/oil
OIL_FRAC = 0.50

# fixed physics knobs (the FORCE MODEL is what experiments change, not these dials)
PHYS = dict(repel=5.0, attract=0.30, polarity=1.0, cohesion=0.0, skew=0.0,
            morph=0.70, momentum=0.30, speed=1.20, water_dipole=0.8)
SINKS = dict(sink_repel=6.0, sink_attract=1.0, sink_polarity=0.25)
STATE = dict(conservative=True, repel_contact=1.0, rigidity=0.0,
             selectivity=0.30, temperature=0.03)


def _cfg():
    return VivariumConfig(**{**DEFAULTS, "N": N})


def _build(seed, **species):
    e = PolarPackEngine(_cfg(), seed, **species, **PHYS)
    for k, v in {**SINKS, **STATE}.items():
        setattr(e, k, v)
    return e


def _neighbours(e):
    delta, d2 = e._periodic_delta()
    near = d2 < NEAR ** 2
    np.fill_diagonal(near, False)
    return delta, near


def _assembly(e):
    """(head_water − baseline) + (tail_dry − baseline), averaged over amphiphiles."""
    ai = e._ai
    if not ai.size:
        return 0.0
    delta, near = _neighbours(e)
    sp, head = e.species, e.amphi_head()
    out = []
    for idx, i in enumerate(ai):
        nb = np.where(near[i])[0]
        if not nb.size:
            continue
        u = -delta[i, nb]                                   # bearing i → j
        u = u / (np.linalg.norm(u, axis=1, keepdims=True) + 1e-9)
        side = u @ head[idx]
        hs, ts = nb[side > 0], nb[side <= 0]
        base_w, base_a = (sp[nb] == WATER).mean(), (sp[nb] == AMPHI).mean()
        hw = (sp[hs] == WATER).mean() - base_w if hs.size else 0.0
        td = (sp[ts] == AMPHI).mean() - base_a if ts.size else 0.0
        out.append(hw + td)
    return float(np.mean(out)) if out else 0.0


def _demix(e):
    """Rescaled water/oil like-fraction: 0 = fully mixed, 1 = fully demixed."""
    _, near = _neighbours(e)
    sp = e.species
    same = sp[:, None] == sp[None, :]
    tot = near.sum()
    if not tot:
        return 0.0
    like = (near & same).sum() / tot
    return float(max(0.0, (like - 0.5) * 2.0))


def _occupancy(e):
    """How many of an 8×8 grid of cells contain a token — collapse detector."""
    p = e.X[:, :POS_DIM][:, :2]
    b = e.cfg.pos_bound
    g = np.floor((p + b) / (2 * b) * 8).clip(0, 7).astype(int)
    return len(set(map(tuple, g.tolist())))


def _gate_base_identity():
    """PolarPackEngine with the polar features off must still reduce to PackEngine exactly."""
    cfg = _cfg()
    a = PolarPackEngine(cfg, 0, water_frac=0.0, polarity=0.0)
    b = PackEngine(cfg, 0)
    for _ in range(200):
        a.step()
        b.step()
    return float(np.max(np.abs(a.X - b.X)))


def main() -> int:
    scores, demixes, occs = [], [], []
    for s in SEEDS:
        e = _build(s, water_frac=WATER_FRAC_AMPHI, amphi_frac=AMPHI_FRAC)
        for _ in range(STEPS):
            e.step()
        scores.append(_assembly(e))
        occs.append(_occupancy(e))

        d = _build(s, water_frac=WATER_FRAC_DEMIX, oil_frac=OIL_FRAC)
        for _ in range(STEPS):
            d.step()
        demixes.append(_demix(d))

    delta = _gate_base_identity()
    occ = int(np.min(occs))
    print(f"emergence_score: {np.mean(scores):.6f}")
    print(f"demix_excess: {np.mean(demixes):.4f}")
    print(f"gate_occupancy: {occ}  (need >= 55)")
    print(f"gate_base_identity: {delta:.2e}  (need 0)")
    ok = (delta == 0.0) and (occ >= 55)
    print(f"gates_pass: {'YES' if ok else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
