"""Measure the 3-D lipid's geometry, then PREDICT the minimum vesicle size before running one.

WHY THIS RUNS FIRST

A planted 300-lipid 3-D vesicle collapsed: lumen water 60 -> 10, shell CV 0.136 -> 0.282, and the
render went from a clean ring cross-section to a filled ball. The obvious explanation is geometric --
300 lipids place the mid-surface at R ~ 4.1 while the bilayer is about as thick, so the lumen was
marginal before the first step. That explanation is plausible, post-hoc, and therefore worth nothing
until it makes a prediction that can fail.

So this measures, on a planted FLAT bilayer relaxed under the same field:

    a   area per lipid per leaflet
    d   head-to-head thickness

and predicts the smallest vesicle with a lumen of at least `lumen_min`:

    R_mid  =  d/2 + lumen_min          (mid-surface radius)
    N      =  4 pi R_mid^2 / a         (both leaflets, from the mass-balance rule)

FALSIFICATION, STATED BEFORE THE RUN
    If a vesicle planted at this N collapses the way the 300-lipid one did -- lumen draining toward
    bulk and shell CV rising -- then the geometric explanation is WRONG and the force field does not
    support a 3-D vesicle, which is a result about the physics rather than about the sizing.
    If it holds with the lumen stationary and shell CV flat or falling, the collapse was a sizing
    error and 3-D stability is established.

The flat bilayer is planted, not assembled, because this measures the lipid's dimensions, not whether
a membrane forms. Both are needed and they are separate questions.
"""

from __future__ import annotations

import sys

import numpy as np

from field import Field, HEAD, TAIL, WATER
from integrate import Inertial


def plant_flat(n_side, n_tail, L, gap):
    """Two leaflets on a square lattice in the xy plane, tails meeting at z = 0, heads pointing out."""
    nb = 1 + n_tail
    n_lip = 2 * n_side * n_side
    n = n_lip * nb
    X = np.zeros((n, 3))
    species = np.empty(n, dtype=np.int64)
    mol = np.arange(n).reshape(n_lip, nb)
    species[mol[:, 0]] = HEAD
    species[mol[:, 1:]] = TAIL
    xs = (np.arange(n_side) - (n_side - 1) / 2.0) * gap
    gx, gy = np.meshgrid(xs, xs, indexing="ij")
    flat = np.stack([gx.ravel(), gy.ravel()], axis=1)
    k = 0
    for sgn in (+1.0, -1.0):
        for j in range(len(flat)):
            idx = mol[k]
            for b in range(nb):
                z = sgn * (0.5 + (nb - 1 - b) * 1.0)
                X[idx[b]] = np.array([flat[j, 0], flat[j, 1], z])
            k += 1
    bonds = np.concatenate([np.stack([mol[:, b], mol[:, b + 1]], 1) for b in range(nb - 1)])
    return X, species, bonds, mol


def geometry(X, mol, n_side):
    """Area per lipid per leaflet, and head-to-head thickness."""
    head = X[mol[:, 0]]
    tail = X[mol[:, 1:]].mean(axis=1)
    upper = head[:, 2] > tail[:, 2]
    thickness = float(head[upper][:, 2].mean() - head[~upper][:, 2].mean())
    # in-plane area actually occupied: the bounding span of one leaflet over its lipid count
    p = head[upper][:, :2]
    span_x = float(p[:, 0].max() - p[:, 0].min())
    span_y = float(p[:, 1].max() - p[:, 1].min())
    # spans measure centre-to-centre, so one lattice step is added back on each axis
    per = int(upper.sum())
    step_x, step_y = span_x / max(n_side - 1, 1), span_y / max(n_side - 1, 1)
    area = (span_x + step_x) * (span_y + step_y)
    return area / per, abs(thickness)


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
    n_tail = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    lumen_min = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    n_side = 8
    gap, L = 1.1, 40.0

    X, species, bonds, mol = plant_flat(n_side, n_tail, L, gap)
    f = Field(species, bonds, L)
    a0, d0 = geometry(X, mol, n_side)
    kT, dt = 0.17, 8e-3
    ig = Inertial(f, kT, dt, seed=1)
    print(f"planted flat 3-D bilayer: {len(mol)} lipids (1 head + {n_tail} tails), "
          f"vacuum, kT={kT}", flush=True)
    print(f"{'step':>8}{'E/lipid':>10}{'a (area/lipid)':>16}{'d (thickness)':>15}", flush=True)
    print(f"{0:>8}{f.energy(X) / len(mol):>10.3f}{a0:>16.3f}{d0:>15.3f}", flush=True)
    every = max(steps // 6, 1)
    for t in range(1, steps + 1):
        X = ig.step(X)
        if t % every == 0:
            a, d = geometry(X, mol, n_side)
            print(f"{t:>8}{f.energy(X) / len(mol):>10.3f}{a:>16.3f}{d:>15.3f}", flush=True)

    a, d = geometry(X, mol, n_side)
    R_mid = d / 2.0 + lumen_min
    N = 4.0 * np.pi * R_mid ** 2 / a
    print(f"\nMEASURED   a = {a:.3f} sigma^2 per lipid per leaflet, d = {d:.3f} sigma")
    print(f"PREDICTION for a lumen of at least {lumen_min} sigma:")
    print(f"    R_mid = d/2 + lumen = {d / 2:.2f} + {lumen_min:.1f} = {R_mid:.2f}")
    print(f"    N     = 4 pi R_mid^2 / a = {N:.0f} lipids")
    print(f"\nThe 300-lipid vesicle that collapsed had R_mid = "
          f"{np.sqrt(300 * a / (4 * np.pi)):.2f}, i.e. a lumen of "
          f"{np.sqrt(300 * a / (4 * np.pi)) - d / 2:.2f} sigma.")
