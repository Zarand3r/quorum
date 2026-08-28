"""Per-species bead size: the default must change nothing, and the identity must survive a change.

`sigma_species` exists to make HEAD AREA reachable, because the packing parameter P = v/(a0*l) is the
bottom-up origin of spontaneous curvature and `_mixture.chain_bonds` already records that the tail
axis cannot move it. Two things must hold or the knob is worse than useless:

  1. At the default it is an EXACT no-op. Every number in AUTONOMOUS_LOG.md was measured on the scalar
     path; if adding the parameter perturbs the default even in the last bit, none of them is
     comparable to anything measured afterwards.
  2. Away from the default the transformer heads still reproduce `field.forces`. Per-species sigma
     enters the RADIAL GATE, which is exactly the part the "every force is an attention head" claim
     rests on, so a change here is the most likely way that claim could quietly stop being true.
"""

from __future__ import annotations

import numpy as np
import pytest

from field import Field, HEAD, TAIL, WATER, N_SPECIES
from transformer import VivariumTransformer


def _system(seed=0, n=90, L=12.0):
    """A small mixed system with bonds, so the branched-chain path is exercised too."""
    rng = np.random.default_rng(seed)
    X = rng.uniform(-L / 2, L / 2, (n, 2))
    species = np.array([HEAD, TAIL, TAIL] * 10 + [WATER] * (n - 30), dtype=np.int64)
    bonds = np.array([[3 * m, 3 * m + 1] for m in range(10)]
                     + [[3 * m, 3 * m + 2] for m in range(10)], dtype=np.int64)
    return X, species, bonds, L


def test_default_is_bit_identical_to_the_scalar_path():
    """The no-op guarantee, asserted at the bit level rather than by tolerance."""
    X, species, bonds, L = _system()
    base = Field(species, bonds, L)
    explicit = Field(species, bonds, L, sigma_species=np.ones(N_SPECIES))
    assert np.array_equal(base.forces(X), explicit.forces(X))
    assert base.energy(X) == explicit.energy(X)


def test_default_matches_a_rescaled_sigma_the_same_way():
    """Uniform (non-unit) sigma must also collapse onto the scalar path exactly, so the Lorentz rule
    is not quietly introducing a factor when sigma != 1."""
    X, species, bonds, L = _system()
    base = Field(species, bonds, L, sigma=1.3)
    explicit = Field(species, bonds, L, sigma=1.3, sigma_species=np.full(N_SPECIES, 1.3))
    assert np.array_equal(base.forces(X), explicit.forces(X))


def test_a_bigger_head_actually_changes_the_forces():
    """A knob that has never moved anything is not a knob."""
    X, species, bonds, L = _system()
    base = Field(species, bonds, L)
    big = np.ones(N_SPECIES)
    big[HEAD] = 1.6
    wide = Field(species, bonds, L, sigma_species=big)
    assert not np.allclose(base.forces(X), wide.forces(X))


def test_bigger_head_pushes_heads_apart_not_tails():
    """The change must be LOCAL to the species touched: a larger head enlarges head-involved contact
    distances and leaves tail-tail alone. Otherwise `sigma_species` is a global rescale wearing a
    per-species label."""
    X, species, bonds, L = _system()
    big = np.ones(N_SPECIES)
    big[HEAD] = 1.6
    f = Field(species, bonds, L, sigma_species=big)
    i = np.array([0, 1], dtype=np.int64)          # bead 0 is a HEAD, bead 1 a TAIL
    j = np.array([3, 4], dtype=np.int64)          # bead 3 is a HEAD, bead 4 a TAIL
    sig = f.pair_sigma(i, j)
    assert sig[0] == pytest.approx(1.6)           # head-head: (1.6 + 1.6)/2
    assert sig[1] == pytest.approx(1.0)           # tail-tail untouched


def test_transformer_identity_survives_per_species_sigma():
    """The claim the project rests on, re-checked on the NEW path.

    If this ever fails, per-species sigma is not expressible as an attention head and the geometry
    programme costs the transformer-only framing something. It should not: sigma_ij is a function of
    the pair's species, i.e. of the token channel, which is what the head already reads.
    """
    X, species, bonds, L = _system(seed=4)
    big = np.ones(N_SPECIES)
    big[HEAD] = 1.55
    f = Field(species, bonds, L, sigma_species=big)
    tf = VivariumTransformer(f)
    heads = tf.attention(X)
    direct = f.forces(X)
    scale = max(1.0, float(np.abs(direct).max()))
    assert np.abs(heads - direct).max() / scale < 1e-13


def test_gradient_still_matches_finite_differences_with_a_bigger_head():
    """Forces are -dU/dX by construction, but the Lorentz rule adds a per-pair factor to both the
    radial argument AND the 1/sigma prefactor. Three chain-rule bugs have appeared in this function
    before, each caught only by a numerical check."""
    X, species, bonds, L = _system(seed=7, n=40, L=9.0)
    big = np.ones(N_SPECIES)
    big[HEAD] = 1.4
    f = Field(species, bonds, L, sigma_species=big)
    F = f.forces(X)
    h = 1e-6
    for idx in [(0, 0), (1, 1), (5, 0), (12, 1)]:
        Xp, Xm = X.copy(), X.copy()
        Xp[idx] += h
        Xm[idx] -= h
        num = -(f.energy(Xp) - f.energy(Xm)) / (2 * h)
        assert abs(num - F[idx]) < 1e-4 * max(1.0, abs(num))


def test_malformed_sigma_species_is_a_construction_error():
    X, species, bonds, L = _system()
    with pytest.raises(ValueError, match="entries"):
        Field(species, bonds, L, sigma_species=np.ones(N_SPECIES + 1))
    with pytest.raises(ValueError, match="> 0"):
        bad = np.ones(N_SPECIES)
        bad[HEAD] = 0.0
        Field(species, bonds, L, sigma_species=bad)
