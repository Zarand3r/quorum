"""M1 of ROADMAP_V2: the Yuan-Li-Zhang membrane potential, reimplemented in our own engine.

M0 established that stock LAMMPS `pair_style ylz` self-assembles vesicles in ~3 minutes. This module
reimplements the SAME potential with our own integrator and boundary conditions, so that a failure
downstream localises to our engine rather than to the physics. Nothing here is novel; the point is
that it should reproduce M0.

The potential, from the LAMMPS documentation and Yuan et al. (2010):

    U = u_R(r) + [1 - phi] eps                       r <  r_min
    U = u_A(r) phi                                   r_min < r < r_c

    u_R(r) = eps [ (r_min/r)^4 - 2 (r_min/r)^2 ]
    u_A(r) = -eps cos^(2 zeta)[ (pi/2) (r - r_min)/(r_c - r_min) ]
    phi    = 1 + mu (a - 1)
    a      = (n_i x r_hat).(n_j x r_hat) + beta (n_i - n_j).r_hat - beta^2

with r_min = 2^(1/6) sigma. Using the identity

    (n_i x r_hat).(n_j x r_hat) = n_i.n_j - (n_i.r_hat)(n_j.r_hat)

the angular function becomes, with ci = n_i.r_hat, cj = n_j.r_hat,

    a = n_i.n_j - ci cj + beta (ci - cj) - beta^2

which is the form differentiated below. mu sets bending rigidity, beta sets spontaneous curvature,
and zeta sets the width of the attractive well and hence in-plane diffusivity.

Why this potential is the right bridge for this project: it is bounded and finite at contact, it
uses ONE particle per lipid patch so the particle count is fixed and small, and its angular part is
built entirely from inner products between per-particle orientation vectors modulated by a
relative-position direction -- the algebra attention already performs.

Correctness here is not assumed. `check_gradients()` compares the analytic force and torque against
finite differences of U, which is the only way to catch a sign or projection error in an anisotropic
potential; such an error typically still produces plausible-looking aggregates.
"""

from __future__ import annotations

import numpy as np


def cell_pairs(x, L, rc):
    """Pairs within rc via a cell list, each unordered pair emitted once.

    Same forward-half scheme validated against brute force in dpd_reference: visit the self cell and
    the lexicographically forward half of the 3^D offsets, so no pair is produced twice. Kept local
    rather than imported because dpd_reference's version is a method bound to that class's state.
    """
    n, D = len(x), x.shape[1]
    ncell = max(3, int(L / rc))
    cs = L / ncell
    cell = (x / cs).astype(np.int64) % ncell
    mult = ncell ** np.arange(D)[::-1]
    flat = (cell * mult).sum(axis=1)
    order = np.argsort(flat, kind="stable")
    counts = np.bincount(flat, minlength=ncell ** D)
    starts = np.concatenate([[0], np.cumsum(counts)])

    offs = np.array(np.meshgrid(*([(-1, 0, 1)] * D), indexing="ij")).reshape(D, -1).T
    offs = offs[(offs * (3 ** np.arange(D))).sum(axis=1) >= 0]
    ar = np.arange(n)
    I, J = [], []
    for off in offs:
        nb = (((cell + off) % ncell) * mult).sum(axis=1)
        cnt = counts[nb]
        if not cnt.any():
            continue
        i_idx = np.repeat(ar, cnt)
        base = np.repeat(starts[nb], cnt)
        within = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        j_idx = order[base + within]
        keep = i_idx < j_idx if not off.any() else np.ones(len(i_idx), bool)
        if keep.any():
            I.append(i_idx[keep])
            J.append(j_idx[keep])
    if not I:
        e = np.zeros(0, np.int64)
        return e, e
    return np.concatenate(I), np.concatenate(J)


class YLZ:
    """Yuan-Li-Zhang particles: position plus a unit orientation, with a Langevin thermostat.

    Rotational state is a unit vector n and an angular velocity w kept perpendicular to n, since the
    particles are uniaxial and spin about n is unobservable. Both translational and rotational
    degrees of freedom are thermostatted, otherwise the orientations freeze and the membrane cannot
    be fluid.
    """

    def __init__(self, n_part, L, kT=0.1724, eps=1.0, sigma=1.0, zeta=4.5, mu=3.0, beta=0.1,
                 rc=2.6, dt=0.01, gamma=1.0, seed=0, bounded_core=False, contact=3.0):
        self.rng = np.random.default_rng(seed)
        self.n, self.L, self.dt, self.kT, self.gamma = n_part, float(L), dt, kT, gamma
        self.eps, self.zeta, self.mu, self.beta, self.rc = eps, zeta, mu, beta, rc
        self.rmin = 2.0 ** (1.0 / 6.0) * sigma
        # M3 of ROADMAP_V2. Published YLZ uses u_R = eps[(rmin/r)^4 - 2(rmin/r)^2], which DIVERGES
        # as r^-4 at contact (u_R(0.01) ~ 1.6e8). Vivarium forbids divergent kernels, so the core
        # must be replaced by a bounded one. The harmonic below is matched to the original in value,
        # slope and curvature at rmin -- u_R(rmin) = -eps, u_R'(rmin) = 0 (rmin is the minimum), and
        # u_R''(rmin) = 8 eps/rmin^2 -- so k = 4 eps/rmin^2 and the contact energy is a finite 3 eps.
        # Everything else about the model is untouched, so a change in outcome is attributable to
        # this substitution alone.
        # `contact` is the finite energy at r=0 in units of eps. u(0) = -eps + k rmin^2, so
        # k = (contact + eps)/rmin^2. contact=3 reproduces the curvature-matched harmonic, which
        # collapses; the scan asks whether a stiffer bounded barrier both prevents collapse and
        # preserves vesiculation.
        self.bounded_core = bool(bounded_core)
        self.contact = float(contact)
        self.k_core = (self.contact + eps) / self.rmin ** 2
        self.x = self.rng.uniform(0, L, (n_part, 3))
        self.v = self.rng.normal(0.0, np.sqrt(kT), (n_part, 3))
        self.v -= self.v.mean(axis=0)
        nn = self.rng.normal(size=(n_part, 3))
        self.nhat = nn / np.linalg.norm(nn, axis=1, keepdims=True)
        self.w = np.zeros((n_part, 3))
        self._f = None
        self._tq = None
        self._perp_w()

    def _perp_w(self):
        self.w -= (np.einsum("ic,ic->i", self.w, self.nhat))[:, None] * self.nhat

    # ---- potential ----

    def _pair_terms(self, i, j):
        rij = self.x[i] - self.x[j]
        rij -= self.L * np.round(rij / self.L)
        r = np.linalg.norm(rij, axis=1)
        m = (r < self.rc) & (r > 1e-9)
        return i[m], j[m], rij[m], r[m]

    def energy(self):
        i, j = cell_pairs(self.x, self.L, self.rc)
        if not len(i):
            return 0.0
        i, j, rij, r = self._pair_terms(i, j)
        if not len(i):
            return 0.0
        rhat = rij / r[:, None]
        ni, nj = self.nhat[i], self.nhat[j]
        ci = np.einsum("ic,ic->i", ni, rhat)
        cj = np.einsum("ic,ic->i", nj, rhat)
        a = np.einsum("ic,ic->i", ni, nj) - ci * cj + self.beta * (ci - cj) - self.beta ** 2
        phi = 1.0 + self.mu * (a - 1.0)
        uR = self._u_rep(r)
        arg = 0.5 * np.pi * (r - self.rmin) / (self.rc - self.rmin)
        uA = -self.eps * np.cos(arg) ** (2 * self.zeta)
        near = r < self.rmin
        return float(np.where(near, uR + (1.0 - phi) * self.eps, uA * phi).sum())

    def _u_rep(self, r):
        if self.bounded_core:
            return -self.eps + self.k_core * (self.rmin - r) ** 2
        return self.eps * ((self.rmin / r) ** 4 - 2.0 * (self.rmin / r) ** 2)

    def _du_rep(self, r):
        if self.bounded_core:
            return -2.0 * self.k_core * (self.rmin - r)
        return self.eps * (-4.0 * self.rmin ** 4 / r ** 5 + 4.0 * self.rmin ** 2 / r ** 3)

    def forces_torques(self):
        """Analytic dU/dx and dU/dn, converted to force and torque. Verified in check_gradients()."""
        f = np.zeros_like(self.x)
        tq = np.zeros_like(self.x)
        i, j = cell_pairs(self.x, self.L, self.rc)
        if not len(i):
            return f, tq
        i, j, rij, r = self._pair_terms(i, j)
        if not len(i):
            return f, tq
        rhat = rij / r[:, None]
        ni, nj = self.nhat[i], self.nhat[j]
        ci = np.einsum("ic,ic->i", ni, rhat)
        cj = np.einsum("ic,ic->i", nj, rhat)
        a = np.einsum("ic,ic->i", ni, nj) - ci * cj + self.beta * (ci - cj) - self.beta ** 2
        phi = 1.0 + self.mu * (a - 1.0)

        near = r < self.rmin
        w = self.rc - self.rmin
        arg = 0.5 * np.pi * (r - self.rmin) / w
        cosa = np.cos(arg)
        uA = -self.eps * cosa ** (2 * self.zeta)
        # d uA/dr = -eps * 2 zeta cos^(2zeta-1) * (-sin) * (pi/2w) = eps zeta pi/w cos^(2zeta-1) sin
        duA = self.eps * self.zeta * np.pi / w * cosa ** (2 * self.zeta - 1) * np.sin(arg)
        duR = self._du_rep(r)

        dU_dr = np.where(near, duR, duA * phi)          # radial part at fixed orientation
        dU_dphi = np.where(near, -self.eps, uA)
        dU_da = self.mu * dU_dphi

        # angular dependence enters x through r_hat
        da_drhat = -(cj[:, None] * ni + ci[:, None] * nj) + self.beta * (ni - nj)
        # d r_hat / d r_i = (I - r_hat r_hat^T)/r
        proj = da_drhat - (np.einsum("ic,ic->i", da_drhat, rhat))[:, None] * rhat
        dU_dxi = dU_dr[:, None] * rhat + (dU_da / r)[:, None] * proj

        np.add.at(f, i, -dU_dxi)
        np.add.at(f, j, dU_dxi)

        # torques: tau = -n x dU/dn
        dU_dni = dU_da[:, None] * (nj - cj[:, None] * rhat + self.beta * rhat)
        dU_dnj = dU_da[:, None] * (ni - ci[:, None] * rhat - self.beta * rhat)
        np.add.at(tq, i, -np.cross(ni, dU_dni))
        np.add.at(tq, j, -np.cross(nj, dU_dnj))
        return f, tq

    # ---- integration ----

    def step(self):
        """Velocity-Verlet on conservative forces, then an EXACT Ornstein-Uhlenbeck thermostat.

        The first version folded Langevin friction and noise into BOTH half-kicks, which applies the
        noise twice at half weight and yields a variance of gamma*kT*dt instead of 2*gamma*kT*dt.
        It measured T = 0.091 against a target of 0.1724 -- almost exactly half, the same signature
        as the DPD thermostat bug recorded in dpd_reference.step (T = 0.51 against 1.0). Splitting
        the conservative and stochastic parts removes the ambiguity: the OU update below is exact for
        any dt, so temperature no longer depends on the timestep.

        The conservative force is carried across steps, so there is one force evaluation per step.
        """
        if self._f is None:
            self._f, self._tq = self.forces_torques()
        self.v += 0.5 * self.dt * self._f
        self.w += 0.5 * self.dt * self._tq
        self._perp_w()
        self.x = (self.x + self.dt * self.v) % self.L
        self.nhat = self.nhat + self.dt * np.cross(self.w, self.nhat)
        self.nhat /= np.linalg.norm(self.nhat, axis=1, keepdims=True)

        self._f, self._tq = self.forces_torques()
        self.v += 0.5 * self.dt * self._f
        self.w += 0.5 * self.dt * self._tq

        c1 = np.exp(-self.gamma * self.dt)
        sd = np.sqrt(self.kT * (1.0 - c1 * c1))
        self.v = c1 * self.v + sd * self.rng.normal(size=self.v.shape)
        self.w = c1 * self.w + sd * self.rng.normal(size=self.w.shape)
        self._perp_w()

    def temperature(self):
        return float((self.v ** 2).sum() / (3 * self.n))


def check_gradients(seed=0, n_part=40, L=6.0, h=1e-6):
    """Analytic force and torque against finite differences of U.

    An anisotropic potential with a wrong sign or a missing projection still produces plausible
    aggregates, so this is the only honest way to know the port is faithful before running it.
    """
    s = YLZ(n_part, L, seed=seed, beta=0.15)
    f, tq = s.forces_torques()

    err_f = 0.0
    for k in range(6):
        for c in range(3):
            s.x[k, c] += h
            up = s.energy()
            s.x[k, c] -= 2 * h
            dn = s.energy()
            s.x[k, c] += h
            err_f = max(err_f, abs((-(up - dn) / (2 * h)) - f[k, c]))

    err_t = 0.0
    for k in range(6):
        for c in range(3):
            axis = np.zeros(3)
            axis[c] = 1.0
            n0 = s.nhat[k].copy()
            for sgn in (+1, -1):
                nn = n0 + sgn * h * np.cross(axis, n0)
                s.nhat[k] = nn / np.linalg.norm(nn)
                if sgn > 0:
                    up = s.energy()
                else:
                    dn = s.energy()
            s.nhat[k] = n0
            err_t = max(err_t, abs((-(up - dn) / (2 * h)) - tq[k, c]))
    return err_f, err_t


if __name__ == "__main__":
    ef, et = check_gradients()
    print(f"max |analytic force  - numerical dU/dx| = {ef:.3e}")
    print(f"max |analytic torque - numerical dU/dn| = {et:.3e}")
    print("PASS" if ef < 1e-4 and et < 1e-4 else "*** GRADIENT CHECK FAILED ***")
