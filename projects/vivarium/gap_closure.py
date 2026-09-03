"""Does a planted arc close? The high-power endpoint for the 2-D knob ladder.

WHY THIS FILE EXISTS

Every knob test before it was scored on the SELF-ASSEMBLY vesicle rate, which is 2/18 ~ 11%. At six
seeds per arm that design resolves nothing -- the last rung returned 0/6 vs 0/6, and 0/6 is the
EXPECTED result for both arms. Two full-length runs were spent learning that.

Closure is controlled by the ribbon's end-to-end gap, the one reaction coordinate in this project that
has ever been validated (docs/RESULTS.md):

    3.4 sigma  5/5      6.7 sigma  4/5      10.1 sigma  1/10

Fisher on the extremes is p = 0.0016, and closure is FAST -- 4 of 5 seeds closed by step 10,000
against a 300,000 budget. A graded, cheap endpoint instead of a rare, expensive one.

THE GEOMETRY, RE-DERIVED

`_mixture._plant_ring(span=s)` puts n lipids on an arc at R_mid = n*lat/(4*pi*s), with lat = 2 for a
branched 4-tail lipid, so the missing sector's arc length is

    gap = 2*pi*R_mid*(1 - s) = (n*lat/2) * (1 - s)/s      =>      s = (n*lat/2)/((n*lat/2) + gap)

Checked against the two radii published with the table: N=70 gap 10.1 -> R_mid 12.75 (published 12.8);
N=300 gap 10.1 -> 49.35 (published 49.3). The harness inverts the formula to place a requested gap, so
a gap is never typed as a span.

WHAT `closed` MEANS -- fixed in the spec BEFORE any run

`n_enclosed >= 1` at any checkpoint: the detector the published table names. `vesicle_call` is
recorded in its own column but is NOT the gate. Choosing between two available yardsticks after seeing
the data is a failure this project has already committed once.

SCOPE LIMIT, not worked around: this assay hands the system its curvature, so it tests CLOSURE GIVEN A
MEMBRANE, not assembly-then-closure. A pass supports "the chemistry reduces", never "vesicles emerge
from geometry alone".

    python gap_closure.py --gate          # instrument gate: reproduce the published dose-response
    python gap_closure.py --rung 1        # one rung of specs/2026-09-02_knob_ladder_2d.md
"""

from __future__ import annotations

import os as _os

# Workers are THREADS in one process; every BLAS call would otherwise spawn its own pool and they
# thrash. Measured cost of omitting this elsewhere in this project: 23.4 CPU-hours against ~4.5 of
# work. Must run BEFORE numpy is imported.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import itertools
import os
import pathlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

import _mixture
from _lumen_field import n_enclosed, vesicle_call
from field import Field, HEAD, TAIL, WATER, N_SPECIES

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "gap_closure.tsv"
STATES = _HERE / "docs" / "states_gap"

N_LIP, L_BOX, KT, PHI, DT = 70, 45.0, 0.45, 0.55, 8e-3
LAT = 2.0                       # lateral footprint of a branched 4-tail lipid, per _plant_ring
STEPS, CHECK_EVERY, TAIL_STEPS = 300_000, 10_000, 50_000
GAPS = (3.4, 10.1)              # the two gates of the dose-response; 6.7 is the interpolation point
_LOCK = threading.Lock()
COLUMNS = ("rung", "arm", "gap", "span", "seed", "closed", "first_closed_step",
           "n_enc_final", "vesicle_call", "steps_run", "largest", "wall_s")

# The production chemistry, written out rather than read from default_chi(), which consults
# VIVARIUM_CHI_* in the process environment -- a global that another engine in the same process can
# change underneath this one.
PRODUCTION = {"tt": 0.70, "hh": 0.20, "ht": -0.25, "hw": 0.75, "tw": 0.00, "ww": 0.50}

# The ladder of specs/2026-09-02_knob_ladder_2d.md, with Amendment 1's three arms per rung:
#   A  baseline      the rung below, unchanged
#   B  removal       the knob zeroed, nothing added
#   C  replacement   the knob zeroed plus the geometric/thermodynamic mechanism
# B exists so a pass cannot be credited to the mechanism when the knob was simply not load-bearing.
#
# Rungs beyond 1 are added ONLY after the rung below returns a verdict, because each builds on
# whichever arm won. Pre-writing them would commit the ladder to a chemistry that may not survive.
ARMS = {
    "0":  ("production baseline",         dict(PRODUCTION),                    1.0),
    "1B": ("chi_HT removed",              {**PRODUCTION, "ht": 0.00},          1.0),
    "1C": ("chi_HT -> head sigma 0.95",   {**PRODUCTION, "ht": 0.00},          0.95),
    # Rung 1 verdict: arm B passed, so chi_HT is removed with NO replacement and sigma_head stays 1.0
    # -- adding a geometric parameter that buys nothing is a knob gained, not a knob removed.
    "2B": ("chi_HH removed",              {**PRODUCTION, "ht": 0.00, "hh": 0.00}, 1.0),
}


def span_for_gap(gap: float, n: int = N_LIP) -> float:
    """Invert gap = (n*lat/2)*(1-s)/s. A gap is never typed as a span anywhere in this file."""
    half = n * LAT / 2.0
    return half / (half + float(gap))


def chi_from(spec: dict) -> np.ndarray:
    chi = np.zeros((N_SPECIES, N_SPECIES))
    chi[TAIL, TAIL] = spec["tt"]
    chi[HEAD, HEAD] = spec["hh"]
    chi[WATER, WATER] = spec["ww"]
    chi[HEAD, TAIL] = chi[TAIL, HEAD] = spec["ht"]
    chi[HEAD, WATER] = chi[WATER, HEAD] = spec["hw"]
    chi[TAIL, WATER] = chi[WATER, TAIL] = spec["tw"]
    return chi


def run_one(rung: str, gap: float, seed: int, steps: int = STEPS) -> dict:
    t0 = time.perf_counter()
    label, spec, sig_head = ARMS[rung]
    span = span_for_gap(gap)
    d = 2
    lip_beads = N_LIP * 5
    n_water = int(round(PHI * L_BOX ** d / _mixture.C_D[d] * (2 ** d))) - lip_beads
    if n_water < 0:
        raise ValueError(f"L={L_BOX} too small for {N_LIP} lipids at phi={PHI}")
    X, species, bonds, mols, wi, chains = _mixture.build(
        0, N_LIP, n_water, L_BOX, d, plant=f"arc{span:.6f}", branched=True, seed=seed)
    sig = np.full(N_SPECIES, 1.0)
    sig[HEAD] = sig_head
    f = Field(species, bonds, L_BOX, chi=chi_from(spec), sigma_species=sig)
    ig = _mixture.make_step_engine(f, X, KT, DT, 1 + seed, engine="transformer")
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)

    # Amendment 2: stop TAIL_STEPS after the first closure. The registered endpoint is
    # "n_enclosed >= 1 at ANY checkpoint", so its value is already determined once one is seen and
    # early exit is exactly equivalent for it. The tail is not padding -- it turns the secondary
    # readouts into a PERSISTENCE check (did the ring survive further noise). Runs that never close
    # are unaffected and run the full budget.
    first, ne, ran = -1, 0, steps
    X = np.ascontiguousarray(X, dtype=np.float64)
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % CHECK_EVERY == 0:
            ne = int(n_enclosed(X, mm, L_BOX)[0])
            if ne >= 1 and first < 0:
                first = i + 1
            # PROGRESS, every 100k. A run that prints nothing until it returns is how a 4-hour job in
            # this project got killed on a cost model that was wrong by 5x: the only way to price the
            # sweep was a solo benchmark, which does not include worker contention.
            if first >= 0 and (i + 1) - first >= TAIL_STEPS:
                ran = i + 1
                break
            if (i + 1) % 100_000 == 0:
                print(f"    [{rung} gap={gap} sd={seed}] {i+1}/{steps} n_enc={ne} "
                      f"first={first} ({time.perf_counter()-t0:.0f}s)", flush=True)
    ok, _why = vesicle_call(X, mm, L_BOX)
    # SAVE THE COORDINATES. Every structural claim in this project has to be checked against a
    # picture -- the scalar has contradicted the render every time one was made. A `closed` column
    # with no state behind it cannot be checked, so the first two seeds of each arm/gap are kept.
    if seed % 100 < 2:
        STATES.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(STATES / f"r{rung}_g{gap}_sd{seed}.npz",
                            X=X, mols=mm, species=species, L=L_BOX, gap=gap, closed=int(first >= 0))
    return {"rung": rung, "arm": label, "gap": gap, "span": round(span, 6), "seed": seed,
            "closed": int(first >= 0), "first_closed_step": first, "n_enc_final": ne,
            "vesicle_call": int(ok), "steps_run": ran, "largest": len(mm), "wall_s": round(time.perf_counter() - t0, 1)}


def _append(row: dict) -> None:
    with _LOCK:
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        new = not RESULTS.exists()
        with open(RESULTS, "a") as fh:
            if new:
                fh.write("\t".join(COLUMNS) + "\n")
            fh.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def _fisher_1s(a: int, na: int, b: int, nb: int) -> float:
    """One-sided Fisher exact, P(closure in arm A >= observed) under independence. No scipy here."""
    from math import comb
    tot, k = na + nb, a + b
    p = 0.0
    for x in range(a, min(na, k) + 1):
        p += comb(na, x) * comb(nb, k - x)
    return p / comb(tot, k)


def load():
    if not RESULTS.exists():
        return []
    out = []
    for line in RESULTS.read_text().splitlines()[1:]:
        f = line.split("\t")
        if len(f) == len(COLUMNS):
            out.append(dict(zip(COLUMNS, f)))
    return out


def score() -> int:
    rows = load()
    if not rows:
        print("  no results yet")
        return 0
    by = {}
    for r in rows:
        by.setdefault((r["rung"], float(r["gap"])), []).append(int(r["closed"]))
    print(f"  {'rung':>4} {'arm':>28} {'gap':>6} {'closed':>9} {'vcall':>6}")
    for k in sorted(by):
        v = by[k]
        vc = sum(int(r["vesicle_call"]) for r in rows
                 if r["rung"] == k[0] and float(r["gap"]) == k[1])
        print(f"  {k[0]:>4} {ARMS[k[0]][0]:>28} {k[1]:>6} {sum(v):>4}/{len(v):<4} {vc:>6}")
    for rung in sorted({r['rung'] for r in rows}):
        near, far = by.get((rung, 3.4)), by.get((rung, 10.1))
        if not near or not far:
            continue
        p = _fisher_1s(sum(near), len(near), sum(far), len(far))
        disc = sum(near) / len(near) > sum(far) / len(far) and p <= 0.05
        print(f"\n  rung {rung} ({ARMS[rung][0]}): near {sum(near)}/{len(near)} vs "
              f"far {sum(far)}/{len(far)}, Fisher one-sided p = {p:.4f}")
        print(f"    coordinate still discriminates (near > far, p <= 0.05): {disc}")
        if rung == "0":
            g = sum(near) >= 4 * len(near) / 5 and sum(far) <= 3 * len(far) / 10 and p <= 0.05
            print(f"    GATE I (reproduces the published dose-response): {g}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true", help="rung 0: the instrument gate")
    ap.add_argument("--rung", type=str)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--seed0", type=int, default=100)
    ap.add_argument("--steps", type=int, default=STEPS)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args(argv)
    if a.score or (a.rung is None and not a.gate):
        return score()
    rungs = ["0"] if a.gate else [x.strip() for x in a.rung.split(",") if x.strip()]
    done = {(r["rung"], float(r["gap"]), int(r["seed"])) for r in load()}
    todo = [(rg, g, sd) for rg, g, sd in itertools.product(
        rungs, GAPS, range(a.seed0, a.seed0 + a.seeds)) if (rg, g, sd) not in done]
    names = ", ".join(f"{r} ({ARMS[r][0]})" for r in rungs)
    print(f"gap_closure {names}: {len(todo)} runs, "
          f"N={N_LIP} L={L_BOX} {a.steps} steps, {a.workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, r, g, sd, a.steps): (r, g, sd) for r, g, sd in todo}
        for fut in as_completed(futs):
            r, g, sd = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:
                print(f"  rung{r} gap={g} sd={sd}: FAILED {exc!r}", flush=True)
                continue
            _append(row)
            print(f"  rung{r} gap={g:<5} sd={sd}: closed={row['closed']} "
                  f"first={row['first_closed_step']} vcall={row['vesicle_call']} "
                  f"({row['wall_s']}s)", flush=True)
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
