"""The rung I skipped: is a planted FLAT bilayer stable in this DPD amphiphile model?

I went straight to closed rings. A vesicle is a bilayer bent shut, so if the flat membrane is not
stable nothing downstream can be. This is the cheapest possible discriminator between "my amphiphile
parameters are wrong" and "closure specifically is hard".

Planted: two leaflets, tails meeting at the midplane, heads facing solvent on both faces -- the same
geometry the conventional reference (cooke_deserno.py) uses. Order parameter: fraction of amphiphiles
whose axis is within 30 degrees of the membrane normal, which is ~1 for an intact bilayer and falls to
the random value as it melts.
"""
import numpy as np
from dpd_reference import DPD

RHO, KT, A0 = 3.0, 1.0, 25.0

def plant_bilayer(n_amph, nb, da, N, dim=3, seed=0):
    L = (N / RHO) ** (1.0 / dim)
    sp = np.zeros(N, int); bonds = []
    for k in range(n_amph):
        b0 = k * nb
        sp[b0] = 1; sp[b0 + 1:b0 + nb] = 2
        for t in range(nb - 1):
            bonds.append((b0 + t, b0 + t + 1))
    a = np.full((3, 3), A0); a[0, 2] = a[2, 0] = A0 + da; a[1, 2] = a[2, 1] = A0 + da
    d = DPD(N, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=dim)
    half = n_amph // 2
    per_side = int(np.ceil(np.sqrt(half))) if dim == 3 else half
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        m = half if leaf == 0 else n_amph - half
        for k in range(m):
            idx = (leaf * half + k)
            if dim == 3:
                gx, gy = k % per_side, k // per_side
                base = np.array([(gx + 0.5) * L / per_side, (gy + 0.5) * L / per_side, L / 2])
                ax = np.array([0.0, 0.0, 1.0])
            else:
                base = np.array([(k + 0.5) * L / m, L / 2])
                ax = np.array([0.0, 1.0])
            for t in range(nb):
                off = 0.4 + (nb - 1 - t) * 0.5          # head outermost
                d.x[idx * nb + t] = (base + sgn * off * ax) % L
    return d

def order(d, n_amph, nb, dim):
    heads = np.arange(n_amph) * nb
    tails = np.stack([d.x[np.arange(n_amph) * nb + t] for t in range(1, nb)]).mean(axis=0)
    u = d.x[heads] - tails
    u -= d.L * np.round(u / d.L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    nrm = np.zeros(dim); nrm[-1] = 1.0
    return float((np.abs(u @ nrm) > np.cos(np.pi / 6)).mean())

# Published DPD membrane models use a MUCH stronger water-tail repulsion than I had been using:
# roughly a_WT ~ 75 against a_WW = 25, i.e. Delta-a ~ 50, where these runs used 15-30. Aggregates
# formed at the weak setting but the bilayer melted (order 1.00 -> 0.13), which is the signature of
# a hydrophobic drive too weak to hold a membrane rather than of a closure problem.
for dim in (3, 2):
    N = 9000 if dim == 3 else 2500
    print(f"\n{dim}-D planted bilayer, N={N}")
    print(f"{'da':>5}{'n_amph':>8}{'nb':>4}{'order t=0':>11}{'2k':>7}{'6k':>7}{'15k':>7}   verdict")
    for da in (30.0, 50.0, 75.0):
        for nb in (4, 5):
            # Area per amphiphile must place neighbours INSIDE rc=1, or the "bilayer" is a grid of
            # rods that never touch. At N=9000 the box is L=14.4, so the previous 100 per leaflet
            # gave spacing 1.44 -- beyond the cutoff. Every earlier "melts" row measured that sparse
            # grid, not the physics. Choose the count from a target area per amphiphile instead.
            L_box = (N / RHO) ** (1.0 / dim)
            extent = L_box ** (dim - 1)          # membrane area in 3-D, membrane length in 2-D
            n_amph = int(2 * extent / (1.30 if dim == 3 else 1.05))
            d = plant_bilayer(n_amph, nb, da, N, dim=dim, seed=1)
            o = [order(d, n_amph, nb, dim)]
            for tgt in (2000, 6000, 15000):
                while getattr(d, "_t", 0) < tgt:
                    d.step(); d._t = getattr(d, "_t", 0) + 1
                o.append(order(d, n_amph, nb, dim))
            print(f"{da:>5.0f}{n_amph:>8}{nb:>4}{o[0]:>11.2f}{o[1]:>7.2f}{o[2]:>7.2f}{o[3]:>7.2f}   "
                  f"{'BILAYER HOLDS' if o[3] > 0.55 else 'melts'}", flush=True)
            # save so the membrane can be LOOKED at, not only scored
            np.savez_compressed(
                f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/"
                f"bl{dim}d_da{int(da)}_nb{nb}.npz",
                x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=nb, nh=1)
