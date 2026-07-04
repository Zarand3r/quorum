"""M2 model configuration (the NCA reaction-diffusion-advection rule).

Loaded from the ``nca`` section of ``configs/model.yaml``. Pure numpy mechanism
(no torch); see IMPLEMENTATION_PLAN_M2.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULTS: dict = {
    "hidden_dim": 8,
    "iface_dim": 4,
    "directions": 4,
    "mlp_width": 16,
    "bind_temperature": 0.5,
    "bind_bias": 1.0,
    "advection_gain": 0.5,
    "reaction_scale": 0.1,
    "diffusivity": [0.24, 0.24, 0.10, 0.10, 0.04, 0.04, 0.0, 0.0],
}


@dataclass(frozen=True)
class ModelConfig:
    hidden_dim: int
    iface_dim: int
    directions: int
    mlp_width: int
    bind_temperature: float
    bind_bias: float
    advection_gain: float
    reaction_scale: float
    diffusivity: tuple[float, ...]


def load_model_config(path: str | Path) -> ModelConfig:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    nca = raw.get("nca", {})
    d = {**_DEFAULTS, **{k: nca[k] for k in _DEFAULTS if k in nca}}
    diffusivity = tuple(float(x) for x in d["diffusivity"])
    hidden_dim = int(d["hidden_dim"])
    if len(diffusivity) != hidden_dim:
        raise ValueError(
            f"diffusivity length {len(diffusivity)} != hidden_dim {hidden_dim}"
        )
    if not 0.0 <= float(d["advection_gain"]) <= 1.0:
        raise ValueError("advection_gain must be in [0,1] (flux limiter)")
    return ModelConfig(
        hidden_dim=hidden_dim,
        iface_dim=int(d["iface_dim"]),
        directions=int(d["directions"]),
        mlp_width=int(d["mlp_width"]),
        bind_temperature=float(d["bind_temperature"]),
        bind_bias=float(d["bind_bias"]),
        advection_gain=float(d["advection_gain"]),
        reaction_scale=float(d["reaction_scale"]),
        diffusivity=diffusivity,
    )
