"""The fixed weights of the toy transformer (PLAN.md §4). Random init at S0.

`W_c` is the *grounded* readout: an embedding → the harmonic coefficients of its
contour blob, which are also its attention **query** (ligand). `M` is the fixed
complementarity metric that turns those same coefficients into the **key**
(receptor): a π-rotation of the contour (harmonic k scaled by (−1)^k), so a high
score means i's surface facing j complements j's surface facing i.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fold.config import FoldConfig


@dataclass
class FoldWeights:
    W_c: np.ndarray  # [d, 2K]   embedding → contour coeffs (= query / ligand)
    M: np.ndarray    # [2K, 2K]  complementarity metric (→ key / receptor)
    W_v: np.ndarray  # [d, d]    value
    W1: np.ndarray   # [d, H]    MLP
    b1: np.ndarray   # [H]
    W2: np.ndarray   # [H, d]
    b2: np.ndarray   # [d]
    P: np.ndarray    # [d, 2]    2D position projection

    @staticmethod
    def random(cfg: FoldConfig, seed: int) -> "FoldWeights":
        rng = np.random.default_rng(seed)
        d, k, h = cfg.d, cfg.k_harmonics, cfg.mlp_width
        s = 1.0 / np.sqrt(d)

        # complementarity: rotating a contour by π multiplies harmonic k by (−1)^k;
        # both the cos_k and sin_k coefficient of each harmonic share that sign.
        signs = np.array([(-1.0) ** k for k in range(1, k + 1)])
        metric = np.diag(np.repeat(signs, 2))

        if d == 2:
            proj = np.eye(2)
        else:
            proj, _ = np.linalg.qr(rng.standard_normal((d, 2)))  # orthonormal columns
            proj = proj[:, :2]

        return FoldWeights(
            W_c=rng.standard_normal((d, 2 * k)) * s,
            M=metric,
            W_v=rng.standard_normal((d, d)) * s,
            W1=rng.standard_normal((d, h)) * s,
            b1=np.zeros(h),
            W2=rng.standard_normal((h, d)) * (1.0 / np.sqrt(h)),
            b2=np.zeros(d),
            P=proj,
        )
