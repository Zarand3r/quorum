import sys, os, glob
sys.path.insert(0, "/home/rbao/quorum-thermolife/bazel-bin/projects/vivarium/_mixture.runfiles/rules_python~~pip~vivarium_deps_312_numpy/site-packages")
import numpy as np
from collections import deque

def enclosed_analysis(X, mols, wi, L, cell=1.0, memb=1.6):
    """Is a closed aggregate wrapping WATER or VACUUM?

    Rasterize the box; mark cells within `memb` of any lipid bead as membrane; flood-fill the non-membrane
    cells from the boundary to find OUTSIDE. Any non-membrane cell not reached is ENCLOSED. Then compare
    water density inside those cells with water density outside. A vesicle encloses water at about bulk
    density; a surfactant-coated vapour bubble encloses nothing. This distinguishes the two cases, which
    look identical in a render and which `lumen` and the render disagreed about.
    """
    # RECENTRE FIRST. The aggregate is free to straddle the periodic boundary, and in wrapped
    # coordinates a ring that does so spans the whole box (measured: x 0.0-150.0, y 0.0-150.0 for a
    # planted N=300 ring), so its rasterized membrane is cut in two and never forms a closed curve.
    # The detector then reports "no enclosed region" for a structure that is enclosed by construction --
    # which is exactly what it did on its positive control. Same failure as the render slab and the
    # centroid before it: working in wrapped coordinates without recentring.
    n = int(np.ceil(L / cell))
    lip = np.concatenate(mols)
    # Minimum-image unwrapping cannot rescue a cluster wider than L/2, and this ring is 96 sigma across
    # in a 150 box. But the stored coordinates are already contiguous -- the plant centres the ring on the
    # origin -- and it is the `% L` in the rasterizer that splits it. So shift the aggregate to the box
    # centre using its RAW centroid, then wrap: the structure lands whole in the middle and the grid sees
    # a closed curve.
    X = X - X[lip].mean(axis=0) + L / 2.0
    g = np.zeros((n, n), bool)
    idx = np.floor((X[lip] % L) / cell).astype(int) % n
    r = int(np.ceil(memb / cell))
    for dx in range(-r, r+1):
        for dy in range(-r, r+1):
            if dx*dx + dy*dy <= r*r:
                g[(idx[:,0]+dx) % n, (idx[:,1]+dy) % n] = True
    outside = np.zeros((n, n), bool)
    q = deque()
    for i in range(n):
        for j in (0, n-1):
            for a, b in ((i, j), (j, i)):
                if not g[a, b] and not outside[a, b]:
                    outside[a, b] = True; q.append((a, b))
    while q:
        a, b = q.popleft()
        for da, db in ((1,0),(-1,0),(0,1),(0,-1)):
            p, qq = (a+da) % n, (b+db) % n
            if not g[p, qq] and not outside[p, qq]:
                outside[p, qq] = True; q.append((p, qq))
    enclosed = (~g) & (~outside)
    if enclosed.sum() == 0:
        return None
    wid = np.floor((X[wi] % L) / cell).astype(int) % n
    w_in = enclosed[wid[:,0], wid[:,1]].sum()
    w_out = outside[wid[:,0], wid[:,1]].sum()
    rho_in = w_in / enclosed.sum(); rho_out = w_out / max(outside.sum(), 1)
    return enclosed.sum()*cell*cell, w_in, rho_in/max(rho_out,1e-9)

print("Enclosed-region test: does a closed aggregate wrap WATER or VACUUM?\n")
print(f"{'file':<46}{'area':>8}{'n_water_in':>12}{'rho_in/rho_out':>16}")
for fn in sorted(glob.glob("/home/rbao/quorum-thermolife/projects/vivarium/docs/states/mix2d_random_N120_exp_*.npz")):
    z = np.load(fn, allow_pickle=True)
    X, L = z["X"], float(z["L"])
    mols = [np.asarray(m, dtype=np.int64) for m in z["mols"]]
    sp = z["species"]
    wi = np.flatnonzero(sp == 2)
    if not len(wi): continue
    r = enclosed_analysis(X, mols, wi, L)
    name = os.path.basename(fn)[:44]
    print(f"{name:<46}" + ("      no enclosed region" if r is None else f"{r[0]:>8.0f}{r[1]:>12d}{r[2]:>16.2f}"))
