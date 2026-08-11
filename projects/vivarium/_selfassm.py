"""Self-assembly with a VALIDATED engine and PUBLISHED parameters. No planting.

The engine now reproduces the Groot-Warren equation of state (p/p_pred 0.92-0.99, converging with
density) and holds temperature at every timestep tested. Parameters are literature set B:
a_WW=a_TT=25, a_HH=35, a_HT=a_WT=80, a_HW=15, lipid = 1 head + 3 tails.

Planted bilayers melted, but the planting geometry is my own construction and is the weakest link.
The literature claim is about SPONTANEOUS assembly from a random start, so test that directly.
"""
import sys
import numpy as np
from dpd_reference import DPD

RHO, KT, NB = 3.0, 1.0, 4
A = np.array([[25.0, 15.0, 80.0],
              [15.0, 35.0, 80.0],
              [80.0, 80.0, 25.0]])          # rows/cols: water, head, tail

def build(n_amph, N, seed, dim=3):
    L = (N / RHO) ** (1.0 / dim)
    sp = np.zeros(N, int); bonds = []
    for k in range(n_amph):
        b0 = k * NB
        sp[b0] = 1; sp[b0 + 1:b0 + NB] = 2
        for t in range(NB - 1):
            bonds.append((b0 + t, b0 + t + 1))
    d = DPD(N, L, kT=KT, a_matrix=A, species=sp, bonds=np.array(bonds),
            k_bond=100.0, r0=0.7, dt=0.02, seed=seed, dim=dim)
    for k in range(n_amph):
        c = d.rng.uniform(0, L, dim)
        u = d.rng.normal(size=dim); u /= np.linalg.norm(u)
        for t in range(NB):
            d.x[k * NB + t] = (c + t * 0.6 * u) % L
    return d

def clusters(d, n_amph):
    tails = np.array([k * NB + t for k in range(n_amph) for t in range(1, NB)])
    x = d.x[tails]
    dd = x[:, None, :] - x[None, :, :]
    dd -= d.L * np.round(dd / d.L)
    close = np.linalg.norm(dd, axis=2) < 1.0
    m = NB - 1
    adj = close.reshape(n_amph, m, n_amph, m).any(axis=(1, 3))
    np.fill_diagonal(adj, False)
    seen, out = set(), []
    for s0 in range(n_amph):
        if s0 in seen: continue
        st, c = [s0], []; seen.add(s0)
        while st:
            u = st.pop(); c.append(u)
            for v in np.where(adj[u])[0]:
                if v not in seen: seen.add(v); st.append(v)
        out.append(c)
    return sorted(out, key=len, reverse=True)

def lumen(d, cell=0.8, min_cells=25):
    L = d.L; n = max(8, int(L / cell))
    occ = np.zeros((n,) * d.dim, bool)
    gi = (d.x[d.species != 0] / L * n).astype(int) % n
    occ[tuple(gi.T)] = True
    free = ~occ
    reach = np.zeros_like(free)
    for ax in range(d.dim):
        sl0 = [slice(None)] * d.dim; sl0[ax] = 0
        sl1 = [slice(None)] * d.dim; sl1[ax] = -1
        reach[tuple(sl0)] |= free[tuple(sl0)]
        reach[tuple(sl1)] |= free[tuple(sl1)]
    while True:
        g = reach.copy()
        for ax in range(d.dim):
            g |= np.roll(reach, 1, axis=ax) | np.roll(reach, -1, axis=ax)
        g &= free
        if g.sum() == reach.sum(): break
        reach = g
    interior = free & ~reach
    if not interior.any(): return 0
    seen, best = set(), 0
    for p in map(tuple, np.argwhere(interior)):
        if p in seen: continue
        st = [p]; seen.add(p); c = 0
        while st:
            q = st.pop(); c += 1
            for ax in range(d.dim):
                for dv in (1, -1):
                    r = list(q); r[ax] = (r[ax] + dv) % n; r = tuple(r)
                    if interior[r] and r not in seen:
                        seen.add(r); st.append(r)
        best = max(best, c)
    return best if best >= min_cells else 0

phi, steps, N, seed = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
n_amph = int(phi * N / NB)
d = build(n_amph, N, seed)
for _ in range(steps):
    d.step()
cl = [c for c in clusters(d, n_amph) if len(c) >= 3]
lu = lumen(d)
tag = f"sa_phi{int(phi*100)}_N{N}_s{seed}"
print(f"RESULT {tag:<22}n={n_amph:<5}aggs={len(cl):<4}largest={len(cl[0]) if cl else 0:<5}"
      f"lumen={lu:<5}T={d.temperature():.2f} homog={d.density_homogeneity():.2f}   "
      f"{'*** VESICLE ***' if lu >= 25 else 'no lumen'}", flush=True)
np.savez_compressed(
    f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/{tag}.npz",
    x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=1)
