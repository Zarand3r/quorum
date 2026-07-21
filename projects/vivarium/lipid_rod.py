"""Rigid 2-bead lipid rods — the minimal amphiphile that self-assembles BILAYERS and VESICLES in 2D.

Why this and not `membrane.py`: that engine's affinity depends on orientations that keep changing, so
its force is NON-conservative — it has no energy to minimise and settles into a *flowing* nematic
(laminar streaming), packing head-to-tail rather than side-by-side. Here each lipid is a rigid ROD
(one token, but a SHAPE): a hydrophilic HEAD bead and a hydrophobic TAIL bead rigidly offset along the
token's orientation. All interactions are genuine pair potentials between beads, so the total force IS
the gradient of an energy → OVERDAMPED dynamics MINIMISE that energy → the structure SETTLES (no
streaming). Excluded volume forces side-by-side packing; tail–tail attraction builds a two-row bilayer;
a finite bilayer CLOSES into a vesicle to bury its exposed hydrophobic edge → it ENCLOSES space.

Still faithful: fixed N tokens; each dynamical term is an attention-weighted sum over relative bead
vectors (a pair potential is a distance-attention readout); we specify only LAWS (bead affinities) and
reagents (species at init), never which lipid binds which. This is the Cooke–Deserno solvent-free
minimal lipid, adapted to 2D, with inert water beads kept for visualisation.

    bazel run //projects/vivarium:lipid_rod -- --probe
"""

from __future__ import annotations

import argparse

import numpy as np

from rng import base_rng

WATER, LIPID = 0, 1
_EPS = 1e-12

# bead types
_HEAD, _TAIL, _POLAR = 0, 1, 2


def _unit(v, axis=-1):
    return v / (np.linalg.norm(v, axis=axis, keepdims=True) + 1e-9)


class RodEngine:
    """N amphiphile tokens (rigid head–tail rods) + inert water, overdamped on a torus."""

    def __init__(self, seed, N=110, pos_bound=6.0, water_frac=0.45,
                 ell=0.55, sigma=0.6, wc=1.6, k_rep=2.0, k_att=2.5, n_tail=2,
                 mu=0.008, mu_rot=0.05, temp=0.12, anneal=12000,
                 maxstep=0.15, r_neigh=1.6):
        self.n_tail = n_tail    # number of hydrophobic tail beads (longer tail → flat bilayer, not micelle)
        self.N = N
        self.pos_bound = pos_bound
        self.L = 2.0 * pos_bound
        self.ell = ell          # rod length (head↔tail separation)
        self.sigma = sigma      # bead diameter (excluded-volume range)
        self.wc = wc            # tail–tail attractive range (∝ solvent quality; Cooke's w_c)
        self.k_rep = k_rep      # excluded-volume stiffness
        self.k_att = k_att      # hydrophobic tail–tail attraction strength
        self.mu = mu            # translational mobility (overdamped)
        self.mu_rot = mu_rot    # rotational mobility
        self.temp = temp        # thermostat amplitude (anneals to 0)
        self.anneal = anneal
        self.maxstep = maxstep  # per-step displacement cap (stability)
        self.r_neigh = r_neigh
        r = base_rng(seed)
        self.rng = base_rng(seed + 991)
        self.species = (r.random(N) > water_frac).astype(int)
        self.pos = r.uniform(-pos_bound, pos_bound, (N, 2))
        o = r.standard_normal((N, 2))
        self.orient = _unit(o)
        self.orient[self.species == WATER] = 0.0
        self.vel = np.zeros((N, 2))   # last displacement (for the viewer's speed readout)
        self.t = 0

    # ---- bead bookkeeping -------------------------------------------------
    def _beads(self):
        """Return (bead_pos, bead_type, owner, lever). Each lipid is a 3-bead rod along its orientation
        o: HEAD at −ℓ·o (hydrophilic), then two TAIL beads at 0 and +ℓ·o (hydrophobic). The two-bead
        tail is itself a little rod, so tails pack side-by-side into a flat slab → a BILAYER, not a
        round micelle. Water is one inert POLAR bead."""
        is_lip = self.species == LIPID
        lip = np.where(is_lip)[0]
        wat = np.where(~is_lip)[0]
        nl = len(lip)
        o = self.orient[lip]
        # head at −ℓ·o; then n_tail tail beads at 0, +ℓ·o, +2ℓ·o, … along the tail.
        offs = [(-self.ell, _HEAD)] + [(k * self.ell, _TAIL) for k in range(self.n_tail)]
        beads, types, levers = [], [], []
        for s, typ in offs:
            beads.append(self.pos[lip] + s * o)
            types.append(np.full(nl, typ))
            levers.append(s * o)
        beads.append(self.pos[wat]); types.append(np.full(len(wat), _POLAR))
        levers.append(np.zeros((len(wat), 2)))
        bp = np.concatenate(beads, axis=0)
        bt = np.concatenate(types)
        owner = np.concatenate([lip] * len(offs) + [wat])
        lever = np.concatenate(levers, axis=0)
        return bp, bt, owner, lever

    def step(self):
        bp, bt, owner, lever = self._beads()
        M = bp.shape[0]
        d = bp[None, :, :] - bp[:, None, :]              # j − i  (M,M,2)
        d = d - self.L * np.round(d / self.L)            # min image
        dist = np.sqrt(np.einsum("ijc,ijc->ij", d, d) + _EPS)
        rhat = d / dist[..., None]
        np.fill_diagonal(dist, np.inf)                   # ignore self

        # (1) excluded volume — every bead pair that overlaps (dist < σ) pushes apart. LINEAR spring in
        #     the overlap depth: a soft, bounded WCA-like core. Force on i points along −r̂ (away from j).
        overlap = np.clip(self.sigma - dist, 0.0, None)
        f_rep = self.k_rep * overlap                     # magnitude on i toward −r̂_ij

        # (2) hydrophobic attraction — ONLY tail–tail, in the shell σ ≤ dist ≤ σ+w_c, a smooth cosine
        #     well (Cooke's attractive tail that stands in for the solvent). Pulls i toward j (+r̂).
        tt = (bt[:, None] == _TAIL) & (bt[None, :] == _TAIL)
        x = np.clip((dist - self.sigma) / self.wc, 0.0, 1.0)
        att = np.where(tt, np.cos(0.5 * np.pi * x) ** 2, 0.0)   # 1 at contact → 0 at σ+w_c
        att = np.where(dist >= self.sigma, att, 0.0)
        f_att = self.k_att * att                         # magnitude on i toward +r̂_ij

        # per-bead net force = Σ_j (attraction toward j − repulsion away from j) along r̂_ij.
        # EXCLUDE bead pairs on the SAME lipid — the rod is rigid, so its own beads must not push/pull
        # each other (they sit inside σ of one another). Missing this injects huge spurious intra-lipid
        # forces and makes the integrator blow up.
        same = owner[:, None] == owner[None, :]
        mag = np.where(same, 0.0, f_att - f_rep)         # (M,M): + pulls together, − pushes apart
        fb = np.einsum("ij,ijc->ic", mag, rhat)          # (M,2)

        # map bead forces back to their token: net force + torque (2D scalar cross of lever × force)
        N = self.N
        F = np.zeros((N, 2))
        np.add.at(F, owner, fb)
        torque = lever[:, 0] * fb[:, 1] - lever[:, 1] * fb[:, 0]
        T = np.zeros(N)
        np.add.at(T, owner, torque)

        # overdamped translation (with capped step) + annealed thermal kick
        disp = self.mu * F
        cur = self.temp * max(0.0, 1.0 - self.t / self.anneal)
        if cur > 0.0:
            disp = disp + cur * self.mu * self.rng.standard_normal((N, 2))
        sp = np.linalg.norm(disp, axis=1, keepdims=True)
        disp = np.where(sp > self.maxstep, disp * self.maxstep / (sp + 1e-12), disp)
        self.vel = disp
        p = self.pos + disp
        self.pos = ((p + self.pos_bound) % self.L) - self.pos_bound

        # overdamped rotation of the rod (lipids only); renormalise the orientation
        is_lip = self.species == LIPID
        dtheta = np.clip(self.mu_rot * T, -0.4, 0.4)
        c, s = np.cos(dtheta), np.sin(dtheta)
        ox, oy = self.orient[:, 0], self.orient[:, 1]
        newo = np.stack([c * ox - s * oy, s * ox + c * oy], axis=1)
        self.orient = np.where(is_lip[:, None], _unit(newo), 0.0)
        self.t += 1

    def measure(self):
        from metrics_membrane import measure
        return measure(self.pos, self.species, self.orient, self.L, self.r_neigh)


def _cfg(a):
    return dict(N=a.N, water_frac=a.water, ell=a.ell, sigma=a.sigma, wc=a.wc, k_rep=a.krep,
               k_att=a.katt, n_tail=a.ntail, mu=a.mu, mu_rot=a.murot, temp=a.temp, anneal=a.anneal)


def probe(a):
    e = RodEngine(a.seed, **_cfg(a))
    lip = (e.species == LIPID)
    print(" tick    S    side  sheet clust  speed   drift")
    for _ in range(0, a.ticks + 1, a.every):
        m = e.measure()
        v = e.vel[lip]
        speed = float(np.mean(np.linalg.norm(v, axis=1)))
        drift = float(np.linalg.norm(v.mean(0)))
        print(f"{e.t:6d}  {m['S']:.3f}  {m['side']:.3f}  {m['sheetness']:5.2f}  {m['n_lipid_clusters']:3d}  "
              f"{speed:.4f}  {drift:.4f}")
        for _ in range(a.every):
            e.step()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=12000)
    p.add_argument("--every", type=int, default=1500)
    p.add_argument("--N", type=int, default=110)
    p.add_argument("--water", type=float, default=0.45)
    p.add_argument("--ell", type=float, default=0.55)
    p.add_argument("--sigma", type=float, default=0.6)
    p.add_argument("--wc", type=float, default=1.6)
    p.add_argument("--krep", type=float, default=2.0)
    p.add_argument("--katt", type=float, default=2.5)
    p.add_argument("--ntail", type=int, default=2)
    p.add_argument("--mu", type=float, default=0.008)
    p.add_argument("--murot", type=float, default=0.05)
    p.add_argument("--temp", type=float, default=0.12)
    p.add_argument("--anneal", type=int, default=12000)
    a = p.parse_args(argv)
    probe(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
