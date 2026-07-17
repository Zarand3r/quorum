"""Engine: the one clock (IMPLEMENTATION_PLAN.md Step 2, M1).

A single `step()` advances **both** the state (block forward) **and** the weights
(local predictive plasticity) — the simulation *is* the learning. There is no
separate `train()`/`fit()` phase (P2). `snapshot()` is strictly read-only (P5).
"""

from __future__ import annotations

import copy

import numpy as np

from block import Weights, forward_verbose, make_weights
from config import VivariumConfig
from plasticity import learn
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
        self.last_loss: float = float("nan")  # measured surprise (diagnostic, read-only)

    def step(self) -> None:
        # one clock: forward, then a local weight update from the same tick's error.
        X_next, A, msg = forward_verbose(
            self.X, self.weights, self.cfg, self.ablate, self.seed, self.t
        )
        self.weights, self.last_loss = learn(
            self.weights, self.X, A, msg, X_next, self.t, self.cfg
        )
        self.X = X_next
        self.t += 1

    def snapshot(self) -> dict:
        return _snapshot(self.X, self.weights, self.cfg, self.t)

    def fork(self) -> "Engine":
        """A deep, independent copy — used by the read-only measurement harness to
        probe the run without perturbing it (P5/P3). Stepping a fork never touches self."""
        return copy.deepcopy(self)
