"""Groot-Warren DPD: the bounded-force reference. Stage D of docs/ROADMAP_RESET.md.

This is deliberately OUTSIDE the transformer constraint. Plain numpy, ordinary pair loops, a real
DPD thermostat. Same role `cooke_deserno.py` plays for conventional forces: answer "is this reachable
at all?" with a known-good model, so that a later failure inside Vivarium localises to the engine or
to the architecture rather than to the physics.

Why DPD specifically. Vivarium's excluded volume is already bounded and pairwise-additive (measured:
total repulsion grows 7.74x from z=1 to z=32), so boundedness is not what broke the solvent. What
differs is CALIBRATION: Vivarium's `repel` was chosen, DPD's `a` is fitted to a target
compressibility. DPD is the existence proof that bounded soft forces support amphiphilic mesophases,
so it separates "bounded forces cannot" from "these parameters do not".

Three pair forces, all cut off at rc:

    F_C = a_ij (1 - r/rc) r_hat                    conservative, finite at r=0
    F_D = -gamma w(r)^2 (r_hat . v_ij) r_hat       dissipative
    F_R = sigma w(r) theta / sqrt(dt) r_hat        random

with w(r) = 1 - r/rc and sigma^2 = 2 gamma kT. The last relation is fluctuation-dissipation: the same
gamma that damps sets the noise, which is what gives DPD a genuine temperature. Vivarium's `speed`
defect was exactly a violation of that coupling, so it is worth stating explicitly here.

All three are pairwise and antisymmetric, so momentum is conserved exactly and the thermostat is
Galilean-invariant -- the property an ordinary Langevin bath does not have.
"""

from __future__ import annotations

import numpy as np


class DPD:
    """Groot-Warren DPD in 2 or 3 dimensions, species-dependent repulsion, harmonic bonds.

    3-D matters: essentially all open-source DPD vesicle work is 3-D. A 2-D "vesicle" is a closed
    RING, a different and far less studied object, and a planted one dissolved at 8 of 9 parameter
    sets tested here. See DECISIONS.md D7.
    """

    def __init__(self, n, L, kT=1.0, rc=1.0, gamma=4.5, dt=0.02, seed=0,
                 species=None, a_matrix=None, a=25.0, bonds=None, k_bond=100.0, r0=0.7, dim=2):
        self.rng = np.random.default_rng(seed)
        self.n, self.L, self.rc, self.kT, self.gamma, self.dt = n, float(L), rc, kT, gamma, dt
        self.dim = int(dim)
        self.sigma = np.sqrt(2.0 * gamma * kT)
        self.x = self.rng.uniform(0, L, (n, self.dim))
        self.v = self.rng.normal(0.0, np.sqrt(kT), (n, self.dim))
        self.v -= self.v.mean(axis=0)                     # zero net momentum
        self.species = np.zeros(n, int) if species is None else np.asarray(species, int)
        ns = int(self.species.max()) + 1
        self.a = np.full((ns, ns), float(a)) if a_matrix is None else np.asarray(a_matrix, float)
        assert np.allclose(self.a, self.a.T), "conservative matrix must be symmetric"
        self._f = None
        self.angles = np.zeros((0, 3), int)   # (i, j, k) triples, j is the vertex
        self.k_ang = 0.0
        self.bonds = np.zeros((0, 2), int) if bonds is None else np.asarray(bonds, int)
        self.k_bond, self.r0 = k_bond, r0

    def _pairs(self):
        """Pairs within rc via a CELL LIST: O(N) instead of O(N^2).

        A 2-D vesicle is a closed ring, so it needs a ribbon with ENDS -- and at N=1200 the aggregates
        span the periodic box instead, leaving nothing to join. Reaching finite aggregates means a
        bigger box at the same concentration, and the full (N,N) matrix is 200 MB at N=5000. Cells of
        side >= rc mean each particle only checks its own cell and the 8 around it.

        Verified against the O(N^2) path in `pairs_match_bruteforce` below.
        """
        L, rc, n, D = self.L, self.rc, self.n, self.dim
        ncell = max(3, int(L / rc))
        cs = L / ncell
        cell = (self.x / cs).astype(np.int64) % ncell
        mult = ncell ** np.arange(D)[::-1]
        flat = (cell * mult).sum(axis=1)
        order = np.argsort(flat, kind="stable")
        counts = np.bincount(flat, minlength=ncell ** D)
        starts = np.concatenate([[0], np.cumsum(counts)])

        I, J = [], []
        ar = np.arange(n)
        offs = np.array(np.meshgrid(*([(-1, 0, 1)] * D), indexing="ij")).reshape(D, -1).T
        for off in offs:
            nb = (((cell + off) % ncell) * mult).sum(axis=1)
            cnt = counts[nb]
            if not cnt.any():
                continue
            i_idx = np.repeat(ar, cnt)
            base = np.repeat(starts[nb], cnt)
            within = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
            j_idx = order[base + within]
            keep = i_idx < j_idx
            if keep.any():
                I.append(i_idx[keep]); J.append(j_idx[keep])
        if not I:
            e = np.zeros(0, np.int64)
            return e, e, np.zeros((0, D)), np.zeros(0)
        i = np.concatenate(I); j = np.concatenate(J)
        rij = self.x[i] - self.x[j]
        rij -= L * np.round(rij / L)
        r2 = np.einsum("ic,ic->i", rij, rij)
        m = r2 < rc ** 2
        return i[m], j[m], rij[m], np.maximum(np.sqrt(r2[m]), 1e-9)

    def pairs_bruteforce(self):
        """Reference O(N^2) pair list, kept so the cell list can be validated against it."""
        d = self.x[:, None, :] - self.x[None, :, :]
        d -= self.L * np.round(d / self.L)
        r2 = np.einsum("ijc,ijc->ij", d, d)
        iu = np.triu_indices(self.n, 1)
        m = r2[iu] < self.rc ** 2
        return iu[0][m], iu[1][m]

    def forces(self, with_dissipative=True):
        """Returns (force, virial). Virial gives the pressure via the standard 2-D relation."""
        f = np.zeros_like(self.x)
        i, j, rij, r = self._pairs()
        w = 1.0 - r / self.rc
        rhat = rij / r[:, None]

        aij = self.a[self.species[i], self.species[j]]
        fc = (aij * w)[:, None] * rhat                       # conservative

        pair = fc
        if with_dissipative:
            vij = self.v[i] - self.v[j]
            rv = np.einsum("ic,ic->i", rhat, vij)
            fd = -(self.gamma * w ** 2 * rv)[:, None] * rhat
            theta = self.rng.normal(0.0, 1.0, len(r))
            fr = (self.sigma * w * theta / np.sqrt(self.dt))[:, None] * rhat
            pair = pair + fd + fr

        np.add.at(f, i, pair)
        np.add.at(f, j, -pair)                                # Newton's third law, exactly

        virial = float(np.einsum("ic,ic->", rij, fc))         # conservative part only
        if len(self.angles) and self.k_ang > 0.0:
            # THREE-BODY BENDING, the ingredient published DPD membrane models have and mine did not.
            # U = k3 (1 + cos psi) with psi the angle at the vertex measured between the two bond
            # vectors, so straight (cos psi = -1) is the minimum. Fully flexible tails coil instead of
            # packing into leaflets, which is exactly what the amorphous blobs looked like.
            a_, b_, c_ = self.angles[:, 0], self.angles[:, 1], self.angles[:, 2]
            r1 = self.x[a_] - self.x[b_]
            r2 = self.x[c_] - self.x[b_]
            r1 -= self.L * np.round(r1 / self.L)
            r2 -= self.L * np.round(r2 / self.L)
            n1 = np.linalg.norm(r1, axis=1) + 1e-12
            n2 = np.linalg.norm(r2, axis=1) + 1e-12
            cos = np.einsum("ic,ic->i", r1, r2) / (n1 * n2)
            # dU/dcos = k3; forces follow the standard angle-gradient expressions
            g1 = -self.k_ang * (r2 / (n1 * n2)[:, None] - (cos / n1 ** 2)[:, None] * r1)
            g2 = -self.k_ang * (r1 / (n1 * n2)[:, None] - (cos / n2 ** 2)[:, None] * r2)
            np.add.at(f, a_, g1)
            np.add.at(f, c_, g2)
            np.add.at(f, b_, -(g1 + g2))      # vertex takes the reaction: net force is zero
        if len(self.bonds):
            b = self.bonds
            db = self.x[b[:, 0]] - self.x[b[:, 1]]
            db -= self.L * np.round(db / self.L)
            rb = np.maximum(np.linalg.norm(db, axis=1), 1e-9)
            fb = (-self.k_bond * (rb - self.r0))[:, None] * (db / rb[:, None])
            np.add.at(f, b[:, 0], fb)
            np.add.at(f, b[:, 1], -fb)
            virial += float(np.einsum("ic,ic->", db, fb))
        return f, virial

    def step(self):
        """Velocity-Verlet carrying the force across steps: ONE force evaluation per step.

        The random force must enter the integration exactly once per dt. A naive two-evaluation
        Verlet draws it twice, giving two kicks of dt/2 with variance sigma^2/dt -- total
        0.5*dt*sigma^2 instead of dt*sigma^2, i.e. half the intended noise, which measured as
        T = 0.51 against a target of 1.0. Reusing the draw across the two calls does NOT fix it,
        because the pair list changes when positions move between them and the noise vector no longer
        matches. Carrying the force forward avoids the problem entirely, and halves the cost.
        """
        if self._f is None:
            self._f, _ = self.forces()
        self.v += 0.5 * self.dt * self._f
        self.x = (self.x + self.dt * self.v) % self.L
        self._f, _ = self.forces()                    # one draw, one evaluation, per step
        self.v += 0.5 * self.dt * self._f

    # ---- diagnostics: the solvent gate from docs/ROADMAP_RESET.md ----

    def temperature(self):
        return float((self.v ** 2).sum() / (self.dim * self.n))   # dim dof per particle

    def pressure(self):
        _, vir = self.forces(with_dissipative=False)
        rho = self.n / self.L ** 2
        vol = self.L ** self.dim
        return self.n / vol * self.temperature() + vir / (self.dim * vol)

    def rdf(self, bins=60, rmax=None):
        rmax = rmax or 3.0 * self.rc
        d = self.x[:, None, :] - self.x[None, :, :]
        d -= self.L * np.round(d / self.L)
        r = np.linalg.norm(d, axis=2)[np.triu_indices(self.n, 1)]
        r = r[r < rmax]
        hist, edges = np.histogram(r, bins=bins, range=(0.0, rmax))
        c = 0.5 * (edges[1:] + edges[:-1])
        rho = self.n / self.L ** 2
        norm = np.pi * (edges[1:] ** 2 - edges[:-1] ** 2) * rho * self.n / 2.0
        return c, hist / np.maximum(norm, 1e-12)

    def nn_stats(self):
        d = self.x[:, None, :] - self.x[None, :, :]
        d -= self.L * np.round(d / self.L)
        D = np.linalg.norm(d, axis=2)
        np.fill_diagonal(D, np.inf)
        nn = D.min(axis=1)
        return float(np.median(nn)), float((nn < 0.3 * self.rc).mean())

    def density_homogeneity(self, cells=6):
        """Std/mean of cell occupancy. A condensing solvent shows this growing without bound."""
        idx = (self.x / self.L * cells).astype(int) % cells
        m = cells ** np.arange(self.dim)[::-1]
        flat = (idx * m).sum(axis=1)
        counts = np.bincount(flat, minlength=cells ** self.dim).astype(float)
        return float(counts.std() / max(counts.mean(), 1e-9))
