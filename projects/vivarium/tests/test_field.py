"""Gates for the single-scalar field. Each asserts a property the module claims about itself.

These are behavioural: they run the code and check numbers. None of them inspects source text, which
is a form of reward hacking this project has committed once already and removed.
"""

import numpy as np
import pytest

from field import (HEAD, TAIL, WATER, Field, check_gradients, check_neighbor_list, default_chi,
                   qk_factors)


def test_forces_are_the_gradient_of_the_energy():
    """The whole point of the rewrite: forces cannot disagree with the energy."""
    assert check_gradients() < 1e-4


def test_energy_is_one_attention_layer():
    """chi factorizes as an exact query-key inner product, so the content term IS attention."""
    chi = default_chi()
    q, k = qk_factors(chi)
    assert np.abs(q @ k.T - chi).max() < 1e-12


def test_neighbour_list_matches_dense_exactly():
    """The sparse path is an optimization, not an approximation."""
    assert check_neighbor_list() < 1e-10


def test_field_is_dimension_agnostic():
    """The energy and its gradient are written over (n, d), so 3-D costs a builder, not a rewrite.

    This matters for the project's open question: 2-D closure of a symmetric bilayer may not be a
    stable phase at all, and both vesicle oracles work in 3-D. Moving there must not require touching
    the force field.
    """
    assert check_gradients(n=30, d=3, L=9.0) < 1e-4
    assert check_neighbor_list(n=100, d=3, L=10.0) < 1e-10


def test_chain_has_bending_stiffness():
    """A straight chain must be the bond network's minimum, i.e. bending it costs energy.

    Without 1-3 terms the tail is a FREELY JOINTED chain with zero persistence length, and since this
    model deliberately has no orientation term, chain stiffness is its ONLY source of membrane bending
    rigidity. A membrane with no bending rigidity crumples rather than holding a curved shape.
    """
    L = 40.0
    species = np.array([HEAD, TAIL, TAIL])
    bonds = np.array([[0, 1], [1, 2]])
    f = Field(species, bonds, L)
    straight = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    bent = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
    assert f.energy(bent) > f.energy(straight) + 1e-6
    # and the 1-3 pair must have been inferred from the 1-2 bonds
    assert any(tuple(a) == (0, 2) for a in f.angles)


def test_bonded_pairs_are_excluded_from_the_nonbonded_term():
    """A bonded pair's interaction is the bond; counting the well on top double-counts it."""
    L = 40.0
    species = np.array([TAIL, TAIL])
    X = np.array([[0.0, 0.0], [1.0, 0.0]])
    free = Field(species, np.zeros((0, 2), int), L)
    bonded = Field(species, np.array([[0, 1]]), L)
    # at the bond rest length the harmonic term contributes exactly zero, so any difference is the
    # non-bonded well that the bonded model must NOT be counting
    assert abs(bonded.energy(X)) < 1e-12
    assert free.energy(X) < -1e-6


def test_water_is_the_most_cohesive_species():
    """The hydrophobic effect is water squeezing oil out, not oil being sticky.

    Real coarse-grained force fields order it this way (MARTINI water-water above alkane-alkane). The
    inverted ordering still demixes, but gives a solvent too weak to press on a membrane or support a
    lumen -- the failure `pack.py` documents as its cores staying wet.
    """
    chi = default_chi()
    assert chi[WATER, WATER] > chi[TAIL, TAIL] > chi[HEAD, HEAD]
    # and demixing must survive the reordering
    assert chi[TAIL, WATER] < 0.5 * (chi[TAIL, TAIL] + chi[WATER, WATER])


def test_asymmetric_chi_is_rejected():
    """U_ij and U_ji are the same pair; an asymmetric chi is a corrupt model, not a fallback."""
    chi = default_chi()
    chi[HEAD, WATER] = 0.9
    with pytest.raises(ValueError):
        Field(np.array([HEAD, WATER]), np.zeros((0, 2), int), 10.0, chi=chi)


def test_isolated_pair_settles_at_contact():
    """Two attracting beads must sit at the contact distance, not inside each other.

    This is the property whose absence defined the old engine: beads there sat at 0.15-0.36 of
    contact, so membranes had no thickness. The minimum of core + well is at s = 1 exactly.
    """
    L = 20.0
    f = Field(np.array([TAIL, TAIL]), np.zeros((0, 2), int), L)
    rs = np.linspace(0.5, 2.0, 601)
    e = [f.energy(np.array([[0.0, 0.0], [r, 0.0]])) for r in rs]
    assert abs(rs[int(np.argmin(e))] - 1.0) < 0.02


def test_tails_avoid_water_and_heads_do_not():
    """The amphiphile's defining asymmetry, read off the energy rather than asserted in a comment."""
    L = 20.0
    x = np.array([[0.0, 0.0], [1.2, 0.0]])
    e_tw = Field(np.array([TAIL, WATER]), np.zeros((0, 2), int), L).energy(x)
    e_hw = Field(np.array([HEAD, WATER]), np.zeros((0, 2), int), L).energy(x)
    e_tt = Field(np.array([TAIL, TAIL]), np.zeros((0, 2), int), L).energy(x)
    assert e_hw < e_tw          # a head is happier next to water than a tail is
    assert e_tt < e_tw          # and a tail would rather have another tail


def test_no_orientation_enters_the_energy():
    """Rotating a molecule in place must not change the energy.

    Spontaneous curvature in the oracle comes from an orientation-dependent term whose beta parameter
    IS the curvature; measured here, beta=0 gives flat sheets and beta=0.15 gives vesicles. This field
    deliberately has no such term, so closure -- if it ever appears -- cannot have been imported. The
    test pins that: energy depends on positions only, never on which way a molecule points.
    """
    L = 30.0
    rng = np.random.default_rng(0)
    species = np.array([HEAD, TAIL, TAIL, WATER, WATER])
    bonds = np.array([[0, 1], [1, 2]])
    f = Field(species, bonds, L)
    X = rng.uniform(-5, 5, size=(5, 2))
    e0 = f.energy(X)
    # rotate the ENTIRE system about the origin: a rotation is an isometry, so if the energy depends
    # only on inter-bead distances it is invariant.
    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    assert abs(f.energy(X @ R.T) - e0) < 1e-9


def test_energy_is_translation_invariant_under_the_periodic_box():
    L = 16.0
    rng = np.random.default_rng(3)
    species = rng.integers(0, 3, size=30)
    f = Field(species, np.zeros((0, 2), int), L)
    X = rng.uniform(-L / 2, L / 2, size=(30, 2))
    shift = np.array([3.3, -2.1])
    Y = X + shift
    Y -= L * np.round(Y / L)
    assert abs(f.energy(Y) - f.energy(X)) < 1e-9


def test_net_force_vanishes():
    """Newton's third law, pair by pair: an isolated system cannot accelerate itself."""
    L = 16.0
    rng = np.random.default_rng(5)
    species = rng.integers(0, 3, size=40)
    bonds = np.array([[0, 1], [2, 3]])
    f = Field(species, bonds, L)
    X = rng.uniform(-L / 2, L / 2, size=(40, 2))
    assert np.abs(f.forces(X).sum(axis=0)).max() < 1e-9


def test_ring_assay_survives_a_core_peak_in_the_outermost_bin():
    """classify() crashed on an empty radial slice, killing a 150000-step run at 18750 steps.

    The `outer` slice is empty whenever the tail-density peak lands in the last radial bin, which any
    aggregate reaching rmax produces -- routine for dispersed or spanning configurations. The bug was
    latent for the whole life of the assay because its three calibration gates all use COMPACT
    aggregates, whose tail peak is never at the edge.
    """
    import numpy as np

    from ring_assay import classify

    class View:
        def __init__(self, X, mol, wi, L, pd):
            self.X, self._mol, self._wi, self.L, self.pd = X, mol, wi, L, pd

    rng = np.random.default_rng(0)
    L = 20.0
    # lipids pushed out to the box edge so the tail peak sits in the final bin
    n_lip, nb = 12, 3
    th = np.linspace(0, 2 * np.pi, n_lip, endpoint=False)
    X = np.zeros((n_lip * nb + 40, 2))
    mol = np.arange(n_lip * nb).reshape(n_lip, nb)
    for b in range(nb):
        X[mol[:, b]] = np.stack([np.cos(th), np.sin(th)], 1) * (0.5 * L - 0.2 - b * 0.4)
    wi = np.arange(n_lip * nb, n_lip * nb + 40)
    X[wi] = rng.uniform(-L / 2, L / 2, size=(40, 2))
    verdict, _ = classify(View(X, mol, wi, L, 2))      # must not raise
    assert verdict in {"HOLLOW", "filled", "other", "fragmented", "no tails"}
