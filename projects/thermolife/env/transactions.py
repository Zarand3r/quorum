"""The conservation core: the only mutator of energy + the physical fields
driven by cell actions (PLAN.md §12, I1/I3/I12).

Conserved quantity ``T = Σ nutrient + Σ energy + Σ waste`` (unit factor χ=1).
Every mutation here is a zero-sum move between accounted stores plus named
sinks — nothing is created (P3). Concretely, per tick over the alive cells:

  uptake u = min(demand, nutrient_here)          # bounded by availability (P2)
    nutrient -= u
    energy   += η·u                              # conversion
    waste    += α·u                              # byproduct (η+α ≤ 1)
    sink conversion_loss += (1−η−α)·u            # dissipated

  metabolic drain m = min(cost_metabolic, energy)  # unconditional (drives death)
    energy -= m ; sink energy_spent += m ; heat += β·m

  discretionary action cost c (move/signal)      # cost-FIRST, refusable (P7)
    applied only where energy ≥ c; else refused (energy unchanged, not created)
    energy -= c ; sink energy_spent += c ; heat += β·c

Spent energy leaves ``T`` entirely (dissipated as heat, which is *not* a
conserved quantity). Movement/relocation of a cell is handled by the tick loop,
not here — relocating energy between cells is conservative by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from env.config import WorldConfig
from env.fields import Field, World


@dataclass
class TransactionReport:
    """Per-tick outcome of :func:`apply_conservative_transactions`.

    The three deltas are the ledger contributions this tick; ``refused`` is the
    number of cells whose discretionary action was denied for lack of energy.
    """

    uptaken: float = 0.0
    conversion_loss: float = 0.0
    energy_spent: float = 0.0
    refused: int = 0


@dataclass
class TransactionLedger:
    """Running account of every source/sink for the conserved quantity ``T``.

    ``expected_total(initial_T)`` is the value the measured ``T`` must equal
    (within float tolerance) at any tick — the P1 gate checks against *this*,
    not against a re-summed "truth".
    """

    source_injected: float = 0.0  # nutrient injected by the scenario source
    conversion_loss: float = 0.0  # (1−η−α)·u dissipated in conversion
    energy_spent: float = 0.0     # metabolic + action costs (dissipated as heat)
    waste_decayed: float = 0.0    # waste removed by decay
    decomp_loss: float = 0.0      # decomposition return loss (Step 4)

    def book(self, report: TransactionReport) -> None:
        self.conversion_loss += report.conversion_loss
        self.energy_spent += report.energy_spent

    def net(self) -> float:
        return (
            self.source_injected
            - self.conversion_loss
            - self.energy_spent
            - self.waste_decayed
            - self.decomp_loss
        )

    def expected_total(self, initial_total: float) -> float:
        return initial_total + self.net()


def apply_conservative_transactions(
    world: World,
    uptake_demand: np.ndarray,
    action_cost: np.ndarray,
    cfg: WorldConfig,
) -> TransactionReport:
    """Apply uptake, metabolic drain, and discretionary action costs in place.

    ``uptake_demand`` and ``action_cost`` are ``[H, W]`` per-cell intents.
    Returns a :class:`TransactionReport` of the tick's ledger contributions.
    """
    ec = cfg.energy
    beta = cfg.fields["heat"].beta
    eta, alpha = ec.eta, cfg.fields["waste"].alpha
    loss_frac = 1.0 - eta - alpha
    if loss_frac < -1e-12:
        raise ValueError(f"η+α must be ≤ 1 (got η={eta}, α={alpha})")

    alive_mask = (world.alive >= cfg.lifecycle.alive_threshold).astype(world.energy.dtype)

    nutrient = world.fields[:, :, Field.NUTRIENT]
    waste = world.fields[:, :, Field.WASTE]
    heat = world.fields[:, :, Field.HEAT]
    energy = world.energy

    # 1. Uptake — bounded by available nutrient (non-negativity, P2).
    u = np.minimum(uptake_demand * alive_mask, nutrient)
    u = np.maximum(u, 0.0)
    nutrient -= u
    energy += eta * u
    waste += alpha * u
    conversion_loss = float((loss_frac * u).sum())

    # 2. Metabolic drain — unconditional, bounded by available energy.
    m = np.minimum(ec.cost_metabolic * alive_mask, energy)
    energy -= m
    heat += beta * m
    energy_spent = float(m.sum())

    # 3. Discretionary action cost — cost-first, refused if unaffordable (P7).
    requested = action_cost * alive_mask
    afford = energy >= requested
    applied = np.where(afford, requested, 0.0)
    energy -= applied
    heat += beta * applied
    energy_spent += float(applied.sum())
    refused = int(np.count_nonzero((requested > 0.0) & ~afford))

    return TransactionReport(
        uptaken=float(u.sum()),
        conversion_loss=conversion_loss,
        energy_spent=energy_spent,
        refused=refused,
    )
