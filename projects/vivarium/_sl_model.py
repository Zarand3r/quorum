"""Shillcock-Lipowsky style DPD amphiphile: H3(C4)2 with stiffened tails.

Everything my earlier attempts lacked, added at once because they are one model, not four knobs:
  * architecture  3 head beads, TWO 4-bead tails (11 beads), not 1 head + 1 short tail
  * bending       three-body angle potential k3 ~ 15 on the hydrophobic chains. Fully flexible tails
                  coil instead of packing into leaflets -- the amorphous blobs I kept producing
  * chemistry     a_WW=a_TT=25, a_HH=35, a_HT=a_WT=80, a_HW=15 (head MORE compatible with water than
                  water is with itself; my earlier a_HW=25 was not hydrophilic enough)
  * bonds         k=128, l0=0.5

The engine underneath is validated against the Groot-Warren equation of state (p/p_pred 0.92-0.99)
and holds temperature across an 8x timestep range, so a failure here is the model, not the integrator.
"""
import sys
import numpy as np
from dpd_reference import DPD

RHO, KT = 3.0, 1.0
NH, NT, NTAIL = 3, 4, 2                 # heads, beads per tail, number of tails
NB = NH + NT * NTAIL                    # 11
A = np.array([[25.0, 15.0, 80.0],
              [15.0, 35.0, 80.0],
              [80.0, 80.0, 25.0]])      # water, head, tail

def build(n_amph, N, seed, dim=3):
    L = (N / RHO) ** (1.0 / dim)
    sp = np.zeros(N, int); bonds = []; angles = []
    for k in range(n_amph):
        b = k * NB
        sp[b:b + NH] = 1
        sp[b + NH:b + NB] = 2
        for t in range(NH - 1):                     # head backbone
            bonds.append((b + t, b + t + 1))
        for c in range(NTAIL):                      # two tails, both on the last head
            t0 = b + NH + c * NT
            bonds.append((b + NH - 1, t0))
            for t in range(NT - 1):
                bonds.append((t0 + t, t0 + t + 1))
            angles.append((b + NH - 1, t0, t0 + 1))  # stiffen the hydrophobic chains
            for t in range(NT - 2):
                angles.append((t0 + t, t0 + t + 1, t0 + t + 2))
    d = DPD(N, L, kT=KT, a_matrix=A, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=dim)
    d.angles = np.array(angles)
    d.k_ang = 15.0
    for k in range(n_amph):                          # random position, random orientation, extended
        b = k * NB
        c = d.rng.uniform(0, L, dim)
        u = d.rng.normal(size=dim); u /= np.linalg.norm(u)
        for t in range(NH):
            d.x[b + t] = (c - (NH - t) * 0.5 * u) % L
        for cc in range(NTAIL):
            t0 = b + NH + cc * NT
            perp = d.rng.normal(size=dim); perp -= perp @ u * u
            perp /= np.linalg.norm(perp) + 1e-12
            for t in range(NT):
                d.x[t0 + t] = (c + (t + 1) * 0.5 * u + (cc - 0.5) * 0.5 * perp) % L
    return d

def clusters(d, n_amph):
    tails = np.array([k * NB + NH + t for k in range(n_amph) for t in range(NT * NTAIL)])
    x = d.x[tails]
    dd = x[:, None, :] - x[None, :, :]
    dd -= d.L * np.round(dd / d.L)
    close = np.linalg.norm(dd, axis=2) < 1.0
    m = NT * NTAIL
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
        s0 = [slice(None)] * d.dim; s0[ax] = 0
        s1 = [slice(None)] * d.dim; s1[ax] = -1
        reach[tuple(s0)] |= free[tuple(s0)]; reach[tuple(s1)] |= free[tuple(s1)]
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

frac, steps, N, seed = float(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
n_amph = int(frac * N / NB)
d = build(n_amph, N, seed)
for _ in range(steps):
    d.step()
cl = [c for c in clusters(d, n_amph) if len(c) >= 3]
lu = lumen(d)
tag = f"sl_f{int(frac*100)}_N{N}_s{seed}"
print(f"RESULT {tag:<20}n={n_amph:<4}aggs={len(cl):<4}largest={len(cl[0]) if cl else 0:<5}"
      f"lumen={lu:<5}T={d.temperature():.2f} homog={d.density_homogeneity():.2f}   "
      f"{'*** VESICLE ***' if lu >= 25 else 'no lumen'}", flush=True)
np.savez_compressed(
    f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/{tag}.npz",
    x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=NH)
