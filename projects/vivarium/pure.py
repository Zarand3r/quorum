"""Experiment: can the TRANSFORMER do everything — move positions *and* resist collapse —
with NO bolt-on force law?

Position is just the first two channels of the embedding, and the whole embedding is updated
by one transformer block (local grounded attention + MLP + LayerNorm), optionally with a
non-gradient skew term and a non-reciprocal attention component. So "moving" and "morphing" are
the *same* operation — the block's output. We then search weights (seeds) + anti-collapse knobs
against measured aliveness and *measured* P6 (identity ablation), since here P6 is NOT
guaranteed by construction (the MLP is a per-agent engine).

    bazel run //projects/vivarium:pure -- --search      # sweep knobs × seeds
    bazel run //projects/vivarium:pure -- --probe        # trace one config

The whole point of the force-law substrate was that a plain transformer moving positions either
COLLAPSES (attention is a contraction → rank collapse) or breaks P6 (the MLP moves each agent
independently). This file tries to beat both from *inside* the transformer.
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass, replace

import numpy as np

from aliveness import evaluate
from config import DEFAULTS, POS_DIM, VivariumConfig
from rng import base_rng, rng_for

_LN_EPS = 1e-5
_MLP_H = 2


@dataclass(frozen=True)
class PW:
    W_c: np.ndarray   # (d, 2K) selection → contour = query (grounding)
    M: np.ndarray     # (2K, 2K) π-rotation complementarity
    W_v: np.ndarray   # (d, d) value
    W1: np.ndarray
    b1: np.ndarray
    W2: np.ndarray
    b2: np.ndarray
    J: np.ndarray     # (d, d) skew — non-gradient drive (no fixed point)

    def names(self):
        return ("W_c", "M", "W_v", "W1", "b1", "W2", "b2", "J")


def make(cfg: VivariumConfig, seed: int) -> PW:
    rng = base_rng(seed + 1)
    d, twoK, h = cfg.d, cfg.shape_dim, _MLP_H * cfg.d
    W_c = np.zeros((d, twoK))
    W_c[POS_DIM : POS_DIM + twoK, :] = np.eye(twoK)  # shape channels of X
    signs = np.array([(-1.0) ** (k + 1) for k in range(cfg.n_harmonics) for _ in range(2)])
    M = np.diag(signs)
    W_v = rng.standard_normal((d, d)) / np.sqrt(d)
    W1 = rng.standard_normal((d, h)) / np.sqrt(d)
    b1 = np.zeros(h)
    W2 = rng.standard_normal((h, d)) / np.sqrt(h)
    b2 = np.zeros(d)
    Jr = rng.standard_normal((d, d)) / np.sqrt(d)
    J = Jr - Jr.T
    return PW(W_c=W_c, M=M, W_v=W_v, W1=W1, b1=b1, W2=W2, b2=b2, J=J)


def _ln(X: np.ndarray) -> np.ndarray:
    mu = X.mean(1, keepdims=True)
    var = X.var(1, keepdims=True)
    return (X - mu) / np.sqrt(var + _LN_EPS)


def _neighbors(pos, k):
    diff = pos[:, None, :] - pos[None, :, :]
    d2 = np.einsum("ijc,ijc->ij", diff, diff)
    return np.argsort(d2, axis=1, kind="stable")[:, :k]


def _attention(X, w, cfg, nonrecip):
    pos = X[:, :POS_DIM]
    C = X @ w.W_c
    dock = (C @ (C @ w.M).T) / np.sqrt(cfg.shape_dim)
    diff = pos[:, None, :] - pos[None, :, :]
    d2 = np.einsum("ijc,ijc->ij", diff, diff)
    score = dock - cfg.dist_lambda * d2
    idx = _neighbors(pos, cfg.n_neighbors)
    mask = np.zeros_like(score, dtype=bool)
    np.put_along_axis(mask, idx, True, axis=1)
    score = np.where(mask, score, -np.inf)
    m = score.max(1, keepdims=True)
    e = np.exp(score - m)
    A = e / e.sum(1, keepdims=True)
    if nonrecip > 0.0:
        A = A + nonrecip * (A - A.T)  # inject the antisymmetric (circulating) part
    return A


class PureEngine:
    """Transformer moves AND morphs everything. cfg carries: dist_lambda, morph_spin (skew),
    n_neighbors. `nonrecip` injects non-reciprocal attention; `ln_pos` LayerNorms position too."""

    def __init__(self, cfg, seed, ablate="none", nonrecip=0.0, ln_pos=True, scale=1.0,
                 spin_pos=True, noise=0.0):
        self.cfg = cfg
        self.seed = seed
        self.ablate = ablate
        self.nonrecip = nonrecip
        self.ln_pos = ln_pos
        self.scale = scale  # residual gain on (message + skew) — tames over-energetic seeds
        self.spin_pos = spin_pos  # if False, the skew drives only the shape (position moves by
        #                           interaction only) → less global rotation, more complex motion
        self.noise = noise  # seeded per-step Gaussian noise (Langevin) → wandering / state-switching
        self.spin = cfg.morph_spin  # skew-rotation gain (mutable live knob)
        self.w = make(cfg, seed)
        rng = base_rng(seed)
        X = rng.standard_normal((cfg.N, cfg.d)) * 0.5
        X[:, :POS_DIM] *= 2.0
        self.X = X
        self.t = 0

    def _ablate(self, A):
        if self.ablate == "identity":
            return np.eye(A.shape[0])
        if self.ablate == "shuffle":
            perm = rng_for(self.seed, self.t).permutation(A.shape[0])
            return A[:, perm]
        return A

    def step(self):
        A = self._ablate(_attention(self.X, self.w, self.cfg, self.nonrecip))
        msg = A @ (self.X @ self.w.W_v)
        spin = 0.0
        if self.spin > 0:
            if self.spin_pos:
                spin = self.spin * (self.X @ self.w.J)  # rotates everything (global spin)
            else:
                # skew only the non-position channels → shape morphs, position doesn't globally rotate.
                spin = np.zeros_like(self.X)
                spin[:, POS_DIM:] = self.spin * (
                    self.X[:, POS_DIM:] @ self.w.J[POS_DIM:, POS_DIM:]
                )
        X1 = self.X + self.scale * (msg + spin)
        if self.noise > 0.0:
            # seeded (reproducible) Gaussian kick — a Langevin drive: breaks symmetry, lets the
            # colony escape metastable states and wander/switch instead of settling into one swirl.
            X1 = X1 + self.noise * rng_for(self.seed, self.t).standard_normal(self.X.shape)
        X1 = self._norm(X1)
        X2 = self._norm(X1 + np.tanh(X1 @ self.w.W1 + self.w.b1) @ self.w.W2 + self.w.b2)
        self.X = X2
        self.t += 1

    def fork(self):
        import copy
        return copy.deepcopy(self)

    def snapshot(self):
        from block import neighbor_indices
        pos = self.X[:, :POS_DIM]
        C = self.X @ self.w.W_c
        tokens = [
            {"x": float(pos[i, 0]), "y": float(pos[i, 1]), "c": C[i].tolist()}
            for i in range(self.cfg.N)
        ]
        idx = neighbor_indices(pos, self.cfg.n_neighbors)
        edges = [[int(i), int(j)] for i in range(self.cfg.N) for j in idx[i] if int(j) != i]
        return {"status": "running", "tick": self.t, "n": self.cfg.N,
                "tokens": tokens, "edges": edges}

    def _norm(self, X):
        if self.ln_pos:
            return _ln(X)
        # LayerNorm the non-position channels only; keep raw position (clipped) so it can spread.
        z = _ln(X[:, POS_DIM:])
        p = np.clip(X[:, :POS_DIM], -self.cfg.pos_bound, self.cfg.pos_bound)
        return np.concatenate([p, z], axis=1)


def _cfg(**over):
    return VivariumConfig(**{**DEFAULTS, **over})


def _alive(cfg, seed, ablate, nonrecip, ln_pos, scale, ticks, window):
    e = PureEngine(cfg, seed, ablate=ablate, nonrecip=nonrecip, ln_pos=ln_pos, scale=scale)
    for _ in range(ticks):
        e.step()
    return evaluate(e, window)


def search():
    seeds = (0, 1, 2, 3)
    grid = {
        "dist_lambda": [0.5, 1.5],
        "morph_spin": [0.3],
        "nonrecip": [1.0, 2.0],
        "ln_pos": [False],
        "scale": [0.3, 0.5, 0.7],
    }
    keys = list(grid)
    rows = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        o = dict(zip(keys, combo))
        cfg = _cfg(dist_lambda=o["dist_lambda"], morph_spin=o["morph_spin"])
        none, ident, defo = [], [], []
        for s in seeds:
            rn = _alive(cfg, s, "none", o["nonrecip"], o["ln_pos"], o["scale"], 1500, 40)
            ri = _alive(cfg, s, "identity", o["nonrecip"], o["ln_pos"], o["scale"], 1500, 40)
            none.append(rn["aliveness"]); ident.append(ri["aliveness"]); defo.append(rn["deformation"])
        rows.append((float(np.mean(none)), float(np.mean(ident)), float(np.mean(defo)), o))
    rows.sort(reverse=True, key=lambda x: x[0])
    print("pure-transformer search (T=1500, seeds 0-2). aliveness | identity | P6margin | deform | knobs")
    for al, idn, df, o in rows[:12]:
        knobs = " ".join(f"{k}={v}" for k, v in o.items())
        print(f"  alive={al:.3f} | identity={idn:.3f} | P6={al-idn:+.3f} | deform={df:.3f} | {knobs}")


def probe(nonrecip, ln_pos, spin, lam, seed, ablate="none", scale=0.5, spin_pos=True, noise=0.0):
    cfg = _cfg(dist_lambda=lam, morph_spin=spin)
    e = PureEngine(cfg, seed, ablate=ablate, nonrecip=nonrecip, ln_pos=ln_pos, scale=scale,
                   spin_pos=spin_pos, noise=noise)
    print(" tick  alive  spread  motion  cohere  struct  deform")
    for k in range(0, 3001, 500):
        r = evaluate(e, 40)
        print(f"{e.t:5d}  {r['aliveness']:.3f}  {r['spread']:.3f}  {r['motion']:.4f}   "
              f"{r['coherence']:.3f}   {r['structure']:.3f}   {r['deformation']:.3f}")
        for _ in range(500):
            e.step()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--search", action="store_true")
    p.add_argument("--probe", action="store_true")
    p.add_argument("--nonrecip", type=float, default=1.0)
    p.add_argument("--ln_pos", action="store_true")
    p.add_argument("--spin", type=float, default=0.3)
    p.add_argument("--lam", type=float, default=1.5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ablate", choices=["none", "identity", "shuffle"], default="none")
    p.add_argument("--scale", type=float, default=0.5)
    p.add_argument("--flat-pos", dest="spin_pos", action="store_false",
                   help="skew only the shape (position moves by interaction only → more complex)")
    p.add_argument("--noise", type=float, default=0.0, help="seeded Langevin noise sigma")
    a = p.parse_args(argv)
    if a.search:
        search()
    else:
        probe(a.nonrecip, a.ln_pos, a.spin, a.lam, a.seed, a.ablate, a.scale, a.spin_pos, a.noise)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
