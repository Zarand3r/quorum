"""Is this real physics, or a simulation that merely looks like one?

This file is the answer to that question, and it is meant to be readable as an argument rather than as
a list of assertions. It has four parts:

  1. THE MAPPING      every attention head, written as the equation it computes, checked against that
                      equation's analytic form. If a head does not equal its physics, say so here.
  2. THE CONSERVATION LAWS   the things that make a dynamics physics rather than an animation:
                      Newton's third law, F = -grad U, and invariance under the symmetries of space.
  3. STATISTICAL MECHANICS   the thermostat must produce the Boltzmann distribution it claims.
  4. THE ORACLE       a membrane potential from the literature -- one that is KNOWN to produce
                      vesicles -- expressed in these same primitives, exactly.

Why an oracle at all: physical realism is not a matter of opinion here. The laws are known and there
are published models that reproduce them, so "is our force law real physics?" reduces to "does it
agree with one, exactly, on the same configuration?" Parts 1-3 check internal consistency; part 4 is
the external check, and it is the only one that can catch a model that is self-consistently wrong.

WHAT THIS FILE DELIBERATELY DOES NOT CLAIM. Passing it means the dynamics obeys the laws it is built
from. It does NOT mean the model is a faithful lipid: the departures from real membranes are
catalogued in `docs/ROADMAP.md` 5b (no electrostatics, zero chain bending rigidity, no hydrodynamics,
2-D), and no test here would fail because of any of them. Realism of the LAW and realism of the
MOLECULE are different questions; this file settles only the first.
"""

from __future__ import annotations

import numpy as np
import pytest

import _mixture
from field import Field, HEAD, N_SPECIES, TAIL, WATER, _core, _well
from gap_closure import PRODUCTION, chi_from
from transformer import VivariumTransformer

L_BOX, N_LIP, PHI = 40.0, 24, 0.55


def _system(seed=0, plant="random"):
    nw = int(round(PHI * L_BOX ** 2 / np.pi * 4)) - N_LIP * 5
    X, species, bonds, mols, _, _ = _mixture.build(0, N_LIP, nw, L_BOX, 2, plant=plant,
                                                   branched=True, seed=seed)
    f = Field(species, bonds, L_BOX, chi=chi_from(PRODUCTION))
    return np.ascontiguousarray(X, dtype=np.float64), f


# =================================================================================================
# 1. THE MAPPING — each head is an equation, and here is that equation
# =================================================================================================

def test_nonbonded_head_is_the_pair_force_of_its_potential():
    """The non-bonded head must equal  -(1/r) dU/dr  for  U = eps*[core(s) + well(s)*chi],  s = r/sigma.

    This is the whole "every force is an attention operation" claim, at the level of one equation. The
    head returns a scalar per pair which is multiplied by the separation vector, so it must BE the
    radial derivative divided by r -- not merely be correlated with it.
    """
    X, f = _system()
    tf = VivariumTransformer(f)
    pairs, sep, dist = tf._nonbonded_pairs(X)
    got = tf._score_nonbonded(dist, pairs)

    sig = f.pair_sigma(pairs[0], pairs[1])
    chi = f.content_pairs(pairs[0], pairs[1])
    s = dist / sig
    _, duc = _core(s, f.core_height)
    _, duw = _well(s, f.rc)
    dudr = f.eps * (duc + duw * chi) / sig              # dU/dr, chain rule through s = r/sigma
    dudr = np.where(dist < f.rc * sig, dudr, 0.0)       # the cutoff, applied identically
    want = -dudr / np.maximum(dist, 1e-12)

    assert np.abs(got - want).max() < 1e-12, "the non-bonded head is not -(1/r) dU/dr"


def test_bond_head_is_hookes_law():
    """The bond head must equal  -k(r - r0)/r  exactly. A spring is the simplest known-answer case."""
    X, f = _system()
    tf = VivariumTransformer(f)
    for pairs, k, r0 in f._springs():
        if not len(pairs):
            continue
        d = X[pairs[:, 0]] - X[pairs[:, 1]]
        d -= f.L * np.round(d / f.L)
        r = np.linalg.norm(d, axis=1)
        got = tf._score_spring(k, r0)(r, pairs)
        want = -k * (r - r0) / np.maximum(r, 1e-12)
        assert np.abs(got - want).max() < 1e-12, "the bond head is not Hooke's law"


def test_query_key_inner_product_IS_the_interaction_matrix():
    """`q_i . k_j` must equal the chi table entry for the pair's species, to floating point.

    This is what licenses calling the model a transformer at all: the content term of the attention
    score is an inner product between per-token vectors, and it is numerically the interaction matrix.
    """
    X, f = _system()
    tf = VivariumTransformer(f)
    _, _, iu = f._pairs(X)
    from_table = f.content_pairs(iu[0], iu[1])
    from_channel = np.einsum("ic,ic->i", tf.q()[iu[0]], tf.k()[iu[1]])
    assert np.abs(from_table - from_channel).max() < 1e-12


def test_the_attention_sum_equals_the_force_law():
    """All heads summed must equal `field.forces` — one forward pass, one force evaluation.

    Two implementations of one force law is the most expensive defect this project has had: they were
    each internally consistent and consistent with DIFFERENT physics, and 48 CPU-hours were scored
    against the wrong one before anyone compared them.
    """
    X, f = _system()
    a, b = f.forces(X), VivariumTransformer(f).attention(X)
    assert np.abs(a - b).max() <= 1e-9 * max(np.abs(a).max(), 1.0)


# =================================================================================================
# 2. THE CONSERVATION LAWS — what separates physics from animation
# =================================================================================================

def test_newtons_third_law_the_forces_sum_to_zero():
    """Sum of all internal forces must be zero. This is the test that caught the sister stack.

    `polar_pack`'s electrostatic head read a token's contour along the wrong bearing, so `prod` was
    asymmetric and `F_ij != -F_ji`. It ran for three months documented as "CONSERVATIVE ... relaxes to
    a free-energy minimum" while injecting a net force of 2.1 into the system. Found by exactly this
    check, not by any result looking wrong.
    """
    X, f = _system()
    for F in (f.forces(X), VivariumTransformer(f).attention(X)):
        assert np.abs(F.sum(axis=0)).max() < 1e-9, "net internal force is not zero"


def test_force_is_minus_the_gradient_of_the_energy():
    """F = -grad U by central differences. Without this there is no energy, hence no temperature,
    no line tension and no bending modulus, and nothing can be compared to a published number."""
    X, f = _system()
    F = f.forces(X)
    rng = np.random.default_rng(0)
    h, worst = 1e-6, 0.0
    for a in rng.choice(len(X), size=8, replace=False):
        for c in range(X.shape[1]):
            Xp, Xm = X.copy(), X.copy()
            Xp[a, c] += h
            Xm[a, c] -= h
            num = -(f.energy(Xp) - f.energy(Xm)) / (2 * h)
            worst = max(worst, abs(num - F[a, c]) / max(abs(num), 1.0))
    assert worst < 1e-4, f"worst relative gradient error {worst:.3e}"


def test_translational_invariance_galilean():
    """Shifting every particle by the same vector must not change any force. Space has no origin."""
    X, f = _system()
    F0 = f.forces(X)
    for shift in ([3.7, -1.2], [L_BOX / 2, L_BOX / 3]):
        F1 = f.forces(np.ascontiguousarray(X + np.array(shift)))
        assert np.abs(F0 - F1).max() < 1e-9, f"forces changed under a uniform shift by {shift}"


def test_rotational_invariance():
    """Rotating the system must rotate the forces with it. Space has no preferred direction.

    Checked in a box large enough that no pair interacts across the periodic boundary, because the
    periodic image lattice is NOT rotationally invariant — that is a property of the box, not of the
    force law, and conflating the two would make this test either vacuous or unpassable.
    """
    rng = np.random.default_rng(3)
    n = 40
    L = 400.0                                    # >> rc, so wrapping never enters
    X = rng.uniform(-8.0, 8.0, (n, 2))
    species = np.array([HEAD, TAIL, TAIL, WATER] * (n // 4), dtype=np.int64)
    bonds = np.array([[4 * m, 4 * m + 1] for m in range(n // 4)], dtype=np.int64)
    f = Field(species, bonds, L, chi=chi_from(PRODUCTION))
    th = 0.7
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    F0 = f.forces(np.ascontiguousarray(X))
    F1 = f.forces(np.ascontiguousarray(X @ R.T))
    assert np.abs(F1 - F0 @ R.T).max() < 1e-8, "forces do not rotate with the system"


def test_energy_is_conserved_with_the_thermostat_off():
    """With no friction and no noise the integrator must conserve the total energy.

    This is the check that the force law and the integrator agree: a force that is not a gradient, or
    a timestep that is too large, both show up here as drift.
    """
    X, f = _system(seed=1)
    ig = _mixture.make_step_engine(f, X, 0.0, 8e-3, 7, engine="transformer")
    ig.gamma = 0.0
    ig.v = np.zeros_like(X)

    def total(Y):
        return f.energy(Y) + 0.5 * float((ig.v ** 2).sum())

    Y = X.copy()
    for _ in range(40):
        Y = ig.step(Y)
    e0 = total(Y)
    for _ in range(400):
        Y = ig.step(Y)
    drift = abs(total(Y) - e0) / max(abs(e0), 1.0)
    assert drift < 0.02, f"energy drifted {drift:.2%} with the thermostat off"


# =================================================================================================
# 3. STATISTICAL MECHANICS — the thermostat must produce the distribution it claims
# =================================================================================================

def test_equipartition_gives_back_the_temperature_that_was_asked_for():
    """<v^2> per degree of freedom must equal kT/m. A thermostat that does not is not a thermostat."""
    kT = 0.45
    X, f = _system(seed=2)
    ig = _mixture.make_step_engine(f, X, kT, 8e-3, 11, engine="transformer")
    Y = X.copy()
    for _ in range(2000):
        Y = ig.step(Y)
    acc = []
    for _ in range(3000):
        Y = ig.step(Y)
        acc.append(float((ig.v ** 2).mean()))
    got = float(np.mean(acc))
    assert abs(got - kT) / kT < 0.10, f"kinetic temperature {got:.4f} against the requested {kT}"


# =================================================================================================
# 4. THE ORACLE — a literature potential that DOES make vesicles, in these same primitives
# =================================================================================================

def test_a_published_membrane_potential_is_exactly_an_attention_layer():
    """Yuan-Li-Zhang, the potential whose published use is vesicle formation, written as attention.

    This is the external check. YLZ is a real membrane model from the literature; `attention_ylz`
    rewrites its energy as a radial gate times a query-key inner product, using the identity

        n_i . n_j - (n_i.r_hat)(n_j.r_hat)  ==  n_i^T (I - r_hat r_hat^T) n_j

    which is exactly what relative-position-aware attention computes. If the rewrite is exact, then
    "every force is an attention operation" is not a restriction that costs physics — a potential
    known to produce the target phenomenon fits inside the same primitives with no approximation.
    """
    from attention_ylz import check_identity
    worst = check_identity(seed=0, n_part=120, L=10.0, trials=3)
    worst = float(np.max(np.abs(np.asarray(worst, dtype=float))))
    assert worst < 1e-10, f"the YLZ-as-attention rewrite is not exact: {worst:.3e}"


@pytest.mark.parametrize("engine", ["transformer", None])
def test_both_engines_agree_so_the_transformer_costs_no_physics(engine):
    """The transformer path and the ordinary force path must integrate to the same trajectory.

    If they diverge, then "transformer-only" is a different model rather than a different spelling of
    the same one, and every physical number measured under it would need re-deriving.
    """
    X, f = _system(seed=5)
    ig = _mixture.make_step_engine(f, X.copy(), 0.0, 8e-3, 3, engine=engine)
    ig.gamma = 0.0
    Y = X.copy()
    for _ in range(50):
        Y = ig.step(Y)
    ref = _mixture.make_step_engine(f, X.copy(), 0.0, 8e-3, 3, engine="transformer")
    ref.gamma = 0.0
    Z = X.copy()
    for _ in range(50):
        Z = ref.step(Z)
    assert np.abs(Y - Z).max() < 1e-8
