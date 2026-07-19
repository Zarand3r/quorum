"""Engine: the fast clock (dock-and-morph dynamics).

A `step()` advances the state by one fixed-rule dock-and-morph application — motion
by neighbour forces, morph by the block. No per-tick learning: the rule is fixed on
this clock (a slow/macro clock that adapts the rule is future work). `snapshot()` is
read-only (P5); `fork()` gives the measurement harness an independent copy (P5/P3).
"""

from __future__ import annotations

import copy

import numpy as np

from block import Weights, forward_verbose, make_weights
from config import VivariumConfig
from render import snapshot as _snapshot
from substrate import init_state


class Engine:
    def __init__(self, cfg: VivariumConfig, seed: int, ablate: str = "none") -> None:
        self.cfg = cfg
        self.seed = seed
        self.ablate = ablate  # coupling ablation for the P6 control arms ("none" = real run)
        self.weights: Weights = make_weights(cfg, seed)
        self.X: np.ndarray = init_state(cfg, seed)
        self.t: int = 0

    def step(self) -> None:
        self.X, _ = forward_verbose(self.X, self.weights, self.cfg, self.ablate, self.seed, self.t)
        self.t += 1

    def snapshot(self) -> dict:
        return _snapshot(self.X, self.weights, self.cfg, self.t)

    def fork(self) -> "Engine":
        """A deep, independent copy — used by the read-only measurement harness to
        probe the run without perturbing it (P5/P3)."""
        return copy.deepcopy(self)
