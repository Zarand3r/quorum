"""Does a planted 3-D vesicle HOLD? The first experiment of the 3-D pivot.

WHY THIS FIRST

The 3-D track is blocked on closure (`hollow` pinned at 0.49 across every intervention), but that
blocker was diagnosed largely BEFORE the bending defect was found, and the precondition was never
retested afterwards: `docs/REVIEWER_HANDOFF_2026-08-31.md` records "a planted vesicle collapses into a
solid ball" as a pre-fix observation. Testing whether the target state is even stable is cheaper than
testing whether it can be reached, and it splits the problem cleanly:

    holds     -> closure is kinetic; the question is nucleation, as in 2-D
    collapses -> the force field cannot support a 3-D vesicle at all, which is a more fundamental
                 result than anything the knob ladder produced

TWO THINGS THIS FIXES ABOUT HOW 3-D WAS RUN

1. `bend_r0` IS PASSED EXPLICITLY. `Field`'s default is **2.0** -- the broken quartic value -- read
   from `VIVARIUM_BEND_R0` in the process environment. `vesicle_assembly.py` never passes it, and the
   string `bend_r0` appears in no harness file in this project. So the bending fix was applied only
   through a process-global variable, the exact mechanism that once gave two A/B arms the same value
   and produced bit-identical results. Verified numerically: at r0 = 2 the harmonic coefficient
   V/delta^2 -> 0.0004 while V/delta^4 -> 0.9375 constant; at r0 = 4, V/delta^2 -> 15.0 constant.

2. The endpoint is `_lumen3d.n_enclosed_3d`, which is validated in 3-D. The old `n_enclosed` is a 2-D
   flood-fill: on these very controls it reads **0 for a hollow shell and 0 for two hollow shells**.
   Thirty-nine 3-D runs were scored against it.
"""
from __future__ import annotations

import os as _os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import itertools
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

import _mixture
from _lumen3d import n_enclosed_3d, vesicle_call_3d
from field import Field, cooke_chi, HEAD, N_SPECIES

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "vesicle3d.tsv"
STATES = _HERE / "docs" / "states_3d"

L_BOX, KT, DT = 30.0, 1.0, 8e-3
W_C, K_BOND, SIGMA_HEAD = 1.4, 30.0, 0.95      # as vesicle_assembly.py, inside the fluid band
AREA_PER_LIPID = 1.2                            # standard coarse-grained value
COLUMNS = ("bend_r0", "n_lip", "seed", "steps", "n_enc_first", "n_enc_final",
           "lumen_first", "lumen_final", "held", "vcall_final", "wall_s")


def plant_vesicle(n_lip, L, seed=0, n_tail=4):
    """Two leaflets on a sphere: heads out on the outside, heads in on the inside, tails meeting at the
    mid-surface. R_mid is solved from the lipid count so neither leaflet is over-packed -- planting a
    count that does not match the radius is a defect that has appeared four times in this project
    (`references.py`: "THE LIPID COUNT FOLLOWS THE BOX, never the reverse")."""
    rng = np.random.default_rng(seed)
    half = n_tail // 2
    reach = 0.866 + (half - 1)
    gap = 0.5
    # n = (4 pi R_out^2 + 4 pi R_in^2) / a, with R_out/in = R_mid +/- (gap + reach)
    off = gap + reach
    # solve 4 pi ((R+off)^2 + (R-off)^2) = n a  ->  8 pi (R^2 + off^2) = n a
    R_mid = float(np.sqrt(max(n_lip * AREA_PER_LIPID / (8 * np.pi) - off * off, 0.25)))
    R_out, R_in = R_mid + off, max(R_mid - off, 0.6)
    n_out = int(round(n_lip * R_out ** 2 / (R_out ** 2 + R_in ** 2)))
    n_in = n_lip - n_out

    def fibonacci(n):
        """Near-uniform points on a sphere. Random points clump, and a clumped leaflet plants beads at
        separation ~0, which no relaxation can repair because the push direction is 0/0."""
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = np.pi * (1 + 5 ** 0.5) * i
        return np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), np.cos(phi)], axis=1)

    X, species, bonds, mols = [], [], [], []
    k = 0
    for count, R_head, sgn in ((n_out, R_out, +1.0), (n_in, R_in, -1.0)):
        if count <= 0:
            continue
        u = fibonacci(count)
        # A local frame per lipid so the two tails sit side by side, as _plant_ring does in 2-D.
        # The reference axis is chosen PER LIPID as the one it is least aligned with: a fixed axis
        # degenerates wherever u is parallel to it (cross -> 0), which put beads 0.006 apart at the
        # poles -- separations no relaxation can repair, because the push direction is 0/0.
        tmp = np.zeros_like(u)
        tmp[np.arange(len(u)), np.argmin(np.abs(u), axis=1)] = 1.0
        t1 = np.cross(u, tmp)
        t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
        head = L / 2 + u * R_head
        idx = []
        X.append(head); species.append(np.full(count, HEAD)); idx.append(np.arange(k, k + count))
        k += count
        for branch in (-0.5, +0.5):
            for b in range(half):
                pos = head - sgn * u[:, :] * (0.866 + b) + t1 * branch
                X.append(pos); species.append(np.full(count, 1)); idx.append(np.arange(k, k + count))
                k += count
        cols = np.stack(idx, axis=1)
        mols.append(cols)
        for c in range(1, cols.shape[1]):
            parent = 0 if (c - 1) % half == 0 else c - 1
            bonds.append(np.stack([cols[:, parent], cols[:, c]], axis=1))
    X = np.concatenate(X); species = np.concatenate(species)
    mols = np.concatenate(mols, axis=0); bonds = np.concatenate(bonds, axis=0)
    return np.ascontiguousarray(X, dtype=np.float64), species, bonds, mols


def minimise(f, X, steps=4000, cap=0.02):
    """Capped steepest descent at zero temperature, before any dynamics.

    The rigid radial plant is over-packed BY CONSTRUCTION: a lipid's tails sit at smaller radius than
    its head, so the same angular density crowds into (R_tail/R_head)^2 of the area -- 62% at
    R_out = 8.9, which doubles bead density and leaves ~4400 pairs inside 0.8 sigma.

    With a BOUNDED core those overlaps do not push apart, they pass THROUGH: started from the raw
    plant the system reached E/lipid = -161 (about 32 attractive contacts per bead) and 2.8 million
    neighbour pairs -- interpenetrating piles, the failure this project has already retracted results
    over, not a membrane.

    Zero-temperature descent with a per-step displacement cap resolves the overlaps without a
    thermostat injecting energy while they are still there. `references.py`: "A REFERENCE MUST BE
    RELAXED BEFORE IT IS READ."
    """
    for _ in range(steps):
        F = f.forces(X)
        n = np.linalg.norm(F, axis=1, keepdims=True)
        X = X + np.where(n > 0, F / np.maximum(n, 1e-12), 0.0) * np.minimum(n * 1e-4, cap)
    return X


def run_one(bend_r0: float, n_lip: int, seed: int, steps: int, check_every: int = 25_000) -> dict:
    t0 = time.perf_counter()
    X, species, bonds, mols = plant_vesicle(n_lip, L_BOX, seed)
    sig = np.full(N_SPECIES, 1.0); sig[HEAD] = SIGMA_HEAD
    # bend_r0 EXPLICIT. Field's default is 2.0 from the environment; see the module docstring.
    f = Field(species, bonds, L_BOX, chi=cooke_chi(), sigma_species=sig,
              rc=1.0 + W_C, k_bond=K_BOND, bend_r0=bend_r0)
    X = minimise(f, X)
    ig = _mixture.make_step_engine(f, X, KT, DT, 1 + seed, engine="transformer")
    first = last = None
    lf = ll = 0
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % check_every == 0:
            c, sizes = n_enclosed_3d(X, mols, L_BOX)
            if first is None:
                first, lf = c, (sizes[0] if sizes else 0)
            last, ll = c, (sizes[0] if sizes else 0)
            print(f"    [r0={bend_r0} N={n_lip} sd={seed}] {i+1}/{steps} n_enc={c} "
                  f"lumen={ll} ({time.perf_counter()-t0:.0f}s)", flush=True)
    ok, _ = vesicle_call_3d(X, mols, L_BOX)
    STATES.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(STATES / f"r0{bend_r0}_N{n_lip}_sd{seed}.npz",
                        X=X, mols=mols, species=species, L=L_BOX)
    return {"bend_r0": bend_r0, "n_lip": n_lip, "seed": seed, "steps": steps,
            "n_enc_first": first, "n_enc_final": last, "lumen_first": lf, "lumen_final": ll,
            "held": int(last == 1), "vcall_final": int(ok),
            "wall_s": round(time.perf_counter() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-lip", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--steps", type=int, default=300_000)
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args(argv)
    todo = list(itertools.product((2.0, 4.0), range(1, a.seeds + 1)))
    print(f"planted 3-D vesicle: {len(todo)} runs, N={a.n_lip}, L={L_BOX}, {a.steps} steps", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, r0, a.n_lip, sd, a.steps): (r0, sd) for r0, sd in todo}
        for fut in as_completed(futs):
            try:
                r = fut.result(); rows.append(r)
                print(f"  r0={r['bend_r0']} sd={r['seed']}: n_enc {r['n_enc_first']}->{r['n_enc_final']} "
                      f"lumen {r['lumen_first']}->{r['lumen_final']} held={r['held']}", flush=True)
            except Exception as exc:
                print(f"  {futs[fut]}: FAILED {exc!r}", flush=True)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS, "w") as fh:
        fh.write("\t".join(COLUMNS) + "\n")
        for r in sorted(rows, key=lambda r: (r["bend_r0"], r["seed"])):
            fh.write("\t".join(str(r[c]) for c in COLUMNS) + "\n")
    for r0 in (2.0, 4.0):
        v = [r for r in rows if r["bend_r0"] == r0]
        if v:
            print(f"\n  bend_r0={r0} ({'BROKEN quartic' if r0 == 2.0 else 'FIXED harmonic'}): "
                  f"held {sum(r['held'] for r in v)}/{len(v)}   "
                  f"vesicle_call {sum(r['vcall_final'] for r in v)}/{len(v)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
