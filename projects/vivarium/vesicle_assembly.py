"""Self-assembly at a size where a vesicle can exist. Harness for
specs/2026-08-30_vesicle_feasible_geometry.md.

Runs our engine and the Cooke-Deserno oracle over the same (N, L) grid, scored by the same validated
instrument, so a disagreement localises to the engine rather than to the measurement.

    python vesicle_assembly.py --run
    python vesicle_assembly.py --score
"""

from __future__ import annotations

import argparse
import itertools
import os
import pathlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

import _mixture
from bilayer_metrics import classify
from field import Field, cooke_chi
from _mixture import make_step_engine

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "vesicle_assembly.tsv"
STATES = _HERE / "docs" / "states_protected"

N_LIP = 1000
BOXES = (30.0, 36.0)          # both above the 26.0 spanning threshold for N = 1000
W_C, KT = 1.4, 1.0            # inside the fluid band of our own reproduced phase map
RC, K_BOND, SIGMA_HEAD, DT = 1.0 + W_C, 30.0, 0.95, 8e-3
CHECK_EVERY = 25_000

# Endpoint fixed before any data. Controls: vesicle 0.000/0.83, sheet 0.573/0.21, blob 0.987/0.89.
HOLLOW_MAX, ANISO_MIN, THICK_MIN = 0.25, 0.5, 3.0
COLUMNS = ("engine", "L", "seed", "steps", "thickness", "hollow", "aniso",
           "debounced", "formed", "wall_s")
_LOCK = threading.Lock()


def is_vesicle(m: dict) -> bool:
    return (m["hollow"] < HOLLOW_MAX and m["aniso_l1_l3"] > ANISO_MIN
            and m["thickness"] > THICK_MIN)


def run_ours(L: float, seed: int, steps: int) -> dict:
    t0 = time.perf_counter()
    X, species, bonds, mols, wi, chains = _mixture.build(
        N_LIP, 0, 0, L, 3, tails=(2, 2), plant="random", branched=False, seed=seed)
    f = Field(species, bonds, L, chi=cooke_chi(),
              sigma_species=np.array([SIGMA_HEAD, 1.0, 1.0]), rc=RC, k_bond=K_BOND)
    ig = make_step_engine(f, X, KT, DT, 1 + seed, engine="transformer")
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    return _loop("ours", L, seed, steps, t0, lambda: ig.step(X), mm, lambda: X, X, ig)


def _loop(tag, L, seed, steps, t0, _unused, mols, _g, X, ig):
    run = best = 0
    last = {}
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % CHECK_EVERY == 0:
            last = classify(X, mols)
            run = run + 1 if is_vesicle(last) else 0
            best = max(best, run)
    if best >= 2:
        STATES.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(STATES / f"assembly_{tag}_L{L:g}_sd{seed}_s{steps}.npz",
                            X=X, mols=mols, L=L, steps=steps)
    return {"engine": tag, "L": L, "seed": seed, "steps": steps,
            "thickness": last.get("thickness", 0), "hollow": last.get("hollow", 1),
            "aniso": last.get("aniso_l1_l3", 0), "debounced": best,
            "formed": int(best >= 2), "wall_s": round(time.perf_counter() - t0, 1)}


def run_oracle(L: float, seed: int, steps: int) -> dict:
    from cooke_deserno import CookeDeserno
    t0 = time.perf_counter()
    cd = CookeDeserno(N_LIP, L, w_c=1.6, kT=1.1, dt=0.01, seed=seed)
    run = best = 0
    last = {}
    for i in range(steps):
        cd.step()
        if (i + 1) % CHECK_EVERY == 0:
            last = classify(cd.X, cd.mol)
            run = run + 1 if is_vesicle(last) else 0
            best = max(best, run)
    if best >= 2:
        STATES.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(STATES / f"assembly_oracle_L{L:g}_sd{seed}_s{steps}.npz",
                            X=cd.X, mols=cd.mol, L=L, steps=steps)
    return {"engine": "oracle", "L": L, "seed": seed, "steps": steps,
            "thickness": last.get("thickness", 0), "hollow": last.get("hollow", 1),
            "aniso": last.get("aniso_l1_l3", 0), "debounced": best,
            "formed": int(best >= 2), "wall_s": round(time.perf_counter() - t0, 1)}


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


def score() -> int:
    if not RESULTS.exists():
        print("  no results yet")
        return 0
    rows = [l.split("\t") for l in RESULTS.read_text().splitlines()[1:]]
    by = {}
    for r in rows:
        by.setdefault((r[0], float(r[1])), []).append(int(r[8]))
    print(f"  {'engine':>8} {'L':>6} {'formed':>10}")
    for k in sorted(by):
        v = by[k]
        print(f"  {k[0]:>8} {k[1]:>6} {sum(v):>4}/{len(v)}")
    ours = max((sum(v) / len(v) for (e, _), v in by.items() if e == "ours"), default=0)
    orac = max((sum(v) / len(v) for (e, _), v in by.items() if e == "oracle"), default=0)
    print(f"\n  PASS (ours >= 2/3 in any box): {ours >= 0.66}")
    print(f"  AC-2 (oracle also fails -> recipe untested, not our engine): {orac < 0.66}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--steps", type=int, default=400_000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    if a.score or not a.run:
        return score()
    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines()[1:]:
            f = line.split("\t")
            done.add((f[0], float(f[1]), int(f[2])))
    todo = [(e, L, sd) for e, L, sd in itertools.product(("ours", "oracle"), BOXES,
                                                         range(1, a.seeds + 1))
            if (e, L, sd) not in done]
    print(f"assembly: {len(todo)} runs, N={N_LIP}, {a.steps} steps, {a.workers} workers", flush=True)
    fn = {"ours": run_ours, "oracle": run_oracle}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(fn[e], L, sd, a.steps): (e, L, sd) for e, L, sd in todo}
        for fut in as_completed(futs):
            e, L, sd = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:
                print(f"  {e} L={L} sd={sd}: FAILED {exc!r}", flush=True)
                continue
            _append(row)
            print(f"  {row['engine']:>6} L={row['L']:g} sd={sd}: thick={row['thickness']} "
                  f"hollow={row['hollow']} aniso={row['aniso']} formed={row['formed']} "
                  f"({row['wall_s']}s)", flush=True)
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
