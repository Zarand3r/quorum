"""THE E0 GATE (IMPLEMENTATION_PLAN.md Step 5, property P8).

Real stakes: there is a critical drift speed v* (empirically ≈0.26 for eco.yaml).
  - below it, a forager that tracks the source LIVES;
  - above it, the forager falls behind and STARVES;
  - a frozen control starves at ANY speed.
Survival requires motion — the economy is neither trivially survivable nor hopeless.
Evidence curve: `bazel run //projects/thermolife:eco_run -- --sweep ...`.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from eco.config import load_eco_config
from eco.engine import run
from eco.policies import frozen, hand_forager

_CFG = Path(__file__).resolve().parent.parent / "configs" / "eco.yaml"

_V_SLOW = 0.06   # ≪ v*  — forager thrives, frozen starves
_V_FAST = 0.35   # ≫ v*  — even the forager cannot keep pace


def _cfg(drift_v):
    return dataclasses.replace(load_eco_config(_CFG), drift_v=drift_v)


def test_conservation_under_forager_longrun() -> None:
    """P1 at scale: 10k ticks under the forager, ledger closed throughout."""
    res = run(_cfg(_V_SLOW), ticks=10000, policy=hand_forager)
    assert res["max_abs_residual"] < 1e-9, res["max_abs_residual"]


def test_frozen_control_starves() -> None:
    """A non-moving population starves even at the slow drift — motion, not luck."""
    res = run(_cfg(_V_SLOW), ticks=800, policy=frozen)
    assert res["final_n"] == 0
    assert res["survived"] < 800


def test_e0_gate_survives_slow() -> None:
    """Below v*, the forager tracks the source and persists far past starvation time."""
    forager = run(_cfg(_V_SLOW), ticks=800, policy=hand_forager)
    control = run(_cfg(_V_SLOW), ticks=800, policy=frozen)
    assert forager["final_n"] > 0            # still alive at 800
    assert forager["survived"] == 800
    assert forager["survived"] > 5 * control["survived"]  # ≫ static starvation time


def test_e0_gate_starves_fast() -> None:
    """Above v*, the forager falls behind and the population goes extinct."""
    res = run(_cfg(_V_FAST), ticks=600, policy=hand_forager)
    assert res["final_n"] == 0
    assert res["survived"] < 600


def test_gate_separates() -> None:
    """The two regimes are cleanly separated (one config lives, one dies)."""
    slow = run(_cfg(_V_SLOW), ticks=600, policy=hand_forager)
    fast = run(_cfg(_V_FAST), ticks=600, policy=hand_forager)
    assert slow["final_n"] > 0 and fast["final_n"] == 0
