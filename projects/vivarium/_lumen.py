"""Build a LUMEN metric that survives planted controls, before trusting any vesicle claim.

The current `enclosed` flood-fill fires on everything: 29 on a field of compact micelles, 19 on a
branched worm network. Both are false positives -- it counts grid gaps BETWEEN aggregates, and pockets
at branch points, as if they were interiors.

A lumen is a property of ONE aggregate: solvent that cannot escape without crossing that aggregate.
So the fixed metric is per-aggregate, requires a contiguous pocket above a minimum area (a real
interior, not a one-cell gap), and is calibrated on planted structures:

    planted vesicle (ring)  -> must score high
    planted micelle (disc)  -> must score ~0
    branched worms          -> must score ~0

Anything that cannot separate those three is not a vesicle detector.
"""
import numpy as np
from dpd_reference import DPD

RHO, KT, A0, DA = 4.0, 1.0, 25.0, 15.0

def plant(kind, n_amph=60, nb=3, n_head=1, N=2000, seed=0):
    L = np.sqrt(N / RHO)
    sp = np.zeros(N, int); bonds = []
    for k in range(n_amph):
        b0 = k * nb
        sp[b0:b0 + n_head] = 1; sp[b0 + n_head:b0 + nb] = 2
        for t in range(nb - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0); a[0, 2] = a[2, 0] = A0 + DA; a[1, 2] = a[2, 1] = A0 + DA
    d = DPD(N, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds), dt=0.02, seed=seed)
    c = np.array([L / 2, L / 2])
    if kind == "vesicle":
        R = 4.0
        half = n_amph // 2
        for leaf, sgn, m in ((0, +1.0, half), (1, -1.0, n_amph - half)):
            for k in range(m):
                idx = (leaf * half + k) if leaf == 0 else (half + k)
                th = 2 * np.pi * k / m
                u = np.array([np.cos(th), np.sin(th)])
                for t in range(nb):
                    rr = R + sgn * (0.5 + t * 0.7)      # heads outermost on each face
                    d.x[idx * nb + t] = (c + rr * u) % L
    else:                                              # compact micelle: tails in, heads out
        for k in range(n_amph):
            th = 2 * np.pi * k / n_amph
            u = np.array([np.cos(th), np.sin(th)])
            for t in range(nb):
                d.x[k * nb + t] = (c + (2.6 - t * 0.7) * u) % L
    return d

def lumen(d, nb=3, n_head=1, cell=0.45, min_cells=20):
    """Largest contiguous solvent pocket enclosed by amphiphile, in grid cells.

    min_cells=20 rejects a 13-cell false positive: a planted micelle whose tails do not quite reach
    the centre leaves a hole that is topologically interior but is not a lumen. The planted VESICLE
    scores 53, so the two are cleanly separated at 20.
    """
    L = d.L
    n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (d.x[d.species != 0] / L * n).astype(int) % n
    occ[gi[:, 0], gi[:, 1]] = True
    free = ~occ
    seen = np.zeros_like(free)
    stack = [(i, j) for i in range(n) for j in (0, n - 1) if free[i, j]]
    stack += [(i, j) for j in range(n) for i in (0, n - 1) if free[i, j]]
    for a, b in stack:
        seen[a, b] = True
    while stack:
        a, b = stack.pop()
        for da_, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p, q = a + da_, b + db
            if 0 <= p < n and 0 <= q < n and free[p, q] and not seen[p, q]:
                seen[p, q] = True; stack.append((p, q))
    # interior cells = free but unreachable from the boundary; take the LARGEST connected pocket
    interior = free & ~seen
    best, visited = 0, np.zeros_like(interior)
    for i in range(n):
        for j in range(n):
            if interior[i, j] and not visited[i, j]:
                st, c = [(i, j)], 0; visited[i, j] = True
                while st:
                    a, b = st.pop(); c += 1
                    for da_, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        p, q = a + da_, b + db
                        if 0 <= p < n and 0 <= q < n and interior[p, q] and not visited[p, q]:
                            visited[p, q] = True; st.append((p, q))
                best = max(best, c)
    return best if best >= min_cells else 0

# A planted vesicle DISSOLVED in 2000 steps at da=15, n=60. Self-assembly cannot produce what the
# force field will not hold, so scan for where a planted vesicle SURVIVES before hunting emergence.
print(f"{'da':>5}{'n_amph':>8}{'nb':>4}{'lumen t=0':>11}{'t=2k':>7}{'t=6k':>7}   verdict")
for da in (15.0, 25.0, 40.0):
    for n_amph, nb in ((60, 3), (100, 3), (100, 4)):
        globals()["DA"] = da
        d = plant("vesicle", n_amph=n_amph, nb=nb, N=2500)
        l0 = lumen(d)
        for _ in range(2000):
            d.step()
        l2 = lumen(d)
        for _ in range(4000):
            d.step()
        l6 = lumen(d)
        print(f"{da:>5.0f}{n_amph:>8}{nb:>4}{l0:>11}{l2:>7}{l6:>7}   "
              f"{'VESICLE SURVIVES' if l6 >= 20 else 'dissolves'}", flush=True)
