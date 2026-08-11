"""3-D DPD amphiphile self-assembly: the regime where open-source vesicle work actually lives.

Parameters follow common DPD practice rather than being invented: rho=3, a_ii=25, cross repulsion
raised by da for water-tail and head-tail, amphiphiles of a few beads with a harmonic backbone.

Lumen detection in 3-D: grid the box, mark cells containing amphiphile, flood the solvent inward from
the boundary by iterated dilation, and take the largest connected pocket the flood cannot reach. A
vesicle traps a big contiguous interior; a micelle traps nothing; a branched network traps many tiny
pockets, which is why the largest CONNECTED pocket is used and not the total.
"""
import sys
import numpy as np
from dpd_reference import DPD

RHO, KT, A0 = 3.0, 1.0, 25.0

def build(n_amph, n_total, nb, n_head, da, seed):
    L = (n_total / RHO) ** (1.0 / 3.0)
    sp = np.zeros(n_total, int); bonds = []
    for k in range(n_amph):
        b0 = k * nb
        sp[b0:b0 + n_head] = 1
        sp[b0 + n_head:b0 + nb] = 2
        for t in range(nb - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0)
    a[0, 2] = a[2, 0] = A0 + da        # water-tail: the hydrophobic effect
    a[1, 2] = a[2, 1] = A0 + da        # head-tail
    d = DPD(n_total, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=3)
    for k in range(n_amph):            # each amphiphile a compact random-oriented rod
        b0 = k * nb
        c = d.rng.uniform(0, L, 3)
        u = d.rng.normal(size=3); u /= np.linalg.norm(u)
        for t in range(nb):
            d.x[b0 + t] = (c + t * 0.5 * u) % L
    return d

def lumen(d, cell=0.8, min_cells=25):
    L = d.L
    n = max(8, int(L / cell))
    occ = np.zeros((n, n, n), bool)
    gi = (d.x[d.species != 0] / L * n).astype(int) % n
    occ[gi[:, 0], gi[:, 1], gi[:, 2]] = True
    free = ~occ
    reach = np.zeros_like(free)
    reach[0, :, :] |= free[0, :, :]; reach[-1, :, :] |= free[-1, :, :]
    reach[:, 0, :] |= free[:, 0, :]; reach[:, -1, :] |= free[:, -1, :]
    reach[:, :, 0] |= free[:, :, 0]; reach[:, :, -1] |= free[:, :, -1]
    while True:                                   # iterated dilation = flood fill, vectorised
        g = reach.copy()
        for ax in (0, 1, 2):
            g |= np.roll(reach, 1, axis=ax) | np.roll(reach, -1, axis=ax)
        g &= free
        if g.sum() == reach.sum():
            break
        reach = g
    interior = free & ~reach
    if not interior.any():
        return 0
    lab = np.zeros_like(interior, np.int32)
    best, cur = 0, 0
    idx = np.argwhere(interior)
    seen = set()
    for p in map(tuple, idx):
        if p in seen: continue
        cur += 1; st = [p]; seen.add(p); c = 0
        while st:
            a, b, cc = st.pop(); c += 1
            for ax, dv in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
                q = [a, b, cc]; q[ax] += dv
                q = tuple(v % n for v in q)
                if interior[q] and q not in seen:
                    seen.add(q); st.append(q)
        best = max(best, c)
    return best if best >= min_cells else 0

def agg_sizes(d, n_amph, nb, n_head):
    tails = np.array([k * nb + t for k in range(n_amph) for t in range(n_head, nb)])
    x = d.x[tails]
    m = nb - n_head
    dd = x[:, None, :] - x[None, :, :]
    dd -= d.L * np.round(dd / d.L)
    close = np.linalg.norm(dd, axis=2) < 1.0
    adj = close.reshape(n_amph, m, n_amph, m).any(axis=(1, 3))
    np.fill_diagonal(adj, False)
    seen, out = set(), []
    for s0 in range(n_amph):
        if s0 in seen: continue
        st, c = [s0], 0; seen.add(s0)
        while st:
            u = st.pop(); c += 1
            for v in np.where(adj[u])[0]:
                if v not in seen: seen.add(v); st.append(v)
        out.append(c)
    return sorted(out, reverse=True)

phi, steps, nb, nh, da, seed, ntot = (float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]),
                                      int(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]),
                                      int(sys.argv[7]))
n_amph = int(phi * ntot / nb)
d = build(n_amph, ntot, nb, nh, da, seed)
for _ in range(steps):
    d.step()
sz = [s for s in agg_sizes(d, n_amph, nb, nh) if s >= 3]
lu = lumen(d)
tag = f"d3_phi{int(phi*100)}_{nb}h{nh}_da{int(da)}_s{seed}"
print(f"RESULT {tag:<24}n={n_amph:<5}aggs={len(sz):<4}largest={max(sz) if sz else 0:<5}"
      f"lumen={lu:<5}T={d.temperature():.2f} homog={d.density_homogeneity():.2f}   "
      f"{'*** VESICLE ***' if lu >= 25 else 'no lumen'}", flush=True)
np.savez_compressed(
    f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/{tag}.npz",
    x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=nb, nh=nh)
