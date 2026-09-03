"""Gel, fluid, or gas? The phase instrument for specs/2026-09-03_phase_search.md.

WHY THIS AND NOT A YES/NO

Cooke, Kremer & Deserno's taxonomy has THREE outcomes, not two, and this project has been treating it
as two. Quoted in docs/DEEP_RESEARCH_2026-08-31.md: "At sufficiently low temperature the bilayer
adopted a gel phase; within a more elevated temperature range a fluid phase can be reached; at
sufficiently high temperature a bilayer under zero tension always fell apart."

A gel is CONDENSED but ARRESTED. It holds whatever shape it is given and cannot anneal into a new one,
so it looks like a healthy membrane to every structural metric this project owns while being unable to
do the one thing a vesicle needs: coarsen and change topology.

TWO OBSERVABLES, because either alone misleads

    condensed   largest connected aggregate as a fraction of all lipids. Separates gas from the rest
                and nothing else -- a gel and a fluid both score ~1.
    mobile      NEIGHBOUR RETENTION: of a lipid's k nearest neighbours at t0, what fraction are still
                among its k nearest at t1. A fluid forgets its neighbours; a gel keeps them.

Neighbour retention rather than mean-squared displacement, because MSD is faked by collective drift
and by breathing modes -- the aggregate translating or pulsing as a body registers as motion while
every lipid keeps the same neighbours. Retention is invariant to both.

    gel   = condensed AND NOT mobile
    fluid = condensed AND mobile
    gas   = NOT condensed

VALIDATION IS A SEPARATION TEST. `validate()` requires three known-answer controls to land in three
DIFFERENT boxes -- a deep freeze, Cooke's own published fluid point, and a boil. Scoring the intended
case well is not enough and has misled this project repeatedly; the instrument must discriminate.
"""
from __future__ import annotations

import os as _os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import pathlib

import numpy as np

import _mixture
from field import Field, HEAD, N_SPECIES
from gap_closure import chi_from

EPS = 1.0
N_LIP, L_BOX, DT = 70, 45.0, 8e-3
K_NEIGH = 6
CONDENSED_MIN = 0.60      # below this the aggregate has broken up -> gas
MOBILE_MAX = 0.70         # retention above this means neighbours are not being exchanged -> gel
# Connectivity cut for lipid CENTROIDS, derived from the geometry rather than tuned on the controls.
# `_plant_ring` gives a branched 4-tail lipid a lateral footprint of `lat = 2.0`, and the two leaflets
# sit tail-tip to tail-tip so their centroids are ~2.4 apart. A cut of 1.5x the footprint spans the
# bilayer; anything below ~2.6 measures ONE LEAFLET and reports a perfectly intact planted ring as
# 0.600 -- which is exactly what cut = 2.0 did on the first run of this file.
CUT = 3.0


def centroids(X, mols, L):
    """Per-lipid centroid, unwrapped against the molecule's own head so a lipid straddling the
    boundary does not average to the middle of the box."""
    ref = X[mols[:, 0]][:, None, :]
    d = X[mols] - ref
    d -= L * np.round(d / L)
    return ref[:, 0, :] + d.mean(axis=1)


def neighbours(C, L, k=K_NEIGH):
    d = C[:, None, :] - C[None, :, :]
    d -= L * np.round(d / L)
    r2 = np.einsum("ijk,ijk->ij", d, d)
    np.fill_diagonal(r2, np.inf)
    return np.argsort(r2, axis=1)[:, :k]


def retention(n0, n1) -> float:
    """Fraction of each lipid's original k neighbours still among its k nearest. 1 = frozen."""
    return float(np.mean([len(set(a) & set(b)) / len(a) for a, b in zip(n0, n1)]))


def condensed(C, L, cut=CUT) -> float:
    """Largest connected component of lipid centroids, as a fraction. Gas breaks this."""
    n = len(C)
    seen = -np.ones(n, dtype=np.int64)
    best = 0
    cur = 0
    for s in range(n):
        if seen[s] >= 0:
            continue
        stack, seen[s] = [s], cur
        size = 0
        while stack:
            i = stack.pop()
            size += 1
            d = C - C[i]
            d -= L * np.round(d / L)
            m = np.where((np.einsum("ij,ij->i", d, d) < cut * cut) & (seen < 0))[0]
            seen[m] = cur
            stack.extend(m.tolist())
        best = max(best, size)
        cur += 1
    return best / n


def classify(cond: float, ret: float) -> str:
    if cond < CONDENSED_MIN:
        return "gas"
    return "gel" if ret > MOBILE_MAX else "fluid"


def measure(t_star: float, w_star: float = 1.5, chi_tt: float = 1.0, sigma_head: float = 0.95,
            equil: int = 60_000, window: int = 60_000, seed: int = 1, phi: float = 0.0) -> dict:
    """Plant a closed bilayer ring, equilibrate, then watch whether neighbours are exchanged.

    A PLANTED membrane, not an assembled one: the question is whether an existing membrane can
    rearrange, which is separable from whether one can form. Confounding the two is how a gel hides.
    """
    kT = t_star * EPS * chi_tt
    d = 2
    lip = N_LIP * 5
    n_water = 0 if phi <= 0 else int(round(phi * L_BOX ** d / _mixture.C_D[d] * (2 ** d))) - lip
    X, species, bonds, mols, wi, chains = _mixture.build(
        0, N_LIP, n_water, L_BOX, d, plant="arc1.0", branched=True, seed=seed)
    sig = np.full(N_SPECIES, 1.0)
    sig[HEAD] = sigma_head
    spec = {"tt": chi_tt, "hh": 0.0, "ht": 0.0, "hw": 0.0, "tw": 0.0, "ww": 0.0}
    f = Field(species, bonds, L_BOX, chi=chi_from(spec), sigma_species=sig, rc=1.0 + w_star)
    ig = _mixture.make_step_engine(f, X, kT, DT, 1 + seed, engine="transformer")
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    X = np.ascontiguousarray(X, dtype=np.float64)

    for _ in range(equil):
        X = ig.step(X)
    C0 = centroids(X, mm, L_BOX)
    n0 = neighbours(C0, L_BOX)
    for _ in range(window):
        X = ig.step(X)
    C1 = centroids(X, mm, L_BOX)
    ret = retention(n0, neighbours(C1, L_BOX))
    cond = condensed(C1, L_BOX)
    # bond integrity: at high T* the chains go floppy and "fluid" could mean "falling apart"
    bl = X[bonds[:, 0]] - X[bonds[:, 1]]
    bl -= L_BOX * np.round(bl / L_BOX)
    return {"t_star": t_star, "w_star": w_star, "kT": round(kT, 4), "seed": seed,
            "condensed": round(cond, 3), "retention": round(ret, 3),
            "phase": classify(cond, ret),
            "bond_mean": round(float(np.linalg.norm(bl, axis=1).mean()), 3)}


def _structural_controls() -> bool:
    """Fix the connectivity cut WITHOUT reference to temperature.

    A planted ring is intact by construction and must read 1.0; a dispersed random start is a gas by
    construction and must read low. These are structural facts, so they calibrate `CUT` independently
    of the phase controls -- tuning the cut on the same runs used to validate the instrument would be
    circular.
    """
    out = {}
    for tag, plant in (("planted ring (intact)", "arc1.0"), ("dispersed (gas)", "random")):
        X, sp, b, mols, wi, ch = _mixture.build(0, N_LIP, 0, L_BOX, 2, plant=plant,
                                                branched=True, seed=1)
        mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
        C = centroids(np.ascontiguousarray(X, dtype=np.float64), mm, L_BOX)
        out[tag] = condensed(C, L_BOX)
        print(f"  {tag:>22}: condensed = {out[tag]:.3f}")
    ok = (out["planted ring (intact)"] > 0.95
          and out["dispersed (gas)"] < CONDENSED_MIN)
    print(f"  cut = {CUT} separates intact from dispersed: {ok}\n")
    return ok


def validate() -> int:
    """Three known-answer controls that must land in THREE DIFFERENT boxes."""
    print("STRUCTURAL controls (fix the cut, no dynamics, no temperature):")
    struct = _structural_controls()
    print("PHASE controls:")
    cases = [("deep freeze", 0.10, "gel"),
             ("Cooke fluid point", 1.10, "fluid"),
             ("boil", 5.00, "gas")]
    print(f"  {'control':>18} {'T*':>6} {'kT':>6} {'condensed':>10} {'retention':>10} "
          f"{'phase':>7} {'expected':>9}")
    got = {}
    for name, ts, want in cases:
        m = measure(ts)
        got[name] = m
        flag = "" if m["phase"] == want else "   <-- MISMATCH"
        print(f"  {name:>18} {ts:>6} {m['kT']:>6} {m['condensed']:>10} {m['retention']:>10} "
              f"{m['phase']:>7} {want:>9}{flag}")
    ok = all(got[n]["phase"] == w for n, _, w in cases) and struct
    distinct = len({got[n]["phase"] for n, _, _ in cases}) == 3
    print(f"\n  all three match their known answer: {ok}")
    print(f"  the three land in three DIFFERENT boxes: {distinct}")
    print(f"  INSTRUMENT USABLE: {ok and distinct}")
    return 0 if (ok and distinct) else 1


# The map, in reduced units. T* covers every configuration this project has used (0.375 = rung 6A,
# 0.45 = rung 6B, 0.643 = production and rungs 0-5) plus Cooke's fluid point and above. w* brackets
# Cooke's safe band, whose lower edge (0.8) is a documented hard floor.
T_STARS = (0.375, 0.45, 0.643, 0.9, 1.1, 1.4, 1.8)
W_STARS = (1.0, 1.5, 2.0)
OURS = {0.375: "rung 6A", 0.45: "rung 6B", 0.643: "production / rungs 0-5", 1.1: "Cooke reference"}
RESULTS = pathlib.Path(__file__).resolve().parent / "docs" / "results" / "phase_map.tsv"
COLUMNS = ("t_star", "w_star", "kT", "seed", "condensed", "retention", "phase", "bond_mean")


def _row(t, w, sd):
    return measure(t, w_star=w, seed=sd)


def run_map(seeds=3, workers=20):
    import itertools, os
    from concurrent.futures import ProcessPoolExecutor, as_completed
    todo = [(t, w, sd) for t, w, sd in itertools.product(T_STARS, W_STARS, range(1, seeds + 1))]
    print(f"phase map: {len(todo)} runs ({len(T_STARS)}x{len(W_STARS)} cells, {seeds} seeds)",
          flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_row, t, w, sd): (t, w, sd) for t, w, sd in todo}
        for fut in as_completed(futs):
            try:
                rows.append(fut.result())
            except Exception as exc:
                print(f"  {futs[fut]}: FAILED {exc!r}", flush=True)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS, "w") as fh:
        fh.write("\t".join(COLUMNS) + "\n")
        for r in sorted(rows, key=lambda r: (r["t_star"], r["w_star"], r["seed"])):
            fh.write("\t".join(str(r[c]) for c in COLUMNS) + "\n")
        fh.flush(); os.fsync(fh.fileno())
    return show()


def show():
    if not RESULTS.exists():
        print("  no map yet"); return 0
    rows = [dict(zip(COLUMNS, l.split("\t"))) for l in RESULTS.read_text().splitlines()[1:]]
    import collections
    print(f"\n  {'T*':>7} " + " ".join(f"{('w*=' + str(w)):>16}" for w in W_STARS) + "   note")
    for t in T_STARS:
        cells = []
        for w in W_STARS:
            v = [r for r in rows if float(r["t_star"]) == t and float(r["w_star"]) == w]
            if not v:
                cells.append(f"{'-':>16}"); continue
            ph = collections.Counter(r["phase"] for r in v).most_common(1)[0][0]
            cond = sum(float(r["condensed"]) for r in v) / len(v)
            ret = sum(float(r["retention"]) for r in v) / len(v)
            cells.append(f"{ph:>5} {cond:4.2f}/{ret:4.2f}")
        print(f"  {t:>7} " + " ".join(f"{c:>16}" for c in cells) + f"   {OURS.get(t, '')}")
    print("\n  cells show: phase  condensed/retention   (gel = condensed & retention > 0.70)")
    return 0


if __name__ == "__main__":
    import sys
    if "--map" in sys.argv:
        raise SystemExit(run_map())
    if "--show" in sys.argv:
        raise SystemExit(show())
    raise SystemExit(validate())
