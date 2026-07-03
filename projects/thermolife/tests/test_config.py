"""Step 0 — config loader (IMPLEMENTATION_PLAN.md Step 0)."""

from __future__ import annotations

from pathlib import Path

import pytest

from env.config import ConfigError, load_world_config

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def test_loads_expected_keys() -> None:
    cfg = load_world_config(_CONFIG, scenario="static_gradient")
    assert cfg.height == 64
    assert cfg.width == 64
    assert cfg.energy.eta == pytest.approx(0.80)
    assert cfg.scenario.name == "static_gradient"
    # static_gradient defines a source and a removal tick (the Slice-0 gate).
    assert cfg.scenario.source["kind"] == "static"
    assert cfg.scenario.removal_tick == 5000
    # nutrient field constants come through.
    assert cfg.fields["nutrient"].diffusion == pytest.approx(0.10)


def test_default_scenario_is_static_gradient() -> None:
    assert load_world_config(_CONFIG).scenario.name == "static_gradient"


def test_unknown_scenario_fails_fast() -> None:
    with pytest.raises(ConfigError, match="unknown scenario"):
        load_world_config(_CONFIG, scenario="does_not_exist")


def test_missing_key_fails_fast(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("grid: {height: 8, width: 8}\n")  # missing fields/energy/...
    with pytest.raises(ConfigError, match="missing required key"):
        load_world_config(bad)
