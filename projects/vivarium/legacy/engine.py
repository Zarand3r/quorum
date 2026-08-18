"""Engine: the fast clock (dock-and-morph dynamics).

A `step()` advances the state by one fixed-rule dock-and-morph application — motion
by neighbour forces, morph by the block. No per-tick learning: the rule is fixed on
this clock (a slow/macro clock that adapts the rule is future work). `snapshot()` is
read-only (P5); `fork()` gives the measurement harness an independent copy (P5/P3).
"""

from __future__ import annotations

import copy

import numpy as np

from block import POS_DIM, Weights, make_weights, positions, step_fields
from config import VivariumConfig
from render import snapshot as _snapshot
from rng import base_rng
from substrate import init_state


class Engine:
    def __init__(self, cfg: VivariumConfig, seed: int, ablate: str = "none") -> None:
        self.cfg = cfg
        self.seed = seed
        self.ablate = ablate  # coupling ablation for the P6 control arms ("none" = real run)
        self.weights: Weights = make_weights(cfg, seed)
        self.X: np.ndarray = init_state(cfg, seed)
        self.vel: np.ndarray = np.zeros((cfg.N, POS_DIM))  # position velocity (momentum/inertia)
        # fixed per-agent type for the typed force (Particle-Life / E–I), decorrelated from init.
        self.types: np.ndarray = base_rng(seed + 2).integers(0, cfg.n_types, cfg.N)
        self.t: int = 0

    def step(self) -> None:
        force, z2, _ = step_fields(
            self.X, self.weights, self.cfg, self.ablate, self.seed, self.t, self.types
        )
        # momentum integration: inertia smooths a jittery force into coherent motion.
        self.vel = self.cfg.momentum * self.vel + force
        p_next = np.clip(positions(self.X) + self.vel, -self.cfg.pos_bound, self.cfg.pos_bound)
        self.X = np.concatenate([p_next, z2], axis=1)
        self.t += 1

    def snapshot(self) -> dict:
        return _snapshot(self.X, self.weights, self.cfg, self.t)

    def fork(self) -> "Engine":
        """A deep, independent copy — used by the read-only measurement harness to
        probe the run without perturbing it (P5/P3)."""
        return copy.deepcopy(self)
