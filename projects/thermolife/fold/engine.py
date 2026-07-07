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
        self._base = seed
        self._gen = 0          # which fold in the gallery (bumps on convergence)
        self._t = 0            # total iterations
        self._since = 0        # iterations since the current fold started
        self._fold_step = 0.0
        self.w, self.x = self._instantiate()

    def _instantiate(self):
        """Fresh toy transformer + tokens for the current gallery index (deterministic)."""
        s = self._base if self._gen == 0 else (self._base * 10007 + self._gen)
        w = FoldWeights.random(self.cfg, s)
        rng = np.random.default_rng([s, 10_000])  # decorrelate embeddings from weights
        x = rng.standard_normal((self.cfg.n_tokens, self.cfg.d)) * self.cfg.init_scale
        return w, x

    def step(self) -> None:
        x1, _, _ = block_step(self.x, self.w, self.cfg)
        self._fold_step = float(np.linalg.norm(x1 - self.x) / np.sqrt(self.x.size))
        self.x = x1
        self._t += 1
        self._since += 1
        # a fold that has settled → start the next one (fold gallery; PLAN.md D3)
        if (
            self.cfg.reseed_on_converge
            and self._since >= self.cfg.min_iters_before_reseed
            and self._fold_step < self.cfg.converge_eps
        ):
            self._gen += 1
            self.w, self.x = self._instantiate()
            self._since = 0

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
            "fold": self._gen,
            "fold_iter": self._since,
            "n": self.cfg.n_tokens,
            "fold_step": round(self._fold_step, 5),
            "max_attn": round(float(off_diag.max()), 3),
            "tokens": tokens,
            "edges": edges,
        }
