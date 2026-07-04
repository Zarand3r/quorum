"""NCA state — a hidden-state field + a conserved mass/occupancy field (M2).

Toroidal (periodic) grid so attention advection conserves mass exactly with no
boundary loss — standard for Game-of-Life / reaction-diffusion. ``hidden`` is a
field defined everywhere (Eulerian); ``mass`` is the transported "stuff" whose
motion renders as entities moving.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

import numpy as np

from model.config import ModelConfig


@dataclass
class NCAState:
    hidden: np.ndarray  # [H, W, C] float64
    mass: np.ndarray    # [H, W]   float64, >= 0
    tick: int

    @property
    def height(self) -> int:
        return self.hidden.shape[0]

    @property
    def width(self) -> int:
        return self.hidden.shape[1]

    @staticmethod
    def seed(
        height: int, width: int, cfg: ModelConfig, seed: int, blob_frac: float = 0.12
    ) -> "NCAState":
        rng = np.random.default_rng(seed)
        hidden = rng.standard_normal((height, width, cfg.hidden_dim)) * 0.1
        mass = np.zeros((height, width))
        cy, cx = height // 2, width // 2
        r = max(1, int(min(height, width) * blob_frac))
        yy, xx = np.ogrid[:height, :width]
        mass[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 1.0
        return NCAState(hidden=hidden, mass=mass, tick=0)

    def copy(self) -> "NCAState":
        return replace(self, hidden=self.hidden.copy(), mass=self.mass.copy())

    def state_hash(self) -> str:
        h = hashlib.sha256()
        h.update(np.ascontiguousarray(self.hidden).tobytes())
        h.update(np.ascontiguousarray(self.mass).tobytes())
        h.update(np.int64(self.tick).tobytes())
        return h.hexdigest()
