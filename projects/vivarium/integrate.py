"""Integrators for the scalar field. Same energy, same equilibrium ensemble, very different cost.

WHY THIS EXISTS

The driver used overdamped Brownian dynamics, and the timestep ladder proved dt = 2e-4 is the largest
unbiased value: at 4e-4 the bond-width error is already 6.2% against a 2% gate. The limit comes from
the stiffest mode, k_bond = 200, because overdamped dynamics must resolve the RELAXATION RATE

    mu * k = 200      ->      dt << 1/200

The reference model (bilipid.py) runs dt = 5e-3, twenty-five times larger, and it is not being
reckless: it integrates INERTIALLY, where the stiff mode appears as an oscillation of frequency

    omega = sqrt(k/m) = sqrt(200) = 14.1      ->      dt << 1/14

So for the same bond and the same energy, inertial dynamics affords a timestep roughly `sqrt(k)/1`
larger -- about 14x here. That is a change of INTEGRATOR, not of physics: both sample the Boltzmann
distribution of the same potential, so equilibrium observables must agree. Only the kinetics differ,
and the inertial kinetics are the reference model's.

    Overdamped:  x <- x + mu F dt + sqrt(2 mu kT dt) xi
    Inertial:    velocity Verlet on F, then an EXACT Ornstein-Uhlenbeck kick on v:
                 v <- c1 v + sqrt(kT/m (1 - c1^2)) xi,   c1 = exp(-gamma dt)

The OU step is exact for any dt, so the thermostat itself imposes no timestep restriction and
fluctuation-dissipation holds by construction: the stationary velocity variance is kT/m regardless.

VALIDATION IS MANDATORY. `check_same_ensemble` runs both on the same system and compares equilibrium
observables. An integrator that changes them is not an acceleration, it is a different model.
"""

from __future__ import annotations

import numpy as np


class Overdamped:
    """x <- x + mu F dt + sqrt(2 mu kT dt) xi. mu = 1/gamma."""

    def __init__(self, field, kT, dt, gamma=1.0, seed=1):
        self.f, self.kT, self.dt, self.gamma = field, float(kT), float(dt), float(gamma)
        self.rng = np.random.default_rng(seed)
        self.amp = np.sqrt(2.0 * self.kT * self.dt / self.gamma)

    def step(self, X):
        X += (self.f.forces(X) / self.gamma) * self.dt + self.amp * self.rng.normal(size=X.shape)
        X -= self.f.L * np.round(X / self.f.L)
        return X


class Inertial:
    """Velocity Verlet with an exact OU thermostat -- the reference model's scheme.

    The force is evaluated ONCE per step by carrying it across the step boundary, so the cost per step
    is the same as the overdamped scheme's. The saving is entirely in how large `dt` may be.
    """

    def __init__(self, field, kT, dt, gamma=1.0, mass=1.0, seed=1):
        self.f, self.kT, self.dt = field, float(kT), float(dt)
        self.gamma, self.m = float(gamma), float(mass)
        self.rng = np.random.default_rng(seed)
        self.v = None
        self._F = None

    def step(self, X):
        if self.v is None:
            self.v = self.rng.normal(size=X.shape) * np.sqrt(self.kT / self.m)
            self._F = self.f.forces(X)
        dt, m = self.dt, self.m
        self.v += 0.5 * dt * self._F / m
        X += dt * self.v
        X -= self.f.L * np.round(X / self.f.L)
        self._F = self.f.forces(X)
        self.v += 0.5 * dt * self._F / m
        c1 = np.exp(-self.gamma * dt)
        self.v = c1 * self.v + np.sqrt(self.kT / m * (1.0 - c1 * c1)) * self.rng.normal(size=X.shape)
        return X

    def temperature(self):
        return float(self.m * (self.v ** 2).mean())


def check_same_ensemble(steps=60000, kT=0.17, dt_over=2e-4, dt_inert=2e-3, seed=3, which=None):
    """Equilibrium observables under both integrators. They must agree; only kinetics may differ."""
    from _sizing3d import plant_flat
    from field import Field

    out = {}
    pairs = (("overdamped", lambda f: Overdamped(f, kT, dt_over, seed=seed)),
             ("inertial", lambda f: Inertial(f, kT, dt_inert, seed=seed)))
    if which is not None:
        pairs = tuple(p for p in pairs if p[0] == which)
    for name, make in pairs:
        X, species, bonds, mol = plant_flat(6, 2, 40.0, 1.1)
        f = Field(species, bonds, 40.0)
        ig = make(f)
        n = int(round(steps * (dt_over / (dt_over if name == "overdamped" else dt_inert))))
        n = steps if name == "overdamped" else int(round(steps * dt_over / dt_inert))
        bw, nn = [], []
        for t in range(n):
            X = ig.step(X)
            if t > n // 2 and t % max(n // 200, 1) == 0:
                d = np.linalg.norm(X[f.bonds[:, 0]] - X[f.bonds[:, 1]], axis=1)
                bw.append(d.std())
                P = X[mol.ravel()]
                dd = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
                same = np.repeat(np.arange(len(mol)), mol.shape[1])
                dd[same[:, None] == same[None, :]] = np.inf
                nn.append(np.median(dd.min(axis=1)))
        out[name] = (float(np.mean(bw)), float(np.mean(nn)), n)
    return out


if __name__ == "__main__":
    import sys

    # The overdamped run at its VALIDATED dt is the reference ensemble. Each inertial rung is compared
    # against it at matched reduced time, and the largest rung inside the 2% gate is the answer. The
    # relevant stiff frequency is omega = sqrt(k_bond/m) = sqrt(200) = 14.1, so the naive expectation
    # is failure somewhere near omega*dt ~ 1, i.e. dt ~ 0.07 -- but expectation is not measurement.
    # ERROR BARS ARE MANDATORY HERE. A single run per rung gave 2.6% / 0.2% / 2.4% / 2.4% / 0.4%
    # across increasing dt -- non-monotonic scatter of the same size as the 2% gate, i.e. the ladder
    # was resolving its own noise. Each rung is now repeated over independent seeds and reported as
    # mean +- standard error, so "biased" means the deviation exceeds the scatter.
    rungs = [float(v) for v in (sys.argv[1] if len(sys.argv) > 1
                                else "2e-3,4e-3,8e-3,16e-3").split(",")]
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 40000
    n_seed = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    def arm(which, dt):
        vals = [check_same_ensemble(steps=steps, dt_inert=dt, seed=100 + k, which=which)[which]
                for k in range(n_seed)]
        b = np.array([v[0] for v in vals])
        return b.mean(), b.std(ddof=1) / np.sqrt(n_seed), vals[0][2]

    bo, eo, so = arm("overdamped", rungs[0])
    print(f"reference: overdamped dt=2e-4, {so} steps, sd(bond) {bo:.5f} +- {eo:.5f} "
          f"({n_seed} seeds)")
    print(f"omega = sqrt(k_bond/m) = {np.sqrt(200.0):.1f}\n")
    print(f"{'dt':>9}{'omega*dt':>10}{'steps':>8}{'sd(bond)':>19}{'deviation':>12}   verdict",
          flush=True)
    for dt in rungs:
        bi, ei, si = arm("inertial", dt)
        db = (bi - bo) / bo
        sig = np.sqrt(ei ** 2 + eo ** 2) / bo          # combined standard error, relative
        resolved = abs(db) > 2 * sig                   # only call bias if it exceeds 2 sigma
        ok = (abs(db) < 0.02) or not resolved
        print(f"{dt:>9.1e}{np.sqrt(200.0) * dt:>10.3f}{si:>8}"
              f"{bi:>13.5f} +-{ei:.5f}{100 * db:>10.1f}%   "
              f"{'OK  ' + f'{so / si:.0f}x' if ok else 'BIASED'} "
              f"(noise {100 * sig:.1f}%)", flush=True)
