"""P_fuse: do two aggregates in CONTACT actually merge, or is transport the whole story?

Coarsening is arrested -- the largest aggregate has held at 178/200 for 105000 steps while satellites
sit metres away in simulation terms and never arrive. The measured `D_M = D_1 / N_beads` explains why
they never MEET. It does not say what happens when they do.

Those are different blockers with different cures:

    they rarely meet, but merge on contact   -> pure transport limit; fix with concentration,
                                                seeding, or an explicit-solvent-free speedup
    they meet often but bounce apart         -> a FUSION BARRIER; more sampling will not help and the
                                                interaction form is implicated

This places two equal aggregates deliberately IN CONTACT and asks only whether they become one. That
removes diffusion from the question entirely, which is what makes it cheap and decisive.

MEASURED, over independent seeds: the fraction of trials in which the two aggregates are a single
connected cluster at the end, and the size of the largest cluster relative to the total.

FALSIFICATION, STATED BEFORE THE RUN
    If P_fuse is near 1, transport is the whole story and the emergence failures are a sampling
    problem with a known scaling. If P_fuse is near 0 despite starting in contact, there is a barrier
    to merging two bilayer patches, and no amount of running or concentration will produce one
    aggregate -- which would redirect the work at the interaction form.
"""

import sys
from collections import deque

import numpy as np

from field import Field, HEAD, TAIL, WATER
from integrate import Inertial


def two_patches(n_each, n_tail, L, gap, n_water, seed=0):
    """Two flat two-leaflet ribbons, end to end, separated by `gap` along x."""
    rng = np.random.default_rng(seed)
    nb = 1 + n_tail
    n_lip = 2 * n_each
    n = n_lip * nb + n_water
    X = np.zeros((n, 2))
    species = np.empty(n, dtype=np.int64)
    mol = np.arange(n_lip * nb).reshape(n_lip, nb)
    species[mol[:, 0]] = HEAD
    species[mol[:, 1:]] = TAIL
    per = n_each // 2
    k = 0
    for patch, x0 in ((0, -(per * 1.05 + gap) / 2), (1, +(per * 1.05 + gap) / 2)):
        xs = (np.arange(per) - (per - 1) / 2.0) * 1.05 + x0
        for sgn in (+1.0, -1.0):
            for j in range(per):
                idx = mol[k]
                for b in range(nb):
                    X[idx[b], 0] = xs[j]
                    X[idx[b], 1] = sgn * (0.5 + (nb - 1 - b) * 1.0)
                k += 1
    wi = np.arange(n_lip * nb, n)
    species[wi] = WATER
    X[wi] = rng.uniform(-L / 2, L / 2, size=(n_water, 2))
    return X, species, np.concatenate([np.stack([mol[:, b], mol[:, b + 1]], 1)
                                       for b in range(nb - 1)]), mol


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


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    n_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    # GEOMETRY CHECK, done analytically before trusting the run. Each patch is (n_each/2) * 1.05 wide,
    # so two patches plus the gap must FIT in L. The first launch used n_each = 60 in L = 40: each
    # patch 31.5 wide, two spanning 63 + gap in a 40 box, so they wrapped through the periodic
    # boundary and overlapped. That would have produced a meaningless P_fuse rather than an obviously
    # broken one, which is the dangerous kind.
    # kT is now swept: the gap-0 arm is a PATCH STABILITY test, not just a fusion control. At 15
    # seeds only 7/15 joined patches stayed joined at kT = 0.45, so a bilayer patch splits more often
    # than not at the temperature chosen for fluidity. Too cold is a gel that cannot rearrange; too
    # warm is a patch that falls apart. This maps the window between.
    kT = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
    n_tail, n_each, L, phi = 4, 30, 40.0, 0.55
    width = (n_each // 2) * 1.05
    assert 2 * width + 2.5 + 4.0 < L, (
        f"two patches of width {width:.1f} plus the largest gap do not fit in L={L}")
    n_water = int(round(phi * L * L / (np.pi * 0.25))) - (1 + n_tail) * 2 * n_each

    print(f"P_fuse: two {n_each}-lipid patches placed IN CONTACT, branched, kT={kT}, "
          f"{n_seed} seeds, {steps} steps")
    print(f"{'gap':>6}{'merged':>9}{'largest frac (mean)':>22}   verdict", flush=True)
    for gap in ([0.0] if len(sys.argv) > 3 else [0.0, 1.0, 2.5]):
        fracs = []
        for sd in range(n_seed):
            X, species, bonds, mol = two_patches(n_each, n_tail, L, gap, n_water, seed=sd)
            if sd == 0:
                from _shot import render_initial
                render_initial(X, species, L, f"pfuse_gap{gap:g}")
            f = Field(species, bonds, L)
            ig = Inertial(f, kT, 8e-3, seed=500 + sd)
            for _ in range(steps):
                X = ig.step(X)
            fracs.append(largest_frac(X, mol, L))
        merged = sum(1 for x in fracs if x > 0.9)
        m = float(np.mean(fracs))
        print(f"{gap:>6.1f}{merged:>5}/{n_seed:<3}{m:>22.3f}   "
              f"{'FUSE readily' if merged >= n_seed - 1 else 'barrier to fusion' if merged == 0 else 'partial'}",
              flush=True)
