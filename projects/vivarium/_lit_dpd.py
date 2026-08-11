"""Published DPD membrane parameter sets, implemented exactly rather than reconstructed.

My own guesses had a_TW = 40-55 and a_HW = 25. The literature uses a_TW = 80 and a_HW as low as 15 --
i.e. my tail was not hydrophobic enough AND my head was not hydrophilic enough. Amphiphilicity is the
DIFFERENCE between those, so both errors compounded.

  set A   a_HH = a_TT = a_WW = 25, a_HT = 40, a_TW = 80, a_HW = 25
  set B   a_WW = a_TT = 25, a_HH = 35, a_HT = 80, a_WT = 80, a_HW = 15

Lipid = 1 head + 3 tails on Hookean bonds, solvent = single beads (the standard mapping).
Species: 0 water, 1 head, 2 tail.
"""
import sys
import numpy as np
from dpd_reference import DPD

RHO, KT = 3.0, 1.0

SETS = {
    "A": {"WW": 25.0, "HH": 25.0, "TT": 25.0, "HT": 40.0, "TW": 80.0, "HW": 25.0},
    "B": {"WW": 25.0, "HH": 35.0, "TT": 25.0, "HT": 80.0, "TW": 80.0, "HW": 15.0},
}

def amat(p):
    a = np.zeros((3, 3))
    a[0, 0], a[1, 1], a[2, 2] = p["WW"], p["HH"], p["TT"]
    a[0, 1] = a[1, 0] = p["HW"]
    a[0, 2] = a[2, 0] = p["TW"]
    a[1, 2] = a[2, 1] = p["HT"]
    return a

def make(n_amph, N, pset, dim, seed, nb=4, planted=False):
    L = (N / RHO) ** (1.0 / dim)
    sp = np.zeros(N, int); bonds = []
    for k in range(n_amph):
        b0 = k * nb
        sp[b0] = 1; sp[b0 + 1:b0 + nb] = 2
        for t in range(nb - 1):
            bonds.append((b0 + t, b0 + t + 1))
    d = DPD(N, L, kT=KT, a_matrix=amat(SETS[pset]), species=sp, bonds=np.array(bonds),
            k_bond=100.0, r0=0.7, dt=0.02, seed=seed, dim=dim)
    if planted:
        half = n_amph // 2
        per = int(np.ceil(np.sqrt(half))) if dim == 3 else half
        for leaf, sgn in ((0, +1.0), (1, -1.0)):
            m = half if leaf == 0 else n_amph - half
            for k in range(m):
                idx = leaf * half + k
                if dim == 3:
                    base = np.array([((k % per) + 0.5) * L / per,
                                     ((k // per) + 0.5) * L / per, L / 2])
                    ax = np.array([0.0, 0.0, 1.0])
                else:
                    base = np.array([(k + 0.5) * L / m, L / 2]); ax = np.array([0.0, 1.0])
                for t in range(nb):
                    d.x[idx * nb + t] = (base + sgn * (0.4 + (nb - 1 - t) * 0.5) * ax) % L
    else:
        for k in range(n_amph):
            c = d.rng.uniform(0, L, dim)
            u = d.rng.normal(size=dim); u /= np.linalg.norm(u)
            for t in range(nb):
                d.x[k * nb + t] = (c + t * 0.6 * u) % L
    return d

def order(d, n_amph, nb, dim):
    heads = np.arange(n_amph) * nb
    tails = np.stack([d.x[np.arange(n_amph) * nb + t] for t in range(1, nb)]).mean(axis=0)
    u = d.x[heads] - tails
    u -= d.L * np.round(u / d.L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    nrm = np.zeros(dim); nrm[-1] = 1.0
    return float((np.abs(u @ nrm) > np.cos(np.pi / 6)).mean())

dim, N = 3, 9000
L = (N / RHO) ** (1.0 / 3.0)
n_amph = int(2 * L * L / 1.30)
print(f"PLANTED BILAYER, 3-D, N={N}, L={L:.1f}, n_amph={n_amph} (area/lipid 1.30)")
print(f"{'set':>4}{'a_TW':>6}{'a_HW':>6}{'t=0':>7}{'2k':>7}{'6k':>7}{'15k':>7}   verdict")
for pset in ("A", "B"):
    d = make(n_amph, N, pset, dim, 1, planted=True)
    o = [order(d, n_amph, 4, dim)]
    for tgt in (2000, 6000, 15000):
        while getattr(d, "_t", 0) < tgt:
            d.step(); d._t = getattr(d, "_t", 0) + 1
        o.append(order(d, n_amph, 4, dim))
    p = SETS[pset]
    print(f"{pset:>4}{p['TW']:>6.0f}{p['HW']:>6.0f}{o[0]:>7.2f}{o[1]:>7.2f}{o[2]:>7.2f}{o[3]:>7.2f}   "
          f"{'BILAYER HOLDS' if o[3] > 0.55 else 'melts'}", flush=True)
    np.savez_compressed(
        f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/lit{pset}_planted.npz",
        x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=4, nh=1)
