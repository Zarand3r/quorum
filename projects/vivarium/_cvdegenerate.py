"""Can shell CV tell a hollow vesicle from a solid ball AT OUR SYSTEM SIZE?

Shell CV = std(r)/mean(r) over the aggregate's beads. Its discriminating power is a ratio question, not
an absolute one:

    thin shell of thickness t at radius R   CV = (t/sqrt(12)) / R
    solid ball of radius R                  CV = sqrt(3/80) / (3/4) = 0.258, independent of R

So CV separates the two only while t << R. The oracle's vesicles read 0.045, which for a bilayer about
5 sigma thick implies R ~ 32 sigma. Ours are planted at R_mid = 5.71 in a box of L = 25, where t and R
are the SAME SIZE -- the planted 300-lipid vesicle reads 0.246 at step 0, before a single step of
dynamics, and a solid ball reads 0.258.

If those are indistinguishable, then every 3-D conclusion drawn from shell CV -- including "the
aggregate is a filled blob, not a shell" and the falsification criterion "CV rising away from 0.05" --
was drawn from a metric with no discriminating power in the regime it was applied to, and the 0.05
target was geometrically unreachable at N = 300 in L = 25 regardless of the physics.

FALSIFICATION, STATED BEFORE THE RUN
    If the planted hollow shell and the solid ball differ by more than the seed-to-seed spread, CV
    discriminates and the readings stand. If they do not, CV is void here and a replacement observable
    is required -- the obvious one being the radial density profile, which asks directly whether the
    centre is empty.
"""

from __future__ import annotations

import numpy as np

from _cvcontrol import _shell, score
from _mixture import _unwrapped_centroid, _wrap

L = 25.0


def _ball(n, R, centre, rng, NB=3):
    """A SOLID ball of the same bead count and outer radius: the negative control."""
    v = rng.normal(size=(n * NB, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    r = R * rng.uniform(0, 1, size=(n * NB, 1)) ** (1.0 / 3.0)
    X = centre + v * r
    mols = [np.arange(i * NB, (i + 1) * NB) for i in range(n)]
    return list(X), mols


def hollowness(X, mols, L, nbin=12):
    """Bead density in the inner third of the aggregate over the density in the shell region.

    0 = empty centre (a vesicle), ~1 = uniformly filled (a ball). Unlike CV this asks the question
    directly, so it does not degrade as the membrane thickness approaches the radius.
    """
    X = np.asarray(X, float) % L
    beads = np.concatenate(mols)
    P = X[beads]
    c = _unwrapped_centroid(P, L)
    r = np.linalg.norm(_wrap(P - c, L), axis=1)
    R = np.percentile(r, 95)
    inner = r < R / 3.0
    outer = (r > R / 3.0) & (r < R)
    v_in = (R / 3.0) ** 3
    v_out = R ** 3 - v_in
    d_in = inner.sum() / v_in
    d_out = max(outer.sum() / v_out, 1e-12)
    return float(d_in / d_out)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    # Sweep the thickness-to-radius ratio. NB = 5 with R_mid 5.71 is the 4-tail lipid this project
    # actually runs; NB = 3 at R = 12 is the thin-shell regime the oracle sits in.
    print(f"{'geometry':<34}{'shell CV':>10}{'CV gap':>9}{'hollow':>9}{'hollow gap':>12}")
    for NB, R_mid, label in ((5, 5.71, "OUR 4-tail lipid, R_mid 5.71"),
                             (5, 12.0, "same lipid, R_mid 12"),
                             (3, 12.0, "thin shell, R_mid 12"),
                             (3, 20.0, "oracle-like, R_mid 20")):
        # The box must hold the structure: at L = 25 a shell of R_mid 12 is wider than the box and
        # wraps onto itself, which produced hollowness 2.8 for a hollow shell in a first version.
        Lb = 4.0 * (R_mid + NB)
        centre = np.array([Lb / 2] * 3)
        n = int(4 * np.pi * R_mid ** 2 / 1.2)
        R_in = R_mid - (NB - 1) / 2.0
        Xs, ms = _shell(n, R_in, centre, rng, NB=NB)
        Xb, mb = _ball(n, R_mid + (NB - 1) / 2.0, centre, rng, NB=NB)
        cs, cb = score(Xs, ms, Lb), score(Xb, mb, Lb)
        hs, hb = hollowness(Xs, ms, Lb), hollowness(Xb, mb, Lb)
        print(f"{label:<34}{cs:>10.3f}{abs(cs - cb):>9.3f}{hs:>9.3f}{abs(hs - hb):>12.3f}")
    print()
    print("CV gap is how far the hollow shell sits from a SOLID BALL of the same beads.")
    print("A gap near zero means shell CV cannot tell a vesicle from a blob in that geometry.")
