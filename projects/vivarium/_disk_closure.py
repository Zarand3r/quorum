"""Does a planted flat bilayer DISK close into a vesicle? Scanning the bending stiffness.

The literature route from our two failure modes to a vesicle is a competition between edge line
tension Gamma and bending rigidity kappa, with a critical disk radius

    R_c = 2 kappa / Gamma

Below R_c a disk stays open; above it the shrinking rim pays for the bending and the disk closes.
Reported behaviour is branched shapes -> flat disks as line tension rises, then a SHARP disk ->
vesicle transition. Our two results sit on either side of that: the 2-D ribbons branched (line
tension too low, no bending term at all), and the 3-D SL slab is stiff (k_ang=15) and box-spanning,
so it has no rim to pay for closure and R_c is large.

This tests the mechanism directly instead of waiting for self-assembly. Planting the disk removes
the aggregation kinetics entirely: if a disk with R > R_c exists, closure is downhill and fast. A
scan over k_ang moves kappa at fixed chemistry, so a closure threshold in k_ang IS the R_c relation.

Disk radius is set from the geometry measured on the spanning slab (d = 5.03 rc, a = 1.65 rc^2), so
the planted disk holds exactly the amphiphiles a vesicle of the target radius needs.
"""
import sys
import numpy as np
from dpd_reference import DPD
from _sl_model import RHO, KT, NH, NT, NTAIL, NB, A

D_MEM, A_LIP = 5.03, 1.65          # measured on sl_f28_N12000_s1 by _geom.py


def plant_disk(R_ves, N, k_ang, seed, dim=3):
    """Flat bilayer disk holding exactly the amphiphiles a vesicle of radius R_ves would need."""
    n_amph = int(4 * np.pi * (R_ves ** 2 + max(R_ves - D_MEM, 0.0) ** 2) / A_LIP)
    per_leaf = n_amph // 2
    R_disk = np.sqrt(per_leaf * A_LIP / np.pi)
    L = (N / RHO) ** (1.0 / dim)
    assert 2 * R_disk + 3.0 < L, f"disk R={R_disk:.1f} does not fit in L={L:.1f}"

    sp = np.zeros(N, int); bonds = []; angles = []
    for k in range(n_amph):
        b = k * NB
        sp[b:b + NH] = 1
        sp[b + NH:b + NB] = 2
        for t in range(NH - 1):
            bonds.append((b + t, b + t + 1))
        for c in range(NTAIL):
            t0 = b + NH + c * NT
            bonds.append((b + NH - 1, t0))
            for t in range(NT - 1):
                bonds.append((t0 + t, t0 + t + 1))
            angles.append((b + NH - 1, t0, t0 + 1))
            for t in range(NT - 2):
                angles.append((t0 + t, t0 + t + 1, t0 + t + 2))
    d = DPD(N, L, kT=KT, a_matrix=A, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=dim)
    d.angles = np.array(angles)
    d.k_ang = float(k_ang)

    # hexagonal lattice inside R_disk gives the target area per amphiphile
    pitch = np.sqrt(A_LIP / (np.sqrt(3) / 2))
    pts = []
    m = int(R_disk / pitch) + 2
    for i in range(-m, m + 1):
        for j in range(-m, m + 1):
            px = (i + 0.5 * (j % 2)) * pitch
            py = j * pitch * np.sqrt(3) / 2
            if px * px + py * py <= R_disk ** 2:
                pts.append((px, py))
    pts = np.array(pts)
    order = np.argsort(pts[:, 0] ** 2 + pts[:, 1] ** 2)
    pts = pts[order][:per_leaf]
    c0 = np.full(dim, L / 2)
    zs_h = [2.5, 2.0, 1.5]                      # head-to-head spans 5.0 == measured d
    zs_t = [1.0, 0.5, 0.0, -0.5]
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        for q in range(per_leaf):
            k = leaf * per_leaf + q
            if k >= n_amph:
                break
            b = k * NB
            px, py = pts[q % len(pts)]
            for t in range(NH):
                d.x[b + t] = (c0 + np.array([px, py, sgn * zs_h[t]])) % L
            for cc in range(NTAIL):
                t0 = b + NH + cc * NT
                dx = (cc - 0.5) * 0.45
                for t in range(NT):
                    d.x[t0 + t] = (c0 + np.array([px + dx, py, sgn * zs_t[t]])) % L
    return d, n_amph, R_disk


def shape_and_lumen(d, n_amph, cells=26):
    """Asphericity of the aggregate plus enclosed-water cells.

    A flat disk has one small gyration eigenvalue; a closed vesicle has three comparable ones.
    Lumen is water the box exterior cannot reach: flood-fill non-lipid cells from the boundary and
    count what is left over, which is zero for a disk and positive only once the shell closes.
    """
    lip = d.species != 0
    P = d.x[lip]
    c = P.mean(axis=0)
    q = P - c
    q -= d.L * np.round(q / d.L)
    ev = np.sort(np.linalg.eigvalsh(np.cov(q.T)))[::-1]
    flat = float(ev[2] / ev[0])                       # ~0 for a disk, ~1 for a sphere

    # A lumen must contain WATER. Flood-filling merely-unoccupied cells counts the voids inside
    # the bilayer's own tail core, which read 51-68 on disks that were still provably flat
    # (asphericity 0.08) -- the same false positive that retired the old `enclosed` metric.
    occ = np.zeros((cells,) * 3, bool)
    idx = (d.x[lip] / d.L * cells).astype(int) % cells
    occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    wat = np.zeros((cells,) * 3, bool)
    widx = (d.x[~lip] / d.L * cells).astype(int) % cells
    wat[widx[:, 0], widx[:, 1], widx[:, 2]] = True
    free = ~occ
    seen = np.zeros_like(free)
    stack = [(i, j, k) for i in range(cells) for j in range(cells) for k in range(cells)
             if (i in (0, cells - 1) or j in (0, cells - 1) or k in (0, cells - 1)) and free[i, j, k]]
    for s in stack:
        seen[s] = True
    while stack:
        i, j, k = stack.pop()
        for di, dj, dk in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            a, b_, cc = i + di, j + dj, k + dk
            if 0 <= a < cells and 0 <= b_ < cells and 0 <= cc < cells and free[a, b_, cc] and not seen[a, b_, cc]:
                seen[a, b_, cc] = True
                stack.append((a, b_, cc))
    lumen = int((free & ~seen & wat).sum())      # enclosed AND actually holding water
    return flat, lumen


if __name__ == "__main__":
    R_ves = float(sys.argv[1]); N = int(sys.argv[2]); steps = int(sys.argv[3])
    print(f"{'k_ang':>6}{'n_amph':>8}{'R_disk':>8}{'L':>7}{'step':>8}"
          f"{'asphere':>9}{'lumen':>7}{'T':>7}   note", flush=True)
    for k_ang in (float(x) for x in sys.argv[4].split(",")):
        d, n_amph, R_disk = plant_disk(R_ves, N, k_ang, seed=1)
        for t in range(steps + 1):
            if t % (steps // 5) == 0:
                fl, lu = shape_and_lumen(d, n_amph)
                note = "CLOSED" if (fl > 0.55 and lu > 15) else ("curling" if fl > 0.35 else "flat")
                print(f"{k_ang:>6.1f}{n_amph:>8}{R_disk:>8.2f}{d.L:>7.1f}{t:>8}"
                      f"{fl:>9.3f}{lu:>7d}{d.temperature():>7.3f}   {note}", flush=True)
            d.step()
        np.savez_compressed(
            f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/"
            f"disk_R{R_ves:g}_k{k_ang:g}_N{N}.npz",
            x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=NH)
