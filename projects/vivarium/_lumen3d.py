"""Enclosure detection in THREE dimensions.

WHY THIS FILE EXISTS

`_lumen_field.n_enclosed` is a 2-D detector. `_interior_mask` builds `np.zeros((n, n))` and floods with
4-connectivity, so in 3-D it is not merely inaccurate -- it is measuring a different object. A planted,
genuinely hollow 3-D sphere reads `[0, 0, 0, 0]` under it while the 2-D ring reads `[1, 1, 1, 1]`.
**Thirty-nine 3-D runs were scored against that detector before it was caught**, and both closure
claims resting on them were withdrawn.

This is the 3-D replacement. It mirrors the 2-D logic step for step so the two are comparable:

  1. UNWRAP the aggregate by connectivity, then centre it in the box. Centring on a raw wrapped
     centroid is meaningless for a cluster straddling a boundary, and the 2-D detector once read
     n_enclosed 1 centred and 0 for the same ring moved onto the edge.
  2. Stamp each bead as a BALL of radius `r = round(bead / 2 cell)`, not a single voxel. A single-voxel
     stamp leaves a membrane porous at cell = 0.5 and the fill leaks straight through.
  3. Flood the free space inward from the six FACES of the box. Anything free and unreached is
     enclosed.
  4. Label the enclosed regions and return (count, sizes).

`bead` is a DILATION DIAMETER, calibrated, not the physical bead size -- the same quantity the 2-D
detector documents. Note the aliasing inherited from that convention: at cell = 0.5 the ladder
1.0/1.5/2.0/3.0 maps to r = 1/2/2/3, so beads 1.5 and 2.0 are the SAME mask. Three distinct dilations,
not four.
"""
from __future__ import annotations

import numpy as np

from _lumen_field import unwrap_cluster


def _ball(r: int):
    o = range(-r, r + 1)
    return [(dx, dy, dz) for dx in o for dy in o for dz in o if dx * dx + dy * dy + dz * dz <= r * r]


def occupancy(X, mols, L, cell=0.5, bead=1.0):
    """Boolean voxel grid with the aggregate unwrapped and centred, beads stamped as balls."""
    P = unwrap_cluster(X, mols, L)
    if P is None:
        P = np.asarray(X)[np.concatenate(mols)]
    P = P - P.mean(axis=0) + L / 2.0
    n = max(8, int(L / cell))
    occ = np.zeros((n, n, n), bool)
    gi = (P / L * n).astype(int) % n
    r = max(1, int(round(bead / (2 * cell))))
    for dx, dy, dz in _ball(r):
        occ[(gi[:, 0] + dx) % n, (gi[:, 1] + dy) % n, (gi[:, 2] + dz) % n] = True
    return occ


def _flood_from_faces(free):
    """Free voxels reachable from the box surface, by iterative 6-connected dilation.

    Dilation rather than a Python stack: the grid is ~10^5-10^6 voxels and a per-voxel loop in Python
    costs seconds per call, which at one call per checkpoint per dilation is not affordable.
    """
    seen = np.zeros_like(free)
    seen[0], seen[-1] = free[0], free[-1]
    seen[:, 0], seen[:, -1] = free[:, 0], free[:, -1]
    seen[:, :, 0], seen[:, :, -1] = free[:, :, 0], free[:, :, -1]
    while True:
        nxt = seen.copy()
        nxt[1:] |= seen[:-1]
        nxt[:-1] |= seen[1:]
        nxt[:, 1:] |= seen[:, :-1]
        nxt[:, :-1] |= seen[:, 1:]
        nxt[:, :, 1:] |= seen[:, :, :-1]
        nxt[:, :, :-1] |= seen[:, :, 1:]
        nxt &= free
        if nxt.sum() == seen.sum():
            return nxt
        seen = nxt


def _components(mask, min_cells):
    """Sizes of 6-connected components of `mask`, descending. Components are few, so seeding one at a
    time and dilating is cheaper than a general labelling pass."""
    remaining = mask.copy()
    sizes = []
    while remaining.any():
        seed = np.zeros_like(remaining)
        idx = np.argwhere(remaining)[0]
        seed[tuple(idx)] = True
        while True:
            nxt = seed.copy()
            nxt[1:] |= seed[:-1]
            nxt[:-1] |= seed[1:]
            nxt[:, 1:] |= seed[:, :-1]
            nxt[:, :-1] |= seed[:, 1:]
            nxt[:, :, 1:] |= seed[:, :, :-1]
            nxt[:, :, :-1] |= seed[:, :, 1:]
            nxt &= remaining
            if nxt.sum() == seed.sum():
                break
            seed = nxt
        c = int(seed.sum())
        if c >= min_cells:
            sizes.append(c)
        remaining &= ~seed
    sizes.sort(reverse=True)
    return len(sizes), sizes


def n_enclosed_3d(X, mols, L, cell=0.5, bead=1.0, min_cells=40):
    """(count, sizes) of separate regions the aggregate seals off from the box surface."""
    free = ~occupancy(X, mols, L, cell, bead)
    return _components(free & ~_flood_from_faces(free), min_cells)


def vesicle_call_3d(X, mols, L, cell=0.5):
    """Is this a 3-D vesicle? Returns (bool, reason).

    Same two clauses as the 2-D gate, with the 3-D volume law. A closed vesicle of n lipids has surface
    area n*a per leaflet; with two leaflets and area-per-lipid a, R = sqrt(n * a / (8 pi)) and the
    enclosed volume is 4/3 pi R^3. `a` is taken as 1.2 sigma^2, the standard coarse-grained value.
    """
    counts = [n_enclosed_3d(X, mols, L, cell=cell, bead=b)[0] for b in (1.0, 2.0, 3.0)]
    if not all(c == 1 for c in counts):
        return False, f"n_enclosed_3d unstable across dilation: {counts}"
    lumen = n_enclosed_3d(X, mols, L, cell=cell)[1][0]
    n = len(mols)
    R = np.sqrt(n * 1.2 / (8.0 * np.pi))
    expected = (4.0 / 3.0) * np.pi * R ** 3 / cell ** 3
    ratio = lumen / expected
    if ratio < 0.10:
        return False, f"lumen {lumen} is {ratio:.3f} of the {expected:.0f} expected for {n} lipids"
    return True, f"lumen {lumen}, {ratio:.3f} of expected, stable at 1 across dilation"


# --------------------------------------------------------------------------------------------------
def _controls(seed=0, L=30.0):
    """Five structures whose answers are known BY CONSTRUCTION. The instrument must SEPARATE them, not
    merely score the shell well -- scoring one case correctly is what let the 2-D detector run on 3-D
    data for 39 runs."""
    rng = np.random.default_rng(seed)
    out = {}

    def as_mols(pts):
        X = np.asarray(pts, dtype=float)
        return X, np.arange(len(X)).reshape(-1, 1)

    def shell(centre, R, n=4000):
        v = rng.normal(size=(n, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        return centre + v * R

    out["hollow shell"] = as_mols(shell(np.full(3, L / 2), 7.0))
    out["solid ball"] = as_mols(np.full(3, L / 2) + rng.normal(size=(4000, 3))
                                * 0 + (np.full(3, L / 2) + (rng.random((4000, 3)) - 0.5) * 14.0))
    out["gas"] = as_mols(rng.random((4000, 3)) * L)
    xy = (rng.random((4000, 2)) - 0.5) * (L - 2) + L / 2
    out["flat bilayer slab"] = as_mols(np.column_stack(
        [xy, L / 2 + np.where(rng.random(4000) < 0.5, 1.0, -1.0)]))
    out["two shells"] = as_mols(np.vstack([shell(np.array([L / 3, L / 2, L / 2]), 4.5, 2500),
                                           shell(np.array([2 * L / 3, L / 2, L / 2]), 4.5, 2500)]))
    return out


def validate() -> int:
    L = 30.0
    want = {"hollow shell": 1, "solid ball": 0, "gas": 0, "flat bilayer slab": 0, "two shells": 2}
    ctl = _controls(L=L)
    print(f"  {'control':>20} {'n_enclosed_3d':>14} {'expected':>9} {'largest lumen':>14}")
    got = {}
    for k in ("hollow shell", "solid ball", "gas", "flat bilayer slab", "two shells"):
        X, mols = ctl[k]
        c, sizes = n_enclosed_3d(X, mols, L)
        got[k] = c
        flag = "" if c == want[k] else "   <-- MISMATCH"
        print(f"  {k:>20} {c:>14} {want[k]:>9} {(sizes[0] if sizes else 0):>14}{flag}")
    ok = all(got[k] == want[k] for k in want)
    print(f"\n  every control matches its known answer: {ok}")
    print(f"  the shell is separated from ball, gas AND slab: "
          f"{got['hollow shell'] == 1 and got['solid ball'] == 0 and got['gas'] == 0 and got['flat bilayer slab'] == 0}")
    print(f"  two shells are counted as two, not one:  {got['two shells'] == 2}")
    print(f"  INSTRUMENT USABLE: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(validate())
