"""Read-only aliveness probe over a run (measurement only — never optimised).

    bazel run //projects/vivarium:probe -- --ticks 3000 --every 300

Prints the measured aliveness gauge at checkpoints so we can watch (not reward)
what the colony is doing — e.g. whether it collapses.
"""

from __future__ import annotations

import argparse

from aliveness import evaluate
from config import DEFAULTS, VivariumConfig
from engine import Engine


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="measured aliveness probe")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=3000)
    p.add_argument("--every", type=int, default=300)
    p.add_argument("--window", type=int, default=40)
    # config overrides (M2 exploration knobs)
    p.add_argument("--drift", type=float, default=None)
    p.add_argument("--lam", type=float, default=None)
    p.add_argument("--lr", type=float, default=None)
    p.add_argument("--k", type=int, default=None)
    p.add_argument("--N", type=int, default=None)
    p.add_argument("--ac", type=float, default=None, help="anti-collapse strength β")
    p.add_argument("--skew", type=float, default=None, help="intrinsic rotational drive gain")
    p.add_argument("--ablate", choices=["none", "identity", "shuffle"], default="none")
    a = p.parse_args(argv)

    over = {}
    if a.drift is not None:
        over["drift_rate"] = a.drift
    if a.lam is not None:
        over["dist_lambda"] = a.lam
    if a.lr is not None:
        over["lr"] = a.lr
    if a.k is not None:
        over["n_neighbors"] = a.k
    if a.N is not None:
        over["N"] = a.N
    if a.ac is not None:
        over["anticollapse"] = a.ac
    if a.skew is not None:
        over["skew_gain"] = a.skew
    cfg = VivariumConfig(**{**DEFAULTS, **over})
    e = Engine(cfg, a.seed, ablate=a.ablate)
    print(" tick  alive  spread  motion  cohere  struct    lyap     loss")
    for _ in range(0, a.ticks + 1, a.every):
        r = evaluate(e, a.window)
        print(
            f"{e.t:5d}  {r['aliveness']:.3f}  {r['spread']:.3f}  {r['motion']:.4f}"
            f"   {r['coherence']:.3f}   {r['structure']:.3f}  {r['lyapunov']:+.3f}  {e.last_loss:.5f}"
        )
        for _ in range(a.every):
            e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
