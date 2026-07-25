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
_THERMAL = 0.15  # Langevin kick per unit temperature (kT → Brownian displacement)


def _ln(X):
    mu = X.mean(1, keepdims=True)
    var = X.var(1, keepdims=True)
    return (X - mu) / np.sqrt(var + _LN_EPS)


class PackEngine:
    def __init__(self, cfg, seed, ablate="none", repel=0.15, attract=0.45, skew=1.2, morph=0.7,
                 momentum=0.85, speed=1.5, maxvel=0.25, cohesion=0.08, attn_sink=0.0):
        self.cfg = cfg
        self.seed = seed
        self.ablate = ablate
        self.pd = cfg.pos_dim   # 2 = flat dish, 3 = volumetric dish (all geometry below is N-D)
        # PER-FORCE decay range (NULL attention sink; higher = faster decay = shorter range). Real
        # forces have very different ranges, so each head gets its OWN sink: Pauli repulsion is the
        # shortest-ranged, van der Waals short, electrostatics the longest. Default = the shared
        # attn_sink (0 → plain softmax = the previous engine exactly, base case preserved).
        self.sink_repel = attn_sink       # Pauli exclusion  — shortest range (decays fastest)
        self.sink_attract = attn_sink     # van der Waals    — short range
        self.sink_cohesion = attn_sink    # cohesion shortcut (surface-tension; being deprecated)
        self.repel = repel      # bounded repulsive-attention strength (soft excluded volume)
        self.attract = attract  # complementary-fit attraction (interlocking)
        self.cohesion = cohesion  # surface tension: broad attention → pull toward neighbourhood
        #                           centroid; merges fragments into ONE droplet (M1). 0 = off.
        self.skew = skew        # non-settling shape rotation
        self.morph = morph      # induced-fit FLEXIBILITY: how strongly a token reshapes to fit partners
        self.rigidity = 0.0     # ELASTIC STIFFNESS: restoring pull of the contour toward its ROUND rest
        #   shape each step (C_rest=0). 0 = no restoring (base case); 1 = snaps rigid/round. The true
        #   rigidity ↔ flexibility (morph) tension: morph grows prongs, rigidity relaxes them back.
        self.repel_contact = 0.0  # if >0, repel is a SYMMETRIC overlap force: it acts ONLY when two
        #   agents interpenetrate (d < repel_contact), ∝ overlap depth, zero otherwise (real excluded
        #   volume). Being symmetric (F_ij=−F_ji), it also CONSERVES momentum. 0 → old softmax repel.
        self.conservative = False  # if True, attract & polarity use SYMMETRIC bounded kernels (F_ij=−F_ji)
        #   instead of row-normalised softmax → every force is a gradient of an energy, so the system
        #   RELAXES to a free-energy minimum and STRUCTURES EMERGE. False → old (non-conservative) heads.
        self.momentum = momentum  # position inertia (lower = less zippy; steady speed ≈ force/(1−mom))
        self.speed = speed      # dt-like multiplier on per-step displacement (slow it down to watch)
        self.maxvel = maxvel    # cap on per-step displacement — prevents agents zipping/overshooting
        self.cohere_k = min(24, cfg.N - 1)  # cohesion neighbourhood (broader than interaction k)
        self.cohere_lambda = 0.08           # broad distance kernel (long reach → crosses gaps)
        self.edge_radius = 0.6              # render: draw an edge only between agents this close
        #                                    (small → only touching pairs, not a dense mesh)
        self.selectivity = 0.0             # softmax τ (guarded to 1e-2). NOT thermodynamic temperature:
        #   low = sharp near-argmax → discrete lock-and-key bonds; high = uniform mean-field →
        #   consensus/synchrony/collapse. This is a selectivity dial, not kT (see self.temperature).
        self.temperature = 0.0             # REAL temperature = thermal (Langevin) noise amplitude:
        #   higher → more random Brownian jitter → more DISORDER (melts structure), as kT should. 0=off.
        self.vel = np.zeros((cfg.N, self.pd))
        self.L = 2.0 * cfg.pos_bound
        rng = base_rng(seed + 1)
        d, twoK, h = cfg.d, cfg.shape_dim, _MLP_H * (cfg.d - self.pd)
        self.tK = twoK
        # complementarity mirror: alternate the sign per harmonic order (bump ↔ pocket). 2-D has 2
        # coefficients per order k; 3-D has (2l+1) per order l — same rule, one dimension up.
        if self.pd == 2:
            signs = [(-1.0) ** (k + 1) for k in range(cfg.n_harmonics) for _ in range(2)]
        else:
            signs = [(-1.0) ** l for l in range(1, cfg.n_harmonics + 1) for _ in range(2 * l + 1)]
        self.M = np.diag(np.array(signs))
        # k=0 RADIUS channel: the token's physical SIZE (→ vdW contact area / polarizability), held in
        # the first hidden channel rather than inside the contour vector so the other engines, which
        # assume shape_dim = 2K, are untouched. k≥1 (the contour) stays the shape DEVIATION → charge.
        self.rad_idx = self.pd + cfg.shape_dim
        zdim = d - self.pd
        self.W_v = rng.standard_normal((zdim, zdim)) / np.sqrt(zdim)
        self.W1 = rng.standard_normal((zdim, h)) / np.sqrt(zdim)
        self.b1 = np.zeros(h)
        self.W2 = rng.standard_normal((h, zdim)) / np.sqrt(h)
        self.b2 = np.zeros(zdim)
        Jr = rng.standard_normal((zdim, zdim)) / np.sqrt(zdim)
        self.J = Jr - Jr.T
        # --- plasticity: fast weights = Hebbian linear-attention memory (weights that learn while
        #     alive). W_v/W1/W2/M/J above are the FIXED "slow" weights (the physics/laws). W_fast is
        #     a plastic (z×z) memory that accumulates Hebbian outer products of activity each tick
        #     (= a linear-attention write) with decay (homeostasis), and is read to modulate the
        #     message. Slow weights = fixed laws; fast weights = plastic synapses. Default off. ---
        self.W_k = rng.standard_normal((zdim, zdim)) / np.sqrt(zdim)  # key projection (fixed)
        self.W_val = rng.standard_normal((zdim, zdim)) / np.sqrt(zdim)  # value projection (fixed)
        self.W_fast = np.zeros((zdim, zdim))  # the plastic memory — starts empty, learns while alive
        self.plasticity = 0.0    # read gain (0 = off → identical to the fixed-rule sim)
        self.plast_decay = 0.98  # γ: forgetting / homeostasis (gated linear attention)
        self.plast_lr = 0.05     # η: Hebbian write rate
        r = base_rng(seed)
        X = np.zeros((cfg.N, d))
        X[:, :self.pd] = r.uniform(-cfg.pos_bound, cfg.pos_bound, (cfg.N, self.pd))
        X[:, self.pd:] = r.standard_normal((cfg.N, zdim)) * 0.5
        self.X = X
        self.t = 0

    def _contour(self):
        return self.X[:, self.pd:self.pd + self.tK]  # grounded contour = shape channels

    def _attn(self, score, mask, sink):
        """Bounded attention weights with a per-force NULL sink. score is (N,N) with −inf off-mask.
        denom = Σ_j exp(score−m) + sink·exp(−m): when a row's best neighbour is far/weak, the sink
        dominates and the weights → 0, so the force DECAYS with distance. HIGHER sink = FASTER decay =
        SHORTER range. sink=0 → plain row-stochastic softmax (identical to the previous engine)."""
        m = np.max(score, axis=1, keepdims=True)
        m = np.where(np.isfinite(m), m, 0.0)
        e = np.exp(score - m) * mask
        denom = e.sum(1, keepdims=True) + sink * np.exp(-m)
        return np.where(denom > 0, e / np.where(denom > 0, denom, 1.0), 0.0)

    def _periodic_delta(self):
        p = self.X[:, :self.pd]
        delta = p[:, None, :] - p[None, :, :]          # (N, N, 2) minimum-image on the torus
        delta = delta - self.L * np.round(delta / self.L)
        d2 = np.einsum("ijc,ijc->ij", delta, delta)
        return delta, d2

    def _neighbors(self, d2, k):
        return np.argsort(d2, axis=1, kind="stable")[:, :k]

    def fork(self):
        import copy
        return copy.deepcopy(self)

    def _binding_edges(self):
        """The REAL interaction the transformer computes: each agent's strongest complementary-fit
        attention (A_fit) partner, with the attention weight. This is the honest 'who is binding to
        whom' graph — not a proximity heuristic. Returns [[i, j, weight], ...] for meaningful bonds."""
        C = self._contour()
        delta, d2 = self._periodic_delta()
        idx = self._neighbors(d2, self.cfg.n_neighbors)
        mask = np.zeros_like(d2, dtype=bool)
        np.put_along_axis(mask, idx, True, axis=1)
        np.fill_diagonal(mask, False)
        S_comp = (C @ (C @ self.M).T) / np.sqrt(self.tK)
        tau = max(1e-2, self.selectivity)
        score = np.where(mask, (S_comp - self.cfg.dist_lambda * d2) / tau, -np.inf)
        m = np.max(score, axis=1, keepdims=True)
        m = np.where(np.isfinite(m), m, 0.0)
        A = np.exp(score - m) * mask
        den = A.sum(1, keepdims=True)
        A = np.where(den > 0, A / np.where(den > 0, den, 1.0), 0.0)
        top = np.argmax(A, axis=1)
        edges = []
        for i in range(self.cfg.N):
            w = float(A[i, top[i]])
            if w > 0.25:                     # only the meaningful bonds
                edges.append([int(i), int(top[i]), round(w, 2)])
        return edges

    def snapshot(self):
        pos = self.X[:, :self.pd]
        C = self._contour()
        # in 3-D also ship z so the viewer can render DEPTH (near = bigger/brighter). The dish is
        # simulated volumetrically and drawn as a projection; z is ignored by the 2-D viewer path.
        if self.pd == 3:
            tokens = [{"x": float(pos[i, 0]), "y": float(pos[i, 1]), "z": float(pos[i, 2]),
                       "c": C[i].tolist()} for i in range(self.cfg.N)]
        else:
            tokens = [{"x": float(pos[i, 0]), "y": float(pos[i, 1]), "c": C[i].tolist()}
                      for i in range(self.cfg.N)]
        return {"status": "running", "tick": self.t, "n": self.cfg.N,
                "tokens": tokens, "edges": self._binding_edges(),
                "dims": {"d": self.cfg.d, "pos": self.pd, "shape": self.cfg.shape_dim,
                         "hidden": self.cfg.hidden_dim, "z": self.cfg.z_dim,
                         "h": _MLP_H * self.cfg.z_dim, "N": self.cfg.N,
                         "k": self.cfg.n_neighbors}}

    def step(self):
        cfg = self.cfg
        tau = max(1e-2, self.selectivity)    # softmax selectivity τ (NOT kT — see self.temperature)
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

        dist = np.sqrt(d2 + _DIR_EPS)
        dirn = delta / dist[..., None]                    # unit direction i away from j

        # attract head. A_fit (softmax over complementary fit) always drives the induced-fit MORPH.
        # The attractive FORCE is either the CONSERVATIVE van der Waals kernel (symmetric ⇒ relaxes to
        # an energy minimum) or the old non-conservative −Σ A_fit·Δp (centroid pull).
        score = np.where(mask, (S_comp - cfg.dist_lambda * d2) / tau, -np.inf)
        A_fit = self._attn(score, mask, self.sink_attract)
        if self.conservative:
            # g_ij = sigmoid(S_comp/τ)·exp(−λ_a·d²): symmetric (S_comp, d symmetric), bounded, decaying
            # (a soft vdW well). force = −Σ_j g·dirn = pull toward j; F_ij=−F_ji ⇒ conservative. All
            # pairs (NOT the asymmetric k-NN mask), diagonal zeroed.
            # van der WAALS = London dispersion: proportional to CONTACT AREA / polarizability (the
            # k=0 radius channel) and INDEPENDENT OF CHARGE — which is exactly why neutral alkanes and
            # oils cohere. The old sigmoid(S_comp) read complementary FIT (lock-and-key): a specific
            # binding term, not dispersion, and sigmoid(0)=0.5 made featureless tokens sticky. Bounded
            # (tanh), symmetric, decaying ⇒ still conservative and still transformer-only.
            rad = np.maximum(self.X[:, self.rad_idx], 0.0)             # k=0 coefficient = size ≥ 0
            g = np.tanh(rad[:, None] * rad[None, :] / 0.25) * np.exp(-self.sink_attract * d2)
            np.fill_diagonal(g, 0.0)
            attract = -np.einsum("ij,ijc->ic", g, dirn)
        else:
            attract = -np.einsum("ij,ijc->ic", A_fit, delta)

        # repel head. Two modes:
        #  (a) repel_contact>0 → SYMMETRIC OVERLAP force: acts ONLY when agents interpenetrate
        #      (d < repel_contact), magnitude ∝ overlap depth, zero otherwise = real soft excluded
        #      volume. relu(depth) is bounded and →0 at contact, and overlap_ij=overlap_ji ⇒ symmetric.
        #  (b) else → the previous bounded repulsive ATTENTION (softmax over clash − λ·d²).
        overlap = None
        if self.repel_contact > 0.0:
            # SYMMETRIC overlap over ALL pairs (NOT the asymmetric k-NN mask — that would break
            # symmetry and momentum). overlap_ij = overlap_ji since d is symmetric; contact is short-
            # ranged so this stays local anyway. Zero the diagonal (no self-overlap).
            overlap = np.clip(self.repel_contact - dist, 0.0, None)
            np.fill_diagonal(overlap, 0.0)
            repel = np.einsum("ij,ijc->ic", overlap, dirn)
        else:
            rscore = np.where(mask, (S_direct - cfg.dist_lambda * d2) / tau, -np.inf)
            A_repel = self._attn(rscore, mask, self.sink_repel)
            repel = np.einsum("ij,ijc->ic", A_repel, dirn)

        force = self.attract * attract + self.repel * repel

        # cohesion head (surface tension, M1): a BROAD attention over a larger neighbourhood pulls
        # each agent toward its distance-weighted neighbourhood centroid → fragments coalesce into
        # one droplet. Pure attention (a smoothing/consensus head). Broad kernel reaches across gaps.
        if self.cohesion > 0.0:
            ck = self.cohere_k
            cidx = self._neighbors(d2, ck)
            cmask = np.zeros_like(d2, dtype=bool)
            np.put_along_axis(cmask, cidx, True, axis=1)
            np.fill_diagonal(cmask, False)
            if self.ablate == "identity":
                cmask = np.zeros_like(cmask)
            cscore = np.where(cmask, (-self.cohere_lambda * d2) / tau, -np.inf)
            A_coh = self._attn(cscore, cmask, self.sink_cohesion)
            cohere = -np.einsum("ij,ijc->ic", A_coh, delta)   # toward the neighbourhood centroid
            force = force + self.cohesion * cohere

        force = force + self._extra_force()   # subclass hook (default 0.0) — e.g. contour-charge force

        # OVERDAMPED (Brownian / DPD) integration: a molecule in a viscous solvent has negligible
        # inertia — velocity tracks force (v ≈ μ·F), drag dominates. `momentum` is the small inertial
        # memory (0 = fully overdamped, the physical limit for a dish; >0 adds glide for viewing).
        # Momentum-transfer-on-collision is NOT a separate law: it EMERGES from the symmetric repulsive
        # force + this inertia (and in the true overdamped limit the solvent absorbs momentum anyway).
        self.vel = self.momentum * self.vel + force

        # cap per-step displacement so nothing zips across the dish (overshoot control)
        sp = np.linalg.norm(self.vel, axis=1, keepdims=True)
        self.vel = np.where(sp > self.maxvel, self.vel * self.maxvel / (sp + 1e-9), self.vel)
        p = self.X[:, :self.pd] + self.speed * self.vel
        # REAL TEMPERATURE = thermal (Langevin) noise: seeded Brownian kicks ∝ temperature. Higher →
        # more disorder, melts structure, prevents freezing — the thermodynamically-correct direction
        # (unlike `selectivity`, the softmax τ). The one non-attention op; genuine thermal physics.
        if self.temperature > 0.0:
            p = p + _THERMAL * self.temperature * rng_for(self.seed, self.t).standard_normal(p.shape)
        p = ((p + cfg.pos_bound) % self.L) - cfg.pos_bound  # wrap to the torus

        # induced-fit morph: block updates shape/hidden, coupled through the fit attention
        z = self.X[:, self.pd:]
        msg = A_fit @ (z @ self.W_v)

        # PLASTICITY (weights that learn while alive) — a gated Hebbian fast-weight memory, i.e. the
        # fast-weight form of linear attention. Write: W_fast ← γ·W_fast + η·(kᵀv) (Hebbian outer
        # product = linear-attention memory write) with decay γ (homeostasis). Read: add z·W_fast to
        # the message → the interaction adapts with the history of activity. Slow weights stay fixed
        # (the laws); only these fast weights learn. Default plasticity=0 → skipped entirely.
        if self.plasticity > 0.0:
            k = z @ self.W_k
            v = z @ self.W_val
            if self.ablate != "freeze_plasticity":         # ablation: stop learning, keep reading
                self.W_fast = self.plast_decay * self.W_fast + self.plast_lr * (k.T @ v) / z.shape[0]
            msg = msg + self.plasticity * (z @ self.W_fast)

        spin = self.skew * (z @ self.J) if self.skew > 0 else 0.0
        z1 = _ln(z + self.morph * msg + spin)
        z2 = _ln(z1 + np.tanh(z1 @ self.W1 + self.b1) @ self.W2 + self.b2)
        # RIGIDITY: elastic restoring of the contour toward its round rest shape (C_rest=0). A stiff
        # molecule relaxes its induced deformation back each step; morph is the flexibility that fights it.
        if self.rigidity > 0.0:
            z2[:, :self.tK] = z2[:, :self.tK] * (1.0 - self.rigidity)
        z2 = self._post_morph(z2)             # subclass hook (default identity) — e.g. freeze water shape

        self.X = np.concatenate([p, z2], axis=1)
        self.t += 1

    # --- extension hooks: default to NO-OP so PackEngine behaviour is unchanged (base case). A
    #     subclass adds contour-charge forces / a frozen water species purely additively. ---
    def _extra_force(self):
        return 0.0

    def _post_morph(self, z2):
        return z2


def _cfg(**over):
    return VivariumConfig(**{**DEFAULTS, **over})


def probe(seed, ablate, repel, attract, skew, morph, momentum, cohesion=0.0, plasticity=0.0):
    e = PackEngine(_cfg(), seed, ablate=ablate, repel=repel, attract=attract, skew=skew,
                   morph=morph, momentum=momentum, cohesion=cohesion)
    e.plasticity = plasticity
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


def measure_gas_or_droplet(seed, cohesion=0.0):
    from metrics_pack import measure
    print(f"=== is the packing engine a DROPLET / ONE cluster?  (cohesion={cohesion}) ===")
    for scale, lab in ((1.0, "1x box"), (2.0, "2x box")):
        cfg = _cfg(pos_bound=DEFAULTS["pos_bound"] * scale)
        e = PackEngine(cfg, seed, cohesion=cohesion)
        for _ in range(600):
            e.step()
        m = measure(e.X[:, :e.pd], e.L, radius=1.0)
        print(f"{lab:8s} occupancy={m['occupancy']:.2f}  largest_cluster={m['largest_frac']:.2f}  "
              f"n_clusters={m['n_clusters']:2d}  Rg={m['rg']:.2f}  Rg/box={m['rg_over_box']:.2f}")
    print("ONE droplet: largest_cluster→1, n_clusters→1, occupancy<1, Rg box-independent.")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ablate", choices=["none", "identity", "freeze_plasticity"], default="none")
    p.add_argument("--repel", type=float, default=0.15)
    p.add_argument("--attract", type=float, default=0.45)
    p.add_argument("--skew", type=float, default=1.2)
    p.add_argument("--morph", type=float, default=0.7)
    p.add_argument("--mom", type=float, default=0.85)
    p.add_argument("--cohesion", type=float, default=0.0)
    p.add_argument("--plasticity", type=float, default=0.0)
    a = p.parse_args(argv)
    if a.measure:
        measure_gas_or_droplet(a.seed, a.cohesion)
    else:
        probe(a.seed, a.ablate, a.repel, a.attract, a.skew, a.morph, a.mom, a.cohesion, a.plasticity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
