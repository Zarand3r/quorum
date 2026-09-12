"""A picture of the G5 ladder while it runs. The gate saves a state only if something CURLS.

That is how the previous G4 ended with "0/12, no state crossed the threshold, so there was nothing to
render" -- twenty-four runs and not one image. A verdict with no picture is exactly the shape of every
defect in `docs/MEASUREMENT_DISCIPLINE.md`, so this walks the SAME deterministic trajectory (same
seed, same build, same engine) for one seed per amp.

EACH CHECKPOINT IS WRITTEN TO DISK THE MOMENT IT HAPPENS, and `--assemble` builds the filmstrip from
whatever exists. The first version returned frames from the worker and could only draw the strip once
a whole 150k-step run had finished -- two hours before the first picture, which is no use for looking
at something while it runs. Frames are saved as STATES, not images, so the strip can be re-rendered
differently later without re-running the dynamics.

Not a second implementation of the experiment: it imports `curl`'s own constants and metric, and the
sweep's verdict never comes from here. This only lets someone LOOK.
"""
from __future__ import annotations

import os as _os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import _mixture
from _lumen_field import largest_lipid_cluster
from _shot import disc, write_png
from curl import CHECK_EVERY, DT, INTACT_FRACTION, KT, L_BOX, N_LIP, PHI, aspect
from field import Field, HEAD, N_SPECIES, WATER
from gap_closure import PRODUCTION, chi_from
from manybody import ShapeMLP, assert_calibrated

_HERE = pathlib.Path(__file__).resolve().parent
PANEL, PAD = 220, 6
RGB_WATER, RGB_TAIL, RGB_HEAD, BG = (26, 32, 48), (255, 152, 64), (77, 181, 255), (10, 12, 18)


def panel(X, species, L):
    img = np.full((PANEL, PANEL, 3), BG, np.uint8)
    sc = PANEL / L
    P = np.mod(X, L) * sc
    for sp, rgb, rad, alpha in ((WATER, RGB_WATER, 1.0, 0.55),
                                (None, RGB_TAIL, 1.7, 0.95),
                                (HEAD, RGB_HEAD, 2.1, 1.0)):
        m = (species == sp) if sp is not None else ((species != WATER) & (species != HEAD))
        for x, y in P[m]:
            disc(img, x, y, rad, rgb, alpha)
    return img


def assemble(amps, steps_at, out):
    """Build the filmstrip from whatever frames exist on disk. Safe to call at any time, mid-run."""
    frames = {}
    for a in amps:
        for st in steps_at:
            fp = frame_path(a, st)
            if fp.exists():
                z = np.load(fp)
                frames[(a, st)] = panel(z["X"], z["species"], float(z["L"]))
    grid(frames, amps, steps_at, out)
    return frames


def grid(frames, amps, steps_at, out):
    """frames[(amp, step)] -> panel."""
    rows, cols = len(amps), len(steps_at)
    W = PAD + cols * (PANEL + PAD)
    H = PAD + rows * (PANEL + PAD)
    img = np.full((H, W, 3), 0, np.uint8)
    for r, a in enumerate(amps):
        for c, st in enumerate(steps_at):
            p = frames.get((a, st))
            if p is None:
                continue
            y, x = PAD + r * (PANEL + PAD), PAD + c * (PANEL + PAD)
            img[y:y + PANEL, x:x + PANEL] = p
    write_png(out, img)


FRAMES = _HERE / "docs" / "figures" / "_witness"


def frame_path(amp, step):
    return FRAMES / f"w_a{amp}_s{step}.npz"


def run_one(amp, seed, steps, every, n_ref):
    nw = int(round(PHI * L_BOX ** 2 / np.pi * 4)) - N_LIP * 5
    X, species, bonds, mols, _, _ = _mixture.build(0, N_LIP, nw, L_BOX, 2, plant="flat",
                                                   branched=True, seed=seed)
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    X = np.ascontiguousarray(X, dtype=np.float64)
    sh = ShapeMLP(np.full(N_SPECIES, 1.0), n_ref=n_ref, amp=amp) if amp > 0 else None
    f = Field(species, bonds, L_BOX, chi=chi_from(PRODUCTION), shape=sh)
    if sh is not None:
        assert_calibrated(sh, f.coordination(X), f"witness amp={amp}")
    ig = _mixture.make_step_engine(f, X, KT, DT, 1 + seed, engine="transformer")
    FRAMES.mkdir(parents=True, exist_ok=True)
    out = []
    t0 = time.perf_counter()
    for i in range(steps):
        X = ig.step(X)
        if (i + 1) % every == 0:
            lf = largest_lipid_cluster(X, mm, L_BOX)
            row = (i + 1, round(aspect(X, mm, L_BOX), 4), lf, int(lf >= INTACT_FRACTION * N_LIP),
                   round(time.perf_counter() - t0))
            # written NOW, not returned at the end -- the whole point of this file
            np.savez_compressed(frame_path(amp, i + 1), X=X, species=species, L=L_BOX,
                                amp=amp, step=i + 1, aspect=row[1], largest=lf, intact=row[3])
            out.append(row)
            print(f"  amp={amp:<5} step={i+1:<7} aspect={row[1]:<8} largest={lf:<4} "
                  f"intact={row[3]}  ({row[4]}s)", flush=True)
    return amp, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--amps", default="0.0,1.0,4.0")
    ap.add_argument("--assemble", action="store_true",
                    help="build the filmstrip from frames already on disk and exit")
    ap.add_argument("--n-ref", type=float, required=True)
    ap.add_argument("--seed", type=int, default=800)
    ap.add_argument("--steps", type=int, default=150_000)
    ap.add_argument("--every", type=int, default=CHECK_EVERY)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default=str(_HERE / "docs" / "figures" / "g5_witness.png"))
    a = ap.parse_args(argv)
    amps = [float(x) for x in a.amps.split(",")]
    steps_at = list(range(a.every, a.steps + 1, a.every))
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    if a.assemble:
        fr = assemble(amps, steps_at, a.out)
        print(f"  {len(fr)} frames on disk -> {a.out}")
        for (amp, st) in sorted(fr):
            z = np.load(frame_path(amp, st))
            print(f"  amp={amp:<5} step={st:<7} aspect={float(z['aspect']):<8} "
                  f"largest={int(z['largest']):<4} intact={int(z['intact'])}")
        return 0
    log = []
    print(f"witness: amps={amps} seed={a.seed} {a.steps} steps, frame every {a.every}", flush=True)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_one, amp, a.seed, a.steps, a.every, a.n_ref) for amp in amps]
        for fut in futs:
            amp, rows = fut.result()
            log.extend((amp, st, asp, lf, intact) for st, asp, lf, intact, _ in rows)
            assemble(amps, steps_at, a.out)
            print(f"  -> {a.out}", flush=True)
    print(f"\n  {'amp':>6} {'step':>8} {'aspect':>9} {'largest':>8} {'intact':>7}")
    for amp, st, asp, lf, intact in log:
        print(f"  {amp:>6} {st:>8} {asp:>9} {lf:>8} {intact:>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
