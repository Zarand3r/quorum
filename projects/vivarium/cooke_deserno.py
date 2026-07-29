"""A CONTROL experiment: make a bilayer with ordinary hard-coded physics, no transformer anywhere.

This is deliberately NOT transformer-only. It uses 1/r^12 cores, an explicit energy function and
plain Newtonian integration, all of which vivarium forbids. It exists to answer one question that
vivarium's own failures cannot: **is a bilayer reachable at all in a box this size, on a timescale we
can afford, measured by the metrics we trust?**

Without this control, every negative result in BILAYER_REVIEW.md is ambiguous. A bilayer that never
forms could mean the transformer-only restriction is genuinely too weak, or it could mean the box is
too small, the run too short, the temperature wrong, or the order parameter blind. Finding 21 showed
this project is entirely capable of the last of those. So we first make a bilayer with physics known
to work, then port the LESSONS back rather than the mechanism.

The model is Cooke, Kremer & Deserno, "Tunable generic model for fluid bilayer membranes",
Phys. Rev. E 72, 011506 (2005), the standard solvent-free coarse-grained lipid. Three beads per
lipid, one head and two tails:

    repulsion   WCA between every pair, with b = 0.95 sigma whenever a head is involved and
                b = sigma for tail-tail. The smaller head diameter is what sets the packing
                parameter, and it is the single most important parameter in the model.
    attraction  tail-tail ONLY, -eps cos^2(pi (r-rc)/(2 wc)) between rc and rc+wc, flat -eps below.
                This REPLACES water: the hydrophobic effect is folded into a direct tail cohesion,
                which is why the model needs no solvent and is ~4x cheaper than vivarium per lipid.
    bonds       FENE between consecutive beads.
    stiffness   a harmonic 1-3 spring at rest length 4 sigma, which straightens the chain.

w_c is the tunable knob: near 1.6 sigma the membrane is a fluid bilayer, below ~1.5 it freezes into
a gel, above ~1.8 it falls apart. kT = 1.1 eps.

    bazel run //projects/vivarium:cooke_deserno -- --lipids 200 --steps 200000
"""

from __future__ import annotations

import argparse
import math

import numpy as np

SIGMA = 1.0
EPS = 1.0
B_HEAD = 0.95 * SIGMA          # any pair involving a head
B_TAIL = 1.00 * SIGMA          # tail-tail
R_C = 2.0 ** (1.0 / 6.0) * SIGMA
K_FENE, R_INF = 30.0, 1.5 * SIGMA
K_BEND, L_BEND = 10.0, 4.0 * SIGMA
HEAD, TAIL = 0, 1


class CookeDeserno:
    """Solvent-free three-bead lipids under Langevin dynamics in a periodic box."""

    def __init__(self, n_lipids, box, w_c=1.6, kT=1.1, dt=0.01, gamma=1.0, seed=0):
        self.n_lip = n_lipids
        self.L = np.asarray(box, dtype=float)
        self.w_c, self.kT, self.dt, self.gamma = w_c, kT, dt, gamma
        self.rng = np.random.default_rng(seed)

        n = 3 * n_lipids
        self.species = np.tile(np.array([HEAD, TAIL, TAIL]), n_lipids)
        self.mol = np.arange(n).reshape(n_lipids, 3)

        # Centres on a jittered LATTICE, not uniform random. Two beads landing on top of each other
        # gives WCA a 1/r^12 on a near-zero separation, i.e. an effectively infinite force, and the
        # integrator explodes on step one. A lattice guarantees a minimum separation; the jitter
        # keeps the start disordered so self-assembly is still a real test.
        k = int(math.ceil(n_lipids ** (1.0 / 3.0)))
        grid = np.stack(np.meshgrid(*[np.arange(k)] * 3, indexing="ij"), -1).reshape(-1, 3)
        cen = (grid[:n_lipids] + 0.5) / k * self.L
        cen += self.rng.uniform(-0.15, 0.15, cen.shape) * (self.L / k)
        ax = self.rng.standard_normal((n_lipids, 3))
        ax /= np.linalg.norm(ax, axis=1, keepdims=True)
        self.X = np.empty((n, 3))
        for b in range(3):
            self.X[self.mol[:, b]] = cen + (b - 1.0) * SIGMA * ax
        self.V = self.rng.standard_normal((n, 3)) * math.sqrt(kT)

        # pair tables, built once
        is_tail = self.species == TAIL
        self.tail_pair = is_tail[:, None] & is_tail[None, :]
        self.b_ij = np.where(self.tail_pair, B_TAIL, B_HEAD)
        self.bond_i = np.concatenate([self.mol[:, 0], self.mol[:, 1]])
        self.bond_j = np.concatenate([self.mol[:, 1], self.mol[:, 2]])
        self.bend_i, self.bend_j = self.mol[:, 0], self.mol[:, 2]
        self.skin = 0.6
        self._rebuild_neighbours()

    def _delta(self, a, b):
        d = self.X[a] - self.X[b]
        return d - self.L * np.round(d / self.L)

    def _rebuild_neighbours(self):
        """Verlet list. Every interaction here is short-ranged (longest is R_C + w_c), so the dense
        N x N matrix recomputes ~99% zeros every step. Listing the pairs once per SKIN_EVERY steps
        and reusing them turns the inner loop from O(N^2) into O(pairs), which is what makes a
        10^6-step self-assembly run affordable at all."""
        d = self.X[:, None, :] - self.X[None, :, :]
        d -= self.L * np.round(d / self.L)
        r2 = np.einsum("ijc,ijc->ij", d, d)
        reach = R_C + self.w_c + self.skin
        i, j = np.where(np.triu(r2 < reach * reach, k=1))
        self.ni, self.nj = i, j
        self.n_b = self.b_ij[i, j]
        self.n_tail = self.tail_pair[i, j]
        self.X_built = self.X.copy()

    def forces(self):
        # rebuild when any bead has moved more than half the skin since the list was built
        moved = self.X - self.X_built
        moved -= self.L * np.round(moved / self.L)
        if np.max(np.einsum("ic,ic->i", moved, moved)) > (0.5 * self.skin) ** 2:
            self._rebuild_neighbours()

        d = self.X[self.ni] - self.X[self.nj]
        d -= self.L * np.round(d / self.L)
        # floor the separation before it reaches 1/r^12. Without this a single close approach during
        # equilibration produces a force large enough to eject a bead across the box in one step.
        r = np.maximum(np.linalg.norm(d, axis=1), 0.3)
        F = np.zeros_like(self.X)

        # WCA: purely repulsive, truncated at the minimum of the LJ well
        cut = r < 2.0 ** (1.0 / 6.0) * self.n_b
        rs = np.where(cut, r, 1.0)
        br6 = (self.n_b / rs) ** 6
        mag = np.where(cut, 24.0 * EPS * (2.0 * br6 * br6 - br6) / (rs * rs), 0.0)

        # tail-tail cohesion, the term that stands in for water
        att = self.n_tail & (r > R_C) & (r < R_C + self.w_c)
        ra = np.where(att, r, R_C)
        x = np.pi * (ra - R_C) / (2.0 * self.w_c)
        # V = -eps cos^2 x  =>  F_r = -dV/dr = -eps pi/(2 wc) sin(2x), negative => attractive
        f_att = -EPS * np.pi / (2.0 * self.w_c) * np.sin(2.0 * x)
        mag = mag + np.where(att, f_att / ra, 0.0)

        fp = mag[:, None] * d
        np.add.at(F, self.ni, fp)
        np.add.at(F, self.nj, -fp)

        # FENE bonds
        db = self._delta(self.bond_i, self.bond_j)
        rb = np.linalg.norm(db, axis=1)
        rb = np.clip(rb, 1e-9, R_INF * 0.999)
        fb = (-K_FENE / (1.0 - (rb / R_INF) ** 2))[:, None] * db
        np.add.at(F, self.bond_i, fb)
        np.add.at(F, self.bond_j, -fb)

        # 1-3 straightener
        ds = self._delta(self.bend_i, self.bend_j)
        rs = np.maximum(np.linalg.norm(ds, axis=1), 1e-9)
        fs = (-K_BEND * (rs - L_BEND) / rs)[:, None] * ds
        np.add.at(F, self.bend_i, fs)
        np.add.at(F, self.bend_j, -fs)
        return F

    def step(self, dt=None):
        """BAOAB Langevin.

        The first version used Euler-Maruyama, which cannot integrate a 1/r^12 core: temperature ran
        to 1e12 and FENE bonds stretched to 6 sigma past their 1.5 sigma limit within 5000 steps.
        BAOAB splits the deterministic and stochastic parts symmetrically and stays stable at the
        same timestep. The exact Ornstein-Uhlenbeck O-step also samples the target kT correctly
        rather than approximating it, so temperature is a check on the integrator, not a free knob.
        """
        dt = self.dt if dt is None else dt
        c1 = math.exp(-self.gamma * dt)
        c2 = math.sqrt(self.kT * (1.0 - c1 * c1))

        self.V += 0.5 * dt * self.forces()            # B
        self.X += 0.5 * dt * self.V                   # A
        self.V = c1 * self.V + c2 * self.rng.standard_normal(self.X.shape)   # O
        self.X += 0.5 * dt * self.V                   # A
        self.X -= self.L * np.floor(self.X / self.L)
        self.V += 0.5 * dt * self.forces()            # B

    def minimize(self, steps=4000, max_disp=0.02):
        """Steepest descent with a capped DISPLACEMENT, run before any dynamics.

        The lattice start leaves beads inside each other's WCA cores. Capping the force is not enough
        because the force there is ~1e9: the fix is to bound how far a bead may MOVE per iteration,
        which removes overlaps without ever integrating the divergence. Returns the final max force
        so the caller can assert the configuration is actually relaxed.
        """
        for _ in range(steps):
            F = self.forces()
            n = np.linalg.norm(F, axis=1, keepdims=True)
            self.X += F * np.minimum(max_disp / np.maximum(n, 1e-12), max_disp)
            self.X -= self.L * np.floor(self.X / self.L)
        self.V[:] = 0.0
        return float(np.linalg.norm(self.forces(), axis=1).max())


def axes(sim):
    """Lipid axis, head -> far tail, normalised."""
    u = sim._delta(sim.mol[:, 2], sim.mol[:, 0])
    return u / np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)


def metrics(sim, cutoff=3.0):
    """Orientation-agnostic, and calibrated the way Finding 21 says every metric must be.

    nematic  <2(u_i.u_j)^2 - 1> over neighbouring lipid pairs. In 3-D the isotropic baseline is
             -1/3, NOT 0.
    opposed  fraction of neighbouring pairs pointing OPPOSITE ways. The cutoff is 3.0, not 2.0:
             the two leaflets sit ~2.5 sigma apart centre-to-centre, so a 2.0 cutoff excludes every
             cross-leaflet pair and `opposed` reads 0.000 on a PERFECT planted bilayer. Checked
             against the planted control, which is the only way that bug is visible.
    """
    cen = sim.X[sim.mol[:, 1]]
    d = cen[:, None, :] - cen[None, :, :]
    d -= sim.L * np.round(d / sim.L)
    near = np.einsum("ijc,ijc->ij", d, d) < cutoff ** 2
    np.fill_diagonal(near, False)
    u = axes(sim)
    dot = u @ u.T
    if not near.any():
        return -1 / 3, 0.0, 0.0
    nem = float(np.mean(2.0 * dot[near] ** 2 - 1.0))
    opp = float(np.mean(dot[near] < -0.5))

    # `split`: the two-leaflet signature, measured directly. Take the global director, project the
    # head->tail axis onto it, and ask what fraction of lipids point one way versus the other. A
    # BILAYER is ~0.5 (two opposed leaflets). A monolayer or a micelle is far from 0.5. The previous
    # `flat` metric was useless: on a periodic system it reported the BOX aspect ratio, not the
    # structure, which is precisely the positive-control failure Finding 21 warned about.
    Q = (3.0 * np.einsum("ia,ib->ab", u, u) / len(u) - np.eye(3)) / 2.0
    director = np.linalg.eigh(Q)[1][:, 2]
    proj = u @ director
    split = float(min((proj > 0).mean(), (proj < 0).mean()))
    return nem, opp, split


def plant_bilayer(sim):
    """A perfect bilayer normal to z. The POSITIVE control for every metric below."""
    n = sim.n_lip
    per = n // 2
    k = int(math.ceil(math.sqrt(per)))
    xs = (np.arange(k) + 0.5) / k
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel() * sim.L[0], gy.ravel() * sim.L[1]], axis=1)
    zc = sim.L[2] / 2.0
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = sim.mol[leaf * per:(leaf + 1) * per]
        pts = flat[:len(idx)]
        for bead in range(3):
            # head (bead 0) OUTERMOST, tails toward the midplane
            off = (2.0 - bead) * 0.95 + 0.3
            sim.X[idx[:, bead], 0] = pts[:, 0]
            sim.X[idx[:, bead], 1] = pts[:, 1]
            sim.X[idx[:, bead], 2] = zc + sgn * off
    sim.V[:] = 0.0


def bilayer_signature(sim):
    """Thickness along the director, the measurement that actually distinguishes a bilayer.

    A bilayer has heads in TWO sheets separated by ~2x the molecule length with tails filling the
    space between. A micelle, a cylinder or a blob all fail this even when they score well on
    `nematic`. Per Finding 21 the number is meaningless without both controls, so main() prints the
    planted value and the random value beside the measured one.

    Returns the thickness in sigma between the two head sheets. An earlier version also returned a
    "tail centrality", which was dropped: it read +1.00 on the planted bilayer AND on a random start,
    so it separated nothing. Thickness is the discriminator (planted 4.40, random 1.31).
    """
    u = axes(sim)
    Q = (3.0 * np.einsum("ia,ib->ab", u, u) / len(u) - np.eye(3)) / 2.0
    nrm = np.linalg.eigh(Q)[1][:, 2]
    heads = sim.X[sim.mol[:, 0]] @ nrm
    side = u @ nrm > 0                       # which leaflet each lipid belongs to
    if side.all() or not side.any():
        return 0.0
    thickness = abs(float(heads[side].mean() - heads[~side].mean()))
    return thickness


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--lipids", type=int, default=200)
    p.add_argument("--steps", type=int, default=200000)
    p.add_argument("--every", type=int, default=20000)
    p.add_argument("--wc", type=float, default=1.6)
    p.add_argument("--kt", type=float, default=1.1)
    p.add_argument("--dt", type=float, default=0.01)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--boxz", type=float, default=0.0, help="0 = cubic sized for a tensionless sheet")
    a = p.parse_args(argv)

    # size the box so a flat tensionless bilayer just fits: area per lipid ~1.2 sigma^2 per leaflet
    side = math.sqrt(1.2 * a.lipids / 2.0)
    boxz = a.boxz if a.boxz > 0 else max(2.5 * side, 14.0)
    sim = CookeDeserno(a.lipids, (side, side, boxz), w_c=a.wc, kT=a.kt, dt=a.dt, seed=a.seed)
    print(f"Cooke-Deserno control: {a.lipids} lipids ({3*a.lipids} beads), "
          f"box {side:.1f} x {side:.1f} x {boxz:.1f}, w_c={a.wc} kT={a.kt} dt={a.dt}")
    print("  a bilayer spanning x-y needs ~%d lipids at 1.2 sigma^2 each" % int(2 * side * side / 1.2))
    fmax = sim.minimize()
    print(f"  minimised: max|F| = {fmax:.2f}  (an unminimised lattice start reaches ~1e9 and the "
          f"integrator explodes)")
    # calibrate every metric against BOTH controls before reading any of them (Finding 21)
    import copy
    ctl = copy.deepcopy(sim)
    plant_bilayer(ctl)
    pn, po, ps = metrics(ctl)
    pt = bilayer_signature(ctl)
    rnd = CookeDeserno(a.lipids, sim.L, w_c=a.wc, kT=a.kt, dt=a.dt, seed=a.seed + 99)
    rn, ro, rs_ = metrics(rnd)
    rt = bilayer_signature(rnd)
    print(f"  CONTROLS  planted bilayer: nematic {pn:+.3f} opposed {po:.3f} "
          f"thickness {pt:.2f}")
    print(f"            random start   : nematic {rn:+.3f} opposed {ro:.3f} "
          f"thickness {rt:.2f}")
    print("   step    nematic  opposed  split   thick")
    for t in range(0, a.steps + 1, a.every):
        nem, opp, split = metrics(sim)
        th = bilayer_signature(sim)
        print(f"  {t:7d}   {nem:+.3f}   {opp:.3f}   {split:.3f}  {th:5.2f}", flush=True)
        if t < a.steps:
            for _ in range(a.every):
                sim.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
