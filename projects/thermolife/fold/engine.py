"""FoldEngine — drives the fold as a stepping simulation (PLAN.md §7).

Implements the engine protocol (``step`` / ``tick`` / ``residual`` / ``snapshot``)
so the existing SimController/HTTP server can run it. ``residual`` is the
per-step fold displacement ‖ΔX‖ (→ 0 as the embeddings settle into their fold);
``snapshot`` emits blobs (absolute contour outlines + positions) and the docking
edges. Depends on nothing in ``sim/`` — orchestration owns fold, not vice versa.
"""

from __future__ import annotations

import hashlib

import numpy as np

from fold.config import FoldConfig
from fold.interface import contour_coeffs, contour_polylines
from fold.transformer import attention, block_step
from fold.weights import FoldWeights


class FoldEngine:
    def __init__(self, cfg: FoldConfig, seed: int) -> None:
        self.cfg = cfg
        self.w = FoldWeights.random(cfg, seed)
        rng = np.random.default_rng(seed + 10_000)  # decorrelate embeddings from weights
        self.x = rng.standard_normal((cfg.n_tokens, cfg.d)) * cfg.init_scale
        self._t = 0
        self._fold_step = 0.0

    def step(self) -> None:
        x1, _, _ = block_step(self.x, self.w, self.cfg)
        self._fold_step = float(np.linalg.norm(x1 - self.x) / np.sqrt(self.x.size))
        self.x = x1
        self._t += 1

    @property
    def tick(self) -> int:
        return self._t

    def residual(self) -> float:
        return self._fold_step

    def state_hash(self) -> str:
        h = hashlib.sha256(np.ascontiguousarray(self.x).tobytes())
        h.update(np.int64(self._t).tobytes())
        return h.hexdigest()

    def snapshot(self, status) -> dict:
        c = contour_coeffs(self.x, self.w)
        _, a = attention(self.x, self.w, self.cfg)
        pos = self.x @ self.w.P                          # [N,2]
        outline = pos[:, None, :] + contour_polylines(c, self.cfg)  # [N,P,2] absolute
        tokens = [
            {
                "pos": [round(float(pos[i, 0]), 3), round(float(pos[i, 1]), 3)],
                "contour": np.round(outline[i], 3).tolist(),
            }
            for i in range(self.cfg.n_tokens)
        ]
        off_diag = a.copy()
        np.fill_diagonal(off_diag, 0.0)
        mask = off_diag >= self.cfg.edge_threshold
        ii, jj = np.where(mask)
        edges = [[int(i), int(j), round(float(a[i, j]), 3)] for i, j in zip(ii, jj)]
        return {
            "status": status.value,
            "tick": self._t,
            "n": self.cfg.n_tokens,
            "fold_step": round(self._fold_step, 5),
            "max_attn": round(float(off_diag.max()), 3),
            "tokens": tokens,
            "edges": edges,
        }
