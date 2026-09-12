"""G4: does a planted FLAT ribbon curl? The experiment the MLP was built for.

WHY THIS PROTOCOL

`docs/RESULTS.md` records five independent attempts to curve a flat bilayer, every one a measured null
with the membrane intact: chi_TW (lambda = +2.8 +- 2.8, null WITH power), chi_HH (0/5 at two values),
lipid shape, imposed leaflet THICKNESS asymmetry (0/5), imposed leaflet AREA asymmetry (0/5). So the
null is unusually well characterised -- which is exactly what makes this a good gate.

The structural reason it is a null: chi terms are symmetric PAIR interactions and spontaneous curvature
is a DIFFERENCE between the two leaflets. `manybody.ManyBodyMLP` is the first term in this model that
is not a pair interaction -- a per-token exposure computed from an aggregate over the neighbourhood --
so it is the first candidate that is not excluded a priori.

THE METRIC, AND WHY NOT END-TO-END DISTANCE

The obvious measure is end-to-end distance over contour length. It is not usable: two attempts to
locate a ribbon's ends both failed the same positive control -- a closed ring, which has no termini at
all, read 134 tips under a tip-counting metric and 16 under a contact-degree metric. Local degree
cannot find the end of a BILAYER, where the two leaflets join in a rounded cap.

`aspect` avoids the problem entirely: the ratio of the two covariance eigenvalues of the lipid
CENTROIDS. A flat ribbon is long and thin (small ratio); as it curls the cloud fills out; a closed ring
is isotropic (ratio near 1). No ends need to be found. Validated below against three planted
geometries it must SEPARATE.
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
from _lumen_field import largest_lipid_cluster, n_enclosed
from field import Field, HEAD, N_SPECIES
from gap_closure import chi_from, PRODUCTION
from manybody import ManyBodyMLP, ShapeMLP, assert_calibrated

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "curl.tsv"
STATES = _HERE / "docs" / "states_curl"

N_LIP, L_BOX, KT, PHI, DT = 56, 100.0, 0.45, 0.55, 8e-3
STEPS, CHECK_EVERY = 300_000, 10_000
COLUMNS = ("arm", "scale", "n_ref", "seed", "steps", "aspect0", "aspect_max", "aspect_final",
           "curled", "intact", "largest_final", "n_enc_max", "wall_s")
# `n_ref` joined the schema on 2026-09-11 (Amendment 4). The 24 pre-existing rows were migrated in
# place to n_ref = 6.0 (mlp) / -1 (off, no modulator existed), row count asserted before and after --
# a silent schema change with a column-count filter on read has eaten rows from this project twice.
NA_N_REF = -1.0
# Registered in specs/2026-09-07_mlp_many_body.md, Amendment 3, before any data existed.
CURL_THRESHOLD = 0.45
# A curl only counts if the ribbon is still ONE aggregate. 0.9 of N_LIP allows a couple of lipids to
# evaporate, which the off arm already does; it does not allow the sheet to fall apart.
INTACT_FRACTION = 0.9


def centroids(X, mols, L):
    ref = X[mols[:, 0]][:, None, :]
    d = X[mols] - ref
    d -= L * np.round(d / L)
    return ref[:, 0, :] + d.mean(axis=1)


def aspect(X, mols, L):
    """lambda_min / lambda_max of the lipid-centroid covariance, unwrapped. Flat ~0, ring ~1."""
    C = centroids(X, mols, L)
    # unwrap against the first lipid so a ribbon straddling the boundary is not measured as a blob
    C = C - C[0]
    C -= L * np.round(C / L)
    C = C - C.mean(axis=0)
    ev = np.linalg.eigvalsh(C.T @ C / len(C))
    return float(ev[0] / max(ev[-1], 1e-12))


def validate() -> int:
    """The metric must SEPARATE flat, arc and ring. Scoring the ring well is not enough."""
    nw = int(round(PHI * L_BOX ** 2 / np.pi * 4)) - N_LIP * 5
    print(f"  {'planted geometry':>22} {'aspect':>9}")
    got = {}
    for tag, plant in (("flat ribbon", "flat"), ("arc 0.75", "arc0.75"), ("closed ring", "arc1.0")):
        X, sp, b, mols, wi, ch = _mixture.build(0, N_LIP, nw, L_BOX, 2, plant=plant,
                                                branched=True, seed=1)
        mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
        got[tag] = aspect(np.ascontiguousarray(X, dtype=np.float64), mm, L_BOX)
        print(f"  {tag:>22} {got[tag]:>9.4f}")
    ok = got["flat ribbon"] < got["arc 0.75"] < got["closed ring"]
    print(f"\n  flat < arc < ring (SEPARATES):        {ok}")
    print(f"  curl threshold {CURL_THRESHOLD} sits between flat and ring: "
          f"{got['flat ribbon'] < CURL_THRESHOLD < got['closed ring']}")
    return 0 if ok else 1


def run_one(scale: float, seed: int, steps: int = STEPS, n_ref: float = NA_N_REF) -> dict:
    t0 = time.perf_counter()
    nw = int(round(PHI * L_BOX ** 2 / np.pi * 4)) - N_LIP * 5
    X, species, bonds, mols, wi, chains = _mixture.build(
        0, N_LIP, nw, L_BOX, 2, plant="flat", branched=True, seed=seed)
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    X = np.ascontiguousarray(X, dtype=np.float64)
    # `scale` selects the SHAPE channel now: sigma_head modulated by head-only coordination. The
    # affinity channel (ManyBodyMLP) returned 0/12 on G4 and its feedback sign was diagnosed as
    # stabilising flatness; shape is what sets the packing parameter and therefore curvature.
    sh = (ShapeMLP(np.full(N_SPECIES, 1.0), n_ref=n_ref, amp=scale) if scale > 0 else None)
    f = Field(species, bonds, L_BOX, chi=chi_from(PRODUCTION), shape=sh)
    if sh is not None:
        # Fail before burning 2.4 CPU-hours on a term that is a constant. n_ref = 6.0 against a
        # descriptor of range ~0.2 is what made the first shape-channel G4 uninformative.
        assert_calibrated(sh, f.coordination(X), f"ShapeMLP amp={scale} n_ref={n_ref}")
    ig = _mixture.make_step_engine(f, X, KT, DT, 1 + seed, engine="transformer")

    a0 = aspect(X, mm, L_BOX)
    amax = a0
    nemax = 0
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % CHECK_EVERY == 0:
            a = aspect(X, mm, L_BOX)
            amax = max(amax, a)
            nemax = max(nemax, int(n_enclosed(X, mm, L_BOX)[0]))
            if (i + 1) % 100_000 == 0:
                print(f"    [scale={scale} sd={seed}] {i+1}/{steps} aspect={a:.3f} "
                      f"max={amax:.3f} ({time.perf_counter()-t0:.0f}s)", flush=True)
    afin = aspect(X, mm, L_BOX)
    curled = int(amax >= CURL_THRESHOLD)
    # The criterion this ladder can FAIL BY WINNING. A large enough head modulation will simply take
    # the ribbon apart, and a cloud of fragments is isotropic -- it scores a high `aspect` for the
    # opposite of the reason we care about. A run only counts as a curl if the membrane is still one
    # aggregate. INTACT_FRACTION is the planted ribbon's own connectivity, not a chosen bar.
    lf = largest_lipid_cluster(X, mm, L_BOX)
    intact = int(lf >= INTACT_FRACTION * N_LIP)
    if curled:
        STATES.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(STATES / f"CURL_s{scale}_sd{seed}.npz", X=X, mols=mm,
                            species=species, L=L_BOX, gap=-1.0, closed=curled,
                            steps=steps, seed=seed)
    return {"arm": "mlp" if scale > 0 else "off", "scale": scale,
            "n_ref": round(n_ref, 6) if scale > 0 else NA_N_REF, "seed": seed, "steps": steps,
            "aspect0": round(a0, 4), "aspect_max": round(amax, 4), "aspect_final": round(afin, 4),
            "curled": curled, "intact": intact, "largest_final": lf, "n_enc_max": nemax,
            "wall_s": round(time.perf_counter() - t0, 1)}


def score():
    if not RESULTS.exists():
        print("  no results yet")
        return 0
    rows = [dict(zip(COLUMNS, l.split("\t")))
            for l in RESULTS.read_text().splitlines()[1:] if len(l.split("\t")) == len(COLUMNS)]
    from gap_closure import _fisher_1s
    by = {}
    for r in rows:
        by.setdefault((float(r["scale"]), float(r["n_ref"])), []).append(r)
    print(f"  {'amp':>7} {'n_ref':>8} {'n':>4} {'curled':>9} {'mean aspect_max':>17} "
          f"{'intact':>8}")
    for k in sorted(by):
        v = by[k]
        c = sum(int(r["curled"]) for r in v)
        am = sum(float(r["aspect_max"]) for r in v) / len(v)
        it = sum(int(r["intact"]) for r in v)
        print(f"  {k[0]:>7} {k[1]:>8.4f} {len(v):>4} {c:>4}/{len(v):<4} {am:>17.4f} "
              f"{it:>4}/{len(v):<3}")
    off = [r for k, v in by.items() if k[0] == 0.0 for r in v]
    for k in sorted(k for k in by if k[0] > 0):
        on = by[k]
        if not off or len(on) < 12 or len(off) < 12:
            continue
        # curled AND intact: a fragmented cloud is isotropic for the wrong reason.
        a = sum(int(r["curled"]) and int(r["intact"]) for r in on)
        b = sum(int(r["curled"]) and int(r["intact"]) for r in off)
        p = _fisher_1s(a, len(on), b, len(off))
        print(f"\n  amp {k[0]} (n_ref {k[1]:.4f}): on {a}/{len(on)} vs off {b}/{len(off)}, "
              f"Fisher p = {p:.4f}")
        print(f"    G4 gate (on>=6/12 AND off<=1/12 AND p<=0.05): "
              f"{a >= 6 and b <= 1 and p <= 0.05}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--scales", default="0.0,1.0", help="ShapeMLP amp per arm; 0.0 is the off arm")
    ap.add_argument("--n-ref", type=float, default=None,
                    help="REQUIRED for any arm with amp>0. Derive it; see ShapeMLP.n_ref_from.")
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--seed0", type=int, default=700)
    ap.add_argument("--steps", type=int, default=STEPS)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args(argv)
    if a.validate:
        return validate()
    if a.score:
        return score()
    scales = [float(x) for x in a.scales.split(",")]
    if any(s > 0 for s in scales) and a.n_ref is None:
        raise SystemExit("--n-ref is required for any arm with amp>0: it is a DERIVED constant "
                         "(ShapeMLP.n_ref_from), and leaving it defaulted is the defect of "
                         "Amendment 4.")
    nref = {s: (a.n_ref if s > 0 else NA_N_REF) for s in scales}
    done = set()
    if RESULTS.exists():
        for l in RESULTS.read_text().splitlines()[1:]:
            fl = l.split("\t")
            if len(fl) == len(COLUMNS):
                done.add((float(fl[1]), float(fl[2]), int(fl[3])))
    todo = [(s, sd) for s, sd in itertools.product(scales, range(a.seed0, a.seed0 + a.seeds))
            if (s, nref[s], sd) not in done]
    print(f"G4 curl: {len(todo)} runs, N={N_LIP} L={L_BOX} {a.steps} steps, {a.workers} workers, "
          f"n_ref={a.n_ref}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, s, sd, a.steps, nref[s]): (s, sd) for s, sd in todo}
        for fut in as_completed(futs):
            try:
                r = fut.result()
            except Exception as exc:
                print(f"  {futs[fut]}: FAILED {exc!r}", flush=True)
                continue
            rows.append(r)
            RESULTS.parent.mkdir(parents=True, exist_ok=True)
            new = not RESULTS.exists()
            with open(RESULTS, "a") as fh:
                if new:
                    fh.write("\t".join(COLUMNS) + "\n")
                fh.write("\t".join(str(r[c]) for c in COLUMNS) + "\n")
                fh.flush()
                _os.fsync(fh.fileno())
            print(f"  scale={r['scale']} sd={r['seed']}: aspect {r['aspect0']}->{r['aspect_max']} "
                  f"curled={r['curled']} ({r['wall_s']}s)", flush=True)
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
