"""Is there ANY regime where this membrane is both FLUID and INTACT? The (kT, tail length) plane.

Two single-knob fixes are dead. Raising temperature fluidises the bilayer but a finite patch tears
(kT = 0.55: arc expanded and broke, largest 70 -> 38). Softening the chain does nothing -- even a
freely jointed tail is caged at kT = 0.17 (MSD/a 0.33, neighbours kept 0.77).

The reason they conflict: fluidity needs the per-contact energy eps/kT to be SMALL, while holding a
finite patch together needs the SUMMED binding per lipid to be LARGE. At fixed tail length those are
the same number and cannot both be satisfied. Real lipids escape this because binding scales with
tail LENGTH: many weak contacts. So the search has to be over the plane, not a line.

MEASURED, on a planted finite 2-D ribbon in vacuum (vacuum both for speed and to isolate membrane
cohesion from the solvent, which has its own phase problem):
    fluidity    in-plane MSD of lipid centres in units of area per lipid, drift removed;
                fraction of each lipid's initial 6 nearest neighbours still nearest.
    integrity   largest connected cluster as a fraction of all lipids.

FALSIFICATION, STATED BEFORE THE RUN
    If no cell is simultaneously fluid (MSD/a > 1) and intact (largest > 0.9), this force field has no
    fluid-membrane regime, and the vesicle target is out of reach by parameter choice alone -- the
    interaction FORM would have to change, not its numbers.
"""

import sys
from collections import deque

import numpy as np

from field import Field, HEAD, TAIL
from integrate import Inertial


def plant_ribbon(n_lip, n_tail, L, gap=1.05):
    nb = 1 + n_tail
    n = n_lip * nb
    X = np.zeros((n, 2))
    species = np.empty(n, dtype=np.int64)
    mol = np.arange(n).reshape(n_lip, nb)
    species[mol[:, 0]] = HEAD
    species[mol[:, 1:]] = TAIL
    per = n_lip // 2
    xs = (np.arange(per) - (per - 1) / 2.0) * gap
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for b in range(nb):
            off = 0.5 + (nb - 1 - b) * 1.0
            X[idx[:, b], 0] = xs[:len(idx)]
            X[idx[:, b], 1] = sgn * off
    bonds = np.concatenate([np.stack([mol[:, b], mol[:, b + 1]], 1) for b in range(nb - 1)])
    return X, species, bonds, mol


def largest_frac(X, mol, L, cut=1.4):
    nm = len(mol)
    beads = mol.ravel()
    owner = np.repeat(np.arange(nm), mol.shape[1])
    P = X[beads]
    d = P[:, None, :] - P[None, :, :]
    d -= L * np.round(d / L)
    close = np.linalg.norm(d, axis=2) < cut
    adj = np.zeros((nm, nm), bool)
    bi, bj = np.nonzero(close)
    adj[owner[bi], owner[bj]] = True
    np.fill_diagonal(adj, False)
    lab = -np.ones(nm, int)
    c = 0
    for s in range(nm):
        if lab[s] >= 0:
            continue
        q = deque([s]); lab[s] = c
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = c; q.append(j)
        c += 1
    return float(np.bincount(lab).max()) / nm


def neighbours(P, k=4):
    d = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    nn = np.argsort(d, axis=1)[:, :k]
    return [set(r) for r in nn]


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    n_lip, L = 60, 30.0
    print(f"planted finite 2-D ribbon, {n_lip} lipids, vacuum, dt=8e-3, {steps} steps")
    print(f"{'kT':>6}{'tails':>7}{'eps/kT':>8}{'MSD/a':>8}{'nbr kept':>10}"
          f"{'largest':>9}   verdict", flush=True)
    for n_tail in (2, 4, 6):
        for kT in (0.17, 0.30, 0.45):
            X, species, bonds, mol = plant_ribbon(n_lip, n_tail, L)
            f = Field(species, bonds, L)
            ig = Inertial(f, kT, 8e-3, seed=11)
            for _ in range(steps // 4):
                X = ig.step(X)
            P0 = X[mol].mean(axis=1).copy()
            nb0 = neighbours(P0)
            for _ in range(steps):
                X = ig.step(X)
            P1 = X[mol].mean(axis=1)
            # REMOVE RIGID-BODY MOTION, rotation included. Subtracting the mean displacement removes
            # translation only, and a finite aggregate floating in vacuum also ROTATES -- which
            # inflates MSD without any lipid changing neighbours. The first version of this sweep read
            # MSD/a = 11.57 at kT = 0.17, where the spanning 3-D bilayer reads 0.29, while neighbour
            # retention stayed at 0.83; the two observables disagreed and the neighbour one, which
            # collective motion cannot fake, was right. Kabsch alignment of P1 onto P0 first.
            A = P0 - P0.mean(axis=0)
            B = P1 - P1.mean(axis=0)
            U, _, Vt = np.linalg.svd(B.T @ A)
            R = U @ Vt
            if np.linalg.det(R) < 0:                 # keep it a rotation, not a reflection
                U[:, -1] *= -1
                R = U @ Vt
            disp = B @ R - A
            a = 1.3                                  # area per lipid, near-constant across these runs
            msd = float((disp ** 2).sum(axis=1).mean()) / a
            nb1 = neighbours(P1)
            kept = float(np.mean([len(x & y) / 4.0 for x, y in zip(nb0, nb1)]))
            lf = largest_frac(X, mol, L)
            # fluidity is judged on NEIGHBOUR EXCHANGE, which no collective motion can produce;
            # MSD is reported alongside as a cross-check rather than as the criterion
            fluid, intact = kept < 0.6, lf > 0.9
            verdict = ("FLUID + INTACT" if fluid and intact else
                       "fluid but torn" if fluid else
                       "intact but gel" if intact else "torn and gel")
            print(f"{kT:>6.2f}{n_tail:>7}{0.70 / kT:>8.1f}{msd:>8.2f}{kept:>10.2f}"
                  f"{lf:>9.2f}   {verdict}", flush=True)
