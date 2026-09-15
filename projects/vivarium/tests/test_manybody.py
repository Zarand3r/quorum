"""The many-body modulators: exact forces, ONE force law, and a descriptor that is not a constant.

Three of these four gates existed only as one-off scripts. Each had already caught a defect that
voided an experiment, and none was committed, so the next defect of the same shape was not caught:

  - `field.forces` vs `transformer.attention` -- two implementations of one force law. The MLP was
    wired into the first and the engine runs the second, so G4 attempt 1 ran 24 runs and 48 CPU-hours
    of two IDENTICAL arms (`max|X_off - X_mlp| = 0.000e+00`) and would have reported "the MLP does
    nothing".
  - `forces` vs `-grad energy` -- chi was modulated in one and not the other, so F was the gradient of
    a potential nobody evaluated (1.6e-2 against a 1e-6 floor).
  - **calibration** -- `n_ref = 6.0` was described as "the close-packed 2-D coordination", but the
    descriptor is a sum of smooth kernel weights, not a count: its value in a real membrane is ~0.2.
    Every head therefore got `1 + 0.25*(1 - 0.035) = 1.24`, a uniform 24% inflation with a 0.4%
    spread. The term was INERT, and two registered experiments reported it as a physics null.

The fourth, the separation gate, is the house rule (`docs/MEASUREMENT_DISCIPLINE.md`): a descriptor
that does not SEPARATE the states it is supposed to distinguish cannot drive anything.
"""

from __future__ import annotations

import numpy as np
import pytest

import _mixture
from field import Field, HEAD, N_SPECIES
from gap_closure import PRODUCTION, chi_from
from manybody import CALIBRATION_BAND, ManyBodyMLP, ShapeMLP, assert_calibrated
from transformer import VivariumTransformer

N_LIP, L_BOX, PHI, RC = 24, 40.0, 0.55, 2.5
AMPS = (0.0, 0.25, 1.0, 2.0, 4.0)


def _system(plant="flat", n_lip=N_LIP, L=L_BOX, seed=1):
    nw = int(round(PHI * L ** 2 / np.pi * 4)) - n_lip * 5
    X, species, bonds, mols, _, _ = _mixture.build(0, n_lip, max(nw, 0), L, 2, plant=plant,
                                                   branched=True, seed=seed)
    mm = np.array([np.asarray(m, dtype=np.int64) for m in mols], dtype=np.int64)
    return np.ascontiguousarray(X, dtype=np.float64), species, bonds, mm, L


def _n_ref(X, species, bonds, L, shape):
    """Calibrate against the very state under test, so the gate is about the FORM not the number."""
    probe = Field(species, bonds, L, chi=chi_from(PRODUCTION), shape=shape)
    n = probe.coordination(X)
    return float(n[n > 0.0].mean())


def _shape_field(X, species, bonds, L, amp):
    sh = ShapeMLP(np.ones(N_SPECIES), n_ref=1.0, amp=amp)
    sh.n_ref = _n_ref(X, species, bonds, L, sh)
    return Field(species, bonds, L, chi=chi_from(PRODUCTION), shape=sh)


# ---------------------------------------------------------------------------------------------
# 1. n_ref is not optional


def test_n_ref_has_no_default():
    """A default is how 6.0 survived the descriptor changing under it from all-lipid to head-only."""
    with pytest.raises(TypeError):
        ShapeMLP(np.ones(N_SPECIES))
    with pytest.raises(TypeError):
        ManyBodyMLP()


def test_n_ref_from_is_the_kernel_not_a_count():
    """The whole defect in one assertion: the descriptor's reference value is far below the count."""
    n_ref = ShapeMLP.n_ref_from(a0=2.05, rc=RC)
    assert n_ref == pytest.approx(0.2145, abs=1e-3)
    assert n_ref < 0.5, "if this ever reads ~2 the kernel has been replaced by a count"


# ---------------------------------------------------------------------------------------------
# 2. the calibration guard -- and proof that it trips


def test_calibration_guard_rejects_the_registered_value():
    """Reintroduce the bug and confirm the gate fires. The value 6.0 shipped in two experiments."""
    X, species, bonds, _, L = _system()
    broken = ShapeMLP(np.ones(N_SPECIES), n_ref=6.0)
    n = Field(species, bonds, L, chi=chi_from(PRODUCTION), shape=broken).coordination(X)
    with pytest.raises(ValueError, match="constant offset"):
        assert_calibrated(broken, n, "ShapeMLP@n_ref=6.0")


def test_calibration_guard_accepts_a_derived_value():
    """The guard must accept a derived n_ref AND reject just outside its band.

    REWRITTEN 2026-09-14: the first version set `n_ref` to the descriptor's own mean and then asserted
    the ratio was 1.0. That is true by construction — it could not fail for any implementation of
    `assert_calibrated`, including one that returned 1.0 unconditionally. Testing the BAND is the
    thing that has content: the guard exists to separate a calibrated term from a constant one, so it
    must be shown to do both.
    """
    X, species, bonds, _, L = _system()
    sh = ShapeMLP(np.ones(N_SPECIES), n_ref=1.0)
    derived = _n_ref(X, species, bonds, L, sh)
    sh.n_ref = derived
    n = Field(species, bonds, L, chi=chi_from(PRODUCTION), shape=sh).coordination(X)
    assert assert_calibrated(sh, n, "derived") == pytest.approx(1.0, abs=0.05)

    # just INSIDE the band: accepted
    sh.n_ref = derived * (CALIBRATION_BAND * 0.9)
    assert_calibrated(sh, n, "inside band")

    # just OUTSIDE it, both directions: rejected. Without these the guard could return a constant.
    for factor in (CALIBRATION_BAND * 1.1, 1.0 / (CALIBRATION_BAND * 1.1)):
        sh.n_ref = derived * factor
        with pytest.raises(ValueError, match="constant offset"):
            assert_calibrated(sh, n, f"outside band x{factor:.2f}")


# ---------------------------------------------------------------------------------------------
# 3. the descriptor must SEPARATE, and the modulation must not be a constant


def test_descriptor_separates_flat_from_curved():
    """A head on the outside of a ring must read LESS crowded than one on the inside.

    This is the sign the shape channel needs: less crowded -> larger head -> wedge -> more bend. It is
    also the sign that came out backwards when tails were counted as occluders (+0.2004 all-lipid
    against -0.0661 head-only), so it is pinned here.
    """
    X, species, bonds, _, L = _system(plant="arc1.0", n_lip=32, L=40.0)
    sh = ShapeMLP(np.ones(N_SPECIES), n_ref=1.0)
    n = Field(species, bonds, L, chi=chi_from(PRODUCTION), shape=sh).coordination(X)
    heads = X[species == HEAD]
    rad = np.linalg.norm(heads - heads.mean(axis=0), axis=1)
    outer, inner = rad > np.median(rad), rad <= np.median(rad)
    nh = n[species == HEAD]
    assert nh[outer].mean() < nh[inner].mean(), "outer leaflet must read LESS crowded than inner"


def test_modulation_is_not_a_uniform_offset():
    """With a derived n_ref the head sizes must actually differ across a curved membrane.

    At n_ref = 6.0 the outer/inner wedge on a planted ring was +0.10%; the spread of sigma_head across
    all heads was 0.0045 on a mean of 1.2414. That is a constant, and a constant cannot curve anything.
    """
    X, species, bonds, _, L = _system(plant="arc1.0", n_lip=32, L=40.0)
    sh = ShapeMLP(np.ones(N_SPECIES), n_ref=1.0, amp=0.25)
    sh.n_ref = _n_ref(X, species, bonds, L, sh)
    n = Field(species, bonds, L, chi=chi_from(PRODUCTION), shape=sh).coordination(X)
    sig, _ = sh.sigma_and_dsigma(n, species)
    sh_head = sig[species == HEAD]
    spread = float(sh_head.max() - sh_head.min())
    # The bar is the term's OWN amplitude: a modulation of amplitude `amp` that produces a spread
    # under amp/10 across a curved membrane is not modulating, it is offsetting.
    assert spread > sh.amp / 10.0, f"sigma_head spread {spread:.4f} is a constant at amp={sh.amp}"


# ---------------------------------------------------------------------------------------------
# 4. ONE force law, and it is a gradient


@pytest.mark.parametrize("amp", AMPS)
def test_two_force_paths_agree(amp):
    """G1 as amended 2026-09-09. Both paths were internally consistent -- with different physics."""
    X, species, bonds, _, L = _system()
    f = (Field(species, bonds, L, chi=chi_from(PRODUCTION)) if amp == 0.0
         else _shape_field(X, species, bonds, L, amp))
    a = f.forces(X)
    b = VivariumTransformer(f).attention(X)
    assert np.abs(a - b).max() <= 1e-9 * max(np.abs(a).max(), 1.0)


@pytest.mark.parametrize("amp", (0.25, 1.0, 4.0))
def test_shape_channel_force_is_minus_grad_energy(amp):
    """Central differences. Without the dU/dsigma * dsigma/dn * dn/dx term this reads ~1e-2."""
    X, species, bonds, _, L = _system()
    f = _shape_field(X, species, bonds, L, amp)
    F = f.forces(X)
    rng = np.random.default_rng(0)
    h, worst = 1e-6, 0.0
    for a in rng.choice(len(X), size=10, replace=False):
        for c in range(X.shape[1]):
            Xp, Xm = X.copy(), X.copy()
            Xp[a, c] += h
            Xm[a, c] -= h
            num = -(f.energy(Xp) - f.energy(Xm)) / (2 * h)
            worst = max(worst, abs(num - F[a, c]) / max(abs(num), 1.0))
    assert worst < 1e-4, f"worst relative gradient error {worst:.3e} at amp={amp}"
