"""The missing pole: a THERMALIZED micelle made by this chemistry, not a hand-planted lattice.

Every negative pole so far is a t=0 construction at zero thermal noise, which is exactly what made
the old `flat` term look discriminating when it was not (D10). To calibrate anything at kT=1 the
negative pole has to be thermalized too.

A spherical micelle of the two-tailed H3(C4)2 amphiphile is not physically realisable -- its packing
parameter puts it firmly in the bilayer regime, and forcing its tails to meet at a centre would put
many times bulk density in the core. So the pole is built the honest way: keep the chemistry
identical and remove ONE tail. H3(C4) has half the tail volume at the same head area, which drops the
packing parameter into the micellar regime, and then the model is allowed to assemble its own
micelles from a random start rather than being handed a lattice.

Self-consistent micelle size, for reference when reading the output:
    sphere:  (4/3) pi R^3 = M v_tail   and   4 pi R^2 = M a
    =>       R = 3 v_tail / a  ~ 2.4 rc,  M ~ 45   for v_tail = 4/rho and a = 1.65
"""

import sys

import numpy as np

from dpd_reference import DPD
from _sl_model import RHO, KT, NH, NT, A

NTAIL = 1                      # the single change from the bilayer-forming chemistry
NB = NH + NT * NTAIL           # 7


def build(n_amph, N, seed, dim=3):
    L = (N / RHO) ** (1.0 / dim)
    sp = np.zeros(N, int)
    bonds, angles = [], []
    for k in range(n_amph):
        b = k * NB
        sp[b:b + NH] = 1
        sp[b + NH:b + NB] = 2
        for t in range(NH - 1):
            bonds.append((b + t, b + t + 1))
        t0 = b + NH
        bonds.append((b + NH - 1, t0))
        for t in range(NT - 1):
            bonds.append((t0 + t, t0 + t + 1))
        angles.append((b + NH - 1, t0, t0 + 1))
        for t in range(NT - 2):
            angles.append((t0 + t, t0 + t + 1, t0 + t + 2))
    d = DPD(N, L, kT=KT, a_matrix=A, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=dim)
    d.angles = np.array(angles)
    d.k_ang = 15.0
    for k in range(n_amph):
        b = k * NB
        c = d.rng.uniform(0, L, dim)
        u = d.rng.normal(size=dim)
        u /= np.linalg.norm(u)
        for t in range(NH):
            d.x[b + t] = (c - (NH - t) * 0.5 * u) % L
        for t in range(NT):
            d.x[b + NH + t] = (c + (t + 1) * 0.5 * u) % L
    return d


def clusters(d, n_amph, cut=1.2):
    b0 = np.arange(n_amph) * NB
    beads = np.concatenate([b0 + t for t in range(NB)])
    owner = np.concatenate([np.arange(n_amph) for _ in range(NB)])
    dd = d.x[beads][:, None, :] - d.x[beads][None, :, :]
    dd -= d.L * np.round(dd / d.L)
    i, j = np.nonzero(np.linalg.norm(dd, axis=2) < cut)
    par = np.arange(n_amph)

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for a, b in zip(owner[i], owner[j]):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    sizes = np.bincount(np.array([find(k) for k in range(n_amph)]))
    return sizes[sizes > 0]


if __name__ == "__main__":
    frac, steps, N, seed = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    n_amph = int(frac * N / NB)
    d = build(n_amph, N, seed)
    print(f"single-tail H3(C4), n_amph={n_amph}, N={N}, L={d.L:.2f}", flush=True)
    for t in range(steps + 1):
        if t % max(steps // 5, 1) == 0:
            c = clusters(d, n_amph)
            c = np.sort(c[c > 0])[::-1]
            print(f"  step {t:>6}  aggregates>=3: {int((c >= 3).sum()):>4}  largest {c[0]:>4}  "
                  f"median(>=3) {int(np.median(c[c >= 3])) if (c >= 3).any() else 0:>4}  "
                  f"T={d.temperature():.3f}", flush=True)
        d.step()
    np.savez_compressed(
        f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/"
        f"micelle_pole_f{int(frac * 100)}_N{N}.npz",
        x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=NH)
