"""The per-tick pipeline (PLAN.md §10.1) composed from the env/ layers.

Order: inject sources → diffuse/decay → forager perceive+decide → conservative
transactions (uptake + cost-first action charge) → relocate the forager if the
move was afforded → lifecycle (death/decomposition) → advance tick → optional
invariant check. Synchrony (I7) is trivial in Slice 0 — a single forager means
no cross-agent read-after-write hazard; explicit double-buffering lands with the
NCA rule (M2), when many cells act on the same neighborhood simultaneously.
"""

from __future__ import annotations

from env import invariants
from env.config import WorldConfig
from env.diffusion import diffuse_and_decay, inject_sources
from env.fields import World
from env.lifecycle import apply_lifecycle
from env.transactions import (
    TransactionLedger,
    TransactionReport,
    apply_conservative_transactions,
)
from sim.forager import forager_intents


def tick(
    world: World, cfg: WorldConfig, ledger: TransactionLedger, check: bool = False
) -> TransactionReport:
    """Advance ``world`` by one tick in place; accumulate sources/sinks in ``ledger``."""
    # 1. Sources + field physics.
    ledger.source_injected += inject_sources(world, world.tick)
    ledger.book_decay(diffuse_and_decay(world, cfg))

    # 2. Forager perceives current fields and decides.
    uptake, cost, move = forager_intents(world, cfg)

    # 3. Conservative transactions (uptake + cost-first action charge).
    report = apply_conservative_transactions(world, uptake, cost, cfg)
    ledger.book(report)

    # 4. Relocate the forager iff its move cost was actually paid (refused == 0).
    if move is not None and report.refused == 0:
        (fy, fx), (ty, tx) = move
        world.alive[ty, tx] = world.alive[fy, fx]
        world.alive[fy, fx] = 0.0
        world.energy[ty, tx] += world.energy[fy, fx]  # energy relocates (conserved)
        world.energy[fy, fx] = 0.0

    # 5. Death + decomposition.
    ledger.decomp_loss += apply_lifecycle(world, cfg)

    # 6. Advance and (optionally) assert invariants.
    world.tick += 1
    if check:
        invariants.assert_non_negative(world)
    return report
