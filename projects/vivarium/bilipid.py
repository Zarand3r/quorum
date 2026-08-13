"""M4: a TWO-SPECIES amphiphile that carries its own orientation, and can therefore curve.

Vivarium represents lipids as head/tail beads. YLZ, which is what finally produced vesicles, uses a
single species carrying an explicit orientation vector. This module is the bridge: it keeps the two
species and derives the orientation from them.

    molecule i  =  head h_i (species 1) + tail t_i (species 2), bonded
    centre      c_i = (h_i + t_i)/2
    axis        u_i = (h_i - t_i)/|h_i - t_i|

The inter-molecular interaction is the YLZ form evaluated on (c_i, u_i), with the bounded core from
M3 so no kernel diverges. Nothing is stored beyond bead positions: there are no quaternions and no
angular velocities, because the torque on a molecule emerges naturally as a force COUPLE on its two
beads. That is the point of using two species -- orientation is represented by the pair, not by an
extra state variable.

Why this rescues the head/tail representation. The reason our earlier DPD amphiphile could never
close was not that it had two species; it was that every interaction was isotropic between beads, so
nothing in the model referred to the molecular axis. Spontaneous curvature is

    beta (u_i - u_j) . r_hat

which is ODD under u -> -u. It therefore requires a signed axis, and the head/tail labels are exactly
what supply the sign: u points from tail to head, so a positive beta makes heads splay outward and
selects the sense of curvature. Two species are not an obstacle to curvature; they are what makes the
term meaningful.

Force chain rule, since both c and u depend on the bead positions:

    dc/dh = dc/dt = I/2
    du/dh = -du/dt = (I - u u^T)/|d|,   d = h - t

so with g_c = dU/dc and g_u = dU/du,

    F_h = -[ g_c/2 + (I - u u^T) g_u / |d| ]
    F_t = -[ g_c/2 - (I - u u^T) g_u / |d| ]

`check_gradients` verifies this against finite differences of the total energy, which is the only
way to catch a dropped projection in the chain rule.
"""

from __future__ import annotations

import numpy as np

from ylz import cell_pairs


class BiLipid:
    """Two-species amphiphiles with an orientation derived from the head-tail axis."""

    def __init__(self, n_mol, L, kT=0.1724, eps=1.0, sigma=1.0, zeta=4.5, mu=3.0, beta=0.1,
                 rc=2.6, bond_len=0.5, k_bond=100.0, contact=30.0,
                 dt=0.005, gamma=1.0, seed=0):
        self.rng = np.random.default_rng(seed)
        self.n_mol, self.L, self.dt, self.kT, self.gamma = n_mol, float(L), dt, kT, gamma
        self.eps, self.zeta, self.mu, self.beta, self.rc = eps, zeta, mu, beta, rc
        self.bond_len, self.k_bond = bond_len, k_bond
        self.rmin = 2.0 ** (1.0 / 6.0) * sigma
        self.contact = contact
        self.k_core = (contact + eps) / self.rmin ** 2

        c = self.rng.uniform(0, L, (n_mol, 3))
        u = self.rng.normal(size=(n_mol, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        self.h = (c + 0.5 * bond_len * u) % L
        self.t = (c - 0.5 * bond_len * u) % L
        self.vh = self.rng.normal(0.0, np.sqrt(kT), (n_mol, 3))
        self.vt = self.rng.normal(0.0, np.sqrt(kT), (n_mol, 3))
        self.species = np.tile([1, 2], n_mol)      # head=1, tail=2, interleaved

    # ---- geometry ----

    def frame(self):
        d = self.h - self.t
        d -= self.L * np.round(d / self.L)
        nd = np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        u = d / nd
        c = (self.t + 0.5 * d) % self.L
        return c, u, nd[:, 0]

    def _u_rep(self, r):
        return -self.eps + self.k_core * (self.rmin - r) ** 2

    def _du_rep(self, r):
        return -2.0 * self.k_core * (self.rmin - r)

    # ---- energy ----

    def energy(self):
        c, u, nd = self.frame()
        e_bond = float((0.5 * self.k_bond * (nd - self.bond_len) ** 2).sum())

        i, j = cell_pairs(c, self.L, self.rc)
        if not len(i):
            return e_bond
        rij = c[i] - c[j]
        rij -= self.L * np.round(rij / self.L)
        r = np.linalg.norm(rij, axis=1)
        m = (r < self.rc) & (r > 1e-9)
        i, j, rij, r = i[m], j[m], rij[m], r[m]
        if not len(i):
            return e_bond
        rhat = rij / r[:, None]
        ci = np.einsum("ic,ic->i", u[i], rhat)
        cj = np.einsum("ic,ic->i", u[j], rhat)
        a = np.einsum("ic,ic->i", u[i], u[j]) - ci * cj + self.beta * (ci - cj) - self.beta ** 2
        phi = 1.0 + self.mu * (a - 1.0)
        arg = 0.5 * np.pi * (r - self.rmin) / (self.rc - self.rmin)
        uA = -self.eps * np.cos(arg) ** (2 * self.zeta)
        near = r < self.rmin
        pair = np.where(near, self._u_rep(r) + (1.0 - phi) * self.eps, uA * phi)
        return e_bond + float(pair.sum())

    def forces(self):
        """Bead forces. Molecular torque emerges as a couple on the head and tail."""
        c, u, nd = self.frame()
        g_c = np.zeros_like(c)
        g_u = np.zeros_like(u)

        i, j = cell_pairs(c, self.L, self.rc)
        if len(i):
            rij = c[i] - c[j]
            rij -= self.L * np.round(rij / self.L)
            r = np.linalg.norm(rij, axis=1)
            m = (r < self.rc) & (r > 1e-9)
            i, j, rij, r = i[m], j[m], rij[m], r[m]
        if len(i):
            rhat = rij / r[:, None]
            ui, uj = u[i], u[j]
            ci = np.einsum("ic,ic->i", ui, rhat)
            cj = np.einsum("ic,ic->i", uj, rhat)
            a = np.einsum("ic,ic->i", ui, uj) - ci * cj + self.beta * (ci - cj) - self.beta ** 2
            phi = 1.0 + self.mu * (a - 1.0)

            near = r < self.rmin
            w = self.rc - self.rmin
            arg = 0.5 * np.pi * (r - self.rmin) / w
            cosa = np.cos(arg)
            uA = -self.eps * cosa ** (2 * self.zeta)
            duA = self.eps * self.zeta * np.pi / w * cosa ** (2 * self.zeta - 1) * np.sin(arg)

            dU_dr = np.where(near, self._du_rep(r), duA * phi)
            dU_da = self.mu * np.where(near, -self.eps, uA)

            da_drhat = -(cj[:, None] * ui + ci[:, None] * uj) + self.beta * (ui - uj)
            proj = da_drhat - (np.einsum("ic,ic->i", da_drhat, rhat))[:, None] * rhat
            dU_dci = dU_dr[:, None] * rhat + (dU_da / r)[:, None] * proj
            np.add.at(g_c, i, dU_dci)
            np.add.at(g_c, j, -dU_dci)

            np.add.at(g_u, i, dU_da[:, None] * (uj - cj[:, None] * rhat + self.beta * rhat))
            np.add.at(g_u, j, dU_da[:, None] * (ui - ci[:, None] * rhat - self.beta * rhat))

        # chain rule onto the two beads; the perpendicular projector is what makes it a couple
        perp = g_u - (np.einsum("ic,ic->i", g_u, u))[:, None] * u
        share = perp / nd[:, None]
        f_h = -(0.5 * g_c + share)
        f_t = -(0.5 * g_c - share)

        d = self.h - self.t
        d -= self.L * np.round(d / self.L)
        fb = (-self.k_bond * (nd - self.bond_len))[:, None] * (d / nd[:, None])
        return f_h + fb, f_t - fb

    # ---- integration ----

    def step(self):
        fh, ft = self.forces()
        self.vh += 0.5 * self.dt * fh
        self.vt += 0.5 * self.dt * ft
        self.h = (self.h + self.dt * self.vh) % self.L
        self.t = (self.t + self.dt * self.vt) % self.L
        fh, ft = self.forces()
        self.vh += 0.5 * self.dt * fh
        self.vt += 0.5 * self.dt * ft
        c1 = np.exp(-self.gamma * self.dt)
        sd = np.sqrt(self.kT * (1.0 - c1 * c1))
        self.vh = c1 * self.vh + sd * self.rng.normal(size=self.vh.shape)
        self.vt = c1 * self.vt + sd * self.rng.normal(size=self.vt.shape)

    def temperature(self):
        return float((self.vh ** 2).sum() + (self.vt ** 2).sum()) / (6 * self.n_mol)

    def positions_species(self):
        """Interleaved bead array for rendering and metrics: head, tail, head, tail, ..."""
        x = np.empty((2 * self.n_mol, 3))
        x[0::2], x[1::2] = self.h, self.t
        return x, self.species


def check_gradients(seed=0, n_mol=30, L=6.0, h=1e-6):
    s = BiLipid(n_mol, L, seed=seed, beta=0.15)
    fh, ft = s.forces()
    worst = 0.0
    for arr, f in ((s.h, fh), (s.t, ft)):
        for k in range(5):
            for cc in range(3):
                arr[k, cc] += h
                up = s.energy()
                arr[k, cc] -= 2 * h
                dn = s.energy()
                arr[k, cc] += h
                worst = max(worst, abs((-(up - dn) / (2 * h)) - f[k, cc]))
    return worst


if __name__ == "__main__":
    e = check_gradients()
    print(f"max |analytic bead force - numerical dU/dx| = {e:.3e}")
    print("PASS" if e < 1e-4 else "*** GRADIENT CHECK FAILED ***")
