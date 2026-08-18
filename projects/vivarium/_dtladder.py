"""Timestep convergence: choose the largest dt whose STATIC observables are unbiased.

WHY THE OLD CRITERION WAS WRONG
    dt was justified by F_max * dt = 0.024, i.e. by force magnitude. For overdamped Brownian dynamics

        x <- x + mu F dt + sqrt(2 mu kT dt) xi

    the controlling quantity is the largest CURVATURE of the potential, not the largest force. For a
    harmonic mode U = k x^2 / 2 the Euler-Maruyama map is x <- (1 - mu k dt) x + noise, so stability
    needs mu k dt < 2 -- but long before that, sampling is biased:

        <x^2>_dt = (kT / k) / (1 - mu k dt / 2)

    so the mode is sampled TOO BROAD by a factor that grows with dt. Stability is not accuracy.

    The stiffest mode here is not the core. The core contributes 2 * core_height / sigma^2 = 75.6,
    while the 1-2 bond and the 1-3 stiffener both carry k_bond = 200. The bond therefore sets both
    bounds, and any dt chosen from the core alone is too optimistic.

WHAT IS COMPARED
    Static distributions at matched REDUCED TIME (steps = T / dt), on a planted flat bilayer:
    bond length, 1-3 distance, nearest non-bonded separation, membrane thickness, area per lipid.
    Trajectories are not compared -- they diverge by construction; equilibrium averages must not.

ACCEPTANCE, PREREGISTERED
    The largest dt whose every observable is within 2% of the dt -> 0 reference, which is taken as the
    smallest rung. The predicted bond-variance inflation 1/(1 - k dt / 2) is printed alongside, so the
    measurement can be checked against theory rather than merely inspected.
"""

import sys

import numpy as np

from _sizing3d import geometry, plant_flat
from field import Field


SAMPLE_EVERY_T = 0.01          # reduced-time stride between samples, identical for every rung


def run(dt, T, n_side=6, n_tail=2, kT=0.17, L=40.0, seed=1):
    X, species, bonds, mol = plant_flat(n_side, n_tail, L, 1.1)
    f = Field(species, bonds, L)
    rng = np.random.default_rng(seed)
    amp = np.sqrt(2.0 * kT * dt)
    steps = int(round(T / dt))
    every = max(int(round(SAMPLE_EVERY_T / dt)), 1)
    nb, n13 = f.bonds, f.angles
    acc = {k: [] for k in ("bond", "b13", "nn")}
    for t in range(steps):
        X += f.forces(X) * dt + amp * rng.normal(size=X.shape)
        # sample at equal REDUCED-TIME intervals, not equal step counts: a fixed stride in steps
        # gives the small-dt rungs proportionally more samples over the same physical time, so the
        # rungs would not be compared at equal statistical weight.
        if t > steps // 2 and t % every == 0:
            # the STANDARD DEVIATION of a stiff bond is the diagnostic, not its mean. Euler-Maruyama
            # inflates <x^2> by 1/(1 - k dt / 2), i.e. the width, while the mean of a harmonic mode is
            # almost insensitive to dt -- the first version of this ladder compared means and
            # therefore measured nothing, flagging "bias" from a noisy area estimator instead.
            bd = np.linalg.norm(X[nb[:, 0]] - X[nb[:, 1]], axis=1)
            acc["bond"].append(bd.std())
            if len(n13):
                a13 = np.linalg.norm(X[n13[:, 0]] - X[n13[:, 1]], axis=1)
                acc["b13"].append(a13.std())
            P = X[mol.ravel()]
            d = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
            same = np.repeat(np.arange(len(mol)), mol.shape[1])
            d[same[:, None] == same[None, :]] = np.inf
            acc["nn"].append(np.median(d.min(axis=1)))
    return {k: float(np.mean(v)) for k, v in acc.items() if v}


if __name__ == "__main__":
    T = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
    rungs = [float(v) for v in (sys.argv[2] if len(sys.argv) > 2
                                else "2e-4,4e-4,8e-4,16e-4").split(",")]
    k_stiff = 200.0                     # k_bond, the stiffest mode; core is 2*37.8 = 75.6
    # NOTE. The lowest rung is only a REFERENCE, not a proven converged value: showing that larger
    # timesteps differ from it does not show that it agrees with the dt -> 0 limit. Rungs below the
    # working value are required to establish the asymptote, which is what this run adds.
    print(f"timestep ladder at matched reduced time T = {T}, stiffest mode k = {k_stiff}")
    print(f"stability needs k*dt < 2; predicted variance inflation is 1/(1 - k*dt/2)\n")
    print(f"{'dt':>9}{'k*dt':>7}{'predict':>9}{'steps':>8}"
          f"{'sd(bond)':>10}{'ratio':>8}{'sd(1-3)':>9}{'nn':>8}   verdict", flush=True)
    ref = None
    for dt in rungs:
        kdt = k_stiff * dt
        infl = np.sqrt(1.0 / (1.0 - kdt / 2.0)) if kdt < 2 else float("inf")   # WIDTH, not variance
        r = run(dt, T)
        if ref is None:
            ref, note, ratio = r, "reference (dt -> 0)", 1.0
        else:
            ratio = r["bond"] / ref["bond"]
            worst = max(abs(r[k] - ref[k]) / max(abs(ref[k]), 1e-12) for k in ref)
            note = (f"widths +{100 * (ratio - 1):.1f}% vs predicted +{100 * (infl - 1):.1f}%   "
                    f"{'OK' if worst < 0.02 else 'BIASED'}")
        print(f"{dt:>9.1e}{kdt:>7.3f}{infl:>9.4f}{int(T / dt):>8}"
              f"{r['bond']:>10.5f}{ratio:>8.3f}{r.get('b13', float('nan')):>9.5f}"
              f"{r['nn']:>8.4f}   {note}", flush=True)
