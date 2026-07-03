"""Headless Slice-0 runner + CLI (PLAN.md §12 train/rollout is the M2 loop; this
is the operational Slice-0 loop). Runs the tick pipeline, tracking the metrics
that matter for the Slice-0 gate: conservation residual, forager viability, and
(optionally) the per-tick state-hash sequence for replay determinism (P5).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from env.config import WorldConfig, load_world_config
from env.fields import from_config
from env.invariants import conserved_total
from env.transactions import TransactionLedger
from sim.tick import tick

_DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


@dataclass
class RunResult:
    ticks: int
    ledger: TransactionLedger
    residual_max: float
    alive_history: list[int] = field(default_factory=list)   # live cells per tick
    energy_history: list[float] = field(default_factory=list)  # total energy per tick
    hashes: list[str] = field(default_factory=list)          # per-tick state hash (opt)

    def alive_at(self, t: int) -> int:
        return self.alive_history[t]


def run(
    cfg: WorldConfig,
    seed: int,
    ticks: int,
    check: bool = False,
    record_hashes: bool = False,
) -> RunResult:
    world = from_config(cfg, seed)
    ledger = TransactionLedger()
    t0 = conserved_total(world)
    res = RunResult(ticks=ticks, ledger=ledger, residual_max=0.0)
    alive_thr = cfg.lifecycle.alive_threshold
    for _ in range(ticks):
        tick(world, cfg, ledger, check=check)
        residual = abs(conserved_total(world) - ledger.expected_total(t0))
        res.residual_max = max(res.residual_max, residual)
        res.alive_history.append(int((world.alive >= alive_thr).sum()))
        res.energy_history.append(float(world.energy.sum()))
        if record_hashes:
            res.hashes.append(world.state_hash())
    return res


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="thermolife Slice-0 headless runner")
    p.add_argument("--config", default=str(_DEFAULT_CONFIG))
    p.add_argument("--scenario", default="static_gradient")
    p.add_argument("--ticks", type=int, default=6000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--check", action="store_true", help="assert invariants each tick")
    p.add_argument("--every", type=int, default=500, help="log interval")
    args = p.parse_args(argv)

    cfg = load_world_config(args.config, scenario=args.scenario)
    world = from_config(cfg, args.seed)
    ledger = TransactionLedger()
    t0 = conserved_total(world)
    for _ in range(args.ticks):
        tick(world, cfg, ledger, check=args.check)
        if world.tick % args.every == 0 or world.tick == args.ticks:
            residual = abs(conserved_total(world) - ledger.expected_total(t0))
            alive = int((world.alive >= cfg.lifecycle.alive_threshold).sum())
            print(
                f"tick={world.tick:6d}  alive={alive}  "
                f"energy={world.energy.sum():8.4f}  residual={residual:.2e}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
