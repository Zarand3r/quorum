"""Is the membrane a FLUID or a GEL? The hypothesis that would explain every kinetic failure at once.

A vesicle can only form if the membrane can rearrange: patches must merge, edges must heal, topology
must change. That requires a LIQUID bilayer, in which lipids diffuse past one another. A gel bilayer
is a solid sheet -- it holds whatever shape it is given and cannot anneal into a new one.

Several independent observations here point at gel:

  * leaflet composition never changed in 200000 steps (no flip-flop, no exchange);
  * coarsening stalls after the initial condensation;
  * a planted arc sits open for 250000 steps next to a closed state ~74 kT lower;
  * adding 1-3 chain stiffness took the bilayer from d = 5.72 to 8.00 sigma with area per lipid down
    to 1.15 -- fully extended tails at tight packing, which is what a gel looks like;
  * the solvent phase-separates, because at kT/eps = 0.17 everything is far below its critical point.

That is an inference from consistent signals, not a measurement, so this measures it.

TWO OBSERVABLES, because each alone can mislead
    lateral MSD    in-plane mean squared displacement of lipid centres, with the membrane's own
                   centre-of-mass drift removed. Expressed in units of the area per lipid, so
                   "moved further than one lipid spacing" is directly visible.
    neighbour retention
                   fraction of a lipid's initial six nearest in-leaflet neighbours that are still
                   among its nearest after time t. A fluid forgets its neighbours; a gel keeps them.
                   This one cannot be faked by collective drift or by breathing modes.

The sweep is over TEMPERATURE, because the hypothesis is that kT/eps = 0.17 sits far below the
gel-to-fluid transition. Thickness and connectivity are reported alongside so that "fluid" is not
confused with "dissolved".
"""

import sys

import numpy as np

from _sizing3d import geometry, plant_flat
from field import Field
from integrate import Inertial


def in_leaflet_neighbours(P, upper, k=6):
    """Indices of the k nearest same-leaflet lipids, by in-plane distance."""
    out = {}
    for sel in (upper, ~upper):
        idx = np.flatnonzero(sel)
        if len(idx) <= k:
            continue
        xy = P[idx][:, :2]
        d = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)
        np.fill_diagonal(d, np.inf)
        nn = np.argsort(d, axis=1)[:, :k]
        for a, row in zip(idx, nn):
            out[a] = set(idx[row])
    return out


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    n_side, n_tail, L = 7, 2, 40.0
    print(f"planted flat bilayer, {2 * n_side * n_side} lipids, vacuum, dt=8e-3, {steps} steps")
    print(f"{'kT':>6}{'kT/eps':>8}{'thick':>8}{'a/lipid':>9}{'MSD/a':>8}"
          f"{'nbr kept':>10}   phase", flush=True)
    for kT in (0.17, 0.35, 0.55, 0.75, 1.00):
        X, species, bonds, mol = plant_flat(n_side, n_tail, L, 1.1)
        f = Field(species, bonds, L)
        ig = Inertial(f, kT, 8e-3, seed=5)
        for _ in range(steps // 4):                       # equilibrate before the clock starts
            X = ig.step(X)
        P0 = X[mol].mean(axis=1).copy()
        head0, tail0 = X[mol[:, 0]], X[mol[:, 1:]].mean(axis=1)
        upper = head0[:, 2] > tail0[:, 2]
        nb0 = in_leaflet_neighbours(P0, upper)
        for _ in range(steps):
            X = ig.step(X)
        P1 = X[mol].mean(axis=1)
        a, d = geometry(X, mol, n_side)
        disp = (P1 - P0)[:, :2]
        disp -= disp.mean(axis=0)                          # remove the sheet's own drift
        msd = float((disp ** 2).sum(axis=1).mean())
        nb1 = in_leaflet_neighbours(P1, upper)
        common = [len(nb0[i] & nb1[i]) / 6.0 for i in nb0 if i in nb1]
        kept = float(np.mean(common)) if common else float("nan")
        # a fluid must both FORGET neighbours and still BE a membrane
        fluid = msd / a > 1.0 and kept < 0.6
        gel = msd / a < 0.3 and kept > 0.8
        phase = "FLUID" if fluid else "gel (caged)" if gel else "intermediate"
        if d < 2.0:
            phase = "dissolved / not a membrane"
        print(f"{kT:>6.2f}{kT:>8.2f}{d:>8.2f}{a:>9.3f}{msd / a:>8.2f}{kept:>10.2f}   {phase}",
              flush=True)
