"""Vesicle hunt at scale. A 2-D vesicle is a closed RING, so it needs finite ribbons with ends.

At N=1200 the aggregates spanned the periodic box and had no ends to join. The vectorised cell list
makes N=6000 cost 9 ms/step, so aggregates can stay finite while the box stays large.

Reports enclosed solvent (flood fill from the boundary; a closed ring traps solvent, an open ribbon
does not) beside the largest aggregate, so a big number cannot come from a percolating tangle.
"""
import sys
import numpy as np
from dpd_reference import DPD

RHO, KT, A0, DA, NB = 4.0, 1.0, 25.0, 15.0, 3
N_TOTAL = 6000

def build(n_amph, seed=0, nb=NB, da=DA, n_head=1):
    L = np.sqrt(N_TOTAL / RHO)
    sp = np.zeros(N_TOTAL, int); bonds = []
    for k in range(n_amph):
        b0 = k * nb
        sp[b0:b0 + n_head] = 1            # heads
        sp[b0 + n_head:b0 + nb] = 2       # tails
        for t in range(nb - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0)
    a[0, 2] = a[2, 0] = A0 + da
    a[1, 2] = a[2, 1] = A0 + da
    d = DPD(N_TOTAL, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=100.0, r0=0.7, dt=0.02, seed=seed)
    for k in range(n_amph):
        b0 = k * nb
        c = d.rng.uniform(0, L, 2); th = d.rng.uniform(0, 2 * np.pi)
        u = np.array([np.cos(th), np.sin(th)])
        for t in range(nb):
            d.x[b0 + t] = (c + t * 0.7 * u) % L
    return d

def enclosed(d, cell=0.5):
    L = d.L; n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (d.x[d.species != 0] / L * n).astype(int) % n
    occ[gi[:, 0], gi[:, 1]] = True
    free = ~occ
    seen = np.zeros_like(free); stack = []
    for i in range(n):
        for j in (0, n - 1):
            for a, b in ((i, j), (j, i)):
                if free[a, b] and not seen[a, b]:
                    seen[a, b] = True; stack.append((a, b))
    while stack:
        a, b = stack.pop()
        for da_, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p, q = a + da_, b + db
            if 0 <= p < n and 0 <= q < n and free[p, q] and not seen[p, q]:
                seen[p, q] = True; stack.append((p, q))
    wi = (d.x[d.species == 0] / L * n).astype(int) % n
    return int(sum(1 for a, b in wi if free[a, b] and not seen[a, b]))

def agg_sizes(d, n_amph, nb=NB, n_head=1):
    tails = np.array([k * nb + t for k in range(n_amph) for t in range(n_head, nb)])
    x = d.x[tails]
    dd = x[:, None, :] - x[None, :, :]
    dd -= d.L * np.round(dd / d.L)
    close = np.linalg.norm(dd, axis=2) < 1.0
    m = nb - n_head
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

phi, steps, nb, da, seed = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
n_head = int(sys.argv[6]) if len(sys.argv) > 6 else 1
n_amph = int(phi * N_TOTAL / nb)
d = build(n_amph, seed=seed, nb=nb, da=da, n_head=n_head)
for _ in range(steps):
    d.step()
sz = [s for s in agg_sizes(d, n_amph, nb, n_head) if s >= 3]
enc = enclosed(d)
tag = f"big_phi{int(phi*100)}_nb{nb}h{n_head}_da{int(da)}_s{seed}"
print(f"RESULT {tag:<26}n_amph={n_amph:<5}aggs={len(sz):<4}largest={max(sz) if sz else 0:<5}"
      f"enclosed={enc:<5}T={d.temperature():.2f}   {'LUMEN' if enc >= 10 else 'no lumen'}", flush=True)
np.savez_compressed(
    f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/{tag}.npz",
    x=d.x, species=d.species, L=d.L, n_amph=n_amph)
