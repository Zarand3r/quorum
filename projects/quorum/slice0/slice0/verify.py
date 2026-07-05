"""Slice 0 merge gate.

PLAN.md §15.1 success criterion:

    Mean nearest-neighbor distance (MNND) under the LLM population is
    monotonically lower than under a uniform-random baseline by a
    statistically significant margin (Mann-Whitney U, p < 0.01 over ≥ 10
    seeds).

This harness:

1. Runs ``n_seeds`` copies of the LLM policy and ``n_seeds`` copies of the
   uniform-random baseline. Each rollout is ``ticks`` ticks; the summary
   statistic per rollout is the MEAN MNND over the last third of ticks
   (steady state, per PLAN.md §15.1 §"success").
2. Runs a Mann-Whitney U one-sided test (LLM < baseline) via scipy.
3. Confirms replay determinism on a frozen seed (byte-equal cells_history
   across two runs of the LLM policy at the same seed).
4. Prints a merge verdict.

Not a pytest test — invoked as ``bazel run //projects/quorum/slice0:verify``
because a real run needs a GPU + ~30 GB of RAM.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import stats

from slice0 import runner
from slice0.policy import Policy, UniformRandomPolicy
from slice0.runner import RunConfig, RunResult


LOGGER = logging.getLogger("slice0.verify")


@dataclass(slots=True, frozen=True)
class RolloutSummary:
    seed: int
    backend: str
    initial_mnnd: float
    steady_state_mnnd: float
    wall_seconds: float


def _steady_state_mnnd(result: RunResult) -> float:
    """Mean MNND over the last third of ticks."""
    ms = result.metrics
    if not ms:
        return float("nan")
    start = 2 * len(ms) // 3
    tail = ms[start:]
    return float(np.mean([m.mean_nn_distance for m in tail]))


def _make_backend(name: str, seed: int, model_name: str) -> Policy:
    if name == "uniform_random":
        return UniformRandomPolicy(seed=seed)
    if name == "llm":
        # Import lazy so verify can be inspected without torch installed.
        from slice0._llm_policy import LLMPolicy
        return LLMPolicy(model_name=model_name)
    raise ValueError(f"unknown backend {name!r}")


def _run_one(
    backend_name: str,
    seed: int,
    cfg: RunConfig,
    model_name: str,
) -> RolloutSummary:
    policy = _make_backend(backend_name, seed=seed, model_name=model_name)
    t0 = time.monotonic()
    result = runner.run(RunConfig(cfg.grid_size, cfg.n_agents, cfg.n_ticks, seed=seed), policy)
    wall = time.monotonic() - t0
    return RolloutSummary(
        seed=seed,
        backend=backend_name,
        initial_mnnd=result.metrics[0].mean_nn_distance,
        steady_state_mnnd=_steady_state_mnnd(result),
        wall_seconds=wall,
    )


def _replay_check(
    backend_name: str,
    seed: int,
    cfg: RunConfig,
    model_name: str,
) -> bool:
    """Two runs at the same seed produce byte-identical trajectories."""
    r1 = runner.run(
        RunConfig(cfg.grid_size, cfg.n_agents, cfg.n_ticks, seed=seed),
        _make_backend(backend_name, seed=seed, model_name=model_name),
    )
    r2 = runner.run(
        RunConfig(cfg.grid_size, cfg.n_agents, cfg.n_ticks, seed=seed),
        _make_backend(backend_name, seed=seed, model_name=model_name),
    )
    if len(r1.cells_history) != len(r2.cells_history):
        return False
    for c1, c2 in zip(r1.cells_history, r2.cells_history):
        if not np.array_equal(c1, c2):
            return False
    return r1.metrics == r2.metrics


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--grid-size", type=int, default=32)
    p.add_argument("--n-agents", type=int, default=64)
    p.add_argument("--ticks", type=int, default=100)
    p.add_argument("--n-seeds", type=int, default=10, help="≥10 per PLAN.md §15.1")
    p.add_argument("--seed-base", type=int, default=42)
    p.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    p.add_argument(
        "--treatment", default="llm",
        help="Backend to test against baseline. Default llm; can be a second "
             "baseline for smoke checks.",
    )
    p.add_argument(
        "--baseline", default="uniform_random",
        help="Baseline backend the treatment must beat.",
    )
    p.add_argument(
        "--p-threshold", type=float, default=0.01,
        help="Mann-Whitney U p threshold for merge-gate pass.",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    cfg = RunConfig(
        grid_size=args.grid_size,
        n_agents=args.n_agents,
        n_ticks=args.ticks,
        seed=args.seed_base,
    )

    print(f"grid={cfg.grid_size}x{cfg.grid_size}  agents={cfg.n_agents}  "
          f"ticks={cfg.n_ticks}  seeds={args.n_seeds}")
    print(f"baseline: {args.baseline}   treatment: {args.treatment}")
    if args.treatment == "llm":
        print(f"model: {args.model}")
    print()

    # 1. Replay determinism
    print("=== I8 replay determinism ===")
    replay_seed = args.seed_base
    print(f"replaying {args.treatment} at seed={replay_seed} ...")
    identical = _replay_check(args.treatment, replay_seed, cfg, args.model)
    print(f"identical trajectories: {'YES' if identical else 'NO'}")
    print()

    if not identical:
        print("MERGE VERDICT: FAIL — replay is not deterministic")
        return 2

    # 2. Baseline + treatment rollouts
    print(f"=== rollouts (n={args.n_seeds} per backend) ===")
    baseline_summaries: list[RolloutSummary] = []
    for i in range(args.n_seeds):
        s = _run_one(args.baseline, args.seed_base + i, cfg, args.model)
        baseline_summaries.append(s)
        print(f"[baseline  seed={s.seed:4d}] "
              f"init_mnnd={s.initial_mnnd:5.2f}  "
              f"ss_mnnd={s.steady_state_mnnd:5.2f}  "
              f"wall={s.wall_seconds:5.1f}s")

    treatment_summaries: list[RolloutSummary] = []
    for i in range(args.n_seeds):
        s = _run_one(args.treatment, args.seed_base + i, cfg, args.model)
        treatment_summaries.append(s)
        print(f"[treatment seed={s.seed:4d}] "
              f"init_mnnd={s.initial_mnnd:5.2f}  "
              f"ss_mnnd={s.steady_state_mnnd:5.2f}  "
              f"wall={s.wall_seconds:5.1f}s")

    baseline_ss = np.array([s.steady_state_mnnd for s in baseline_summaries])
    treatment_ss = np.array([s.steady_state_mnnd for s in treatment_summaries])

    # 3. Mann-Whitney U — one-sided: treatment < baseline
    u, p = stats.mannwhitneyu(treatment_ss, baseline_ss, alternative="less")
    print()
    print("=== merge gate ===")
    print(f"baseline steady-state MNND:  mean={baseline_ss.mean():.3f}  "
          f"median={np.median(baseline_ss):.3f}")
    print(f"treatment steady-state MNND: mean={treatment_ss.mean():.3f}  "
          f"median={np.median(treatment_ss):.3f}")
    print(f"Mann-Whitney U (one-sided treatment<baseline): U={u:.1f}  p={p:.5g}")
    print(f"threshold: p < {args.p_threshold}")

    passed = float(p) < args.p_threshold and float(treatment_ss.mean()) < float(baseline_ss.mean())
    print()
    if passed:
        print("MERGE VERDICT: PASS")
        return 0
    print("MERGE VERDICT: FAIL — treatment does not beat baseline at requested significance")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
