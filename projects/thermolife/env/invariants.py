"""Runtime invariant checks (PLAN.md §12 env/invariants.py).

Used by the tests and by the tick loop's debug-flag path. These assert the
conservation and non-negativity properties (P1, P2) against the ledger of
record — not against a re-derived sum.
"""

from __future__ import annotations

import numpy as np

from env.fields import Field, World
from env.transactions import TransactionLedger


def conserved_total(world: World) -> float:
    """The conserved quantity ``T = Σ nutrient + Σ energy + Σ waste`` (χ=1)."""
    nutrient = world.fields[:, :, Field.NUTRIENT].sum()
    waste = world.fields[:, :, Field.WASTE].sum()
    return float(nutrient + world.energy.sum() + waste)


def assert_conserved(
    world: World, ledger: TransactionLedger, initial_total: float, tol: float = 1e-6
) -> None:
    """P1: measured ``T`` equals the ledger's expected total within ``tol``."""
    measured = conserved_total(world)
    expected = ledger.expected_total(initial_total)
    residual = abs(measured - expected)
    if residual > tol:
        raise AssertionError(
            f"conservation residual {residual:.3e} > tol {tol:.1e} "
            f"(measured T={measured:.6f}, ledger expects {expected:.6f})"
        )


def assert_non_negative(world: World) -> None:
    """P2: no field concentration and no cell energy is negative."""
    if world.fields.min() < 0.0:
        raise AssertionError("negative field concentration")
    if world.energy.min() < 0.0:
        raise AssertionError("negative cell energy")


def has_negative(world: World) -> bool:
    return bool(world.fields.min() < 0.0 or world.energy.min() < 0.0)
