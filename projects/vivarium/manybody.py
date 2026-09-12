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


CALIBRATION_BAND = 4.0
"""How far the reference state may sit from `n_ref` before the term is a constant, not a modulation.

Both modulators have the form `g(n / n_ref)`. If the descriptor's actual mean is far from `n_ref`, the
map is evaluated on a tiny interval of its domain and returns almost the same number for every bead:
the term becomes a uniform offset to the chemistry plus noise. A factor of four either way is a sanity
band on the derivation, not a threshold on a result.
"""


def assert_calibrated(mlp, n, tag=""):
    """Fail loudly if a modulator's reference point does not match the descriptor it is fed.

    This is the guard that `n_ref = 6.0` needed and did not have. It ran for two registered
    experiments against a descriptor 18-29x smaller (0.207 planted, 0.334 relaxed, against n_ref 6.0)
    and reported both as physics nulls.
    """
    live = n[n > 0.0]
    if live.size == 0:
        raise ValueError(f"{tag}: descriptor is identically zero; nothing to calibrate against")
    ratio = float(live.mean()) / mlp.n_ref
    if not (1.0 / CALIBRATION_BAND) <= ratio <= CALIBRATION_BAND:
        raise ValueError(
            f"{tag}: n_ref={mlp.n_ref:.4f} but the descriptor's mean over occupied beads is "
            f"{live.mean():.4f} (ratio {ratio:.3f}, band 1/{CALIBRATION_BAND:g}..{CALIBRATION_BAND:g}). "
            f"The term would be a constant offset, not a modulation. Re-derive n_ref.")
    return ratio


def coord_weight(r, rc):
    """Smooth, compactly supported coordination kernel and its derivative.

    (1 - (r/rc)^2)^2 vanishes with zero slope at rc, so both n_i and its gradient are continuous --
    a kernel with a kink would inject impulses into the force at the cutoff.
    """
    s = np.clip(r / rc, 0.0, 1.0)
    u = 1.0 - s * s
    return u * u, (-4.0 * u * s) / rc          # w, dw/dr


class ShapeMLP:
    """Environment-dependent BEAD SIZE. The mechanism `ManyBodyMLP` should have used.

    WHY THE FIRST ATTEMPT FAILED, DIAGNOSED

    `ManyBodyMLP` modulates the interaction STRENGTH chi. G4 measured 0/12 against 0/12, and the
    construction predicts it: a flat bilayer is symmetric, so an environment-dependent term gives both
    leaflets the same value (G2 = 0.0000 exactly) and can only AMPLIFY an existing bend. The sign of
    that feedback is wrong --

        bend -> outer leaflet less crowded -> higher f -> STRONGER attraction on the outer leaflet
             -> outer leaflet CONTRACTS -> the bend FLATTENS

    i.e. it stabilises flatness. G4 was arguably predictable from the construction.

    WHAT POLAR_PACK ACTUALLY MODULATES

    Its MLP does not change affinity, it changes SHAPE: "induced-fit morph -- the block updates the
    shape channels, so an agent deforms its contour to fit its binding partners." In lipid physics
    shape is exactly what sets curvature, through the packing parameter P = v/(a0*l) -- `field.py:249`
    already records that head area is the only geometric lever on it. A cone bends a membrane; a
    cylinder does not; interaction strength does not enter.

    So this modulates sigma_head, and the feedback reverses:

        bend -> outer heads less crowded -> hydration shell expands -> sigma_head GROWS
             -> wedge shape -> MORE bend

    which is positive feedback, and is the standard mechanism for spontaneous curvature rather than an
    analogy to it.

    DERIVED, NOT FITTED. A hydration shell is compressed by lateral crowding. Write the crowding
    deviation as `u_i = 1 - n_i / n_ref`, zero in the reference state, and the response as

        sigma_i = sigma_0 * 2 / (1 + exp(-2 * amp * u_i))

    which is the linear response `sigma_0 * (1 + amp*u)` near the reference (identical value AND slope
    at u = 0) made BOUNDED and SMOOTH. Both properties are load-bearing, not cosmetic:

      - a hydration shell cannot invert, so sigma must stay positive for any u. The linear form needs
        a clamp, and a clamp is a KINK: d(sigma)/dn jumps to zero there, the force stops being
        -grad U, and R3 -- the energy ledger the whole project rests on -- is lost exactly in the
        regime a large `amp` explores.
      - bounded above by 2*sigma_0: a head may at most double, never run away.

    Changed 2026-09-11, before any data at a corrected `n_ref`, and recorded as such in
    `specs/2026-09-07_mlp_many_body.md` Amendment 4.

    At n = n_ref the bead is at its reference size; less crowded means larger. `amp` is the one free
    parameter and is declared as such. `n_ref` is NOT free -- see `n_ref_from`.
    """

    N_IN_LEAFLET_2D = 2      # a 2-D leaflet is a LINE of heads: two in-leaflet neighbours, exactly

    @staticmethod
    def n_ref_from(a0, rc, n_in_leaflet=N_IN_LEAFLET_2D):
        """The descriptor's value in the state where sigma = sigma0. DERIVED, not chosen.

        `n_ref` is not a coordination COUNT -- the descriptor is a sum of smooth kernel weights, and
        `coord_weight` returns 0.107 at a spacing of 2.05 sigma, not 1. Equating the two is the defect
        recorded as Amendment 4 in `specs/2026-09-07_mlp_many_body.md`: `n_ref = 6.0` against a
        descriptor whose range is ~0.2 made the bracket 1.24 for every head in every state -- a
        uniform 24% inflation with a 0.4% spread, i.e. inert.

            n_ref = n_in_leaflet * w(a0; rc)

        `n_in_leaflet` is geometry (2 in 2-D); `a0` is the equilibrium head-head spacing MEASURED in a
        relaxed membrane, not taken from the planter, whose lattice constant is its own choice.
        """
        return float(n_in_leaflet) * float(coord_weight(np.asarray([float(a0)]), float(rc))[0][0])

    def __init__(self, sigma0, n_ref, amp=0.25, subject=(HEAD,), neighbours=(HEAD,)):
        # n_ref has NO DEFAULT on purpose. A default is how 6.0 survived the change of descriptor from
        # all-lipid to head-only without ever being re-derived.
        self.sigma0 = np.asarray(sigma0, dtype=np.float64)
        self.n_ref = float(n_ref)
        if not self.n_ref > 0.0:
            raise ValueError(f"n_ref must be > 0, got {self.n_ref}")
        self.amp = float(amp)
        self.subject = tuple(subject)
        # WHICH beads compress the hydration shell. HEADS ONLY, and this is not cosmetic: with all
        # lipid beads counted, the descriptor is dominated by TAIL packing, and on a curved bilayer the
        # outer leaflet's tails are compressed into a converging region. Measured on a planted ring,
        # outer-minus-inner coordination is
        #     all lipid beads  +0.2004   (outer reads MORE crowded -> sigma shrinks -> flattens)
        #     HEAD beads only  -0.0661   (outer reads LESS crowded -> sigma grows -> bends)
        # i.e. the wrong descriptor inverts the feedback. A hydration shell is compressed by
        # neighbouring HEAD GROUPS; tails are buried in the core and do not touch it.
        self.neighbours = tuple(neighbours)

    def sigma_and_dsigma(self, n, species):
        """Per-BEAD sigma and d(sigma)/dn. Non-subject species keep their species default.

            s  = 2 / (1 + exp(-z)),   z = 2 * amp * (1 - n/n_ref)
            ds/dn = -(amp / n_ref) * s * (2 - s)

        No clamp, no branch: smooth for every n, so the many-body force term stays an exact gradient.
        """
        sig = self.sigma0[species].astype(np.float64)
        dsig = np.zeros_like(sig)
        m = np.isin(species, self.subject)
        if self.amp == 0.0:
            return sig, dsig
        z = 2.0 * self.amp * (1.0 - n[m] / self.n_ref)
        sc = 2.0 / (1.0 + np.exp(-np.clip(z, -700.0, 700.0)))    # clip guards exp overflow only
        s0 = self.sigma0[species[m]]
        sig[m] = s0 * sc
        dsig[m] = -s0 * (self.amp / self.n_ref) * sc * (2.0 - sc)
        return sig, dsig


class ManyBodyMLP:
    """Per-token exposure from coordination, as a real MLP with a residual on a one-hot channel.

    Weights are CONSTRUCTED, not learned, exactly as `Wq`/`Wk` are constructed from the chi
    eigendecomposition: the network expresses a derived law rather than fitting one. `scale = 0`
    reduces it to the identity, which is what makes the off-state test meaningful.
    """

    def __init__(self, n_ref, scale=1.0, width=8, subject=(HEAD,)):
        # No default, for the reason given in `ShapeMLP.n_ref_from`. This channel's descriptor counts
        # ALL lipid beads (it declares no `neighbours`), so its reference value is the all-lipid
        # coordination of a relaxed membrane, not the head-only one.
        self.n_ref = float(n_ref)
        if not self.n_ref > 0.0:
            raise ValueError(f"n_ref must be > 0, got {self.n_ref}")
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
