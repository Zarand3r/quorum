"""CLI for the E0 substrate: single rollout or a drift-speed sweep.

  bazel run //projects/thermolife:eco_run -- --ticks 10000
  bazel run //projects/thermolife:eco_run -- --sweep 0.02 0.04 0.06 0.09 0.12 0.16 0.22
  bazel run //projects/thermolife:eco_run -- --ticks 4000 --policy frozen

The sweep prints a survival-vs-drift curve — the evidence that calibrates v* for the
E0 gate (IMPLEMENTATION_PLAN.md §D D3): the drift speed at the static-starvation knee.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from eco.config import load_eco_config
from eco.engine import run
from eco.policies import frozen, hand_forager

_CFG = Path(__file__).resolve().parent.parent / "configs" / "eco.yaml"
_POLICIES = {"forager": hand_forager, "frozen": frozen}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=10000)
    ap.add_argument("--policy", choices=list(_POLICIES), default="forager")
    ap.add_argument("--drift-v", type=float, default=None, help="override cfg drift_v")
    ap.add_argument("--sweep", type=float, nargs="+", default=None,
                    help="drift_v values → survival-vs-drift curve (both policies)")
    args = ap.parse_args()

    base = load_eco_config(_CFG)

    if args.sweep:
        print(f"drift-sweep over {args.ticks} ticks  (orbit_r={base.orbit_radius})")
        print(f"{'drift_v':>8} {'forager_surv':>13} {'forager_n':>10} "
              f"{'frozen_surv':>12} {'max|resid|':>12}")
        for v in args.sweep:
            cfg = replace(base, drift_v=v)
            fr = run(cfg, args.ticks, policy=hand_forager)
            fz = run(cfg, args.ticks, policy=frozen)
            print(f"{v:>8.3f} {fr['survived']:>13} {fr['final_n']:>10} "
                  f"{fz['survived']:>12} {max(fr['max_abs_residual'], fz['max_abs_residual']):>12.2e}")
        return 0

    cfg = base if args.drift_v is None else replace(base, drift_v=args.drift_v)
    res = run(cfg, args.ticks, policy=_POLICIES[args.policy])
    print(f"policy={args.policy} drift_v={cfg.drift_v} ticks={args.ticks}")
    print(f"  survived={res['survived']}  final_n={res['final_n']}  "
          f"max|residual|={res['max_abs_residual']:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
