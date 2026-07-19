"""Reaction–diffusion morphogenesis: the transformer block AS an RD operator.

The thesis of thermolife made literal. One transformer block, applied to an
embedding field, is one step of a reaction–diffusion PDE:

    ∂x/∂t  =  D · ∇²x            +   R · f(x)
              └─ diffusion ──┘        └ reaction ┘
              ATTENTION               MLP

  • **Diffusion = attention.** A row-stochastic attention matrix A makes each
    token relax toward an attention-weighted average of the others:
    L_i = (A·(x·W_v))_i − x_i is a graph Laplacian (neighbour-mean minus self).
    Crucially the attention is LOCAL (distance-penalized, fold/hk.py): global
    softmax = infinite diffusion rate = instant homogenization (rank collapse);
    finite-range diffusion is what lets structure survive — Turing's condition.
  • **Reaction = MLP + oscillatory core.** The pointwise block f(x) =
    W₂·relu(W₁x+b₁)+b₂ is the local nonlinear kinetics. A purely dissipative
    reaction (random MLP) has a single fixed point, so the field would collapse to
    consensus — thermolife's default fate. Sustained RD patterns require
    OSCILLATORY kinetics (the Belousov–Zhabotinsky reaction, the λ–ω model): so
    the reaction carries a conservative rotation Ω·(x·J), J skew-symmetric, making
    each token a limit-cycle oscillator. Local diffusion then couples the
    oscillators into travelling/spiral morphing that never settles.
  • **Boundedness = LayerNorm.** Keeps the field on a shell so the reaction can't
    blow up; morphing is the direction changing on that shell.

The field GROWS from a single seed token by periodic division (child = parent +
jitter), so the animation is morphogenesis: one shape appears, moves and morphs
continuously, divides, and the daughters differentiate under the same chemistry.
Each token is drawn as its grounded contour blob C = x·W_c (the drawn shape IS
the attention query/key), so you literally watch the embeddings as shapes.

θ is FIXED random (S0): this is the untrained substrate's intrinsic dynamics, a
gallery like the fold — not a trained objective. Reuses FoldWeights and the fold
snapshot schema, so the existing blob viewer (sim/viewer.html) renders it as-is.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from fold.config import FoldConfig, load_fold_config
from fold.hk import distance_penalized_scores
from fold.interface import contour_coeffs, contour_polylines
from fold.transformer import _layernorm, _softmax_rows
from fold.weights import FoldWeights


@dataclass(frozen=True)
class MorphParams:
    """Reaction–diffusion hyperparameters (the fold/contour knobs live in FoldConfig)."""
    dt: float           # integration step — small ⇒ continuous morph (no jumps)
    diffusion: float    # D — attention (graph-Laplacian) strength
    reaction: float     # R — MLP kinetics strength
    omega: float        # Ω — oscillatory (skew) core strength; the anti-collapse floor
    lam: float          # locality λ in s = dock − λ‖Δx‖² (0 = global ⇒ homogenizes)
    split_every: int    # ticks between cell divisions (growth cadence)
    n_max: int          # population cap
    jitter: float       # embedding noise added to a daughter at division
    converge_eps: float # per-step field motion below this (at n_max) ⇒ settled
    min_iters: int      # never hold before this many ticks (let it grow + morph)


_RD_DEFAULTS: dict = {
    "dt": 0.09,
    "diffusion": 0.12,
    "reaction": 0.4,
    "omega": 0.9,
    "lam": 1.8,
    "split_every": 14,
    "n_max": 48,
    "jitter": 0.6,
    "converge_eps": 5e-4,
    "min_iters": 220,
}


def load_morph(path: str | Path) -> tuple[FoldConfig, MorphParams]:
    """Load a FoldConfig (fold/contour knobs) + MorphParams (RD knobs) from one YAML.

    ``load_fold_config`` only reads the fold keys, so RD keys coexist in the same
    file. Both halves fall back to defaults, so a minimal morph.yaml still loads."""
    cfg = load_fold_config(path)
    raw = yaml.safe_load(Path(path).read_text()) or {}
    d = {**_RD_DEFAULTS, **{k: raw[k] for k in _RD_DEFAULTS if k in raw}}
    p = MorphParams(
        dt=float(d["dt"]), diffusion=float(d["diffusion"]), reaction=float(d["reaction"]),
        omega=float(d["omega"]), lam=float(d["lam"]), split_every=int(d["split_every"]),
        n_max=int(d["n_max"]), jitter=float(d["jitter"]), converge_eps=float(d["converge_eps"]),
        min_iters=int(d["min_iters"]),
    )
    if p.n_max < 1:
        raise ValueError("n_max must be ≥ 1")
    if p.split_every < 1:
        raise ValueError("split_every must be ≥ 1")
    return cfg, p


def skew_matrix(seed: int, d: int) -> np.ndarray:
    """A fixed skew-symmetric J = A − Aᵀ. x·J is a conservative rotation (energy-
    preserving), giving the reaction a limit-cycle core so the field never dies to
    a fixed point — the oscillatory kinetics that sustained RD media require."""
    a = np.random.default_rng([seed, 55]).standard_normal((d, d))
    return a - a.T


def rd_step(
    x: np.ndarray, w: FoldWeights, j_skew: np.ndarray, cfg: FoldConfig, p: MorphParams
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One reaction–diffusion transformer step. Returns (new_x, C=query, A=attention).

    x_{t+1} = LayerNorm( x + dt·[ D·(A·x − x) + R·MLP(x) + Ω·(x·J) ] )
              diffusion = A·x − x (graph Laplacian);  reaction = MLP + Ω·rotation.

    Synchronous (reads x, writes a fresh x — J4) and fully vectorized (J3)."""
    c = contour_coeffs(x, w)                                     # grounded query
    if x.shape[0] == 1:
        a = np.ones((1, 1))                                     # a lone seed only sees itself
    else:
        a = _softmax_rows(distance_penalized_scores(c, x, w.M, p.lam))   # LOCAL diffusion
    diffusion = a @ x - x                                      # graph Laplacian (neighbour-mean − self)
    reaction = np.maximum(0.0, x @ w.W1 + w.b1) @ w.W2 + w.b2  # pointwise MLP kinetics
    rotation = x @ j_skew                                      # conservative oscillatory core
    x1 = x + p.dt * (p.diffusion * diffusion + p.reaction * reaction + p.omega * rotation)
    return _layernorm(x1), c, a


class MorphEngine:
    """Grows an embedding field from one seed and evolves it by reaction–diffusion.
    Implements the engine protocol (step/tick/residual/snapshot/state_hash/next_scene)
    so the existing SimController + blob viewer drive it unchanged."""

    def __init__(self, cfg: FoldConfig, seed: int, params: MorphParams | None = None) -> None:
        self.cfg = cfg
        self.p = params if params is not None else load_morph(
            Path(__file__).resolve().parent.parent / "configs" / "morph.yaml")[1]
        self._base = seed
        self._gen = 0
        self._t = 0
        self._since = 0
        self._fold_step = 0.0
        self._held = False
        self.w, self.j, self.x = self._instantiate()
        self._a = np.ones((1, 1))

    def _instantiate(self):
        """Fresh gallery entry (deterministic): new random chemistry θ + skew core +
        a single seed token on the LayerNorm shell."""
        s = self._base if self._gen == 0 else (self._base * 10007 + self._gen)
        w = FoldWeights.random(self.cfg, s)
        j = skew_matrix(s, self.cfg.d)
        rng = np.random.default_rng([s, 30_000])
        x = _layernorm(rng.standard_normal((1, self.cfg.d)) * self.cfg.init_scale)
        return w, j, x

    def _maybe_divide(self, rng: np.random.Generator) -> None:
        """Cell division: each token spawns a jittered daughter, capped at n_max.
        1 → 2 → 4 → … → n_max — morphogenesis from a single seed."""
        n = self.x.shape[0]
        if n >= self.p.n_max:
            return
        room = self.p.n_max - n
        parents = self.x[:room]
        children = parents + self.p.jitter * rng.standard_normal(parents.shape)
        self.x = _layernorm(np.concatenate([self.x, children], axis=0))

    def step(self) -> None:
        if self._held:
            return
        x1, _, a = rd_step(self.x, self.w, self.j, self.cfg, self.p)
        self._fold_step = float(np.linalg.norm(x1 - self.x) / np.sqrt(x1.size))
        self.x, self._a = x1, a
        self._t += 1
        self._since += 1
        if self._t % self.p.split_every == 0:
            self._maybe_divide(np.random.default_rng([self._base, self._t]))
        # hold once the field has grown to cap AND settled — never a silent reseed
        settled = (self.x.shape[0] >= self.p.n_max
                   and self._since >= self.p.min_iters
                   and self._fold_step < self.p.converge_eps)
        if settled:
            self._held = True

    def next_scene(self) -> None:
        self._gen += 1
        self.w, self.j, self.x = self._instantiate()
        self._a = np.ones((1, 1))
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
        pos = self.x @ self.w.P
        outline = pos[:, None, :] + contour_polylines(c, self.cfg)
        n = self.x.shape[0]
        tokens = [
            {"pos": [round(float(pos[i, 0]), 3), round(float(pos[i, 1]), 3)],
             "contour": np.round(outline[i], 3).tolist()}
            for i in range(n)
        ]
        edges = []
        max_attn = 0.0
        if n > 1:
            off = self._a.copy()
            np.fill_diagonal(off, 0.0)
            max_attn = float(off.max())
            ii, jj = np.where(off >= self.cfg.edge_threshold)
            order = np.argsort(-off[ii, jj])[:300]              # cap payload
            edges = [[int(ii[k]), int(jj[k]), round(float(off[ii[k], jj[k]]), 3)] for k in order]
        return {
            "status": status.value,
            "tick": self._t,
            "fold": self._gen,
            "fold_iter": self._since,
            "held": self._held,
            "n": n,
            "fold_step": round(self._fold_step, 5),
            "max_attn": round(max_attn, 3),
            "tokens": tokens,
            "edges": edges,
            "partner": None,          # no docking ground-truth in RD mode
            "accuracy": None,
        }
