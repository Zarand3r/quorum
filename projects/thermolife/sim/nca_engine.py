"""NCAEngine — runs the reaction-diffusion-advection tick as a live simulation
(M2.4). Same engine protocol as ``SimEngine`` (``step``/``tick``/``residual``/
``snapshot``) so ``SimController`` can drive either.

Closed toroidal system: mass is conserved *exactly* by advection (residual =
|mass.sum() − initial|); hidden is cell state (not conserved, relaxes via the
leak, like Gray-Scott's non-conserved species). Coupling mass birth/decay to the
nutrient feed (open-system feed/kill) is deferred to M2b/M5.
"""

from __future__ import annotations

import numpy as np

from env.config import WorldConfig
from model.config import ModelConfig
from model.genome import Genome
from model.rda import rda_step
from model.state import NCAState
from sim.controller import SimStatus


class NCAEngine:
    def __init__(self, world_cfg: WorldConfig, model_cfg: ModelConfig, seed: int) -> None:
        self.model_cfg = model_cfg
        self.genome = Genome.random(model_cfg, seed)
        self.state = NCAState.seed(world_cfg.height, world_cfg.width, model_cfg, seed)
        self._mass0 = float(self.state.mass.sum())

    def step(self) -> None:
        self.state, _ = rda_step(self.state, self.genome, self.model_cfg)

    @property
    def tick(self) -> int:
        return self.state.tick

    def residual(self) -> float:
        return abs(float(self.state.mass.sum()) - self._mass0)

    def snapshot(self, status: SimStatus) -> dict:
        mass = self.state.mass
        h0 = self.state.hidden[:, :, 0]
        h0n = (h0 - h0.min()) / (h0.max() - h0.min() + 1e-9)  # normalize for display
        return {
            "status": status.value,
            "tick": int(self.state.tick),
            "height": self.state.height,
            "width": self.state.width,
            "residual": self.residual(),
            "mass": np.round(mass, 4).tolist(),
            "mass_max": float(mass.max()),
            "hidden": np.round(h0n, 4).tolist(),
            "hidden_max": 1.0,
            # physical-field keys absent in NCA mode (viewer clears those buttons).
            "nutrient": None, "nutrient_max": 0.0,
            "heat": None, "heat_max": 0.0,
            "waste": None, "waste_max": 0.0,
            "forager": None,
            "alive": int((mass > 0.05).sum()),
            "energy_total": float(mass.sum()),
        }
