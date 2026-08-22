"""The tests that decide whether ANY thermodynamic number from this project means anything.

If the forces are not the exact gradient of the stated energy, the dynamics samples no Boltzmann
distribution of any potential, and every line tension, free energy and rate measured here is an
artifact of a non-conservative integrator. Nothing else in the suite checked this: the existing
`test_physics_invariants.py` covers Newton's third law, boundedness and locality, all of which a
wrong-but-antisymmetric force would pass.
"""

import numpy as np

from _mixture import build
from field import Field
from transformer import VivariumTransformer


def _system(seed=3):
    X, species, bonds, mols, wi, chains = build(0, 24, 200, 22.0, 2,
                                                plant="random", branched=True, seed=seed)
    return X, Field(species, bonds, 22.0)


def test_force_is_the_exact_gradient_of_the_energy():
    """F = -dU/dx by central difference on the PRODUCTION topology.

    Measured max relative error 1.8e-8 over components with |F| > 1, which is central-difference
    truncation at h = 1e-6, not a discrepancy.
    """
    X, f = _system()
    F = f.forces(X)
    rng = np.random.default_rng(0)
    h = 1e-6
    worst = 0.0
    for i in rng.choice(len(X), 12, replace=False):
        for d in range(2):
            Xp, Xm = X.copy(), X.copy()
            Xp[i, d] += h
            Xm[i, d] -= h
            num = -(f.energy(Xp) - f.energy(Xm)) / (2 * h)
            if abs(F[i, d]) > 1.0:
                worst = max(worst, abs(num - F[i, d]) / abs(F[i, d]))
    assert worst < 1e-5, f"forces are not the gradient of the energy: rel err {worst:.2e}"


def test_one_forward_pass_conserves_energy_with_the_thermostat_off():
    """Velocity Verlet on exact gradients: drift is bounded and scales as dt^2.

    The SCALING is the discriminator, not the magnitude -- a wrong force gives drift that does not
    fall as dt^2. Measured exponent 1.85 over dt in [1e-3, 8e-3]; at the production dt = 8e-3 the
    drift over 3000 steps is 0.196% of the thermal energy (ndof/2)kT.

    Normalise by the THERMAL scale, never by the total energy: the total is a near-cancellation of
    -115.1 potential against +132.4 kinetic, and dividing by it inflates the drift 8-fold and reads
    as a failure when the dynamics is fine.
    """
    X0, f = _system()
    ndof = X0.size
    thermal = 0.5 * ndof * 0.45
    drifts = []
    for dt in (2e-3, 8e-3):
        tf = VivariumTransformer(f)
        rng = np.random.default_rng(1)
        X, v = X0.copy(), np.random.default_rng(1).normal(size=X0.shape) * np.sqrt(0.45)
        F = tf.attention(X)
        E0 = f.energy(X) + 0.5 * (v ** 2).sum()
        for _ in range(400):
            X, v, F = tf.forward(X, v, dt, 0.0, gamma=0.0, rng=rng, F=F)
        drifts.append(abs(f.energy(X) + 0.5 * (v ** 2).sum() - E0) / thermal)
    assert drifts[1] < 0.01, f"energy drift {drifts[1]:.4f} of thermal at dt=8e-3"
    assert drifts[1] > drifts[0], "drift should grow with dt if it is truncation error"


def test_thermostat_samples_the_correct_kinetic_temperature():
    """<KE> = (d/2) N kT and velocities are Gaussian.

    Measured 1.0002 +- 0.0015 with excess kurtosis +0.006 on 640 degrees of freedom. This is the
    reliable arm of the equipartition check -- small subsystems are statistics-limited, and error
    bars on a single trajectory must be blocked, not computed as if samples were independent
    (measured underestimate: 2.2x).
    """
    X0, f = _system()
    kT, dt = 0.45, 8e-3
    tf = VivariumTransformer(f)
    rng = np.random.default_rng(11)
    X, v = X0.copy(), rng.normal(size=X0.shape) * np.sqrt(kT)
    F = tf.attention(X)
    for _ in range(1500):
        X, v, F = tf.forward(X, v, dt, kT, gamma=1.0, rng=rng, F=F)
    ke, vs = [], []
    for i in range(3000):
        X, v, F = tf.forward(X, v, dt, kT, gamma=1.0, rng=rng, F=F)
        if i % 10 == 0:
            ke.append(0.5 * (v ** 2).sum())
            vs.append(v.copy())
    ratio = np.mean(ke) / (0.5 * X0.size * kT)
    vs = np.concatenate(vs).ravel()
    kurt = ((vs - vs.mean()) ** 4).mean() / vs.var() ** 2 - 3.0
    assert abs(ratio - 1.0) < 0.03, f"kinetic equipartition off: {ratio:.4f}"
    assert abs(kurt) < 0.15, f"velocities not Gaussian: excess kurtosis {kurt:+.4f}"
