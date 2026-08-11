"""Map the 2-D vesicle STABILITY window before hunting emergence in it.

I claimed 2-D vesicles are not a studied object and moved to 3-D after a 9-point scan. That was
overconfident: LAMMPS ships an official 2-D lipid-like self-assembly example, and my own scan already
had a survivor (da=15, n_amph=100, nb=4, lumen 33 -> 0 -> 42, i.e. it collapsed and REOPENED).

A planted vesicle that persists is the precondition for an emergent one -- self-assembly cannot
produce what the force field will not hold. So: map the window around the survivor, with replication,
before spending any more runs on emergence.
"""
import sys
import numpy as np
from dpd_reference import DPD

RHO, KT, A0 = 4.0, 1.0, 25.0

def plant_ring(n_amph, nb, n_head, da, R, N, seed):
    L = np.sqrt(N / RHO)
    sp = np.zeros(N, int); bonds = []
    for k in range(n_amph):
        b0 = k * nb
        sp[b0:b0 + n_head] = 1; sp[b0 + n_head:b0 + nb] = 2
        for t in range(nb - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0); a[0, 2] = a[2, 0] = A0 + da; a[1, 2] = a[2, 1] = A0 + da
    d = DPD(N, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=2)
    c = np.array([L / 2, L / 2])
    half = n_amph // 2
    for leaf, sgn, m, base in ((0, +1.0, half, 0), (1, -1.0, n_amph - half, half)):
        for k in range(m):
            th = 2 * np.pi * k / m
            u = np.array([np.cos(th), np.sin(th)])
            for t in range(nb):
                rr = R + sgn * (0.4 + t * 0.5)     # heads outermost on each face
                d.x[(base + k) * nb + t] = (c + rr * u) % L
    return d

def lumen(d, cell=0.45, min_cells=20):
    L = d.L; n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (d.x[d.species != 0] / L * n).astype(int) % n
    occ[gi[:, 0], gi[:, 1]] = True
    free = ~occ
    reach = np.zeros_like(free)
    reach[0, :] |= free[0, :]; reach[-1, :] |= free[-1, :]
    reach[:, 0] |= free[:, 0]; reach[:, -1] |= free[:, -1]
    while True:
        g = reach.copy()
        for ax in (0, 1):
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
            a, b = st.pop(); c += 1
            for da_, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = ((a + da_) % n, (b + db) % n)
                if interior[q] and q not in seen:
                    seen.add(q); st.append(q)
        best = max(best, c)
    return best if best >= min_cells else 0

print(f"{'da':>4}{'n':>5}{'nb':>4}{'R':>5}{'seed':>5}{'t=0':>6}{'4k':>6}{'10k':>6}{'20k':>6}   verdict")
for da, n_amph, nb, R in ((15, 100, 4, 5.0), (15, 100, 4, 6.5), (15, 140, 4, 7.0),
                          (12, 100, 4, 5.0), (18, 100, 4, 5.0), (15, 100, 5, 5.0)):
    for seed in (1, 2):
        d = plant_ring(n_amph, nb, 1, float(da), R, 2500, seed)
        out = [lumen(d)]
        for tgt in (4000, 10000, 20000):
            while getattr(d, "_t", 0) < tgt:
                d.step(); d._t = getattr(d, "_t", 0) + 1
            out.append(lumen(d))
        print(f"{da:>4}{n_amph:>5}{nb:>4}{R:>5.1f}{seed:>5}"
              f"{out[0]:>6}{out[1]:>6}{out[2]:>6}{out[3]:>6}   "
              f"{'STABLE' if out[3] >= 20 else 'dissolves'}", flush=True)
