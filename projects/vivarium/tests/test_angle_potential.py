"""The BF bending term: V = 0.5*k_theta*(theta - pi)^2.

Registered in specs/2026-09-16_chain_bending_form.md. These are AC-1: the term must satisfy the same
gates every other force in this model satisfies, or a "fidelity fix" has broken the energy ledger.

Default is OFF (k_theta = 0). The off case is tested too, because the whole point of shipping it off
is that no existing result moves.
"""
import numpy as np
import pytest

from field import Field, HEAD, TAIL
from transformer import VivariumTransformer

SPECIES = np.array([HEAD, TAIL, TAIL, TAIL, TAIL], np.int64)
BONDS = np.array([[0, 1], [1, 2], [0, 3], [3, 4]], np.int64)
L = 40.0
STRAIGHT = np.array([[20, 20], [20, 21], [20, 22], [20, 19], [20, 18]], float)


def _cfg(seed):
    return np.random.default_rng(seed).normal(20.0, 1.5, (5, 2))


def test_head_centred_triples_are_excluded():
    """Same rule as the 1-3 spring: a triple centred on a HEAD would pin the branch to 180 degrees."""
    t = Field(SPECIES, BONDS, L).triples.tolist()
    assert t == [[0, 1, 2], [0, 3, 4]]
    assert [1, 0, 3] not in t and [3, 0, 1] not in t


def test_default_is_off_and_bit_identical():
    """Shipping it off means no existing result can move."""
    X = _cfg(0)
    assert Field(SPECIES, BONDS, L).k_theta == 0.0
    a = Field(SPECIES, BONDS, L).forces(X)
    b = Field(SPECIES, BONDS, L, k_theta=0.0).forces(X)
    assert np.abs(a - b).max() == 0.0


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_force_is_minus_gradient_of_energy(seed):
    """AC-1: F = -grad U to better than 1e-4."""
    X = _cfg(seed)
    f = Field(SPECIES, BONDS, L, k_theta=10.0)
    F = f.forces(X)
    h = 1e-6
    num = np.zeros_like(X)
    for i in range(X.shape[0]):
        for d in range(X.shape[1]):
            xp, xm = X.copy(), X.copy()
            xp[i, d] += h
            xm[i, d] -= h
            num[i, d] = -(f.energy(xp) - f.energy(xm)) / (2 * h)
    assert np.abs(F - num).max() < 1e-4


def test_newtons_third_law():
    """AC-1: the term is internal, so it can produce no net force."""
    f = Field(SPECIES, BONDS, L, k_theta=10.0)
    assert np.abs(f.forces(_cfg(3)).sum(axis=0)).max() < 1e-9


@pytest.mark.parametrize("k_theta", [0.0, 1.0, 10.0, 50.0])
@pytest.mark.parametrize("seed", [0, 4])
def test_field_and_attention_paths_agree_exactly(k_theta, seed):
    """AC-1: 0.000e+00, not 'close'. Two independent implementations, one physics.

    The transformer reimplements the term as a two-pass gather/scatter rather than calling
    `field._angle_forces`; if it delegated, this gate could not fail.
    """
    f = Field(SPECIES, BONDS, L, k_theta=k_theta)
    tf = VivariumTransformer(f)
    X = _cfg(seed)
    assert np.abs(f.forces(X) - tf.attention(X)).max() == 0.0


def test_straight_chain_does_not_nan():
    """theta = pi is the MINIMUM, where nearly every triple sits, and dtheta/dr is 1/sin(theta) there.

    Evaluating dV/dtheta and 1/sin separately gives 0 * inf and NaNs the whole force array. The ratio
    (theta - pi)/sin(theta) -> -1 is finite and must be computed as one quantity.
    """
    f = Field(SPECIES, BONDS, L, k_theta=10.0)
    tf = VivariumTransformer(f)
    for F in (f.forces(STRAIGHT), tf.attention(STRAIGHT)):
        assert not np.isnan(F).any()
        assert np.isfinite(F).all()


def test_the_term_actually_bends():
    """A term that is live must cost energy to kink, or it is decorative."""
    f = Field(SPECIES, BONDS, L, k_theta=10.0)
    kinked = STRAIGHT.copy()
    kinked[2] = [20.7, 21.7]
    assert f.energy(kinked) > f.energy(STRAIGHT) + 1.0


def test_folded_chain_does_not_nan():
    """theta = 0 -- the chain folded back on itself -- is the end where 1/sin(theta) is a true NaN.

    sin(0) is exactly 0.0, unlike sin(pi) which evaluates to 1.22e-16, so this is the case that
    silently poisons the force array. Excluded volume should keep the chain out of it; "should" is
    not a guarantee, and a NaN here would destroy a run without an error.
    """
    folded = np.array([[20.0, 20.0], [20.0, 21.0], [20.0, 20.0], [20.0, 19.0], [20.0, 18.0]])
    f = Field(SPECIES, BONDS, L, k_theta=10.0)
    tf = VivariumTransformer(f)
    for F in (f.forces(folded), tf.attention(folded)):
        assert np.isfinite(F).all()
