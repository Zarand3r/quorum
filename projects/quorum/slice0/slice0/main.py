"""Slice 0 CLI runner.

Two backends:

- ``--policy uniform_random`` (default) — the baseline. No torch, fast.
- ``--policy llm`` — real LLM via ``LLMPolicy`` (transformers + GPU).
  Requires the [llm] extra in the lock; fails cleanly with an actionable
  message otherwise.

Examples:

    # baseline (default), 100 ticks
    bazel run //projects/quorum/slice0:main -- --policy uniform_random --ticks 100

    # LLM (Qwen 2.5 1.5B by default), 100 ticks
    bazel run //projects/quorum/slice0:main -- --policy llm --ticks 100 --seed 42
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from slice0 import runner
from slice0.policy import Policy, UniformRandomPolicy
from slice0.runner import RunConfig


LOGGER = logging.getLogger("slice0.main")


def _make_policy(name: str, *, seed: int, model_name: str) -> Policy:
    if name == "uniform_random":
        return UniformRandomPolicy(seed=seed)
    if name == "llm":
        try:
            from slice0._llm_policy import LLMPolicy
        except ImportError as e:
            raise SystemExit(
                f"error: --policy llm requires the [llm] extra "
                f"(torch + transformers). Import failed: {e}\n"
                f"Regenerate the lock with `uv export --extra dev --extra llm` "
                f"and rerun.",
            ) from e
        return LLMPolicy(model_name=model_name)
    raise SystemExit(f"error: unknown --policy {name!r}; expected uniform_random|llm")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--grid-size", type=int, default=32)
    p.add_argument("--n-agents", type=int, default=64)
    p.add_argument("--ticks", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--policy", choices=("uniform_random", "llm"), default="uniform_random")
    p.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    p.add_argument("--log-level", default="info", choices=("critical", "error", "warning", "info", "debug"))
    p.add_argument(
        "--quiet-ticks", action="store_true",
        help="Suppress the per-tick line stream (still print the summary).",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    cfg = RunConfig(
        grid_size=args.grid_size,
        n_agents=args.n_agents,
        n_ticks=args.ticks,
        seed=args.seed,
    )
    policy = _make_policy(args.policy, seed=cfg.seed, model_name=args.model)
    backend = policy.__class__.__name__
    if args.policy == "llm":
        backend = f"LLMPolicy({args.model})"

    print(f"backend: {backend}")
    print(f"config:  grid={cfg.grid_size}x{cfg.grid_size} agents={cfg.n_agents} "
          f"ticks={cfg.n_ticks} seed={cfg.seed}")
    print()

    result = runner.run(cfg, policy)

    if not args.quiet_ticks:
        for m in result.metrics:
            print(
                f"t={m.t:4d}  mnnd={m.mean_nn_distance:5.2f}  "
                f"decorr={m.decorrelation:.3f}  "
                f"movers={m.movers:3d}/{cfg.n_agents}  fwd_passes={m.fwd_passes}"
            )
        print()

    # Summary
    initial_mnnd = result.metrics[0].mean_nn_distance if result.metrics else float("nan")
    final_mnnd = result.metrics[-1].mean_nn_distance if result.metrics else float("nan")
    mean_mnnd = sum(m.mean_nn_distance for m in result.metrics) / max(len(result.metrics), 1)
    print(f"summary: initial_mnnd={initial_mnnd:.3f}  "
          f"mean_mnnd={mean_mnnd:.3f}  final_mnnd={final_mnnd:.3f}")
    print(f"         forward_calls={policy.forward_call_count}  "
          f"generate_calls={policy.generate_call_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
