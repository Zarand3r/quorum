"""The simulation step is a transformer forward pass, and these tests are what make that checkable.

The claim is exact, not approximate: every force in this model is a masked attention head, and one
forward pass equals one integrator step bit-for-bit. Anything weaker would let the "transformer-only"
framing be decorative.
"""

import numpy as np

from field import Field, N_SPECIES
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
    """q_i . k_j built from the token channel equals the Field's species lookup, to floating point.

    This is what makes the MLP insertable without changing anything: the interaction matrix is now read
    out of h rather than out of a table, and at h = one-hot species the two are the same numbers.
    """
    X, f = _system(n=60)
    tf = VivariumTransformer(f)
    _, _, iu = f._pairs(X)
    from_table = f.content_pairs(iu[0], iu[1])
    from_channel = np.einsum("ic,ic->i", tf.q()[iu[0]], tf.k()[iu[1]])
    assert np.abs(from_table - from_channel).max() < 1e-12


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
