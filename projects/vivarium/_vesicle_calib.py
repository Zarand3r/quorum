"""Plant a spherical vesicle with the CORRECT leaflet populations, then calibrate against it.

Two things this fixes, both raised in external review and both confirmed by arithmetic here.

1. `bilayer_frac` (paired AND locally flat) is calibrated only against FLAT bilayers and physically
   sized micelles. The target is curved. A `flat > 0.90` local criterion may systematically reject a
   perfectly good small vesicle, in which case the ">0.5 within a finite aggregate" success target is
   not calibrated against the thing we are trying to produce. Planting real vesicles and reading the
   metric on them is the only way to know.

2. The planted disk experiment this replaces was geometrically unsound. A vesicle's two leaflets sit
   at radii R and R-d, so they need
       N_out = 4 pi R^2 / a        N_in = 4 pi (R-d)^2 / a
   amphiphiles. With the measured d = 5.03 rc and a = 1.65 rc^2 that is 274:7 at R=6 -- a 38:1 ratio.
   A flat disk of the same 281 amphiphiles starts 141:141, so closure would require 134 of them (48%)
   to migrate around the rim from one leaflet to the other. That experiment measured leaflet
   redistribution, differential leaflet strain and flip-flop transport, NOT the bending-versus-edge
   competition it claimed to isolate.

Leaflet asymmetry is therefore built in here from the start, rather than left for the dynamics to
discover.

R/d is reported for every case because it is the honest measure of how extreme the vesicle is. At
R=6, d/R = 0.84: an object almost as thick as its own final radius. Real vesicles have R/d >~ 4.
"""

import sys

import numpy as np

from dpd_reference import DPD
from _sl_model import RHO, KT, NH, NT, NTAIL, NB, A
from _pairing import bilayer_frac

A_LIP = 1.65                      # measured on the spanning slab by _geom.py
ZS_H = [2.5, 2.0, 1.5]            # head offsets from the midplane; head-to-head span = 5.0 == d
ZS_T = [1.0, 0.5, 0.0, -0.5]


def fib_sphere(n):
    """Evenly spaced unit vectors, so a planted leaflet has uniform area per amphiphile."""
    i = np.arange(n) + 0.5
    z = 1.0 - 2.0 * i / n
    r = np.sqrt(np.maximum(1.0 - z * z, 0.0))
    th = np.pi * (1.0 + 5.0 ** 0.5) * i
    return np.stack([r * np.cos(th), r * np.sin(th), z], axis=1)


def plant_vesicle(R_out, k_ang=15.0, seed=1, gap=6.0):
    R_mid = R_out - ZS_H[0]
    R_in = R_mid - ZS_H[0]
    n_out = int(4 * np.pi * R_out ** 2 / A_LIP)
    n_in = int(4 * np.pi * max(R_in, 0.0) ** 2 / A_LIP)
    n_amph = n_out + n_in
    # box: hold the vesicle with a water gap, and stay above the exact lamella crossover
    # L/R > sqrt(2 pi [1 + (1-d/R)^2]), whose R>>d asymptote is sqrt(4 pi) = 3.545
    L_cross = R_out * np.sqrt(2 * np.pi * (1 + (1 - 5.0 / R_out) ** 2))
    L = float(max(2 * R_out + gap, L_cross))
    N = int(RHO * L ** 3)

    sp = np.zeros(N, int)
    bonds, angles = [], []
    for k in range(n_amph):
        b = k * NB
        sp[b:b + NH] = 1
        sp[b + NH:b + NB] = 2
        for t in range(NH - 1):
            bonds.append((b + t, b + t + 1))
        for c in range(NTAIL):
            t0 = b + NH + c * NT
            bonds.append((b + NH - 1, t0))
            for t in range(NT - 1):
                bonds.append((t0 + t, t0 + t + 1))
            angles.append((b + NH - 1, t0, t0 + 1))
            for t in range(NT - 2):
                angles.append((t0 + t, t0 + t + 1, t0 + t + 2))

    d = DPD(N, L, kT=KT, a_matrix=A, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=3)
    d.angles = np.array(angles)
    d.k_ang = float(k_ang)

    c0 = np.full(3, L / 2)
    for leaf, (m, sgn) in enumerate(((n_out, +1.0), (n_in, -1.0))):
        u = fib_sphere(m)
        base = 0 if leaf == 0 else n_out
        for q in range(m):
            b = (base + q) * NB
            n_hat = u[q]
            # a tangent, so the two tails sit side by side rather than on top of each other
            tang = np.cross(n_hat, np.array([0.0, 0.0, 1.0]))
            nt = np.linalg.norm(tang)
            tang = tang / nt if nt > 1e-8 else np.array([1.0, 0.0, 0.0])
            for t in range(NH):
                d.x[b + t] = (c0 + (R_mid + sgn * ZS_H[t]) * n_hat) % L
            for cc in range(NTAIL):
                t0 = b + NH + cc * NT
                off = (cc - 0.5) * 0.45 * tang
                for t in range(NT):
                    d.x[t0 + t] = (c0 + (R_mid + sgn * ZS_T[t]) * n_hat + off) % L
    return d, n_amph, n_out, n_in, R_in


def report(d, n_amph, n_out):
    """Metric read plus the two controls that stop it being read on a corpse."""
    b0 = np.arange(n_amph) * NB
    f, paired, flat = bilayer_frac(d.x, d.L, b0, NB, NH)

    lip = d.species != 0
    P = d.x[lip]
    c = P.mean(axis=0)
    q = P - c
    q -= d.L * np.round(q / d.L)
    ev = np.sort(np.linalg.eigvalsh(np.cov(q.T)))[::-1]
    asph = float(ev[2] / ev[0])

    # water the exterior cannot reach: the lumen must actually HOLD water, or the flood fill just
    # counts voids inside the bilayer's own tail core (that false positive read 51-68 on flat disks)
    cells = 26
    occ = np.zeros((cells,) * 3, bool)
    wat = np.zeros((cells,) * 3, bool)
    li = (d.x[lip] / d.L * cells).astype(int) % cells
    wi = (d.x[~lip] / d.L * cells).astype(int) % cells
    occ[li[:, 0], li[:, 1], li[:, 2]] = True
    wat[wi[:, 0], wi[:, 1], wi[:, 2]] = True
    free = ~occ
    seen = np.zeros_like(free)
    stack = [(i, j, k) for i in range(cells) for j in range(cells) for k in range(cells)
             if (i in (0, cells - 1) or j in (0, cells - 1) or k in (0, cells - 1)) and free[i, j, k]]
    for s in stack:
        seen[s] = True
    while stack:
        i, j, k = stack.pop()
        for di, dj, dk in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a_, b_, c_ = i + di, j + dj, k + dk
            if 0 <= a_ < cells and 0 <= b_ < cells and 0 <= c_ < cells \
                    and free[a_, b_, c_] and not seen[a_, b_, c_]:
                seen[a_, b_, c_] = True
                stack.append((a_, b_, c_))
    lumen = int((free & ~seen & wat).sum())

    # shell radius: is it still a shell, or has it collapsed into a blob?
    com_ = np.stack([d.x[b0 + t] for t in range(NB)]).mean(axis=0)
    rel = com_ - c
    rel -= d.L * np.round(rel / d.L)
    rad = np.linalg.norm(rel, axis=1)
    return f, paired, flat, asph, lumen, float(rad.mean()), float(rad.std())


if __name__ == "__main__":
    steps = int(sys.argv[1])
    radii = [float(x) for x in sys.argv[2].split(",")]
    print(f"{'R_out':>6}{'R/d':>5}{'n_out':>6}{'n_in':>5}{'out:in':>7}{'L':>6}{'N':>7}"
          f"{'step':>7}{'bil_frac':>9}{'paired':>7}{'flat':>6}{'asph':>6}{'lumen':>6}"
          f"{'<r>':>6}{'sd_r':>6}{'T':>6}", flush=True)
    for R in radii:
        d, n_amph, n_out, n_in, R_in = plant_vesicle(R)
        ratio = n_out / max(n_in, 1)
        for t in range(steps + 1):
            if t % max(steps // 4, 1) == 0:
                f, pa, fl, asph, lu, rm, rs = report(d, n_amph, n_out)
                print(f"{R:>6.1f}{R/5.03:>5.1f}{n_out:>6}{n_in:>5}{ratio:>7.1f}"
                      f"{d.L:>6.1f}{d.n:>7}{t:>7}{f:>9.3f}{pa:>7.3f}{fl:>6.3f}{asph:>6.2f}"
                      f"{lu:>6d}{rm:>6.2f}{rs:>6.2f}{d.temperature():>6.2f}", flush=True)
            d.step()
        np.savez_compressed(
            f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/"
            f"ves_planted_R{R:g}.npz",
            x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=NH)
