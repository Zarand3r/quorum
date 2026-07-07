"""EcoState — dense, compacted population arrays (IMPLEMENTATION_PLAN.md Step 1).

Structure-of-arrays over exactly the *living* tokens (compacted, not a fixed-capacity
masked buffer): death is a vectorized boolean-index rebuild and birth is a batched
append — both bounded array ops, never a per-token Python loop (P5). Positions are
continuous ``float`` in R^d — there is no lattice, no cell index (P3).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from eco.config import EcoConfig


@dataclass
class EcoState:
    x: np.ndarray          # [N, d]  positions in embedding space (continuous)
    e: np.ndarray          # [N]     energy ≥ 0
    g: np.ndarray          # [N, d_g] interface genes (heritable)
    mu: np.ndarray         # [d]     current resource-source location
    pool: float            # unharvested resource
    dissipated: float      # cumulative heat
    t: int                 # tick counter
    rng: np.random.Generator

    @property
    def n(self) -> int:
        return int(self.x.shape[0])

    def state_hash(self) -> str:
        """Deterministic content hash (P4). Excludes the RNG object; a run is
        reproduced by seed, and rng draws are folded into x/e/g downstream."""
        h = hashlib.sha256()
        for arr in (self.x, self.e, self.g, self.mu):
            h.update(np.ascontiguousarray(arr, dtype=np.float64).tobytes())
        h.update(np.float64(self.pool).tobytes())
        h.update(np.float64(self.dissipated).tobytes())
        h.update(np.int64(self.t).tobytes())
        return h.hexdigest()


def source_at(t: int, cfg: EcoConfig) -> np.ndarray:
    """Source location at tick ``t`` — a deterministic orbit in the first two dims.

    Linear speed is ``drift_v`` (arclength/tick), so angular step = v / R. The orbit
    keeps the source bounded yet perpetually moving: any *static* configuration sits
    at a fixed distance from an ever-moving source and starves (P8)."""
    mu = np.zeros(cfg.d, dtype=np.float64)
    if cfg.orbit_radius <= 0.0:
        return mu
    omega = cfg.drift_v / cfg.orbit_radius
    ang = omega * t
    mu[0] = cfg.orbit_radius * np.cos(ang)
    mu[1] = cfg.orbit_radius * np.sin(ang)
    return mu


def init_state(cfg: EcoConfig) -> EcoState:
    """Seed a population near the origin with genes drawn from the RNG (P4)."""
    rng = np.random.Generator(np.random.PCG64(cfg.seed))
    x = 0.1 * rng.standard_normal((cfg.n_init, cfg.d))
    e = np.full(cfg.n_init, cfg.e_init, dtype=np.float64)
    g = rng.standard_normal((cfg.n_init, cfg.d_g))
    mu = source_at(0, cfg)
    # pool primed with one injection so tick 0 has resource to compete for
    return EcoState(x=x, e=e, g=g, mu=mu, pool=cfg.inject, dissipated=0.0, t=0, rng=rng)
