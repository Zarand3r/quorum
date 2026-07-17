"""Engine: the one clock (IMPLEMENTATION_PLAN.md Step 1, M0).

At M0 a `step()` advances *state only* through the fixed-weight block — no
learning yet (that is M1). `snapshot()` is strictly read-only (P5). The drift
field `s` is carried but static here; M1 makes it move (the J drive).
"""

from __future__ import annotations

import numpy as np

from block import Weights, forward, make_weights
from config import VivariumConfig
from render import snapshot as _snapshot
from substrate import init_state


class Engine:
    def __init__(self, cfg: VivariumConfig, seed: int) -> None:
        self.cfg = cfg
        self.seed = seed
        self.weights: Weights = make_weights(cfg, seed)
        self.X: np.ndarray = init_state(cfg, seed)
        self.t: int = 0
        self.s: float = 0.0  # external drift field (static at M0)

    def step(self) -> None:
        self.X = forward(self.X, self.weights, self.cfg)
        self.t += 1

    def snapshot(self) -> dict:
        return _snapshot(self.X, self.weights, self.cfg, self.t)
