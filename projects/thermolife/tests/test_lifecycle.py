"""Step 4 — lifecycle (death / decomposition / inertness). Gates P4, P1.

IMPLEMENTATION_PLAN.md Step 4.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from env import fields as F
from env.config import load_world_config
from env.invariants import conserved_total
from env.lifecycle import apply_lifecycle
from env.transactions import apply_conservative_transactions

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _world(seed=42):
    return F.from_config(load_world_config(_CONFIG, scenario="static_gradient"), seed)


def test_dead_cell_is_inert() -> None:
    """P4: a cell below the alive threshold performs no uptake."""
    w = _world()
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.alive[fy, fx] = 0.0  # dead
    w.fields[fy, fx, F.Field.NUTRIENT] = 10.0
    w.energy[fy, fx] = 0.0
    uptake = np.zeros((w.height, w.width))
    uptake[fy, fx] = 5.0
    rep = apply_conservative_transactions(w, uptake, np.zeros_like(uptake), w.cfg)
    assert rep.uptaken == 0.0
    assert w.fields[fy, fx, F.Field.NUTRIENT] == 10.0  # untouched
    assert w.energy[fy, fx] == 0.0


def test_death_on_low_energy() -> None:
    w = _world()
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.energy[fy, fx] = w.cfg.energy.e_lethal  # at the floor
    apply_lifecycle(w, w.cfg)
    assert w.alive[fy, fx] == 0.0


def test_death_on_lethal_heat() -> None:
    w = _world()
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.energy[fy, fx] = 0.5  # healthy energy…
    w.fields[fy, fx, F.Field.HEAT] = w.cfg.barriers.tau_lethal  # …but lethal heat
    apply_lifecycle(w, w.cfg)
    assert w.alive[fy, fx] == 0.0


def test_decomposition_conserves() -> None:
    """P1 across death: T drops by exactly the decomposition loss; nutrient gains
    the returned fraction of biomass."""
    w = _world()
    w.fields[:] = 0.0
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.energy[fy, fx] = 0.6
    w.fields[fy, fx, F.Field.HEAT] = w.cfg.barriers.tau_lethal  # force death, keep energy
    t0 = conserved_total(w)
    frac = w.cfg.lifecycle.decomp_return_fraction
    loss = apply_lifecycle(w, w.cfg)
    assert np.isclose(w.fields[fy, fx, F.Field.NUTRIENT], frac * 0.6, atol=1e-12)
    assert w.energy[fy, fx] == 0.0
    assert np.isclose(loss, (1.0 - frac) * 0.6, atol=1e-12)
    assert np.isclose(conserved_total(w), t0 - loss, atol=1e-12)


def test_decomposition_is_one_time() -> None:
    w = _world()
    fy, fx = np.argwhere(w.alive > 0)[0]
    w.energy[fy, fx] = 0.6
    w.fields[fy, fx, F.Field.HEAT] = w.cfg.barriers.tau_lethal
    first = apply_lifecycle(w, w.cfg)
    nutrient_after = w.fields[fy, fx, F.Field.NUTRIENT]
    second = apply_lifecycle(w, w.cfg)  # already dead + energy 0
    assert first > 0.0
    assert second == 0.0
    assert w.fields[fy, fx, F.Field.NUTRIENT] == nutrient_after  # no further return
