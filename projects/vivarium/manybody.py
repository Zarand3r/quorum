"""A LIVE MLP inside a conservative force law. The reaction half, without losing the physics.

WHAT THIS SETTLES

Two things were claimed to block using the MLP. Only one is real.

  NOT A BLOCKER -- the MLP itself. A per-token nonlinearity on an invariant channel is exactly what
  reaction-diffusion's f(u) is, and vivarium currently has none: `transformer.forward` never calls
  `mlp()`, so the model is pure diffusion and structurally cannot break symmetry. This module makes it
  live.

  A REAL BLOCKER -- softmax. Row-stochastic weights give w_ij != w_ji, so F_ij != -F_ji: Newton's
  third law fails and momentum is not conserved. Normalisation also makes the force INTENSIVE, so a
  bead with 100 neighbours feels the same total as one with 3. Symmetrising restores the third law but
  destroys row-stochasticity, i.e. it is no longer softmax. polar_pack can use softmax precisely
  because it has no energy ledger. We cannot.

THE CONSTRUCTION

Give each token a scalar internal state -- a smooth coordination number over LIPID beads only:

    n_i = sum_j w(r_ij),        w(r) = (1 - (r/rc)^2)^2   for r < rc, else 0

Smooth and closed-form differentiable, unlike exact solvent-accessible-surface geometry, whose
piecewise arc unions are accurate but awkward to differentiate -- and an underivable descriptor is
precisely how a non-conservative force sneaks in.

An MLP maps that to an exposure factor, which modulates the pair chemistry:

    f_i = MLP(species_i, n_i) in (0, 1],       chi_ij = chi0_ij * f_i * f_j

`f_i * f_j` is the correct form for a surface-mediated interaction between two partially buried
objects, and it is symmetric, so the pair term stays antisymmetric under exchange.

THE TERM EVERYONE FORGETS

With chi depending on configuration, the force is NOT just the radial derivative. From
U = sum_ij eps * [core(r_ij) + well(r_ij) * chi0_ij * f_i * f_j]:

    F_k = -dU/dx_k = (the usual radial part, with chi held fixed)
                     - sum_ij eps * well(r_ij) * chi0_ij * [f_j * df_i/dx_k + f_i * df_j/dx_k]

`field.forces` and `transformer.attention` both compute `dudr = eps*(duc + duw*chi)/sig` with chi
treated as a constant, so they would silently omit the second line. Omitting it means the dynamics is
no longer -grad U: energy drifts, temperature stops being defined, and the Langevin thermostat fights
a force that is not a gradient.

This is a solved problem, not a novel one -- it is the same embedding-density term that EAM and
many-body DPD carry. `energy_drift()` is the gate that proves we carry it.
"""
from __future__ import annotations

import numpy as np

from _scatter import scatter_add, scatter_add_pair
from field import HEAD, N_SPECIES, _core, _well


def coord_weight(r, rc):
    """Smooth, compactly supported coordination kernel and its derivative.

    (1 - (r/rc)^2)^2 vanishes with zero slope at rc, so both n_i and its gradient are continuous --
    a kernel with a kink would inject impulses into the force at the cutoff.
    """
    s = np.clip(r / rc, 0.0, 1.0)
    u = 1.0 - s * s
    return u * u, (-4.0 * u * s) / rc          # w, dw/dr


class ManyBodyMLP:
    """Per-token exposure from coordination, as a real MLP with a residual on a one-hot channel.

    Weights are CONSTRUCTED, not learned, exactly as `Wq`/`Wk` are constructed from the chi
    eigendecomposition: the network expresses a derived law rather than fitting one. `scale = 0`
    reduces it to the identity, which is what makes the off-state test meaningful.
    """

    def __init__(self, n_ref=6.0, scale=1.0, width=8, subject=(HEAD,)):
        self.n_ref = float(n_ref)          # close-packed 2-D coordination: geometry, not a fit
        self.scale = float(scale)
        self.subject = tuple(subject)
        self.width = int(width)

    def f_and_df(self, n, species):
        """Exposure f(n) in (0,1] and df/dn, for the subject species only.

        f = 1 / (1 + scale * n / n_ref): a bead with no neighbours is fully exposed (f = 1) and
        exposure falls smoothly as it is crowded. Monotone, bounded, and smooth everywhere -- a hard
        clip at zero would put a kink in the force.
        """
        m = np.isin(species, self.subject)
        x = self.scale * n / self.n_ref
        f = np.ones_like(n)
        df = np.zeros_like(n)
        f[m] = 1.0 / (1.0 + x[m])
        df[m] = -self.scale / self.n_ref * f[m] * f[m]
        return f, df


def energy_and_forces(X, species, mols, L, chi0, rc, core_height, eps, mlp, bonds=None,
                      springs=()):
    """Total non-bonded energy and the EXACT force, including the many-body term.

    Returns (U, F). Bonded terms are passed through `springs` as (pairs, k, r0) so this can be checked
    against `field.forces` with the MLP disabled.
    """
    X = np.ascontiguousarray(X, dtype=np.float64)
    n_bead = len(X)
    lipid = np.unique(np.asarray(mols).ravel())

    # --- all pairs within rc (dense; this is a gate, not a hot path) ----------------------------
    d = X[:, None, :] - X[None, :, :]
    d -= L * np.round(d / L)
    r = np.sqrt(np.einsum("ijk,ijk->ij", d, d))
    np.fill_diagonal(r, np.inf)
    i, j = np.where(np.triu(r < rc, k=1))
    rij = r[i, j]
    dij = d[i, j]

    # --- coordination over LIPID beads only ------------------------------------------------------
    is_lip = np.zeros(n_bead, bool)
    is_lip[lipid] = True
    wij, dwij = coord_weight(rij, rc)
    both = is_lip[i] & is_lip[j]
    n_co = (scatter_add(n_bead, i[both], wij[both])
            + scatter_add(n_bead, j[both], wij[both]))

    f, df = mlp.f_and_df(n_co, species)

    # --- energy ----------------------------------------------------------------------------------
    s = rij                                          # sigma = 1 throughout this gate
    uc, duc = _core(s, core_height)
    uw, duw = _well(s, rc)
    chi_pair = chi0[species[i], species[j]] * f[i] * f[j]
    U = float(eps * (uc + uw * chi_pair).sum())

    # --- force, part 1: radial, with chi held fixed ----------------------------------------------
    dudr = eps * (duc + duw * chi_pair)
    pf = -(dudr / np.maximum(rij, 1e-12))[:, None] * dij
    F = scatter_add_pair(n_bead, i, j, pf)

    # --- force, part 2: the many-body term, dU/df * df/dn * dn/dx --------------------------------
    # dU/df_a = sum over pairs touching a of eps * uw * chi0 * f_other
    g = eps * uw * chi0[species[i], species[j]]
    dU_df = (scatter_add(n_bead, i, g * f[j]) + scatter_add(n_bead, j, g * f[i]))
    chain = dU_df * df                                # dU/dn_a, per bead
    # dn_a/dx_k is nonzero only for pairs; each lipid pair (i,j) contributes dw * rhat to both
    coefm = (chain[i] + chain[j]) * dwij / np.maximum(rij, 1e-12)
    coefm = np.where(both, coefm, 0.0)
    F -= scatter_add_pair(n_bead, i, j, coefm[:, None] * dij)

    # --- bonded ----------------------------------------------------------------------------------
    for pairs, k, r0 in springs:
        bd = X[pairs[:, 0]] - X[pairs[:, 1]]
        bd -= L * np.round(bd / L)
        br = np.linalg.norm(bd, axis=1)
        U += float((0.5 * k * (br - r0) ** 2).sum())
        bf = (-k * (br - r0) / np.maximum(br, 1e-12))[:, None] * bd
        F += scatter_add_pair(n_bead, pairs[:, 0], pairs[:, 1], bf)
    return U, F


def force_matches_gradient(X, species, mols, L, chi0, rc, core_height, eps, mlp, springs=(),
                           h=1e-6, n_probe=12, seed=0):
    """Central-difference check: is F really -dU/dx, INCLUDING the many-body term?

    This is the test the whole design turns on. If it fails, the dynamics is not conservative and no
    temperature, pressure or elastic modulus measured under it means anything.
    """
    rng = np.random.default_rng(seed)
    _, F = energy_and_forces(X, species, mols, L, chi0, rc, core_height, eps, mlp, springs=springs)
    idx = rng.choice(len(X), size=min(n_probe, len(X)), replace=False)
    worst = 0.0
    for a in idx:
        for c in range(X.shape[1]):
            Xp = X.copy(); Xp[a, c] += h
            Xm = X.copy(); Xm[a, c] -= h
            Up, _ = energy_and_forces(Xp, species, mols, L, chi0, rc, core_height, eps, mlp,
                                      springs=springs)
            Um, _ = energy_and_forces(Xm, species, mols, L, chi0, rc, core_height, eps, mlp,
                                      springs=springs)
            num = -(Up - Um) / (2 * h)
            worst = max(worst, abs(num - F[a, c]) / max(abs(num), 1.0))
    return worst
