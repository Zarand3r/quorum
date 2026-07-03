"""Typed configuration loaded from ``configs/world.yaml`` (PLAN.md §12).

Fail-fast (PLAN.md I-failure model): a missing key or an unknown scenario
raises :class:`ConfigError` rather than falling back to a default. The loader
returns plain frozen dataclasses — no hidden defaults, no silent coercion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the world config is missing a key or names an unknown scenario."""


def _require(mapping: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"missing required key {key!r} in {ctx}")
    return mapping[key]


@dataclass(frozen=True)
class FieldConfig:
    diffusion: float
    decay: float
    ambient: float
    # Waste production per unit uptake (waste field only); 0.0 for others.
    alpha: float = 0.0
    # Heat produced per unit energy spent (heat field only); 0.0 for others.
    beta: float = 0.0


@dataclass(frozen=True)
class EnergyConfig:
    eta: float
    cost_metabolic: float
    cost_move: float
    cost_signal: float
    cost_plasticity: float
    cost_repair: float
    e_lethal: float
    e_div: float


@dataclass(frozen=True)
class BarrierConfig:
    tau_lethal: float
    w_lethal: float
    barrier_sharpness: float


@dataclass(frozen=True)
class LifecycleConfig:
    alive_threshold: float
    decomp_return_fraction: float
    population_cap_fraction: float


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    source: dict[str, Any]
    # ``removal_tick`` is the tick at which a static source is switched off
    # (the Slice-0 gate, PLAN.md §15.2); ``None`` means "never removed".
    removal_tick: int | None


@dataclass(frozen=True)
class WorldConfig:
    height: int
    width: int
    batch: int
    fields: dict[str, FieldConfig]
    energy: EnergyConfig
    barriers: BarrierConfig
    lifecycle: LifecycleConfig
    scenario: ScenarioConfig
    seed: int
    deterministic: bool


def _field(raw: dict[str, Any], name: str) -> FieldConfig:
    f = _require(raw, name, "fields")
    return FieldConfig(
        diffusion=float(_require(f, "diffusion", f"fields.{name}")),
        decay=float(_require(f, "decay", f"fields.{name}")),
        # Ambient is only nonzero for heat (cooling target); default 0.0.
        ambient=float(f.get("ambient", 0.0)),
        alpha=float(f.get("alpha", 0.0)),
        beta=float(f.get("beta", 0.0)),
    )


def load_world_config(path: str | Path, scenario: str | None = None) -> WorldConfig:
    """Load and validate a world config, selecting one scenario.

    ``scenario`` defaults to ``"static_gradient"`` (the Slice-0 gate). An
    unknown scenario name raises :class:`ConfigError` — never a silent default.
    """
    text = Path(path).read_text()
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top-level YAML must be a mapping")

    grid = _require(raw, "grid", "world")
    fields_raw = _require(raw, "fields", "world")
    energy_raw = _require(raw, "energy", "world")
    barriers_raw = _require(raw, "barriers", "world")
    lifecycle_raw = _require(raw, "lifecycle", "world")
    scenarios_raw = _require(raw, "scenarios", "world")

    scenario_name = scenario if scenario is not None else "static_gradient"
    if scenario_name not in scenarios_raw:
        available = ", ".join(sorted(scenarios_raw))
        raise ConfigError(
            f"unknown scenario {scenario_name!r}; available: {available}"
        )
    scen_raw = scenarios_raw[scenario_name]

    return WorldConfig(
        height=int(_require(grid, "height", "grid")),
        width=int(_require(grid, "width", "grid")),
        batch=int(grid.get("batch", 1)),
        fields={
            name: _field(fields_raw, name)
            for name in ("nutrient", "waste", "heat", "pheromone")
        },
        energy=EnergyConfig(
            eta=float(_require(energy_raw, "eta", "energy")),
            cost_metabolic=float(_require(energy_raw, "cost_metabolic", "energy")),
            cost_move=float(_require(energy_raw, "cost_move", "energy")),
            cost_signal=float(_require(energy_raw, "cost_signal", "energy")),
            cost_plasticity=float(_require(energy_raw, "cost_plasticity", "energy")),
            cost_repair=float(_require(energy_raw, "cost_repair", "energy")),
            e_lethal=float(_require(energy_raw, "e_lethal", "energy")),
            e_div=float(_require(energy_raw, "e_div", "energy")),
        ),
        barriers=BarrierConfig(
            tau_lethal=float(_require(barriers_raw, "tau_lethal", "barriers")),
            w_lethal=float(_require(barriers_raw, "w_lethal", "barriers")),
            barrier_sharpness=float(
                _require(barriers_raw, "barrier_sharpness", "barriers")
            ),
        ),
        lifecycle=LifecycleConfig(
            alive_threshold=float(
                _require(lifecycle_raw, "alive_threshold", "lifecycle")
            ),
            decomp_return_fraction=float(
                _require(lifecycle_raw, "decomp_return_fraction", "lifecycle")
            ),
            population_cap_fraction=float(
                _require(lifecycle_raw, "population_cap_fraction", "lifecycle")
            ),
        ),
        scenario=ScenarioConfig(
            name=scenario_name,
            source=dict(_require(scen_raw, "source", f"scenarios.{scenario_name}"))
            if scen_raw.get("source") not in (None, "none")
            else {},
            removal_tick=(
                int(scen_raw["removal_tick"])
                if scen_raw.get("removal_tick") is not None
                else None
            ),
        ),
        seed=int(raw.get("seed", 0)),
        deterministic=bool(raw.get("deterministic", True)),
    )
