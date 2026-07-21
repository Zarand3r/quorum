"""Boundaries + induced-fit packing (transformer-only).

Everything is driven by the GROUNDED overlap of the drawn contours (Parseval: the attention
dock score IS the contour overlap), so agents pack like puzzle pieces:

  * repel head  — a bounded REPULSIVE ATTENTION (softmax over direct-clash ⟨C_i,C_j⟩ − λ·d²):
    attend to close/clashing neighbours, move away from that weighted set. Row-stochastic ⇒
    bounded (soft excluded volume), a genuine attention op — NOT a divergent 1/d² kernel
    (strict transformer-only, see design/HARD_REQUIREMENT.md).
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
_DIR_EPS = 1e-4  # softening for the unit-direction normalisation (not a force kernel)


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

        # repel head: bounded repulsive ATTENTION (transformer-only, HARD_REQUIREMENT). Attend to
        # close, clashing neighbours (softmax over clash − λ·d²), then move AWAY from that
        # attention-weighted set: (I − A_repel)·p in relative terms = Σ_j A_repel_ij·delta_ij.
        # A_repel is row-stochastic → bounded (soft excluded volume), NOT a divergent 1/d² kernel.
        rscore = np.where(mask, S_direct - cfg.dist_lambda * d2, -np.inf)
        rm = np.max(rscore, axis=1, keepdims=True)
        rm = np.where(np.isfinite(rm), rm, 0.0)
        A_repel = np.exp(rscore - rm) * mask
        rdenom = A_repel.sum(1, keepdims=True)
        A_repel = np.where(rdenom > 0, A_repel / np.where(rdenom > 0, rdenom, 1.0), 0.0)
        # aggregate the UNIT direction away (the value is the relative *direction*), so the push
        # stays finite as neighbours touch (delta→0) — otherwise soft repel vanishes at contact and
        # agents overlap. Softmax weight (bounded) sets how much; unit vector sets which way.
        dirn = delta / np.sqrt(d2[..., None] + _DIR_EPS)
        repel = np.einsum("ij,ijc->ic", A_repel, dirn)    # away from close/clashing neighbours

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


def measure_gas_or_droplet(seed):
    from metrics_pack import measure
    print("=== M0: is the packing engine a DROPLET (matter) or a GAS? ===")
    for scale, lab in ((1.0, "1x box"), (2.0, "2x box")):
        cfg = _cfg(pos_bound=DEFAULTS["pos_bound"] * scale)
        e = PackEngine(cfg, seed)
        for _ in range(600):
            e.step()
        m = measure(e.X[:, :POS_DIM], e.L, radius=1.0)
        print(f"{lab:8s} occupancy={m['occupancy']:.2f}  largest_cluster={m['largest_frac']:.2f}  "
              f"n_clusters={m['n_clusters']:2d}  Rg={m['rg']:.2f}  Rg/box={m['rg_over_box']:.2f}")
    print("GAS: occupancy high, fragments, Rg/box grows. MATTER: occupancy<1, one cluster, Rg box-independent.")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ablate", choices=["none", "identity"], default="none")
    p.add_argument("--repel", type=float, default=0.1)
    p.add_argument("--attract", type=float, default=0.35)
    p.add_argument("--skew", type=float, default=1.0)
    p.add_argument("--morph", type=float, default=0.5)
    p.add_argument("--mom", type=float, default=0.85)
    a = p.parse_args(argv)
    if a.measure:
        measure_gas_or_droplet(a.seed)
    else:
        probe(a.seed, a.ablate, a.repel, a.attract, a.skew, a.morph, a.mom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
