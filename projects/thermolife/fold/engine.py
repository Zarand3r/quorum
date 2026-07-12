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

from pathlib import Path

from fold.config import FoldConfig
from fold.interface import contour_coeffs, contour_polylines
from fold.transformer import attention, block_step
from fold.vocab import VocabConfig, sample_scene, scene_embed
from fold.weights import FoldWeights


class FoldEngine:
    """Two modes. RANDOM (S0): every gallery entry is a fresh random toy
    transformer + random tokens — the untrained fold. TRAINED (M2): the weights
    and vocabulary come from a training run (``trained_npz``) and stay FIXED;
    the gallery reseeds *scenes* (new shuffle + noise), so what you watch is the
    learned docking generalizing, not new physics each time."""

    def __init__(self, cfg: FoldConfig, seed: int, trained_npz: str | None = None) -> None:
        self.cfg = cfg
        self._base = seed
        self._gen = 0          # which fold in the gallery (bumps on convergence)
        self._t = 0            # total iterations
        self._since = 0        # iterations since the current fold started
        self._fold_step = 0.0
        self._partner = None   # ground-truth partner indices (trained mode)
        self._held = False     # settled/horizon-reached: hold until next_scene()
        self._trained = None
        if trained_npz is not None:
            z = np.load(Path(trained_npz))
            self._trained = {
                "w": FoldWeights(
                    W_c=z["W_c"], M=z["M"], W_v=z["W_v"], W1=z["W1"],
                    b1=z["b1"], W2=z["W2"], b2=z["b2"], P=z["P"],
                ),
                "e_types": z["e_types"],
                "vc": VocabConfig(
                    n_pairs=int(z["n_pairs"]), d=cfg.d,
                    noise_sigma=float(z["noise_sigma"]), init_scale=cfg.init_scale,
                ),
                "t_steps": int(z["t_steps"]),
            }
        self.w, self.x = self._instantiate()

    def _instantiate(self):
        """Fresh gallery entry (deterministic). Random mode: new weights + new
        tokens. Trained mode: fixed weights, new scene."""
        s = self._base if self._gen == 0 else (self._base * 10007 + self._gen)
        if self._trained is not None:
            tr = self._trained
            rng = np.random.default_rng([s, 20_000])
            types, partner, noise = sample_scene(tr["vc"], rng)
            self._partner = partner
            x = scene_embed(tr["e_types"], types, noise, tr["vc"].noise_sigma)
            return tr["w"], x
        w = FoldWeights.random(self.cfg, s)
        rng = np.random.default_rng([s, 10_000])  # decorrelate embeddings from weights
        x = rng.standard_normal((self.cfg.n_tokens, self.cfg.d)) * self.cfg.init_scale
        return w, x

    def step(self) -> None:
        if self._held:            # settled: hold the frame until next_scene()
            return
        x1, _, _ = block_step(self.x, self.w, self.cfg)
        self._fold_step = float(np.linalg.norm(x1 - self.x) / np.sqrt(self.x.size))
        self.x = x1
        self._t += 1
        self._since += 1
        # End-of-scene: instead of silently reseeding (which read as a sudden,
        # discontinuous jump), HOLD the settled scene. The next scene is gated
        # behind an explicit control (next_scene / the viewer's "New scene").
        # TRAINED mode: hold at 2× the trained horizon — past what deep
        # supervision covered, the weight-tied map drifts off the docked config,
        # so showing further would misrepresent what was learned.
        # RANDOM mode: hold once the fold has settled (PLAN.md D3).
        if self._trained is not None:
            if self._since >= 2 * self._trained["t_steps"]:
                self._held = True
        elif (
            self.cfg.reseed_on_converge
            and self._since >= self.cfg.min_iters_before_reseed
            and self._fold_step < self.cfg.converge_eps
        ):
            self._held = True

    def next_scene(self) -> None:
        """Advance the gallery to a fresh scene (explicit, user-gated) and
        release the hold so stepping resumes. Trained mode reseeds a new
        shuffle+noise scene; random mode a fresh random fold."""
        self._gen += 1
        self.w, self.x = self._instantiate()
        self._since = 0
        self._fold_step = 0.0
        self._held = False

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
        partner = None
        accuracy = None
        if self._partner is not None:
            partner = [int(p) for p in self._partner]
            accuracy = round(float((np.argmax(a, axis=1) == self._partner).mean()), 3)
        return {
            "status": status.value,
            "tick": self._t,
            "fold": self._gen,
            "fold_iter": self._since,
            "held": self._held,
            "n": self.cfg.n_tokens,
            "fold_step": round(self._fold_step, 5),
            "max_attn": round(float(off_diag.max()), 3),
            "tokens": tokens,
            "edges": edges,
            "partner": partner,      # trained mode: ground-truth docking targets
            "accuracy": accuracy,    # trained mode: fraction argmax-docked correctly
        }
