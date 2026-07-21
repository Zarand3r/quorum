"""Membrane self-assembly — single-token amphiphiles, anisotropic-affinity LAW, emergent binding.

No dictated bonds, no multi-bead molecules. Each token is one agent with a position and (lipids) an
orientation `o` (a grounded head↔tail axis). The ONLY interaction is an anisotropic affinity — an
attention score bilinear in per-token orientation *queries* and relative *bearing* (a relative-
position-attention variant). Which tokens end up adjacent, and what structure forms, EMERGES; we
specify the LAW (a material property) and the reagents (species at init), never which lipid binds
which. Transformer-faithful (attention-weighted aggregation of relative vectors), fixed N.

THE LAW — an amphiphile prefers a neighbour that is (INTRA) beside it with a parallel normal (tile a
leaflet) or (INTER) across the midplane with an antiparallel normal, tails facing (stack two rows):

    side   = clip(1 − ½β[(o_i·r̂_ij)² + (o_j·r̂_ij)²], 0, 1)         (1 = bond ⊥ both normals)
    intra  = max(0, o_i·o_j) · side                                 (side-by-side, parallel)
    inter  = max(0, −o_i·o_j) · relu(o_i·r̂_ij) · relu(−o_j·r̂_ij)    (tail-to-tail, antiparallel)
    a_ij   = intra + gi·inter

Position: Σ_j a_ij·r̂_ij + bounded steric repel (+ optional weak isotropic cohesion gc for
coalescence); momentum, cap, torus wrap. Torque: intra pulls o_i ∥ o_j, inter points o_i's tail at
the across-neighbour. Optional annealed thermostat (temp) unsticks kinetic traps.

FINDING (2026-07): the anisotropic law robustly self-assembles amphiphiles from a random soup into
ORIENTATIONALLY-ORDERED membrane domains — director order S≈1.0, the correct side-by-side / tail-to-
tail packing motif, tails segregated from water. In this 2D SINGLE-BEAD model the equilibrium domain
is a compact aligned raft (elongated ribbons are kinetic intermediates); a closed vesicle/bilayer
needs a shaped token (Gay-Berne rod / 2-bead lipid) or 3D — the documented next step. See
MEMBRANE_PLAN.md § Findings.

    bazel run //projects/vivarium:membrane -- --probe
    bazel run //projects/vivarium:membrane -- --sweep
"""

from __future__ import annotations

import argparse

import numpy as np

from metrics_membrane import LIPID, WATER, measure
from rng import base_rng

_EPS = 1e-9


def _unit(v, axis=-1):
    return v / (np.linalg.norm(v, axis=axis, keepdims=True) + _EPS)


class MembraneEngine:
    def __init__(self, seed, N=96, pos_bound=6.0, n_neighbors=10, water_frac=0.45,
                 beta=1.0, ga=0.35, gr=0.15, gc=0.02, gi=1.0, kappa=2.0, torque=0.28, nematic=0.0,
                 momentum=0.6, maxvel=0.2, speed=1.0, dist_lambda=0.6, r_neigh=1.8, temp=0.10,
                 anneal=8000):
        self.N = N
        self.pos_bound = pos_bound
        self.L = 2.0 * pos_bound
        self.k = min(n_neighbors, N - 1)
        self.beta = beta          # hydrophobicity anisotropy sharpness
        self.ga = ga              # anisotropic membrane-affinity gain (side-by-side + parallel)
        self.gr = gr              # steric excluded-volume gain
        self.gc = gc              # weak isotropic lipid cohesion (drives coalescence of patches)
        self.gi = gi              # inter-leaflet (tail-to-tail across midplane) gain → bilayer, not raft
        self.kappa = kappa        # rod aspect of the steric shape (0 = disk; >0 forbids end-on stacking)
        self.torque = torque      # orientation alignment rate
        self.nematic = nematic    # nematic (±) alignment with neighbour lipids → ordered rows/sheets
        self.momentum = momentum
        self.maxvel = maxvel
        self.speed = speed
        self.dist_lambda = dist_lambda
        self.r_neigh = r_neigh    # metric neighbourhood radius
        self.temp = temp          # thermostat: initial thermal-noise amplitude (anneals to 0)
        self.anneal = anneal      # ticks over which temp → 0 (linear quench)
        r = base_rng(seed)
        self.rng = base_rng(seed + 991)   # separate stream for the thermostat
        self.species = (r.random(N) > water_frac).astype(int)   # 1 = lipid, 0 = water
        self.pos = r.uniform(-pos_bound, pos_bound, (N, 2))
        o = r.standard_normal((N, 2))
        o[self.species == WATER] = 0.0
        self.orient = _unit(o)
        self.orient[self.species == WATER] = 0.0
        self.vel = np.zeros((N, 2))
        self.t = 0

    def _geometry(self):
        d = self.pos[None, :, :] - self.pos[:, None, :]      # j − i
        d = d - self.L * np.round(d / self.L)                # min image
        d2 = np.einsum("ijc,ijc->ij", d, d)
        dist = np.sqrt(d2 + 1e-12)
        rhat = d / dist[..., None]
        idx = np.argsort(d2, axis=1, kind="stable")[:, : self.k + 1]  # +1 to drop self
        mask = np.zeros_like(d2, dtype=bool)
        np.put_along_axis(mask, idx, True, axis=1)
        np.fill_diagonal(mask, False)
        return d2, rhat, mask

    def step(self):
        d2, rhat, mask = self._geometry()
        is_lip = (self.species == LIPID)
        lippair = mask & is_lip[:, None] & is_lip[None, :]

        # BILAYER CROSS-SECTION LAW. Each lipid carries a head→tail axis o (tail = +o). A 2D bilayer is
        # two rows, tails meeting at the midplane, heads facing water on both sides. Two mechanisms,
        # both attention scores bilinear in the orientation queries o and the relative bearing r̂
        # (relative-position attention) — transformer-faithful, and LAWS (we never say which binds which):
        #   INTRA-leaflet: neighbour beside me (bond ⊥ o) with a PARALLEL normal → tile a row.
        #        intra = max(0, o_i·o_j) · side,   side = 1 when the bond is ⊥ both normals.
        #   INTER-leaflet: neighbour across the midplane — ANTIPARALLEL normal, and each points its
        #        tail (+o) at the other (tail-to-tail) → stack two rows into a bilayer.
        #        inter = max(0, −o_i·o_j) · relu(o_i·r̂_ij) · relu(−o_j·r̂_ij).
        oir = np.einsum("ic,ijc->ij", self.orient, rhat)            # o_i · r̂_ij  (>0: j toward i's tail)
        ojr = np.einsum("jc,ijc->ij", self.orient, rhat)            # o_j · r̂_ij
        oo = np.einsum("ic,jc->ij", self.orient, self.orient)       # o_i · o_j
        side = np.clip(1.0 - 0.5 * self.beta * (oir ** 2 + ojr ** 2), 0.0, 1.0)
        intra = np.maximum(0.0, oo) * side
        inter = np.maximum(0.0, -oo) * np.maximum(0.0, oir) * np.maximum(0.0, -ojr)
        a = np.where(lippair, intra + self.gi * inter, 0.0)         # bilayer affinity

        # position: anisotropic membrane cohesion + ROD-SHAPED steric excluded volume. Each lipid is a
        # rod (the token IS a shape), long along its normal o. The steric repulsion is stronger when a
        # neighbour sits ALONG the axis (o·r̂ large) — two rods cannot overlap end-on — so lipids can
        # only pack SIDE-BY-SIDE, which forces a one-rod-thick sheet (a bilayer) instead of filling in
        # to a raft. κ = rod aspect (0 = isotropic disk). Bounded (Gaussian), local.
        f_aff = self.ga * np.einsum("ij,ijc->ic", a, rhat)
        elong = 1.0 + self.kappa * 0.5 * (oir ** 2 + ojr ** 2)      # rod: bigger along the axis
        rep = np.where(mask, np.exp(-self.dist_lambda * d2) * elong, 0.0)
        f_ster = self.gr * np.einsum("ij,ijc->ic", rep, -rhat)      # push from close neighbours
        force = f_aff + f_ster

        # weak ISOTROPIC lipid cohesion — a soft, longer-range lipid–lipid pull (the hydrophobic
        # effect at range) that lets separate membrane patches drift together and MERGE; the
        # anisotropic term above then re-orders the merged domain into one sheet. Distance-decayed
        # (Gaussian, range r_c) over lipid pairs — a smooth attention kernel, still local, no global
        # term. Off by default (gc=0).
        if self.gc > 0.0:
            r_c = 3.0
            w = np.exp(-d2 / (2.0 * r_c * r_c))
            w = np.where(is_lip[:, None] & is_lip[None, :], w, 0.0)
            np.fill_diagonal(w, 0.0)
            force = force + self.gc * np.einsum("ij,ijc->ic", w, rhat) / (w.sum(1, keepdims=True) + _EPS)

        self.vel = self.momentum * self.vel + force
        sp = np.linalg.norm(self.vel, axis=1, keepdims=True)
        self.vel = np.where(sp > self.maxvel, self.vel * self.maxvel / (sp + _EPS), self.vel)
        p = self.pos + self.speed * self.vel

        # THERMOSTAT (annealed): a thermal kick lets kinetically-trapped fragments break and re-form
        # into larger ordered domains, then quenches to 0 so the final structure is sharp. This is the
        # sampling-temperature / diffusion-noise analog — the annealing that every self-assembly needs.
        if self.temp > 0.0:
            cur = self.temp * max(0.0, 1.0 - self.t / self.anneal)
            if cur > 0.0:
                p = p + cur * self.rng.standard_normal((self.N, 2))
        self.pos = ((p + self.pos_bound) % self.L) - self.pos_bound

        # orientation torque (an orientational LAW): INTRA neighbours pull o_i toward their normal o_j
        # (parallel → flat leaflet); INTER neighbours pull o_i's tail toward the bond r̂_ij (tail-to-tail
        # across the midplane). desired = Σ_j intra_ij·o_j + gi·inter_ij·r̂_ij.
        wi = np.where(lippair, intra, 0.0)
        we = np.where(lippair, self.gi * inter, 0.0)
        desired = _unit(np.einsum("ij,jc->ic", wi, self.orient)
                        + np.einsum("ij,ijc->ic", we, rhat))
        has = ((wi.sum(1, keepdims=True) + we.sum(1, keepdims=True)) > _EPS)
        newo = _unit((1.0 - self.torque) * self.orient + self.torque * desired)
        newo = np.where(has, newo, self.orient)
        self.orient = np.where(is_lip[:, None], newo, 0.0)
        self.t += 1

    def measure(self):
        return measure(self.pos, self.species, self.orient, self.L, self.r_neigh)


def _cfg_from(a):
    return dict(N=a.N, water_frac=a.water, beta=a.beta, ga=a.ga, gr=a.gr, gc=a.gc, gi=a.gi,
                kappa=a.kappa, torque=a.torque, nematic=a.nematic, momentum=a.mom,
                dist_lambda=a.lam, temp=a.temp, anneal=a.anneal)


def probe(a):
    e = MembraneEngine(a.seed, **_cfg_from(a))
    lip = (e.species == LIPID)
    print(" tick    S    side  sheet  clust   speed   drift   (drift≈speed → whole band STREAMS)")
    for _ in range(0, a.ticks + 1, a.every):
        m = e.measure()
        v = e.vel[lip]
        speed = float(np.mean(np.linalg.norm(v, axis=1)))       # mean per-lipid speed
        drift = float(np.linalg.norm(v.mean(0)))                # net centre-of-mass drift
        print(f"{e.t:6d}  {m['S']:.3f}  {m['side']:.3f}  {m['sheetness']:5.2f}  {m['n_lipid_clusters']:3d}   "
              f"{speed:.4f}  {drift:.4f}")
        for _ in range(a.every):
            e.step()


def sweep(a):
    import itertools
    grid = {"beta": [1.0, 1.5, 2.0], "ga": [0.15, 0.25], "torque": [0.25, 0.4],
            "water_frac": [0.5, 0.65]}
    keys = list(grid)
    rows = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        o = dict(zip(keys, combo))
        Ss, sides, shs = [], [], []
        for s in (0, 1, 2):
            e = MembraneEngine(s, N=a.N, water_frac=o["water_frac"], beta=o["beta"], ga=o["ga"],
                               gr=a.gr, torque=o["torque"], momentum=a.mom, dist_lambda=a.lam)
            for _ in range(a.ticks):
                e.step()
            m = e.measure()
            Ss.append(m["S"]); sides.append(m["side"]); shs.append(m["sheetness"])
        rows.append((float(np.mean(Ss)), float(np.mean(sides)), float(np.mean(shs)), o))
    # rank by membrane quality: aligned normals × side-by-side packing
    rows.sort(reverse=True, key=lambda x: x[0] * x[1])
    print(f"membrane sweep (N={a.N}, T={a.ticks}, seeds 0-2). S (align) | side | sheet | knobs")
    for S, sd, sh, o in rows:
        print(f"  S={S:.3f}  side={sd:.3f}  sheet={sh:5.2f}  "
              + " ".join(f"{k}={v}" for k, v in o.items()))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--sweep", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=14000)
    p.add_argument("--every", type=int, default=2000)
    p.add_argument("--N", type=int, default=96)
    p.add_argument("--water", type=float, default=0.45)
    p.add_argument("--beta", type=float, default=1.0)
    p.add_argument("--ga", type=float, default=0.35)
    p.add_argument("--gr", type=float, default=0.15)
    p.add_argument("--gc", type=float, default=0.02)
    p.add_argument("--gi", type=float, default=1.0)
    p.add_argument("--kappa", type=float, default=2.0)
    p.add_argument("--torque", type=float, default=0.28)
    p.add_argument("--nematic", type=float, default=0.0)
    p.add_argument("--temp", type=float, default=0.10)
    p.add_argument("--anneal", type=int, default=8000)
    p.add_argument("--mom", type=float, default=0.6)
    p.add_argument("--lam", type=float, default=0.6)
    a = p.parse_args(argv)
    if a.sweep:
        sweep(a)
    else:
        probe(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
