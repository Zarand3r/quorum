"""Profile one simulation step: wall-clock cost and where it goes.

Iteration speed is a first-class constraint on this project. A 60k-step run is the standard
experiment unit, so a millisecond on the step is an hour a week, and full-submersion runs need
roughly 4x the solvent tokens against an O(N^2) force -- about 16x the work. Guessing at the
bottleneck has been wrong twice here (the core attention was assumed to dominate; it was 15%), so
this measures instead.

Usage:
    bazel run //projects/vivarium:bench_step                     # default 2-D lipid dish
    bazel run //projects/vivarium:bench_step -- --lipids 150 --water 800
    bazel run //projects/vivarium:bench_step -- --profile        # per-function breakdown
    bazel run //projects/vivarium:bench_step -- --scaling        # cost vs token count

`--fingerprint` prints a deterministic summary of the state after a fixed number of steps. Two builds
that agree on it are bit-identical, which is how the trig-sharing optimisation was shown to be a pure
speedup and the Chebyshev recurrence was shown NOT to be (it differs at ~7x machine epsilon, which is
rounding, not physics).
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import time

import numpy as np

from bicelle2d import build

BASE = dict(bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
            attract=1.0, bond_span=2.0, n_tail=2, polarity=0.80, head_q=1.2,
            hydrophobic=0.6, plant=False)

WARMUP = 20


def make(lipids: int, water: int):
    return build(7, n_lip=lipids, n_water=water, **BASE)


def step_ms(engine, steps: int) -> float:
    """Median-free mean wall-clock per step, after a warmup that pays one-off allocation costs."""
    for _ in range(WARMUP):
        engine.step()
    t0 = time.perf_counter()
    for _ in range(steps):
        engine.step()
    return (time.perf_counter() - t0) * 1000.0 / steps


def calibration_ms() -> float:
    """Cost of a fixed reference workload, used to normalise for machine speed.

    A raw millisecond threshold is not portable and turns any loaded machine into a false failure.
    The same (N,N) transcendental-plus-matmul mix the step is dominated by makes a fair yardstick:
    the RATIO of step cost to this is a property of the code, not of the host.
    """
    a = np.linspace(0.0, 1.0, 439 * 439).reshape(439, 439)
    t0 = time.perf_counter()
    for _ in range(5):
        np.cos(a) @ np.sin(a)
    return (time.perf_counter() - t0) * 1000.0 / 5


def profile(engine, steps: int) -> list[tuple[float, str]]:
    for _ in range(WARMUP):
        engine.step()
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(steps):
        engine.step()
    pr.disable()
    st = pstats.Stats(pr, stream=io.StringIO()).sort_stats("tottime")
    rows = [(v[2] * 1000.0 / steps, f"{k[0].split('/')[-1]}:{k[1]} {k[2]}")
            for k, v in st.stats.items()]
    rows.sort(reverse=True)
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lipids", type=int, default=63)
    p.add_argument("--water", type=int, default=250)
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--profile", action="store_true", help="per-function breakdown")
    p.add_argument("--scaling", action="store_true", help="cost vs token count")
    p.add_argument("--fingerprint", action="store_true", help="determinism check")
    a = p.parse_args()

    if a.scaling:
        print(f"{'n_water':>8}{'N':>7}{'ms/step':>10}{'ms/step/N^2':>14}")
        for w in (100, 250, 500, 1000):
            e = make(a.lipids, w)
            n = e.X.shape[0]
            ms = step_ms(e, max(20, a.steps // 4))
            print(f"{w:>8}{n:>7}{ms:>10.2f}{ms / n ** 2 * 1e6:>14.4f}")
        return 0

    e = make(a.lipids, a.water)
    n = e.X.shape[0]
    ms = step_ms(e, a.steps)
    cal = calibration_ms()
    print(f"N = {n} tokens ({a.lipids} lipids, {a.water} water)")
    print(f"  step            {ms:8.2f} ms")
    print(f"  calibration     {cal:8.2f} ms   (machine-speed reference)")
    print(f"  ratio           {ms / cal:8.2f}      <- the portable number; regression-tested")
    print(f"  60k-step run    {ms * 60000 / 1000 / 60:8.1f} min")

    if a.fingerprint:
        f = make(a.lipids, a.water)
        for _ in range(200):
            f.step()
        print(f"  fingerprint     {float(np.abs(f.X).sum()):.12f}")

    if a.profile:
        print(f"\n{'ms/step':>9}  share  where")
        rows = profile(e, max(40, a.steps // 2))
        for t, name in rows[:10]:
            print(f"{t:>9.3f}{t / ms * 100:>7.1f}%  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
