"""Death, decomposition, and dead-cell inertness (PLAN.md §11.1, I4/I15).

A cell dies when its energy falls to the lethal floor or the local heat/waste
rises to the lethal ceiling. On death it decomposes exactly once: a fraction of
its stored energy (its "biomass") returns to the nutrient field and the
remainder is booked as a loss sink, keeping the conserved total ``T`` honest
(P1). Dead cells are inert by construction — the ``alive`` mask gates all action
in :mod:`env.transactions`, so a cell with ``alive < threshold`` neither uptakes
nor emits (P4).
"""

from __future__ import annotations

from env.config import WorldConfig
from env.fields import Field, World


def apply_lifecycle(world: World, cfg: WorldConfig) -> float:
    """Kill + decompose newly-lethal cells in place. Returns decomposition loss.

    The returned loss is the conservation-ledger sink for this tick (booked into
    ``TransactionLedger.decomp_loss``). Only cells that were alive *and* crossed
    a lethal threshold this tick decompose, so decomposition fires exactly once.
    """
    lc = cfg.lifecycle
    alive_before = world.alive >= lc.alive_threshold
    heat = world.fields[:, :, Field.HEAT]
    waste = world.fields[:, :, Field.WASTE]
    nutrient = world.fields[:, :, Field.NUTRIENT]

    lethal = (
        (world.energy <= cfg.energy.e_lethal)
        | (heat >= cfg.barriers.tau_lethal)
        | (waste >= cfg.barriers.w_lethal)
    )
    died = alive_before & lethal
    if not died.any():
        return 0.0

    biomass = world.energy * died                       # energy of the newly dead
    returned = lc.decomp_return_fraction * biomass       # → nutrient (T transfer)
    loss = float(((1.0 - lc.decomp_return_fraction) * biomass).sum())  # → sink

    nutrient += returned
    world.energy[died] = 0.0
    world.alive[died] = 0.0
    return loss


def occupancy_ok(world: World, cfg: WorldConfig) -> bool:
    """I15: fraction of occupied cells stays within the population cap."""
    alive = (world.alive >= cfg.lifecycle.alive_threshold).sum()
    cap = cfg.lifecycle.population_cap_fraction * world.height * world.width
    return bool(alive <= cap)
