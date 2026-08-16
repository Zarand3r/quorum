"""Vivarium's interactions as ONE scalar energy with ONE length scale, differentiated for forces.

WHY THIS EXISTS

The engine in `pack.py` assembles forces by hand from seven independent multipliers -- `repel`,
`attract`, `k_bond`, `polarity`, `hydrophobic`, `satt`, `head_q` -- with no shared length scale. Three
consequences were measured, not guessed:

  * The multipliers are a coupled ensemble. Correcting excluded volume (which was ~4x too weak, beads
    at 0.36 of contact) immediately overpowered `k_bond`, tearing molecules apart at bond mean 1.20,
    and then overpowered `polarity` and `hydrophobic`. Every fix broke something else.
  * Because nothing is anchored to a shared scale, no single physical fact can be imported from a
    reference model. The oracle has one potential with one length scale, so its epsilon, sigma and
    r_min are anchored to each other and travel together.
  * Hand-derived gradients are error-prone. Three chain-rule bugs appeared in one function in this
    project, each caught only by a numerical check.

This module replaces that with a scalar `energy(X)` and its exact gradient. Forces are `-dU/dX` by
construction, so they cannot disagree with any energy, and `check_gradients` proves the derivative.

THE FORM, AND WHY IT IS TRANSFORMER-ONLY

Every non-bonded pair contributes

    U_ij = eps * [ core(r/sigma) + well(r/sigma) * chi_ij ]

with a single energy scale `eps`, a single length `sigma`, and a dimensionless chemistry factor
`chi_ij` that depends only on which species the two beads are. `chi` is a symmetric 3x3 matrix over
(head, tail, water), and it factors as

    chi_ij = q_i . k_j        with   q = E @ sqrtm(chi),  k = E,   E = species one-hot

so the content term is a query-key inner product and the radial factor is a distance kernel over
positions. The whole energy is therefore one unnormalized distance-penalized attention layer -- the
same identity already verified for YLZ at 1.6e-16 in `attention_ylz.py`. No divergent kernels, no
per-pair branching, fixed token count.

WHAT IS DELIBERATELY ABSENT

There is no orientation term and no curvature term. Bead orientation never enters the energy, so
spontaneous curvature cannot be imported through a `beta`-like parameter. Amphiphilicity comes only
from `chi`: heads attract water, tails do not. If a curved membrane appears, it emerged from shape and
packing, which is the whole point of a bottom-up model.

UNITS

`eps` and `sigma` set energy and length. Everything else is a ratio: `chi` is dimensionless, the bond
constant is given in `eps/sigma^2`, and temperature in `eps`. Changing `eps` or `sigma` rescales the
model coherently instead of unbalancing it.
"""

from __future__ import annotations

import numpy as np

HEAD, TAIL, WATER = 0, 1, 2
N_SPECIES = 3


def default_chi():
    """Dimensionless pair affinities. Positive = attract, zero = no attraction beyond the core.

    Only the amphiphile's defining asymmetry is encoded: tails attract tails and avoid water, heads
    are comfortable in water. These are ratios to `eps`, so they stay balanced when `eps` moves.
    """
    chi = np.zeros((N_SPECIES, N_SPECIES))
    chi[TAIL, TAIL] = 1.00                       # the hydrophobic driving force
    chi[HEAD, HEAD] = 0.20
    chi[WATER, WATER] = 0.40
    chi[HEAD, WATER] = chi[WATER, HEAD] = 0.60   # heads are solvated
    chi[HEAD, TAIL] = chi[TAIL, HEAD] = 0.20
    chi[TAIL, WATER] = chi[WATER, TAIL] = 0.00   # tails gain nothing from water
    return chi


def qk_factors(chi):
    """Split chi into query and key matrices so the content term is an inner product.

    chi is symmetric, so chi = V diag(w) V^T. Writing S = V diag(sign(w)) and A = V diag(sqrt(|w|)),
    q_i = A^T e_i and k_j = (S A)^T e_j give q_i . k_j = chi_ij exactly, including for the negative
    eigenvalues a real square root cannot represent.
    """
    w, V = np.linalg.eigh(chi)
    A = V * np.sqrt(np.abs(w))[None, :]
    S = V * np.sign(w)[None, :]
    q = A                                   # row i is q for species i
    k = S * np.sqrt(np.abs(w))[None, :]
    return q, k


def _core(s):
    """Bounded repulsive core and its derivative, in units where contact is s = 1.

    Bounded rather than divergent: the r^-12 and r^-4 cores both need a timestep far smaller than this
    engine uses, and bounded cores in the 30-300 eps range were measured to hold a membrane open.

    QUADRATIC in the overlap, so the force is linear in overlap (the DPD form). A quartic was tried
    first and is too soft near contact: at s = 0.67 it costs 0.7 eps, about 2 kT, so beads compress
    through it freely and packing sat at 0.67. The quadratic costs 6.5 eps there, about 18 kT, while
    still reaching only CORE_HEIGHT at full overlap so the timestep stays usable. The force vanishes
    continuously at s = 1.
    """
    u = np.zeros_like(s)
    du = np.zeros_like(s)
    m = s < 1.0
    x = 1.0 - s[m]
    u[m] = CORE_HEIGHT * x ** 2
    du[m] = -2.0 * CORE_HEIGHT * x
    return u, du


def _well(s, rc):
    """Attractive well and its derivative: a smooth cosine tail from contact out to the cutoff.

    -1 at contact, 0 with zero slope at rc, so forces vanish continuously at the cutoff and no energy
    jump is introduced by truncation.
    """
    u = np.zeros_like(s)
    du = np.zeros_like(s)
    m = (s >= 1.0) & (s < rc)
    z = (s[m] - 1.0) / (rc - 1.0)
    u[m] = -0.5 * (1.0 + np.cos(np.pi * z))
    du[m] = 0.5 * np.pi * np.sin(np.pi * z) / (rc - 1.0)
    inner = s < 1.0
    u[inner] = -1.0
    return u, du


CORE_HEIGHT = 60.0          # in eps; the barrier at full overlap


class Field:
    """Scalar energy over bead positions, plus its exact gradient.

    Positions are (n, d). `species` is (n,) of HEAD/TAIL/WATER. `bonds` is (m, 2) index pairs with a
    single rest length; molecules are chains of beads and nothing else distinguishes them.
    """

    def __init__(self, species, bonds, L, eps=1.0, sigma=1.0, rc=2.5, k_bond=200.0,
                 r_bond=1.0, chi=None):
        self.species = np.asarray(species, dtype=np.int64)
        self.bonds = np.asarray(bonds, dtype=np.int64).reshape(-1, 2)
        self.L = float(L)
        self.eps, self.sigma, self.rc = float(eps), float(sigma), float(rc)
        self.k_bond, self.r_bond = float(k_bond), float(r_bond)
        self.chi = default_chi() if chi is None else np.asarray(chi, dtype=float)
        if not np.allclose(self.chi, self.chi.T):
            raise ValueError("chi must be symmetric: U_ij and U_ji are the same pair")
        self.q, self.k = qk_factors(self.chi)

    # ---- the attention view -------------------------------------------------

    def content(self):
        """The per-pair chemistry as a query-key inner product, (n, n)."""
        Q, K = self.q[self.species], self.k[self.species]
        return Q @ K.T

    def check_identity(self):
        """Max |q_i.k_j - chi_ij| over all species pairs. Proves the factorization is exact."""
        Q, K = self.q, self.k
        return float(np.abs(Q @ K.T - self.chi).max())

    # ---- energy and gradient ------------------------------------------------

    # ---- neighbour list -----------------------------------------------------
    #
    # Pairs beyond rc contribute exactly zero, so only near pairs need visiting. The candidate list is
    # rebuilt densely -- O(n^2), but only every few dozen steps -- out to rc + skin, and reused in
    # between. A rebuild is triggered by ACCUMULATED displacement rather than a fixed period: once any
    # bead has moved skin/2, a pair that was outside rc + skin could have come inside rc, so the list
    # is no longer a superset and must be rebuilt. `check_neighbor_list` proves the sparse path agrees
    # with the dense one.

    SKIN = 0.6
    CHUNK = 512

    def _rebuild(self, X):
        """Candidate pairs within rc + skin, built in row blocks so memory is bounded.

        The whole-array form allocates (n, n, d) doubles -- 864 MB at n = 6000 in 3-D -- which caps
        the system size far below what a 3-D vesicle needs. Blocking makes the cost O(n^2) in time but
        O(CHUNK * n) in memory. Rebuilds are rare: a bead must diffuse skin/2 before the list can go
        stale, which at these settings is several hundred steps.
        """
        n = len(X)
        cut = (self.rc * self.sigma + self.SKIN) ** 2
        pis, pjs = [], []
        for lo in range(0, n, self.CHUNK):
            hi = min(lo + self.CHUNK, n)
            d = X[lo:hi, None, :] - X[None, :, :]
            d -= self.L * np.round(d / self.L)
            r2 = np.einsum("ijc,ijc->ij", d, d)
            rows, cols = np.nonzero(r2 < cut)
            rows = rows + lo
            keep = rows < cols                      # upper triangle only, so each pair appears once
            pis.append(rows[keep])
            pjs.append(cols[keep])
        self._pi = np.concatenate(pis) if pis else np.zeros(0, int)
        self._pj = np.concatenate(pjs) if pjs else np.zeros(0, int)
        self._anchor = X.copy()

    def _pairs(self, X):
        need = not hasattr(self, "_pi") or len(self._anchor) != len(X)
        if not need:
            dsp = X - self._anchor
            dsp -= self.L * np.round(dsp / self.L)
            need = float(np.sqrt(np.einsum("ic,ic->i", dsp, dsp)).max()) > 0.5 * self.SKIN
        if need:
            self._rebuild(X)
        d = X[self._pi] - X[self._pj]
        d -= self.L * np.round(d / self.L)
        r = np.linalg.norm(d, axis=1)
        return d, r, (self._pi, self._pj)

    def _dense_pairs(self, X):
        d = X[:, None, :] - X[None, :, :]
        d -= self.L * np.round(d / self.L)
        r = np.linalg.norm(d, axis=2)
        iu = np.triu_indices(len(X), k=1)
        return d[iu], r[iu], iu

    def energy(self, X):
        d, r, iu = self._pairs(X)
        s = r / self.sigma
        uc, _ = _core(s)
        uw, _ = _well(s, self.rc)
        chi = self.content()[iu]
        u = self.eps * (uc + uw * chi)
        e = float(u[r < self.rc * self.sigma].sum())
        if len(self.bonds):
            bd = X[self.bonds[:, 0]] - X[self.bonds[:, 1]]
            bd -= self.L * np.round(bd / self.L)
            br = np.linalg.norm(bd, axis=1)
            e += float((0.5 * self.k_bond * (br - self.r_bond) ** 2).sum())
        return e

    def forces(self, X):
        """-dU/dX, analytic. Verified against finite differences by `check_gradients`."""
        n = len(X)
        d, r, iu = self._pairs(X)
        s = r / self.sigma
        _, duc = _core(s)
        uw, duw = _well(s, self.rc)
        chi = self.content()[iu]
        # dU/dr, guarding r = 0 where the direction is undefined
        dudr = self.eps * (duc + duw * chi) / self.sigma
        dudr = np.where(r < self.rc * self.sigma, dudr, 0.0)
        safe = np.maximum(r, 1e-12)
        coef = (dudr / safe)[:, None]
        pf = -coef * d                       # force on i from j
        F = np.zeros_like(X)
        np.add.at(F, iu[0], pf)
        np.add.at(F, iu[1], -pf)
        if len(self.bonds):
            bd = X[self.bonds[:, 0]] - X[self.bonds[:, 1]]
            bd -= self.L * np.round(bd / self.L)
            br = np.linalg.norm(bd, axis=1)
            bsafe = np.maximum(br, 1e-12)
            bf = (-self.k_bond * (br - self.r_bond) / bsafe)[:, None] * bd
            np.add.at(F, self.bonds[:, 0], bf)
            np.add.at(F, self.bonds[:, 1], -bf)
        return F


def check_neighbor_list(seed=0, n=120, d=2, L=12.0):
    """Max |sparse - dense| for energy and for the force array. Must be exactly zero up to rounding."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(0.0, L, size=(n, d))
    species = rng.integers(0, N_SPECIES, size=n)
    f = Field(species, np.zeros((0, 2), int), L)
    e_sparse, F_sparse = f.energy(X), f.forces(X)

    class Dense(Field):
        def _pairs(self, X):
            return self._dense_pairs(X)

    g = Dense(species, np.zeros((0, 2), int), L)
    return max(abs(e_sparse - g.energy(X)), float(np.abs(F_sparse - g.forces(X)).max()))


def check_gradients(seed=0, n=24, d=2, L=8.0, h=1e-6):
    """Max |analytic force + numerical dU/dx|. The only claim this module makes about itself."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(0.0, L, size=(n, d))
    species = np.array([HEAD, TAIL, TAIL] * (n // 6) + [WATER] * (n - 3 * (n // 6)))
    bonds = np.array([[i, i + 1] for i in range(0, 3 * (n // 6) - 1, 3)])
    f = Field(species, bonds, L)
    F = f.forces(X)
    worst = 0.0
    for i in range(min(n, 12)):
        for c in range(d):
            X[i, c] += h
            up = f.energy(X)
            X[i, c] -= 2 * h
            dn = f.energy(X)
            X[i, c] += h
            worst = max(worst, abs(-(up - dn) / (2 * h) - F[i, c]))
    return worst


if __name__ == "__main__":
    f = Field(np.array([HEAD, TAIL, WATER]), np.zeros((0, 2), int), 10.0)
    print(f"chi factorization  max |q.k - chi| = {f.check_identity():.3e}  "
          f"(the energy is one attention layer)")
    e = check_gradients()
    print(f"gradient check     max |F + dU/dx| = {e:.3e}")
    nl = check_neighbor_list()
    print(f"neighbour list     max |sparse - dense| = {nl:.3e}")
    ok = e < 1e-4 and f.check_identity() < 1e-10 and nl < 1e-10
    print("PASS" if ok else "*** FAILED ***")
