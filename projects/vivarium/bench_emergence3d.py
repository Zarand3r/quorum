"""FROZEN 3-D benchmark: does a membrane EMERGE from Pauli + vdW + electrostatics in a VOLUME?

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

3-D is the same physics one dimension up: positions are (N,3) and the grounded contour readout
⟨C, basis(bearing)⟩ switches from circular harmonics {cos kθ, sin kθ} to REAL SPHERICAL HARMONICS
Y_lm — still a relative-direction inner product, still Parseval, still transformer-only. It matters
because 2-D dipolar water forms H-bond CHAINS rather than a 3-D network, which structurally caps the
hydrophobic effect (docs/BILAYER_REVIEW.md, Finding 3).

Scores here are NOT comparable to the 2-D benchmark — different dimensionality, different baselines.
This is a separate auto-research run with its own log.

Run:  bazel run //projects/vivarium:bench_emergence3d
"""

from __future__ import annotations

import numpy as np

from config import DEFAULTS, POS_DIM, VivariumConfig
from pack import PackEngine
from polar_pack import AMPHI, OIL, WATER, PolarPackEngine

# ---- the fixed scenario. These numbers define the benchmark; they never change. ----
N = 190                 # in a VOLUME: pos_bound 3 → 6³=216 units³ ⇒ same liquid density as the 2-D dish
STEPS = 1200            # long enough for structure to form, short enough to iterate on
SEEDS = (0, 1)          # averaged, to keep the score out of the single-seed noise floor
NEAR = 1.6              # neighbour cutoff (≈ 1.6 particle diameters)
WATER_FRAC_AMPHI = 0.70  # assembly scenario: 70% water, 30% amphiphile
AMPHI_FRAC = 0.30
WATER_FRAC_DEMIX = 0.50  # hydrophobic scenario: 50/50 water/oil
OIL_FRAC = 0.50

# fixed physics knobs (the FORCE MODEL is what experiments change, not these dials)
# repel 40 (was 5): once the electrostatic force was made genuinely conservative the dish
# CONDENSED at repel=5 — a conservative cohesive liquid minimises its energy by collapsing unless
# excluded volume is stiff enough to hold it open. Real liquids are nearly incompressible, so a
# stiff excluded volume is the physical choice, not a fudge.
PHYS = dict(repel=40.0, attract=0.30, polarity=1.0, cohesion=0.0, skew=0.0,
            morph=0.70, momentum=0.30, speed=1.20, water_dipole=0.8)
# sink_polarity 0.55 (not 0.25 as in 2-D): the 3-D box is half as wide to keep liquid density, and
# at 0.25 the electrostatic kernel is still 0.105 at L/2 — 12.9% of the interaction weight came from
# beyond the minimum-image cutoff, i.e. molecules interacting with their own periodic images.
# Physically defensible as well as necessary: electrostatics in bulk water is Debye-screened.
SINKS = dict(sink_repel=6.0, sink_attract=1.0, sink_polarity=0.55)
STATE = dict(conservative=True, repel_contact=1.0, rigidity=0.0,
             selectivity=0.30, temperature=0.03)


def _cfg():
    # pos_dim=3 ⇒ spherical harmonics; K=2 keeps pos3 + shape8 + hidden5 inside d=16.
    return VivariumConfig(**{**DEFAULTS, "N": N, "pos_dim": 3, "n_harmonics": 2, "pos_bound": 3.0})


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
    """Occupied cells of a 4×4×4 volumetric grid, rescaled to /64 so the gate threshold matches the
    2-D harness. Collapse detector: a condensed droplet leaves most cells empty."""
    p = e.X[:, :e.pd]
    b = e.cfg.pos_bound
    g = np.floor((p + b) / (2 * b) * 4).clip(0, 3).astype(int)
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
    print(f"gate_occupancy: {occ}  (need >= 55 of 64 cells)")
    print(f"gate_base_identity: {delta:.2e}  (need 0)")
    margin = _build(SEEDS[0], water_frac=WATER_FRAC_AMPHI, amphi_frac=AMPHI_FRAC).min_image_margin()
    print(f"gate_min_image: {margin:.2e}  (need < 0.01 — periodic boundaries valid)")
    ok = (delta == 0.0) and (occ >= 55) and (margin < 0.01)
    print(f"gates_pass: {'YES' if ok else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
