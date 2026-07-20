"""Boundaries + induced-fit packing (transformer-only).

Everything is driven by the GROUNDED overlap of the drawn contours (Parseval: the attention
dock score IS the contour overlap), so agents pack like puzzle pieces:

  * repel head  — attention gated by *direct* overlap ⟨C_i, C_j⟩ (shapes clashing / occupying the
    same space), with a 1/d² kernel (EM-like) → excluded volume / boundaries. Linear-attention
    aggregation of relative displacements (the one piece that is force-like; see dynamics_zoo.md).
  * attract head — softmax attention on *complementary* overlap ⟨C_i, C_j·M⟩ (lock-and-key) → agents
    pull toward neighbours they can interlock with.
  * induced-fit morph — the block updates the shape channels via the complementarity attention +
    MLP, so an agent deforms its contour to fit its binding partners.

Periodic (toroidal) domain → no walls, no corner-piling. Fixed-rule, transformer-only (attention +
MLP + LayerNorm), no energy ledger, no variable N.

    bazel run //projects/vivarium:pack -- --probe
"""

from __future__ import annotations

import argparse

import numpy as np

from aliveness import evaluate
from config import DEFAULTS, POS_DIM, VivariumConfig
from rng import base_rng, rng_for

_LN_EPS = 1e-5
_MLP_H = 2
_REPEL_EPS = 1e-2


def _ln(X):
    mu = X.mean(1, keepdims=True)
    var = X.var(1, keepdims=True)
    return (X - mu) / np.sqrt(var + _LN_EPS)


class PackEngine:
    def __init__(self, cfg, seed, ablate="none", repel=0.1, attract=0.35, skew=1.0, morph=0.5,
                 momentum=0.85):
        self.cfg = cfg
        self.seed = seed
        self.ablate = ablate
        self.repel = repel      # 1/d² excluded-volume strength (boundaries)
        self.attract = attract  # complementary-fit attraction (interlocking)
        self.skew = skew        # non-settling shape rotation
        self.morph = morph      # induced-fit morph gain
        self.momentum = momentum  # position inertia: keeps the packed lattice rearranging, not frozen
        self.vel = np.zeros((cfg.N, POS_DIM))
        self.L = 2.0 * cfg.pos_bound
        rng = base_rng(seed + 1)
        d, twoK, h = cfg.d, cfg.shape_dim, _MLP_H * (cfg.d - POS_DIM)
        self.tK = twoK
        signs = np.array([(-1.0) ** (k + 1) for k in range(cfg.n_harmonics) for _ in range(2)])
        self.M = np.diag(signs)
        zdim = d - POS_DIM
        self.W_v = rng.standard_normal((zdim, zdim)) / np.sqrt(zdim)
        self.W1 = rng.standard_normal((zdim, h)) / np.sqrt(zdim)
        self.b1 = np.zeros(h)
        self.W2 = rng.standard_normal((h, zdim)) / np.sqrt(h)
        self.b2 = np.zeros(zdim)
        Jr = rng.standard_normal((zdim, zdim)) / np.sqrt(zdim)
        self.J = Jr - Jr.T
        r = base_rng(seed)
        X = np.zeros((cfg.N, d))
        X[:, :POS_DIM] = r.uniform(-cfg.pos_bound, cfg.pos_bound, (cfg.N, POS_DIM))
        X[:, POS_DIM:] = r.standard_normal((cfg.N, zdim)) * 0.5
        self.X = X
        self.t = 0

    def _contour(self):
        return self.X[:, POS_DIM:POS_DIM + self.tK]  # grounded contour = shape channels

    def _periodic_delta(self):
        p = self.X[:, :POS_DIM]
        delta = p[:, None, :] - p[None, :, :]          # (N, N, 2) minimum-image on the torus
        delta = delta - self.L * np.round(delta / self.L)
        d2 = np.einsum("ijc,ijc->ij", delta, delta)
        return delta, d2

    def _neighbors(self, d2, k):
        return np.argsort(d2, axis=1, kind="stable")[:, :k]

    def fork(self):
        import copy
        return copy.deepcopy(self)

    def snapshot(self):
        pos = self.X[:, :POS_DIM]
        C = self._contour()
        tokens = [{"x": float(pos[i, 0]), "y": float(pos[i, 1]), "c": C[i].tolist()}
                  for i in range(self.cfg.N)]
        _, d2 = self._periodic_delta()
        idx = self._neighbors(d2, self.cfg.n_neighbors)
        edges = [[int(i), int(j)] for i in range(self.cfg.N) for j in idx[i] if int(j) != i]
        return {"status": "running", "tick": self.t, "n": self.cfg.N,
                "tokens": tokens, "edges": edges}

    def step(self):
        cfg = self.cfg
        C = self._contour()
        delta, d2 = self._periodic_delta()
        idx = self._neighbors(d2, cfg.n_neighbors)
        mask = np.zeros_like(d2, dtype=bool)
        np.put_along_axis(mask, idx, True, axis=1)
        np.fill_diagonal(mask, False)                  # neighbours, excluding self

        # grounded overlaps (Parseval)
        S_direct = (C @ C.T) / np.sqrt(self.tK)          # clash: same space, same orientation
        S_comp = (C @ (C @ self.M).T) / np.sqrt(self.tK)  # fit: bump-meets-pocket

        if self.ablate == "identity":
            mask = np.zeros_like(mask)                  # no neighbours → no forces (P6 control)

        # attract head: softmax on complementary fit − distance penalty
        score = np.where(mask, S_comp - cfg.dist_lambda * d2, -np.inf)
        m = np.max(score, axis=1, keepdims=True)
        m = np.where(np.isfinite(m), m, 0.0)
        A_fit = np.exp(score - m) * mask
        denom = A_fit.sum(1, keepdims=True)
        A_fit = np.where(denom > 0, A_fit / np.where(denom > 0, denom, 1.0), 0.0)
        attract = -np.einsum("ij,ijc->ic", A_fit, delta)  # toward complementary neighbours

        # repel head: 1/d² (EM-like), gated by direct clash, over neighbours
        clash = np.maximum(S_direct, 0.0) * mask
        wr = clash / (d2 * np.sqrt(d2) + _REPEL_EPS)      # |delta|/d³ ⇒ 1/d² force magnitude
        repel = np.einsum("ij,ijc->ic", wr, delta)        # away from clashing neighbours

        force = self.attract * attract + self.repel * repel
        self.vel = self.momentum * self.vel + force        # inertia → coherent, non-freezing motion
        p = self.X[:, :POS_DIM] + self.vel
        p = ((p + cfg.pos_bound) % self.L) - cfg.pos_bound  # wrap to the torus

        # induced-fit morph: block updates shape/hidden, coupled through the fit attention
        z = self.X[:, POS_DIM:]
        msg = A_fit @ (z @ self.W_v)
        spin = self.skew * (z @ self.J) if self.skew > 0 else 0.0
        z1 = _ln(z + self.morph * msg + spin)
        z2 = _ln(z1 + np.tanh(z1 @ self.W1 + self.b1) @ self.W2 + self.b2)

        self.X = np.concatenate([p, z2], axis=1)
        self.t += 1


def _cfg(**over):
    return VivariumConfig(**{**DEFAULTS, **over})


def probe(seed, ablate, repel, attract, skew, morph, momentum):
    e = PackEngine(_cfg(), seed, ablate=ablate, repel=repel, attract=attract, skew=skew,
                   morph=morph, momentum=momentum)
    print(" tick  alive  spread  motion  cohere  struct  deform  minsep")
    for _ in range(0, 2001, 400):
        r = evaluate(e, 40)
        # min pairwise separation: near 0 ⇒ clumping/overlap; larger ⇒ packed with spacing
        _, d2 = e._periodic_delta()
        np.fill_diagonal(d2, np.inf)
        minsep = float(np.sqrt(d2.min(1).mean()))
        print(f"{e.t:5d}  {r['aliveness']:.3f}  {r['spread']:.3f}  {r['motion']:.4f}   "
              f"{r['coherence']:.3f}   {r['structure']:.3f}   {r['deformation']:.3f}  {minsep:.3f}")
        for _ in range(400):
            e.step()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ablate", choices=["none", "identity"], default="none")
    p.add_argument("--repel", type=float, default=0.1)
    p.add_argument("--attract", type=float, default=0.35)
    p.add_argument("--skew", type=float, default=1.0)
    p.add_argument("--morph", type=float, default=0.5)
    p.add_argument("--mom", type=float, default=0.85)
    a = p.parse_args(argv)
    probe(a.seed, a.ablate, a.repel, a.attract, a.skew, a.morph, a.mom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
