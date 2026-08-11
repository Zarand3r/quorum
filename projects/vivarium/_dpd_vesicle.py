"""Do any DPD states enclose solvent? And is there a vesicle window between elongated and lamellar?

Stage D gave micellar (phi 0.05) -> elongated (0.12-0.22) -> extended bands (0.35). None of those is
a vesicle. In the AOT reference the vesicle window sits BETWEEN the micellar and lamellar regimes, so
the gap between 0.22 and 0.35 is where to look -- plus longer runs, since closure of an open ribbon is
slower than aggregation.

Lumen test: occupancy grid over the box, flood-fill the solvent from the boundary through cells not
occupied by amphiphile beads, and count solvent beads in pockets that the fill cannot reach. A closed
ring traps them; an open ribbon does not. Reported beside the largest aggregate so a big number cannot
come from a percolating tangle (the artifact that faked a lumen once already, F38).
"""
import numpy as np
from dpd_reference import DPD

RHO, KT, A0, DA, NB = 4.0, 1.0, 25.0, 15.0, 3
N_TOTAL = 1200

def build(n_amph, seed=0):
    L = np.sqrt(N_TOTAL / RHO)
    sp = np.zeros(N_TOTAL, int); bonds = []
    for k in range(n_amph):
        b0 = k * NB
        sp[b0] = 1; sp[b0 + 1:b0 + NB] = 2
        for t in range(NB - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0)
    a[0, 2] = a[2, 0] = A0 + DA
    a[1, 2] = a[2, 1] = A0 + DA
    d = DPD(N_TOTAL, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=100.0, r0=0.7, dt=0.02, seed=seed)
    for k in range(n_amph):
        b0 = k * NB
        c = d.rng.uniform(0, L, 2); th = d.rng.uniform(0, 2 * np.pi)
        u = np.array([np.cos(th), np.sin(th)])
        for t in range(NB):
            d.x[b0 + t] = (c + t * 0.7 * u) % L
    return d

def enclosed(d, cell=0.5):
    """Solvent beads in pockets unreachable from the boundary without crossing amphiphile."""
    L = d.L
    n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    lip = d.x[d.species != 0]
    gi = (lip / L * n).astype(int) % n
    for a, b in gi:
        occ[a % n, b % n] = True
    free = ~occ
    seen = np.zeros_like(free)
    stack = []
    for i in range(n):                              # seed the fill from every boundary cell
        for j in (0, n - 1):
            for a, b in ((i, j), (j, i)):
                if free[a, b] and not seen[a, b]:
                    seen[a, b] = True; stack.append((a, b))
    while stack:
        a, b = stack.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p, q = a + da, b + db
            if 0 <= p < n and 0 <= q < n and free[p, q] and not seen[p, q]:
                seen[p, q] = True; stack.append((p, q))
    wat = d.x[d.species == 0]
    wi = (wat / L * n).astype(int) % n
    trapped = sum(1 for a, b in wi if free[a, b] and not seen[a, b])
    return trapped

def largest_agg(d, n_amph):
    tails = np.array([k * NB + t for k in range(n_amph) for t in range(1, NB)])
    x = d.x[tails]
    dd = x[:, None, :] - x[None, :, :]
    dd -= d.L * np.round(dd / d.L)
    close = np.linalg.norm(dd, axis=2) < 1.0
    m = NB - 1
    adj = close.reshape(n_amph, m, n_amph, m).any(axis=(1, 3))
    np.fill_diagonal(adj, False)
    seen, best = set(), 0
    for s0 in range(n_amph):
        if s0 in seen: continue
        st, c = [s0], 0; seen.add(s0)
        while st:
            u = st.pop(); c += 1
            for v in np.where(adj[u])[0]:
                if v not in seen: seen.add(v); st.append(v)
        best = max(best, c)
    return best

print(f"{'phi':>6}{'steps':>8}{'largest':>9}{'enclosed':>10}   verdict")
for phi, steps in ((0.22, 12000), (0.26, 12000), (0.30, 12000), (0.35, 12000), (0.26, 30000)):
    n_amph = int(phi * N_TOTAL / NB)
    d = build(n_amph, seed=3)
    for _ in range(steps):
        d.step()
    enc, big = enclosed(d), largest_agg(d, n_amph)
    print(f"{phi:>6.2f}{steps:>8}{big:>9}{enc:>10}   "
          f"{'LUMEN' if enc >= 8 else 'no lumen'}", flush=True)
    np.savez_compressed(
        f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/ves_phi{int(phi*100)}_{steps}.npz",
        x=d.x, species=d.species, L=d.L, n_amph=n_amph)
