"""Step 3 — transactions + conservation core. Gates P1, P3, P7, P2.

IMPLEMENTATION_PLAN.md Step 3.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from env import fields as F
from env.config import load_world_config
from env.diffusion import diffuse_and_decay, inject_sources
from env.invariants import assert_non_negative, conserved_total
from env.transactions import TransactionLedger, apply_conservative_transactions

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _world(seed=42):
    return F.from_config(load_world_config(_CONFIG, scenario="static_gradient"), seed)


def test_conservation_over_long_run() -> None:
    """P1: measured T tracks the ledger to tolerance over thousands of ticks."""
    w = _world()
    cfg = w.cfg
    led = TransactionLedger()
    t0 = conserved_total(w)
    fy, fx = np.argwhere(w.alive > 0)[0]

    uptake = np.zeros((cfg.height, cfg.width))
    cost = np.zeros((cfg.height, cfg.width))
    for t in range(3000):
        uptake[fy, fx] = 0.5           # forager grabs nutrient at its cell
        cost[fy, fx] = cfg.energy.cost_move
        led.source_injected += inject_sources(w, t)
        led.book_decay(diffuse_and_decay(w, cfg))
        led.book(apply_conservative_transactions(w, uptake, cost, cfg))
        residual = abs(conserved_total(w) - led.expected_total(t0))
        assert residual < 1e-6, f"tick {t}: residual {residual:.2e}"
    assert_non_negative(w)


def test_no_free_energy_flat_when_idle() -> None:
    """P3: no source, no action ⇒ T changes only by the booked waste-decay sink."""
    w = _world()
    w.fields[:] = 0.0
    w.fields[:, :, F.Field.HEAT] = w.cfg.fields["heat"].ambient
    w.fields[10:15, 10:15, F.Field.WASTE] = 2.0
    w.alive[:] = 0.0  # nobody acts
    zeros = np.zeros((w.height, w.width))
    led = TransactionLedger()
    t0 = conserved_total(w)
    for _ in range(50):
        led.book_decay(diffuse_and_decay(w, w.cfg))
        led.book(apply_conservative_transactions(w, zeros, zeros, w.cfg))
    assert np.isclose(conserved_total(w), t0 + led.net(), atol=1e-9)


def test_uptake_creates_nothing() -> None:
    """P3: a single uptake only redistributes nutrient → energy+waste+loss."""
    w = _world()
    w.fields[:] = 0.0
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.fields[fy, fx, F.Field.NUTRIENT] = 10.0
    w.energy[fy, fx] = 0.0
    uptake = np.zeros((w.height, w.width))
    uptake[fy, fx] = 4.0
    zeros = np.zeros((w.height, w.width))
    t0 = conserved_total(w)
    rep = apply_conservative_transactions(w, uptake, zeros, w.cfg)
    # T dropped by exactly the conversion loss + metabolic energy_spent.
    assert np.isclose(conserved_total(w), t0 - rep.conversion_loss - rep.energy_spent, atol=1e-9)
    # energy + waste gained equals (η+α)·u.
    eta, alpha = w.cfg.energy.eta, w.cfg.fields["waste"].alpha
    gained = w.energy[fy, fx] + w.fields[fy, fx, F.Field.WASTE]
    # metabolic drain reduced energy by cost_metabolic; add it back for the check.
    assert np.isclose(gained + rep.energy_spent, (eta + alpha) * rep.uptaken, atol=1e-9)


def test_cost_coverage_and_refusal() -> None:
    """P7: action cost is debited cost-first; unaffordable actions are refused."""
    w = _world()
    fy, fx = np.argwhere(w.alive > 0)[0]
    ec = w.cfg.energy
    zeros = np.zeros((w.height, w.width))
    cost = np.zeros((w.height, w.width))

    # Affordable: energy = metabolic + move → both applied, energy → 0.
    w.energy[:] = 0.0
    w.energy[fy, fx] = ec.cost_metabolic + ec.cost_move
    cost[fy, fx] = ec.cost_move
    rep = apply_conservative_transactions(w, zeros, cost, w.cfg)
    assert rep.refused == 0
    assert np.isclose(w.energy[fy, fx], 0.0, atol=1e-12)

    # Unaffordable: after metabolic there isn't enough for the move → refused.
    w.energy[fy, fx] = ec.cost_metabolic + 0.5 * ec.cost_move
    rep = apply_conservative_transactions(w, zeros, cost, w.cfg)
    assert rep.refused == 1
    assert np.isclose(w.energy[fy, fx], 0.5 * ec.cost_move, atol=1e-12)  # move not paid


def test_energy_never_negative() -> None:
    """P2: draining more than available clamps at zero, never below."""
    w = _world()
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.energy[fy, fx] = 0.005  # less than cost_metabolic
    zeros = np.zeros((w.height, w.width))
    apply_conservative_transactions(w, zeros, zeros, w.cfg)
    assert w.energy.min() >= 0.0
