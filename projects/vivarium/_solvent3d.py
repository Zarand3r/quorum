"""At what packing fraction is this model's water actually a LIQUID?

A 3-D vesicle run at packing fraction 0.15 produced a render in which the solvent had condensed into
separate droplets with vacuum between them, and the lipid aggregate was a mixed blob. That is not a
solvated system, and every observable taken from it is meaningless -- including a "lumen density 10x
bulk", where bulk was computed as N_water / L^3 and therefore averaged over the vacuum.

The cause is thermodynamic, not numerical. Water carries the strongest well in `chi` (1.00) against
kT = 0.17, i.e. about 5.9 kT, so below its critical density it phase-separates into droplets and
vapour exactly as a Lennard-Jones fluid does. Choosing a packing fraction because it was affordable,
without checking it lies in the liquid, is the same class of error as inheriting a box density
calibrated against interpenetrating beads.

WHAT IS MEASURED
    Pure solvent, no lipid, at several packing fractions. For each:
      * the largest connected water cluster as a fraction of all water -- a liquid at these densities
        percolates, a droplet phase does not;
      * the density contrast between the densest and sparsest regions of the box, on a coarse grid.
        A homogeneous liquid is flat; a droplet phase is not.

FALSIFICATION / ACCEPTANCE, stated first
    A packing fraction is usable when the largest cluster holds essentially all the water AND the
    coarse-grained density contrast is small. The lowest such value is what 3-D runs should use, since
    solvent beads dominate the cost.
"""

import sys
from collections import deque

import numpy as np

from field import Field, WATER
from integrate import Inertial


def largest_water_fraction(X, L, cut=1.5):
    n = len(X)
    d = X[:, None, :] - X[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    lab = -np.ones(n, int)
    c = 0
    for s in range(n):
        if lab[s] >= 0:
            continue
        q = deque([s])
        lab[s] = c
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = c
                    q.append(j)
        c += 1
    return float(np.bincount(lab).max()) / n, c


def density_contrast(X, L, nbin=4):
    idx = np.floor((X + 0.5 * L) / (L / nbin)).astype(int) % nbin
    flat = (idx[:, 0] * nbin + idx[:, 1]) * nbin + idx[:, 2]
    counts = np.bincount(flat, minlength=nbin ** 3).astype(float)
    return float(counts.max() / max(counts.mean(), 1e-9)), float(counts.min() / max(counts.mean(), 1e-9))


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    L, kT = 16.0, 0.17
    print(f"pure solvent, L={L}, kT={kT}, {steps} steps at dt=8e-3")
    print(f"{'phi':>7}{'n_water':>9}{'largest frac':>14}{'clusters':>10}"
          f"{'dens max/mean':>15}{'min/mean':>10}   verdict", flush=True)
    for phi in (0.15, 0.25, 0.35, 0.45, 0.55):
        n = int(round(phi * L ** 3 / (np.pi / 6.0)))
        rng = np.random.default_rng(0)
        X = rng.uniform(-L / 2, L / 2, size=(n, 3))
        species = np.full(n, WATER, dtype=np.int64)
        f = Field(species, np.zeros((0, 2), int), L)
        ig = Inertial(f, kT, 8e-3, seed=2)
        for _ in range(steps):
            X = ig.step(X)
        frac, nc = largest_water_fraction(X, L)
        hi, lo = density_contrast(X, L)
        ok = frac > 0.95 and hi < 1.6 and lo > 0.4
        print(f"{phi:>7.2f}{n:>9}{frac:>14.3f}{nc:>10}{hi:>15.2f}{lo:>10.2f}   "
              f"{'LIQUID' if ok else 'droplets / not homogeneous'}", flush=True)
