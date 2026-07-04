"""The shared genome θ — fixed numpy weights of the NCA rule (M2, PLAN.md §10.5).

One weight set applied to every cell (the "one shared local rule" of a cellular
automaton). M2a uses a random-but-fixed genome; M2b would meta-train it. The
reaction MLP maps ``concat(hidden, message, mass)`` → Δhidden.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from model.config import ModelConfig


@dataclass
class Genome:
    W_lig: np.ndarray  # [C, D, F] — ligand (query) per direction
    W_rec: np.ndarray  # [C, D, F] — receptor (key) per direction
    W_val: np.ndarray  # [C, C]    — value transform
    W1: np.ndarray     # [2C+1, M] — reaction MLP layer 1 (in: hidden, message, mass)
    b1: np.ndarray     # [M]
    W2: np.ndarray     # [M, C]    — reaction MLP layer 2
    b2: np.ndarray     # [C]

    @staticmethod
    def random(cfg: ModelConfig, seed: int, scale: float = 0.5) -> "Genome":
        rng = np.random.default_rng(seed)
        c, f, d, m = cfg.hidden_dim, cfg.iface_dim, cfg.directions, cfg.mlp_width

        def n(*shape: int) -> np.ndarray:
            return rng.standard_normal(shape) * scale

        return Genome(
            W_lig=n(c, d, f),
            W_rec=n(c, d, f),
            W_val=n(c, c),
            W1=n(2 * c + 1, m),
            b1=np.zeros(m),
            W2=n(m, c),
            b2=np.zeros(c),
        )
