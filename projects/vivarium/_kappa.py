"""Bending rigidity from the undulation spectrum of a spanning bilayer.

WHY THIS IS NOW THE ONLY MISSING NUMBER
    The edge costs lambda = +18.31 +- 7.07 eps per end (+40.7 +- 15.7 kT), so closing a ribbon
    recovers about 81 kT by removing two ends. Closing a ribbon of contour length L_c into a circle of
    radius R = L_c / 2pi costs

        E_bend = (kappa/2) * L_c * (1/R^2) = pi * kappa / R

    which at our R ~ 5.9 is about 0.54 * kappa. So closure is thermodynamically favoured whenever

        kappa < 81 kT / 0.54 ~ 150 kT.

    Real membranes sit at 10-30 kT. If ours is in that range, the three closure failures are KINETIC
    and the search should move to nucleation and barriers. If it is above ~150 kT, they are
    THERMODYNAMIC and no amount of sampling will help.

METHOD
    Not by bending a planted arc: every planted arc in this project unrolled, so a constrained-curvature
    measurement would fight the very relaxation it is trying to measure. Instead the standard
    equilibrium route -- thermal undulations of a FLAT spanning bilayer, which is stable here.

    In 2-D the membrane is a line u(x). With E = (kappa/2) integral (u'')^2 dx, equipartition gives

        <|u_q|^2> = kT / (kappa * q^4 * L)

    so 1/<|u_q|^2> is linear in q^4 with slope kappa*L/kT. Fitting the SLOPE rather than reading a
    single mode is what makes this robust: it uses every resolved wavelength and exposes curvature in
    the plot if the model is wrong.

    Only the smallest few q are used. Short wavelengths are contaminated by protrusion and by the
    finite lipid size, which is a known systematic in this measurement, not a subtlety to discover
    later.

FALSIFICATION, STATED BEFORE THE RUN
    The spectrum must actually follow q^-4 over the fitted range. If 1/<|u_q|^2> is not linear in q^4,
    the continuum bending model does not describe this membrane and the extracted kappa is meaningless
    -- report that rather than a number.
"""

import sys

import numpy as np

from _linetension import plant
from field import Field
from integrate import Inertial

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 40000
    kT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.45
    n_tail = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    n_lip = int(sys.argv[4]) if len(sys.argv) > 4 else 120
    L = float(sys.argv[5]) if len(sys.argv) > 5 else 60.0
    phi = 0.55
    n_water = int(round(phi * L * L / (np.pi * 0.25))) - (1 + n_tail) * n_lip

    X, species, bonds, mol = plant(n_lip, n_tail, L, True, n_water, seed=0)
    f = Field(species, bonds, L)
    ig = Inertial(f, kT, 8e-3, seed=400)
    nq = 6
    nbin = 24
    acc = np.zeros(nq)
    cnt = 0
    for t in range(steps):
        X = ig.step(X)
        if t > steps // 3 and t % 100 == 0:
            # midplane height: mean y of the two leaflets, binned along x
            P = X[mol].mean(axis=1)
            xb = np.floor((P[:, 0] + L / 2) / (L / nbin)).astype(int) % nbin
            h = np.array([P[xb == b, 1].mean() if (xb == b).any() else 0.0 for b in range(nbin)])
            h -= h.mean()
            fq = np.fft.rfft(h) / nbin
            acc += np.abs(fq[1:nq + 1]) ** 2
            cnt += 1
    spec = acc / cnt
    q = 2.0 * np.pi * np.arange(1, nq + 1) / L

    print(f"undulation spectrum, {n_lip} lipids (1 head + {n_tail} tails), L={L}, kT={kT}, "
          f"{cnt} samples")
    print(f"{'mode':>5}{'q':>9}{'<|u_q|^2>':>13}{'1/<|u_q|^2>':>14}{'q^4':>12}")
    for i in range(nq):
        print(f"{i + 1:>5}{q[i]:>9.3f}{spec[i]:>13.5f}{1.0 / max(spec[i], 1e-12):>14.2f}"
              f"{q[i] ** 4:>12.5f}")

    # PER-MODE CONSISTENCY, not R^2. A linear fit of 1/<|u_q|^2> against q^4 spanning two and a half
    # decades in x is dominated by its largest point, so R^2 = 0.961 was reported for a spectrum whose
    # per-mode kappa varied 16.7x (10.42, 2.78, 0.62, 0.74 kT). R^2 is a poor test of a power law. If
    # the spectrum really is q^-4 then kappa extracted from EACH mode separately must agree.
    per_mode = (1.0 / np.maximum(spec, 1e-12)) * kT / (L * q ** 4)
    print(f"\n{'mode':>5}{'kappa (eps)':>14}{'kappa (kT)':>13}")
    for i in range(nq):
        print(f"{i + 1:>5}{per_mode[i]:>14.3f}{per_mode[i] / kT:>13.2f}")
    spread = float(per_mode.max() / max(per_mode.min(), 1e-12))
    print(f"\nspread across modes: {spread:.1f}x")
    if spread > 2.0:
        print("SPECTRUM IS NOT q^-4: per-mode kappa disagrees by more than 2x, so the continuum "
              "bending model does not describe this membrane over the resolved wavelengths and NO "
              "kappa is reported. Likely causes: the shortest modes are near the molecular scale "
              "(mode nq has wavelength L/nq, which must stay well above the lipid size) and the "
              "longest is the box itself. A bigger membrane is required, not a longer run.")
    else:
        kappa = float(per_mode.mean())
        print(f"kappa = {kappa:.2f} eps = {kappa / kT:.1f} kT")
        print(f"closure needs kappa < ~150 kT  ->  "
              f"{'FAVOURED, failures are kinetic' if kappa / kT < 150 else 'NOT favoured'}")
