"""Locate this model's fluid-bilayer band in the (attraction width, temperature) plane.

WHY

Cooke & Deserno (J. Chem. Phys. 123, 224710, 2005) map exactly this plane for the cosine tail
attraction that `field._well` implements, and find three phases: gel, fluid, and unstable/gas, with
the fluid band lying between two curves that both rise with the attraction width `w_c`. At
`w_c ~ 1.5` their fluid band sits near `kT/eps ~ 0.9-1.5`.

Vivarium runs at `rc = 2.5` (so `w_c = rc - 1 = 1.5`), `chi_TT = 0.70` and `kT = 0.45`, i.e.
`kT/eps_eff = 0.64` -- BELOW their gel boundary. Every 3-D run in this project may therefore have been
a gel, which does not self-assemble; and a gel is exactly what small frozen non-coarsening aggregates
look like. This script tests that.

METHOD, taken from the paper rather than invented here

CD determined the phase diagram by PLANTING a bilayer and asking what happens to it, not by waiting
for self-assembly. That is far cheaper and it is the method being reproduced. We plant a vesicle (our
3-D planted bilayer), equilibrate, and classify:

    breakup  -- the aggregate falls apart                  (their "gas"/unstable)
    gel      -- it holds together but lipids do not move   (their gel)
    fluid    -- it holds together and lipids diffuse       (their fluid)

The gel/fluid discriminator is the lateral mobility of lipids WITHIN the aggregate, with the
aggregate's own centre-of-mass drift removed. That is the observable CD use (diffusion constant), and
unlike `n_enclosed` it involves no grid and no dimensional assumption.

    python phase_diagram.py --probe     # instrument validation, run this first
    python phase_diagram.py --sweep
"""

from __future__ import annotations

import argparse
import itertools
import os
import pathlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

import _mixture
from field import Field, cooke_chi
from _mixture import make_step_engine

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "phase_diagram.tsv"

# CD's molecule: one head, two tails, LINEAR. Their bead sizes: every head-involved pair 0.95 sigma,
# tail-tail 1.0. Their bonds are FENE k = 30 eps/sigma^2; ours are harmonic, so k_bond = 30 matches
# the stiffness constant but not the functional form -- recorded as a known difference.
N_LIP, L_BOX, DIM = 200, 16.0, 3
SIGMA_HEAD, K_BOND = 0.95, 30.0
DT = 8e-3
COLUMNS = ("rc", "w_c", "kT", "seed", "steps", "frac_largest", "msd_per_1k",
           "core_frac", "hollow", "phase", "wall_s")

# Thresholds CALIBRATED ON THE PROBE (--probe, 2026-08-29), and therefore FITTED, not predictive.
# They are stated here so the classification is reproducible, but the primary result of the sweep is
# the CONTINUOUS msd_per_1k map, which needs no threshold at all. Probe references:
#
#     kT = 0.05 (frozen)      frac 1.000   msd 0.039
#     kT = 0.45 (ours)        frac 1.000   msd 0.242
#     kT = 1.00 (CD fluid)    frac 0.995   msd 1.272
#     kT = 3.00 (too hot)     frac 0.670   msd 14.613
#
# The first pass guessed BREAKUP_FRAC = 0.5 and GEL_MSD = 0.05; the probe showed 0.5 never fires even
# at visible disintegration, and 0.05 would call the frozen-adjacent case fluid. Both moved BEFORE any
# sweep cell was run, and no sweep data existed when they moved.
BREAKUP_FRAC = 0.90    # planted vesicle keeps >= 0.995 while intact; 0.67 at kT = 3.0
GEL_MSD = 0.127        # one tenth of the CD fluid reference (1.272)

_WRITE_LOCK = threading.Lock()


def build_planted(seed: int, kT: float, rc: float):
    """A planted vesicle under Cooke-Deserno chemistry: one tail-tail attraction, heads purely steric."""
    X, species, bonds, mols, wi, chains = _mixture.build(
        N_LIP, 0, 0, L_BOX, DIM, tails=(2, 2), plant="sphere", branched=False, seed=seed)
    sig = np.array([SIGMA_HEAD, 1.0, 1.0])
    f = Field(species, bonds, L_BOX, chi=cooke_chi(), sigma_species=sig, rc=rc, k_bond=K_BOND)
    ig = make_step_engine(f, X, kT, DT, 1 + seed, engine="transformer")
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    return X, f, ig, mm


def core_fraction(P: np.ndarray) -> float:
    """Share of lipid beads inside HALF the aggregate's outer radius. Grid-free hollowness.

    `frac_largest` cannot tell a vesicle from a collapsed globule -- both put every lipid in one
    aggregate, and a render caught exactly that after the metric called a filled blob "intact".
    A uniform ball gives (1/2)^3 = 0.125; a shell gives ~0. No occupancy grid, so this cannot repeat
    the 2-D-detector failure.
    """
    r = np.linalg.norm(P - P.mean(axis=0), axis=1)
    return float((r < 0.5 * r.max()).mean())


HOLLOW_MAX = 0.06          # half the uniform-ball value of 0.125


def _com_removed_msd(a: np.ndarray, b: np.ndarray, L: float) -> float:
    """Mean squared displacement of lipid beads between two frames, with rigid drift removed.

    Minimum-image applied per bead, because the box is periodic and a wrap would otherwise register
    as an enormous jump -- the failure that made an earlier velocity metric meaningless here.
    """
    d = b - a
    d -= L * np.round(d / L)
    d = d - d.mean(axis=0)              # remove the aggregate's own translation
    return float((d ** 2).sum(axis=1).mean())


def run_cell(rc: float, kT: float, seed: int, steps: int) -> dict:
    t0 = time.perf_counter()
    X, f, ig, mols = build_planted(seed, kT, rc)
    lip = np.concatenate(mols)
    warm = steps // 2                    # equilibrate, then measure over the second half
    for _ in range(warm):
        X = ig.step(X)
    ref = X[lip].copy()
    for _ in range(steps - warm):
        X = ig.step(X)
    msd = _com_removed_msd(ref, X[lip], L_BOX) / max(1, (steps - warm)) * 1000.0
    frac = _mixture.largest_cluster(X, mols, L_BOX) / len(mols)
    cf = core_fraction(X[lip])
    hollow = cf <= HOLLOW_MAX
    phase = ("breakup" if frac < BREAKUP_FRAC else ("gel" if msd < GEL_MSD else "fluid"))
    return {"rc": rc, "w_c": round(rc - 1.0, 2), "kT": kT, "seed": seed, "steps": steps,
            "frac_largest": round(frac, 3), "msd_per_1k": round(msd, 4),
            "core_frac": round(cf, 4), "hollow": int(hollow), "phase": phase,
            "wall_s": round(time.perf_counter() - t0, 1)}


def _append(row: dict) -> None:
    with _WRITE_LOCK:
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        new = not RESULTS.exists()
        with open(RESULTS, "a") as fh:
            if new:
                fh.write("\t".join(COLUMNS) + "\n")
            fh.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def probe(steps: int = 4000) -> int:
    """Validate the INSTRUMENT before trusting it, on cases whose answer is known in advance.

    A metric that has never been shown to discriminate is not a metric. This project has sixteen
    recorded instrument defects, the most recent found by exactly this kind of check.
    """
    print("  instrument probe: MSD must be ~0 when frozen and must rise with temperature\n")
    print(f"  {'kT':>6} {'frac_largest':>13} {'msd/1k steps':>14}   expected")
    exp = {0.05: "frozen -> tiny MSD", 0.45: "our current setting", 1.0: "CD fluid -> larger MSD",
           3.0: "far too hot -> breakup"}
    out = {}
    for kT in (0.05, 0.45, 1.0, 3.0):
        r = run_cell(2.5, kT, 1, steps)
        out[kT] = r
        print(f"  {kT:>6} {r['frac_largest']:>13} {r['msd_per_1k']:>14}   {exp[kT]}")
    ok = out[0.05]["msd_per_1k"] < out[1.0]["msd_per_1k"]
    print(f"\n  MSD increases with temperature (0.05 -> 1.0): {ok}")
    print(f"  cold case near zero (< {GEL_MSD}): {out[0.05]['msd_per_1k'] < GEL_MSD}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    if a.probe:
        return probe()
    if not a.sweep:
        ap.error("pass --probe or --sweep")

    rcs = (1.6, 2.0, 2.4, 2.8)                    # w_c = 0.6, 1.0, 1.4, 1.8 -- CD's Fig. 1 x-axis
    kTs = (0.3, 0.45, 0.6, 0.8, 1.0, 1.3)         # brackets our 0.45 and CD's ~1.0
    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines()[1:]:
            f = line.split("\t")
            done.add((float(f[0]), float(f[2]), int(f[3])))
    todo = [(rc, kT, sd) for rc, kT, sd in itertools.product(rcs, kTs, range(1, a.seeds + 1))
            if (rc, kT, sd) not in done]
    print(f"phase sweep: {len(todo)} cells, {a.workers} workers, {a.steps} steps", flush=True)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_cell, rc, kT, sd, a.steps): (rc, kT, sd) for rc, kT, sd in todo}
        for fut in as_completed(futs):
            rc, kT, sd = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:
                print(f"  rc={rc} kT={kT} sd={sd}: FAILED {exc!r}", flush=True)
                continue
            _append(row)
            print(f"  w_c={row['w_c']} kT={row['kT']} sd={sd}: frac={row['frac_largest']} "
                  f"msd={row['msd_per_1k']} -> {row['phase']} ({row['wall_s']}s)", flush=True)
    print(f"  wall total {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
