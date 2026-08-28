"""Sweep head bead size against vesicle formation. Harness for specs/2026-08-28_head_area_geometry.md.

Runs one arm-seed per subprocess, parses the runner's own checkpoint table, and appends ONE row per
run to an append-only TSV with fsync. Restarting after an interruption costs one run, not the sweep.

The gate lives in `gate()` and is scored mechanically from the TSV. It is not allowed to consult
anything else, and its thresholds come from the pre-registration, not from the data.

    python sweep_head_area.py --mode screen     # 3 seeds x 5 arms x 100k steps
    python sweep_head_area.py --mode decision   # 10 seeds x 5 arms x 1M steps
    python sweep_head_area.py --score           # re-score the TSV, print the gate verdict
"""

from __future__ import annotations

import argparse
import itertools
import os
import pathlib
import subprocess
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
RESULTS = _HERE / "docs" / "results" / "head_area_sweep.tsv"

# Fixed by the pre-registration. Do not edit to fit an outcome; append an amendment instead.
ARMS = (1.0, 1.2, 1.4, 1.6, 1.8)
BASELINE = 1.0
N_LIP, L_BOX, KT, PHI, DIM = 200, 25.0, 0.45, 0.0, 3
CHI_HT, CHI_WW = -0.25, 0.50
MODES = {"screen": (3, 100_000), "decision": (10, 1_000_000)}

PASS_BEST, PASS_BASELINE, PASS_P = 0.6, 0.2, 0.05
COLUMNS = ("mode", "sigma_head", "seed", "steps", "largest_max", "nves_max",
           "debounced", "formed", "wall_s")


def _parse(stdout: str):
    """Pull the observables out of the runner's checkpoint table.

    `formed` requires nves >= 1 at two or more CONSECUTIVE checkpoints. Single-checkpoint flicker was
    measured in this project at a 0.057 rate and has produced retracted claims twice.
    """
    largest_max, nves_max, run, best_run = 0, 0, 0, 0
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 19 or not parts[0].isdigit():
            continue
        try:
            largest, nves = int(parts[2]), int(parts[18])
        except ValueError:
            continue
        largest_max = max(largest_max, largest)
        nves_max = max(nves_max, nves)
        run = run + 1 if nves >= 1 else 0
        best_run = max(best_run, run)
    return largest_max, nves_max, best_run, int(best_run >= 2)


def _append(row: dict) -> None:
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    new = not RESULTS.exists()
    with open(RESULTS, "a") as fh:
        if new:
            fh.write("\t".join(COLUMNS) + "\n")
        fh.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _done(mode: str) -> set:
    if not RESULTS.exists():
        return set()
    out = set()
    for line in RESULTS.read_text().splitlines()[1:]:
        f = line.split("\t")
        if len(f) >= 3 and f[0] == mode:
            out.add((float(f[1]), int(f[2])))
    return out


def run_one(mode: str, sigma_head: float, seed: int, steps: int, scratch: pathlib.Path) -> dict:
    env = dict(os.environ)
    env.update(VIVARIUM_ENGINE="transformer", VIVARIUM_CHI_HT=str(CHI_HT),
               VIVARIUM_CHI_WW=str(CHI_WW), VIVARIUM_SIGMA_HEAD=str(sigma_head),
               BUILD_WORKSPACE_DIRECTORY=str(scratch))
    cmd = [sys.executable, str(_HERE / "_mixture.py"), str(steps), str(DIM), str(N_LIP),
           "0.0", str(L_BOX), str(KT), str(PHI), "random", str(seed)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    wall = time.perf_counter() - t0
    largest, nves, best_run, formed = _parse(p.stdout)
    (scratch / "logs").mkdir(parents=True, exist_ok=True)
    (scratch / "logs" / f"{mode}_sh{sigma_head}_sd{seed}.log").write_text(p.stdout + p.stderr)
    return {"mode": mode, "sigma_head": sigma_head, "seed": seed, "steps": steps,
            "largest_max": largest, "nves_max": nves, "debounced": best_run,
            "formed": formed, "wall_s": round(wall, 1)}


def _fisher_one_sided(a, b, c, d) -> float:
    """P(observing this split or a more extreme one) under independence. Exact, no SciPy."""
    from math import comb
    n = a + b + c + d
    row1, col1 = a + b, a + c
    total = comb(n, col1)
    p = 0.0
    for k in range(a, min(row1, col1) + 1):
        p += comb(row1, k) * comb(n - row1, col1 - k)
    return p / total


def gate(mode: str) -> dict:
    """Score mechanically. Returns the verdict; the agent does not get a vote."""
    rows = []
    for line in RESULTS.read_text().splitlines()[1:]:
        f = line.split("\t")
        if f[0] == mode:
            rows.append((float(f[1]), int(f[7])))
    by_arm = {}
    for sh, formed in rows:
        by_arm.setdefault(sh, []).append(formed)
    frac = {sh: sum(v) / len(v) for sh, v in by_arm.items() if v}
    base = frac.get(BASELINE)
    treat = {sh: f for sh, f in frac.items() if sh != BASELINE}
    if base is None or not treat:
        return {"verdict": "INCOMPLETE", "fractions": frac}
    best_sh = max(treat, key=lambda k: treat[k])
    bf, bn = sum(by_arm[best_sh]), len(by_arm[best_sh])
    cf, cn = sum(by_arm[BASELINE]), len(by_arm[BASELINE])
    p = _fisher_one_sided(bf, bn - bf, cf, cn - cf)
    ac2 = base >= PASS_BEST
    ok = (treat[best_sh] >= PASS_BEST) and (base <= PASS_BASELINE) and (p <= PASS_P)
    verdict = "PASS" if ok else ("FAIL (AC-2: baseline also forms)" if ac2 else "FAIL")
    return {"verdict": verdict, "fractions": frac, "best_arm": best_sh,
            "best_formed": f"{bf}/{bn}", "baseline_formed": f"{cf}/{cn}",
            "fisher_p": round(p, 4), "ac2_triggered": ac2}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=sorted(MODES), default="screen")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--scratch", default="/tmp/head_area_sweep")
    a = ap.parse_args(argv)
    if a.score:
        for k, v in gate(a.mode).items():
            print(f"  {k}: {v}")
        return 0
    n_seed, steps = MODES[a.mode]
    scratch = pathlib.Path(a.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    done = _done(a.mode)
    todo = [(sh, sd) for sh, sd in itertools.product(ARMS, range(1, n_seed + 1))
            if (sh, sd) not in done]
    print(f"{a.mode}: {len(todo)} runs to do, {len(done)} already in {RESULTS}", flush=True)
    for sh, sd in todo:
        row = run_one(a.mode, sh, sd, steps, scratch)
        _append(row)
        print(f"  sigma_head={sh} seed={sd}: largest={row['largest_max']} "
              f"nves_max={row['nves_max']} debounced={row['debounced']} "
              f"formed={row['formed']} ({row['wall_s']}s)", flush=True)
    for k, v in gate(a.mode).items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
