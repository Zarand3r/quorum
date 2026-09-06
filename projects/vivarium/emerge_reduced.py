"""H7: does a 2-D vesicle EMERGE under the reduced chemistry? See specs/2026-09-03_H7_*.md

The knob ladder ran entirely on PLANTED ARCS, so it establishes the chemistry needed to close and hold
a vesicle, not that one forms by itself. This asks the emergence question directly, and it is only
affordable because the reduction removed the solvent: 0.55 ms/step against 2.2.
"""
from __future__ import annotations

import os as _os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import os
import pathlib
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

import _mixture
from _lumen_field import n_enclosed, vesicle_call
from field import Field, HEAD, N_SPECIES
from gap_closure import ARMS, chi_from

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "emerge_reduced.tsv"
STATES = _HERE / "docs" / "states_emerge"
N_LIP, L_BOX, KT, DT = 160, 65.0, 0.45, 8e-3
STEPS, CHECK_EVERY = 1_000_000, 50_000
COLUMNS = ("arm", "n_lip", "seed", "steps", "check_every", "vesicle_ckpts", "first_vesicle", "enc_ckpts",
           "largest_max", "largest_final", "wall_s")
_LOCK = threading.Lock()


def run_one(arm: str, seed: int, steps: int = STEPS, check_every: int = CHECK_EVERY,
            n_lip: int = N_LIP) -> dict:
    t0 = time.perf_counter()
    label, spec, sig_head, phi, kT, rc = ARMS[arm]
    d = 2
    lip = n_lip * 5
    n_water = 0 if phi <= 0 else int(round(phi * L_BOX ** d / _mixture.C_D[d] * (2 ** d))) - lip
    X, species, bonds, mols, wi, chains = _mixture.build(
        0, n_lip, n_water, L_BOX, d, plant="random", branched=True, seed=seed)
    sig = np.full(N_SPECIES, 1.0)
    sig[HEAD] = sig_head
    f = Field(species, bonds, L_BOX, chi=chi_from(spec), sigma_species=sig, rc=rc)
    ig = _mixture.make_step_engine(f, X, kT, DT, 1 + seed, engine="transformer")
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    X = np.ascontiguousarray(X, dtype=np.float64)

    ves = enc = 0
    first = -1
    lmax = lfin = 0
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % check_every == 0:
            ne = n_enclosed(X, mm, L_BOX)[0]
            ok, _ = vesicle_call(X, mm, L_BOX)
            if ne >= 1:
                enc += 1
            if ok:
                ves += 1
                if first < 0:
                    first = i + 1
            # `_mixture.largest_cluster` is the SAME helper H5 used for its `largest` column, so
            # this number is directly comparable to the historical production baseline. An earlier
            # draft used count_vesicles()[1], which counts VESICLES not cluster size and read 0 on a
            # perfectly healthy aggregating run.
            lfin = int(_mixture.largest_cluster(X, mm, L_BOX))
            lmax = max(lmax, lfin)
            print(f"    [{arm} sd={seed}] {i+1}/{steps} largest={lfin} enc={ne} ves={ok} "
                  f"({time.perf_counter()-t0:.0f}s)", flush=True)
    STATES.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(STATES / f"{arm}_N{n_lip}_sd{seed}.npz", X=X, mols=mm, species=species,
                        L=L_BOX, gap=-1.0, closed=int(ves > 0))
    return {"arm": arm, "n_lip": n_lip, "seed": seed, "steps": steps,
            "check_every": check_every,
            "vesicle_ckpts": ves,
            "first_vesicle": first, "enc_ckpts": enc, "largest_max": lmax,
            "largest_final": lfin, "wall_s": round(time.perf_counter() - t0, 1)}


def _append(row):
    with _LOCK:
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        new = not RESULTS.exists()
        with open(RESULTS, "a") as fh:
            if new:
                fh.write("\t".join(COLUMNS) + "\n")
            fh.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def score():
    if not RESULTS.exists():
        print("  no results yet")
        return 0
    rows = [dict(zip(COLUMNS, l.split("\t")))
            for l in RESULTS.read_text().splitlines()[1:] if len(l.split("\t")) == len(COLUMNS)]
    from gap_closure import _fisher_1s
    # GROUP BY CADENCE TOO. A vesicle that forms and reopens inside one checkpoint interval
    # is invisible, so runs sampled 5x apart measure different things and must not pool.
    for arm, nl, ce in sorted({(r["arm"], r["n_lip"], r["check_every"]) for r in rows}):
        v = [r for r in rows if r["arm"] == arm and r["n_lip"] == nl
             and r["check_every"] == ce]
        ves = sum(1 for r in v if int(r["vesicle_ckpts"]) > 0)
        enc = sum(1 for r in v if int(r["enc_ckpts"]) > 0)
        lm = sum(int(r["largest_max"]) for r in v) / len(v)
        print(f"  {arm:>4} N={nl:>4} ckpt/{ce}: vesicle {ves}/{len(v)}  any-enclosure {enc}/{len(v)}  "
              f"mean largest_max {lm:.1f}")
        if len(v) >= 20:
            p = _fisher_1s(ves, len(v), 2, 42)
            print(f"        vs historical production baseline 2/42: p = {p:.6f}")
            print(f"        GATE (>= 6/20 AND p <= 0.01): {ves >= 6 and p <= 0.01}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="6B")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=200)
    ap.add_argument("--steps", type=int, default=STEPS)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--check-every", type=int, default=CHECK_EVERY,
                    help="H8: 10000 instead of 50000. A vesicle that forms and reopens "
                         "inside one interval is invisible, and the gap assay measured "
                         "exactly that -- closed at 10k, open again by 60k.")
    ap.add_argument("--n-lip", default=str(N_LIP),
                    help="comma-separated lipid counts. Spanning a box of side L needs about\n"
                         "L lipids for a branched 4-tail lipid (lateral footprint 2 sigma),\n"
                         "so N below ~L cannot form a rimless spanning ribbon and must close\n"
                         "to shed its edges.")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args(argv)
    if a.score:
        return score()
    done = set()
    if RESULTS.exists():
        for l in RESULTS.read_text().splitlines()[1:]:
            f = l.split("\t")
            if len(f) == len(COLUMNS):
                done.add((f[0], int(f[1]), int(f[2])))
    arms = [x.strip() for x in a.arm.split(",") if x.strip()]
    nlips = [int(x) for x in str(a.n_lip).split(",") if x.strip()]
    todo = [(ar, nl, sd) for ar in arms for nl in nlips
            for sd in range(a.seed0, a.seed0 + a.seeds) if (ar, nl, sd) not in done]
    print(f"H7 emergence: {len(todo)} runs, N={N_LIP} L={L_BOX} {a.steps} steps, "
          f"{a.workers} workers", flush=True)
    # PROCESSES, not threads. Solvent-free is 800 beads against 2959 with explicit water, and at
    # that array size numpy's GIL releases no longer cover the per-step work: 16 threads delivered
    # ~2x effective parallelism (8.6 ms/step against 1.02 solo, flat across the whole run, at load 11
    # on 32 cores). The result append happens here in the parent, so no cross-process lock is needed.
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, ar, sd, a.steps, a.check_every, nl): (ar, nl, sd)
                for ar, nl, sd in todo}
        for fut in as_completed(futs):
            ar, nl, sd = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:
                print(f"  {ar} N={nl} sd={sd}: FAILED {exc!r}", flush=True)
                continue
            _append(row)
            print(f"  {ar} N={nl} sd={sd}: vesicle_ckpts={row['vesicle_ckpts']} "
                  f"enc={row['enc_ckpts']} largest_max={row['largest_max']} "
                  f"({row['wall_s']}s)", flush=True)
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
