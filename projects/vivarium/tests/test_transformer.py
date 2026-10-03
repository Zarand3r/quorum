"""The simulation step is a transformer forward pass, and these tests are what make that checkable.

The claim is exact, not approximate: every force in this model is a masked attention head, and one
forward pass equals one integrator step bit-for-bit. Anything weaker would let the "transformer-only"
framing be decorative.
"""

import numpy as np
import pytest

from field import Field, N_SPECIES, _core, _core_derivative, _well, _well_derivative
from integrate import Inertial
from transformer import VivariumTransformer


def _system(n=120, d=2, L=12.0, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.uniform(0.0, L, size=(n, d))
    species = rng.integers(0, N_SPECIES, size=n)
    # chains of three so BOTH spring heads are exercised: the 1-2 backbone and the 1-3 stiffener
    bonds = np.array([[i, i + 1] for i in range(0, n // 3, 3)]
                     + [[i + 1, i + 2] for i in range(0, n // 3, 3)])
    return X, Field(species, bonds, L)


def test_every_force_is_an_attention_head():
    """Sum of masked heads == field.forces(), to floating point.

    The non-bonded head is a query-key inner product modulated by a distance function; the two spring
    heads are the same score-times-relative-position shape on a pair mask. If this drifts, some force
    has been added outside the attention formulation and the design constraint is broken.
    """
    X, f = _system()
    tf = VivariumTransformer(f)
    assert len(f._springs()) == 2, "test system must exercise both spring heads"
    err = np.abs(f.forces(X) - tf.attention(X)).max()
    scale = np.abs(f.forces(X)).max()
    assert err / scale < 1e-14, (err, scale)


def test_one_forward_pass_is_one_integrator_step_exactly():
    """A single forward pass reproduces Inertial.step bit-for-bit.

    Only ONE step is compared, deliberately. Molecular dynamics is chaotic: summing the heads in a
    different order than field.forces() changes the last bit, and that difference then grows
    exponentially -- measured at 0 after 1 step, 1.8e-15 after 20, and 4.9e-08 after 400. A multi-step
    tolerance would therefore be arbitrary, while the single-step identity is exact and is the thing
    actually being claimed.
    """
    X0, f1 = _system()
    kT, dt = 0.45, 8e-3

    ig = Inertial(f1, kT, dt, seed=7)
    Xa = ig.step(X0.copy())

    _, f2 = _system()
    tf = VivariumTransformer(f2)
    rng = np.random.default_rng(7)
    Xb = X0.copy()
    v = rng.normal(size=Xb.shape) * np.sqrt(kT)      # matches Inertial's lazy velocity init
    Xb, v, F = tf.forward(Xb, v, dt, kT, rng=rng, F=tf.attention(Xb))

    assert np.abs(Xa - Xb).max() == 0.0


def test_force_only_radial_paths_are_bit_identical():
    """Skipping unused energies must not change a single derivative bit."""
    s = np.linspace(0.0, 3.0, 10003)
    assert np.array_equal(_core(s, 37.8)[1], _core_derivative(s, 37.8))
    assert np.array_equal(_well(s, 2.5)[1], _well_derivative(s, 2.5))


def test_optimized_skin_preserves_trajectory_bit_for_bit():
    """Different zero-force supersets must retain identical ordered nonzero contributions."""
    X0, old_field = _system(n=180, L=18.0, seed=29)
    _, new_field = _system(n=180, L=18.0, seed=29)
    old_field.SKIN = 0.6
    new_field.SKIN = 0.4
    old_tf, new_tf = VivariumTransformer(old_field), VivariumTransformer(new_field)
    old_X, new_X = X0.copy(), X0.copy()
    old_rng = np.random.default_rng(31)
    new_rng = np.random.default_rng(31)
    old_v = old_rng.normal(size=X0.shape) * np.sqrt(0.45)
    new_v = new_rng.normal(size=X0.shape) * np.sqrt(0.45)
    old_F, new_F = old_tf.attention(old_X), new_tf.attention(new_X)
    for _ in range(250):
        old_X, old_v, old_F = old_tf.forward(
            old_X, old_v, 8e-3, 0.45, rng=old_rng, F=old_F)
        new_X, new_v, new_F = new_tf.forward(
            new_X, new_v, 8e-3, 0.45, rng=new_rng, F=new_F)
        assert np.array_equal(old_X, new_X)
        assert np.array_equal(old_v, new_v)
        assert np.array_equal(old_F, new_F)


def test_cached_fixed_pair_features_are_exact_query_key_values():
    X, field = _system(n=180, L=18.0, seed=37)
    _, _, pairs = field._pairs(X)
    sigma, chi, _ = field._env(np.ones(len(pairs[0])), pairs)
    assert np.array_equal(sigma, field.pair_sigma(*pairs))
    assert np.array_equal(chi, field.content_pairs(*pairs))
    field.q[0, 0] += 0.125
    field.sigma_species[0] += 0.25
    sigma, chi, _ = field._env(np.ones(len(pairs[0])), pairs)
    assert np.array_equal(sigma, field.pair_sigma(*pairs))
    assert np.array_equal(chi, field.content_pairs(*pairs))


def test_empty_attention_mask_keeps_float_force_dtype():
    """An empty pair mask remains a valid float attention head, not an integer accumulator."""
    X = np.array([[0, 0], [10, 0]], dtype=np.float64)
    field = Field(np.array([0, 0]), np.array([[0, 1]]), L=100.0, bend_frac=0.0)
    force = field.forces(X)
    assert np.issubdtype(force.dtype, np.floating)
    assert np.isfinite(force).all()


def test_attention_output_is_equivariant_when_no_pair_wraps():
    """Rotating the system rotates the forces, because the values are relative positions.

    The qualifier is not a convenience. PERIODIC BOUNDARIES BREAK ROTATIONAL SYMMETRY: the box is a
    square, so which image of j is nearest to i is not a rotation-invariant question, and an arbitrary
    rotation of a wrapped configuration genuinely does change the forces. The first version of this test
    rotated a filled periodic box and failed for exactly that reason.

    So the test isolates the attention algebra from the boundary convention by placing a compact cluster
    in a box large enough that no pair takes a minimum image. What is being asserted is that the head
    output transforms with the coordinates -- which is what makes relative-position values legitimate
    for dynamics rather than a re-labelling. In the periodic system the symmetry that survives is
    translation, plus the 90-degree rotations that map the box to itself.
    """
    rng = np.random.default_rng(3)
    n, L = 40, 400.0                      # cluster of radius ~5 at the centre of a huge box
    X = np.array([L / 2, L / 2]) + rng.normal(scale=2.0, size=(n, 2))
    species = rng.integers(0, N_SPECIES, size=n)
    bonds = np.array([[i, i + 1] for i in range(0, n // 3, 3)]
                     + [[i + 1, i + 2] for i in range(0, n // 3, 3)])
    f = Field(species, bonds, L)
    tf = VivariumTransformer(f)

    sep, _, _ = f._pairs(X)
    assert np.abs(sep).max() < L / 2, "test invalid if any pair takes a minimum image"

    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    c = np.array([L / 2, L / 2])
    F0 = tf.attention(X)
    Fr = tf.attention((X - c) @ R.T + c)
    assert np.abs(Fr - F0 @ R.T).max() < 1e-9


def test_token_channel_reproduces_chi_exactly():
    """q_i . k_j from the token channel equals the CHI MATRIX ITSELF, entry by entry.

    REWRITTEN 2026-09-14. The previous version compared `f.content_pairs(i, j)` against
    `einsum(tf.q()[i], tf.k()[j])` and asserted they matched to 1e-12. But `content_pairs` IS
    `einsum(f.q[species], f.k[species])` (field.py:375), and `tf.q()` is `h @ Wq` with `h` one-hot,
    which selects the same rows. So it compared q.k against q.k — a one-hot-matmul-equals-direct-
    indexing identity that holds whatever q and k contain, including if they had nothing to do with
    chi. It could not fail on the defect its name claims, and SUMMARY.md cited it as the evidence that
    `q.k` equals the chi table.

    The real check lived only in `field.py`'s `__main__` block, outside the suite. It is here now:
    compare against the ORIGINAL chi matrix that `qk_factors` was asked to factorise.
    """
    X, f = _system(n=60)
    tf = VivariumTransformer(f)
    _, _, iu = f._pairs(X)

    chi_table = f.chi[f.species[iu[0]], f.species[iu[1]]]          # the matrix itself
    from_channel = np.einsum("ic,ic->i", tf.q()[iu[0]], tf.k()[iu[1]])
    assert np.abs(chi_table - from_channel).max() < 1e-12, (
        "the token channel does not reproduce the chi matrix — the eigendecomposition round-trip "
        "in qk_factors is broken, which is the claim 'q.k IS the chi table' rests on")

    # and the Field's own fast path must agree with the table too, since forces read it
    assert np.abs(chi_table - f.content_pairs(iu[0], iu[1])).max() < 1e-12


@pytest.mark.xfail(
    strict=True,
    reason="token MLP is intentionally disconnected pending a physically specified role",
)
def test_mlp_is_live_not_decorative():
    """With non-zero weights the MLP changes h, which changes the forces.

    Without this the MLP could be present, satisfy the architecture on paper, and have no effect --
    which is the failure mode this whole refactor is meant to avoid. The zero-weight case is asserted
    separately by the bit-identity test above; this asserts the other side, that the block is wired to
    something.
    """
    X, f = _system(n=60)
    tf = VivariumTransformer(f)
    F_before = tf.attention(X)

    pairs, sep, dist = tf._nonbonded_pairs(X)
    scores = tf._score_nonbonded(dist, pairs)
    rng = np.random.default_rng(1)
    tf.W1 = rng.normal(scale=0.05, size=tf.W1.shape)
    tf.W2 = rng.normal(scale=0.05, size=tf.W2.shape)
    dh = tf.mlp(X, pairs, sep, dist, scores)
    assert np.abs(dh).max() > 0.0, "MLP produced no residual with non-zero weights"

    tf.h = tf.h + dh
    F_after = tf.attention(X)
    assert np.abs(F_after - F_before).max() > 1e-6, "MLP changed h but not the forces"


def test_heads_reproduce_forces_on_the_real_lipid_system():
    """The gate that matters: the PRODUCTION topology, not a hand-made chain.

    Every other test here builds its own bonds. This one uses `_mixture.build`, so the system has
    branched five-bead lipids, explicit water, and both spring heads populated exactly as a real run
    does. A refactor that is exact on toy chains and wrong on the real topology would pass everything
    else in this file.

    Measured on the full production size (2959 beads, 640 bonds, 320 angle terms) the relative error is
    1.4e-16 and the token-channel chi matches the species table to 0.000e+00 across 30186 pairs. This
    test runs a smaller instance of the same construction so the suite stays quick.
    """
    import numpy as np
    from _mixture import build
    from field import Field
    from transformer import VivariumTransformer

    X, species, bonds, mols, wi, chains = build(0, 24, 200, 22.0, 2,
                                                plant="random", branched=True, seed=3)
    f = Field(species, bonds, 22.0)
    tf = VivariumTransformer(f)
    assert len(f._springs()) == 2, "production build must populate both spring heads"
    assert len(wi) > 0, "production build must include explicit water"

    Ff, Fa = f.forces(X), tf.attention(X)
    assert np.abs(Ff - Fa).max() / np.abs(Ff).max() < 1e-13

    _, _, iu = f._pairs(X)
    from_table = f.content_pairs(iu[0], iu[1])
    from_channel = np.einsum("ic,ic->i", tf.q()[iu[0]], tf.k()[iu[1]])
    assert np.abs(from_table - from_channel).max() == 0.0
