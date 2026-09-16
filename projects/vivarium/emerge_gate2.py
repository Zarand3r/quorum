"""Per-checkpoint emergence rate under BOTH gates, on the same runs. The number the old one cannot give.

Every rate in `docs/results/` is `vesicle_call`'s. The new gate (`vesicle_gate`) has only ever been
scored on FINAL states -- 9 of 237, a lower bound, because vesicles here are transient. This scores
both gates at every checkpoint of the same trajectory, so the comparison is exact and the new rate is
measured rather than extrapolated.

Own results file, own columns: a schema change to an append-only TSV has silently eaten rows in this
project twice.
"""
from __future__ import annotations

import os as _os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

import _mixture
import emerge_reduced as E
from _lumen_field import largest_lipid_cluster, n_enclosed, vesicle_call
from field import Field, HEAD, N_SPECIES
from gap_closure import chi_from
from vesicle_gate import vesicle

RESULTS = pathlib.Path(__file__).resolve().parent / "docs" / "results" / "emerge_gate2.tsv"
COLUMNS = ("arm", "n_lip", "seed", "steps", "check_every",
           "enc_ckpts", "old_ckpts", "new_ckpts", "first_new", "best_score",
           "largest_max", "wall_s")


def run_one(arm: str, seed: int, steps: int, check_every: int, n_lip: int) -> dict:
    t0 = time.perf_counter()
    label, spec, sig_head, phi, kT, rc = E.ARMS[arm]
    d, L = 2, E.L_BOX
    n_water = 0 if phi <= 0 else int(round(phi * L ** d / _mixture.C_D[d] * (2 ** d))) - n_lip * 5
    X, species, bonds, mols, wi, chains = _mixture.build(
        0, n_lip, n_water, L, d, plant="random", branched=True, seed=seed)
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    sig = np.full(N_SPECIES, 1.0)
    sig[HEAD] = sig_head
    f = Field(species, bonds, L, chi=chi_from(spec), sigma_species=sig, rc=rc)
    ig = _mixture.make_step_engine(f, X, kT, E.DT, 1 + seed, engine="transformer")

    enc = old = new = 0
    first = -1
    best = 0.0
    lmax = 0
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % check_every == 0:
            if n_enclosed(X, mm, L)[0] > 0:
                enc += 1
            if vesicle_call(X, mm, L)[0]:
                old += 1
            ok, score, _d = vesicle(X, species, mm, L)
            best = max(best, score)
            if ok:
                new += 1
                if first < 0:
                    first = i + 1
            lmax = max(lmax, largest_lipid_cluster(X, mm, L))
    return {"arm": arm, "n_lip": n_lip, "seed": seed, "steps": steps, "check_every": check_every,
            "enc_ckpts": enc, "old_ckpts": old, "new_ckpts": new, "first_new": first,
            "best_score": round(best, 3), "largest_max": lmax,
            "wall_s": round(time.perf_counter() - t0, 1)}


def score():
    if not RESULTS.exists():
        print("  no results yet")
        return 0
    rows = [dict(zip(COLUMNS, l.split("\t")))
            for l in RESULTS.read_text().splitlines()[1:] if len(l.split("\t")) == len(COLUMNS)]
    n = len(rows)
    if not n:
        return 0
    e = sum(1 for r in rows if int(r["enc_ckpts"]) > 0)
    o = sum(1 for r in rows if int(r["old_ckpts"]) > 0)
    w = sum(1 for r in rows if int(r["new_ckpts"]) > 0)
    print(f"\n  PER-CHECKPOINT emergence rate over {n} runs, same trajectories:")
    print(f"    enclosure (loose)      {e:>3}/{n}  {100*e/n:5.1f}%")
    print(f"    vesicle_call (old)     {o:>3}/{n}  {100*o/n:5.1f}%")
    print(f"    vesicle_gate (NEW)     {w:>3}/{n}  {100*w/n:5.1f}%")
    sc = sorted(float(r["best_score"]) for r in rows)
    print(f"    best-score distribution: max {sc[-1]:.2f}  >=0.8: "
          f"{sum(1 for s in sc if s >= 0.8)}  >=0.4: {sum(1 for s in sc if s >= 0.4)}  "
          f">0: {sum(1 for s in sc if s > 0)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="0")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=300)
    ap.add_argument("--n-lip", type=int, default=160)
    ap.add_argument("--steps", type=int, default=1_000_000)
    ap.add_argument("--check-every", type=int, default=10_000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args(argv)
    if a.score:
        return score()
    done = set()
    if RESULTS.exists():
        for l in RESULTS.read_text().splitlines()[1:]:
            fl = l.split("\t")
            if len(fl) == len(COLUMNS):
                done.add(int(fl[2]))
    todo = [s for s in range(a.seed0, a.seed0 + a.seeds) if s not in done]
    print(f"emerge_gate2: {len(todo)} runs, N={a.n_lip} {a.steps} steps, {a.workers} workers",
          flush=True)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, a.arm, s, a.steps, a.check_every, a.n_lip): s for s in todo}
        for fut in as_completed(futs):
            try:
                r = fut.result()
            except Exception as exc:
                print(f"  seed {futs[fut]}: FAILED {exc!r}", flush=True)
                continue
            RESULTS.parent.mkdir(parents=True, exist_ok=True)
            new = not RESULTS.exists()
            with open(RESULTS, "a") as fh:
                if new:
                    fh.write("\t".join(COLUMNS) + "\n")
                fh.write("\t".join(str(r[c]) for c in COLUMNS) + "\n")
                fh.flush()
                _os.fsync(fh.fileno())
            print(f"  sd={r['seed']}: enc={r['enc_ckpts']} old={r['old_ckpts']} "
                  f"new={r['new_ckpts']} best={r['best_score']} ({r['wall_s']}s)", flush=True)
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
