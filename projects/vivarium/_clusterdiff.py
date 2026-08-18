"""Cluster diffusion vs size: the kinetic clock that actually governs coarsening.

The earlier "0.26 box crossings" estimate used FREE MONOMER diffusion as the clock. That is the wrong
clock. After the initial rapid condensation the moving objects are aggregates, and their mobility is
what sets whether coarsening can proceed.

FOR THIS INTEGRATOR THE ANSWER IS ANALYTIC, and it is worth stating before measuring. Overdamped
Brownian dynamics with INDEPENDENT per-bead noise gives, for a cluster of N beads,

    dX_com = (1/N) sum_i [ mu F_i dt + sqrt(2 mu kT dt) xi_i ].

Internal forces cancel in pairs, so the deterministic part vanishes for an isolated cluster, and the
noise terms are independent, so their mean has variance 1/N of a single bead's:

    D_cluster = D_1 / N_beads          exactly, i.e. alpha = 1 in D ~ M^-alpha,

regardless of how the cluster is bound internally. There is no hydrodynamic coupling to make large
aggregates move faster, because the model has no momentum-carrying solvent -- explicit water beads
here provide thermodynamics and sterics, not hydrodynamics.

CONSEQUENCE. A 64-lipid patch of 3-bead lipids has 192 beads and therefore diffuses ~192x more slowly
than one bead. Coarsening by aggregate collision becomes drastically slower as it proceeds, which is
exactly the observed trajectory: fast small-cluster formation, then apparently frozen.

This script MEASURES it rather than trusting the algebra, because the derivation assumes an isolated
cluster and the runs are not isolated.
"""

import sys

import numpy as np

from field import Field, HEAD, TAIL


def make_blob(M, n_tail, L, seed=0):
    """A compact aggregate of M lipids, tails inward -- geometry is irrelevant to the COM result."""
    rng = np.random.default_rng(seed)
    nb = 1 + n_tail
    n = M * nb
    X = np.zeros((n, 2))
    species = np.empty(n, dtype=np.int64)
    mol = np.arange(n).reshape(M, nb)
    species[mol[:, 0]] = HEAD
    species[mol[:, 1:]] = TAIL
    R = max(np.sqrt(M / np.pi), 1.2)
    th = (np.arange(M) + 0.5) / M * 2 * np.pi
    rad = np.stack([np.cos(th), np.sin(th)], 1)
    for b in range(nb):
        X[mol[:, b]] = rad * (R + (nb - 1 - b) * 1.0)
    bonds = np.concatenate([np.stack([mol[:, b], mol[:, b + 1]], 1) for b in range(nb - 1)])
    return X, species, bonds, mol


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    kT, dt, n_tail, L = 0.17, 2e-4, 2, 200.0        # big box: isolated cluster, no periodic contact
    print(f"cluster diffusion, kT={kT}, dt={dt}, {steps} steps, isolated in vacuum")
    print(f"prediction: D_M = D_1 / N_beads exactly (independent per-bead noise, internal forces "
          f"cancel in the COM)")
    print(f"{'M lipids':>9}{'N beads':>9}{'D_measured':>13}{'D_1/N':>11}{'ratio':>8}", flush=True)
    D1 = kT                                          # mu = 1, so D_1 = kT
    # A SINGLE trajectory's MSD is far too noisy to test the prediction -- the first run gave ratios
    # scattering 0.13 to 1.20 with no trend, which is sampling noise rather than physics. The MSD is
    # ENSEMBLE-averaged over independent seeds before the diffusion constant is fitted.
    n_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    for M in (1, 2, 4, 8, 16, 32, 64):
        acc = None
        for sd in range(n_seed):
            X, species, bonds, mol = make_blob(M, n_tail, L)
            f = Field(species, bonds, L)
            rng = np.random.default_rng(1000 + sd)
            amp = np.sqrt(2.0 * kT * dt)
            com0 = X.mean(axis=0).copy()
            cur = []
            for t in range(steps):
                X += f.forces(X) * dt + amp * rng.normal(size=X.shape)
                if (t + 1) % 200 == 0:
                    d = X.mean(axis=0) - com0
                    cur.append(float(d @ d))
            acc = np.array(cur) if acc is None else acc + np.array(cur)
        yy = acc / n_seed
        tt = np.arange(1, len(yy) + 1) * 200 * dt
        half = len(tt) // 2
        D = float((tt[half:] @ yy[half:]) / (tt[half:] @ tt[half:]) / 4.0)   # MSD = 4 D t in 2-D
        nb_tot = M * (1 + n_tail)
        print(f"{M:>9}{nb_tot:>9}{D:>13.5f}{D1 / nb_tot:>11.5f}{D / (D1 / nb_tot):>8.2f}", flush=True)
