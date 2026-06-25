"""CLI entry point.

Default policy is ``MockPolicy`` so the toy runs immediately after
``uv sync --extra dev`` without torch. Switch to the real LLM with
``--policy llm`` (requires ``--extra llm``).

Examples:

    uv run python -m toy_v1.main                          # mock, 40 ticks, seed 42
    uv run python -m toy_v1.main --ticks 100 --seed 7     # mock, longer run
    uv run python -m toy_v1.main --policy llm             # real LLM (needs [llm])
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

import numpy as np

from toy_v1 import runner
from toy_v1.grid import EMPTY, RED, BLUE
from toy_v1.policy import MockPolicy
from toy_v1.runner import RunConfig


_GLYPH = {EMPTY: ".", RED: "R", BLUE: "B"}


def ascii_grid(cells: np.ndarray) -> str:
    return "\n".join("".join(_GLYPH[int(v)] for v in row) for row in cells)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Toy v1: LLM Schelling on a grid.")
    p.add_argument("--grid-size", type=int, default=8)
    p.add_argument("--n-agents", type=int, default=30)
    p.add_argument("--ticks", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--policy", choices=("mock", "llm"), default="mock",
        help="mock = MockPolicy (no torch, default); llm = real HF causal LM",
    )
    p.add_argument(
        "--model", default="HuggingFaceTB/SmolLM2-135M-Instruct",
        help="HF model name when --policy=llm",
    )
    p.add_argument(
        "--p-stay", type=float, default=0.5,
        help="MockPolicy STAY probability (only used when --policy=mock)",
    )
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = RunConfig(
        grid_size=args.grid_size,
        n_agents=args.n_agents,
        n_ticks=args.ticks,
        seed=args.seed,
    )

    # Construct the policy.
    if args.policy == "mock":
        policy = MockPolicy(seed=args.seed, p_stay=args.p_stay)
        backend = f"MockPolicy(p_stay={args.p_stay})"
    else:
        # Defer the real import until we know the user actually wants it.
        try:
            from toy_v1.policy import make_llm_policy
            policy = make_llm_policy(args.model)
            backend = f"LLMPolicy({args.model})"
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    print(f"Backend: {backend}")
    print(f"Config: grid={cfg.grid_size}x{cfg.grid_size} agents={cfg.n_agents} "
          f"ticks={cfg.n_ticks} seed={cfg.seed}")
    print()

    result = runner.run(cfg, policy)

    # Initial state (snapshotted by runner before tick 0).
    print("Initial grid:")
    print(ascii_grid(result.initial_cells))
    print()

    # Per-tick lines. fwd_passes is the I3 runtime gate (must == 1).
    for m in result.metrics:
        print(
            f"t={m.t:3d}  same-color={m.same_color_fraction:.3f}  "
            f"movers={m.movers:2d}/{cfg.n_agents}  fwd_passes={m.fwd_passes}"
        )

    print()
    print("Final grid:")
    print(ascii_grid(result.final_cells))
    final_frac = result.metrics[-1].same_color_fraction if result.metrics else 0.0
    print(f"Final same-color fraction: {final_frac:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
