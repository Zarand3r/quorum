"""Stage D gate 3: do bonded amphiphiles in calibrated DPD self-assemble into mesophases?

Gates 1 and 2 passed: the solvent is a healthy liquid (T 1.01, homogeneity 0.12, MSD 16) and species
incompatibility is calibrated (like-fraction 0.50 -> 0.89 as da goes 0 -> 10, against a measured
random null of 0.496).

This is the rung that decides the whole reset. If bounded pairwise forces with a CALIBRATED solvent
produce concentration-dependent amphiphile morphology, then Vivarium's failure was parameterisation
and the transformer question is still open. If they do not, the roadmap's premise is wrong.

Molecule: H-T-T, harmonic bonds. Species 0 = water, 1 = head, 2 = tail.
Water-tail and head-tail repulsion raised by da; everything else at the calibrated a=25.
"""
import numpy as np
from dpd_reference import DPD

RHO, KT, A0, DA = 4.0, 1.0, 25.0, 15.0
NB = 3                     # beads per amphiphile: 1 head + 2 tails

def build(n_amph, n_total, seed=0, dt=0.02):
    L = np.sqrt(n_total / RHO)
    n_lip_beads = n_amph * NB
    assert n_lip_beads < n_total
    sp = np.zeros(n_total, int)
    bonds = []
    for k in range(n_amph):
        b0 = k * NB
        sp[b0] = 1                      # head
        sp[b0 + 1:b0 + NB] = 2          # tails
        for t in range(NB - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0)
    a[0, 2] = a[2, 0] = A0 + DA         # water-tail: the hydrophobic effect
    a[1, 2] = a[2, 1] = A0 + DA         # head-tail
    d = DPD(n_total, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=100.0, r0=0.7, dt=dt, seed=seed)
    # place each amphiphile as a compact random-oriented rod so bonds do not start stretched
    for k in range(n_amph):
        b0 = k * NB
        c = d.rng.uniform(0, L, 2)
        th = d.rng.uniform(0, 2 * np.pi)
        u = np.array([np.cos(th), np.sin(th)])
        for t in range(NB):
            d.x[b0 + t] = (c + t * 0.7 * u) % L
    return d

def aggregates(d, n_amph):
    """Cluster amphiphiles whose TAIL beads share a hydrophobic core."""
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

def aspect(d, comp, n_amph):
    """Radius-of-gyration aspect ratio of one aggregate: ~1 round, >>1 elongated/lamellar."""
    idx = np.array([c * NB + t for c in comp for t in range(NB)])
    p = d.x[idx]
    ref = p[0]
    q = p - ref; q -= d.L * np.round(q / d.L); q = q + ref
    q = q - q.mean(axis=0)
    w = np.linalg.eigvalsh(np.cov(q.T))
    return float(np.sqrt(max(w) / max(min(w), 1e-9)))

print(f"2-D DPD amphiphiles  H-T-T,  a={A0}, da={DA},  rho={RHO}, kT={KT}")
print(f"{'phi':>6}{'n_amph':>8}{'aggs':>6}{'mean':>7}{'largest':>9}{'aspect':>8}{'T':>6}   morphology")
N_TOTAL = 1200
for phi in (0.05, 0.12, 0.22, 0.35):
    n_amph = int(phi * N_TOTAL / NB)
    d = build(n_amph, N_TOTAL, seed=2)
    for _ in range(6000):
        d.step()
    comps = [c for c in aggregates(d, n_amph) if len(c) >= 3]
    if not comps:
        print(f"{phi:>6.2f}{n_amph:>8}{0:>6}{0:>7}{0:>9}{0:>8.1f}{d.temperature():>6.2f}   dispersed")
        continue
    sizes = [len(c) for c in comps]
    asp = aspect(d, comps[0], n_amph)
    morph = ("lamellar/extended" if asp > 3.0 else
             "elongated" if asp > 1.8 else "micellar")
    print(f"{phi:>6.2f}{n_amph:>8}{len(comps):>6}{np.mean(sizes):>7.1f}{max(sizes):>9}"
          f"{asp:>8.1f}{d.temperature():>6.2f}   {morph}", flush=True)
    np.savez_compressed(
        f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/dpd_phi{int(phi*100)}.npz",
        x=d.x, species=d.species, L=d.L, n_amph=n_amph)
