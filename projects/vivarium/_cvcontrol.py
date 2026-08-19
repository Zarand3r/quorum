"""Positive control for the shell-CV metric itself.

Shell CV is the number every 3-D conclusion in this project rests on: the oracle's real vesicles sit
at 0.045-0.057, our emergent aggregates at 0.15-0.37, and "rising away from 0.05" is the stated
falsification criterion for the 3-D negative. So the metric is worth attacking directly.

Two suspected defects, both from `geometry()` in _mixture.py:

  A. The centre is `X[lipid_beads].mean(axis=0)` -- a plain mean of WRAPPED coordinates. For a cluster
     straddling a periodic boundary that lands in empty space, and every radius is then measured from
     a point outside the object. Minimum-image wrapping of the DISPLACEMENT hides it, because every
     radius still comes out below L/2 and therefore still looks plausible.

  B. It averages over ALL lipid beads, not over the largest cluster. In the emergent 3-D runs the
     largest cluster is 119-126 of 300, so two thirds of the beads scored are in OTHER aggregates and
     the number reports global dispersion rather than shell structure.

This plants a KNOWN thin shell -- the answer is known in advance, which is what makes it a control --
and scores it three ways:

    centred          shell alone, at the box centre          the reference value
    straddling       the same shell, translated to a corner  isolates defect A
    plus dispersed   the centred shell + loose lipids        isolates defect B

The expected value is NOT the oracle's 0.045-0.057. This shell is three beads thick at radii 6, 7 and
8, so its intrinsic CV is std/mean of that spread, 0.8165/7 = 0.117. An earlier version of this file
predicted 0.05 and was wrong; the measurement was right. All three configurations must return that
same 0.117, because all three contain the identical shell.

FALSIFICATION, STATED BEFORE THE RUN
    If all three read ~0.05, the metric is sound under both perturbations and every shell-CV number in
    the log stands. If straddling or plus-dispersed inflates, the corresponding class of numbers is
    confounded and must be withdrawn -- which for the emergent 3-D runs means all of them, since those
    are exactly multi-cluster configurations at arbitrary positions.
"""

from __future__ import annotations

import numpy as np

from _mixture import geometry

L, NB = 40.0, 3


def _shell(n, R, centre, rng, NB=NB):
    """n lipids on a sphere of radius R: head outward, tails inward. A deliberately clean shell.

    Directions come from a Fibonacci sphere rather than random normals, and `n` is set from the area
    so the lipids sit about 1.1 sigma apart. A first version sampled 120 random directions on R = 6,
    giving 1.9 sigma spacing -- above the 1.4 bead-linking cutoff, so the "shell" was not a connected
    cluster at all and the largest-cluster scoring saw a stray patch. The control was wrong, not the
    metric. A membrane at real density is connected by construction.
    """
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    v = np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], axis=1)
    X, mols = [], []
    for i in range(n):
        base = len(X)
        for b in range(NB):
            X.append(centre + v[i] * (R + (NB - 1 - b) * 1.0))
        mols.append(np.arange(base, base + NB))
    return X, mols


def score_legacy(X, mols, L):
    """The metric AS IT WAS: plain mean of wrapped coordinates, averaged over every lipid.

    Kept so the size of each defect is measured rather than asserted, and so the fix cannot silently
    regress to it.
    """
    X = np.asarray(X, float) % L
    lipid = np.concatenate(mols)
    cen = X[lipid].mean(axis=0)
    d = X[lipid] - cen
    d -= L * np.round(d / L)
    rt = np.linalg.norm(d, axis=1)
    return float(rt.std() / max(rt.mean(), 1e-9))


def score(X, mols, L):
    X = np.asarray(X, float) % L
    chains = np.full(len(mols), float(NB))
    return geometry(X, mols, np.empty(0, dtype=np.int64), chains, L, 3)["shell_cv"]


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    R = 6.0
    n = int(4 * np.pi * R ** 2 / 1.2)     # area per lipid 1.2 sigma^2, so beads link at cut 1.4

    Xc, mc = _shell(n, R, np.array([L / 2, L / 2, L / 2]), rng)
    cv_centred = score(Xc, mc, L)

    Xs, ms = _shell(n, R, np.array([0.0, 0.0, 0.0]), rng)      # straddles all three boundaries
    cv_straddle = score(Xs, ms, L)

    Xd, md = list(Xc), list(mc)                                 # centred shell + loose lipids
    for _ in range(180):
        c = rng.uniform(0, L, 3)
        base = len(Xd)
        for b in range(NB):
            Xd.append(c + np.array([0.0, 0.0, b * 1.0]))
        md.append(np.arange(base, base + NB))
    cv_dispersed = score(Xd, md, L)

    true_cv = float(np.std([R, R + 1, R + 2]) / np.mean([R, R + 1, R + 2]))
    print(f"{'configuration':<34}{'shell CV':>10}   true value for this shell {true_cv:.3f}")
    print(f"{'centred shell alone':<34}{cv_centred:>10.3f}")
    print(f"{'SAME shell straddling a corner':<34}{cv_straddle:>10.3f}")
    print(f"{'centred shell + 180 loose lipids':<34}{cv_dispersed:>10.3f}")
    print()
    print(f"{'configuration':<34}{'fixed':>8}{'legacy':>9}{'legacy error':>14}")
    for name, X_, m_ in (("centred", Xc, mc), ("straddling", Xs, ms), ("dispersed", Xd, md)):
        cv, old = score(X_, m_, L), score_legacy(X_, m_, L)
        err = abs(cv - true_cv) / true_cv
        print(f"{name:<34}{cv:>8.3f}{old:>9.3f}{abs(old - true_cv) / true_cv:>13.0%}"
              f"   {'PASS' if err < 0.10 else 'FAIL'}")
