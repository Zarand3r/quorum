"""Is the ordered state of Finding 20 reproducible, or is it small-number noise?

A single ordered frame in a fluctuating 8-molecule cluster is a fluctuation until it replicates. This
runs several seeds over many timepoints and reports the FRACTION of frames that score micellar on all
three independent metrics at once, which is the statistic a one-frame reading cannot supply.

    bazel run //projects/vivarium:rung1d -- --seed 1
"""

import argparse

from bilayer3d import build
from micelle_probe import probe


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--lipids", type=int, default=24)
    p.add_argument("--tails", type=int, default=4)
    p.add_argument("--headq", type=float, default=1.2)
    p.add_argument("--bound", type=float, default=4.0)
    p.add_argument("--steps", type=int, default=120000)
    p.add_argument("--every", type=int, default=10000)
    a = p.parse_args(argv)

    e = build(seed=a.seed, n_lip=a.lipids, bound=a.bound, kt=0.02, speed=0.08, repel=12.0,
              k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=a.tails, head_q=a.headq)
    print(f"  N={e.cfg.N} lipids={len(e._mol)} tails={a.tails} head_q={a.headq} "
          f"box={2*a.bound:.1f} margin={e.min_image_margin():.4f}", flush=True)
    hits = frames = 0
    for t in range(0, a.steps + 1, a.every):
        rs = probe(e)
        if rs:
            n, o, sh, cy, a1, a2, shape, o_raw, o_c = rs[0]
            ok = o > 0.50 and sh > 0.70
            # thresholds against the measured null (null_control.py): outward_c p95 = +0.235
            verdict = "MICELLE" if ok else ("partial" if o > 0.296 else "no radial order")
            hits += ok; frames += 1
            print(f"  seed{a.seed} t={t:6d} n={n:3d} cyl_c={o:+.3f} shell={sh:.2f} "
                  f"{shape:6s} {verdict}", flush=True)
        else:
            print(f"  seed{a.seed} t={t:6d} no cluster", flush=True)
        if t < a.steps:
            for _ in range(a.every):
                e.step()
    print(f"  seed{a.seed} SUMMARY {hits}/{frames} frames micellar on all three metrics", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
