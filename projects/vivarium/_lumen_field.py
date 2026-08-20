"""Lumen detector for `field.py` states, using the algorithm validated in `_lumen.py`.

`_lumen.py` established what a lumen detector must do, on planted DPD structures: take the LARGEST
CONTIGUOUS interior pocket rather than the sum of enclosed cells, and impose a minimum area, because a
naive sum "fires on everything -- 29 on a field of compact micelles, 19 on a branched worm network...
it counts grid gaps BETWEEN aggregates, and pockets at branch points, as if they were interiors."

A previous tick of mine overwrote that file with exactly the naive version it warns about, and reported
21 sigma^2 of "enclosed area" for an emergent seed. This restores the validated logic and recalibrates
its threshold for this project's units, against our own planted structures.

Calibration requirement, from `_lumen.py`: planted vesicle high, planted micelle ~0, branched worms ~0.
"""

from __future__ import annotations

import numpy as np


def lumen_cells(X, mols, L, cell=0.5, min_cells=40, bead=1.0):
    """Largest contiguous interior pocket, in grid cells. 0 if below `min_cells`.

    The aggregate is shifted to the box centre by its RAW centroid first: the plant centres structures
    on the origin, and wrapping with `% L` alone splits them across the edge so no closed curve forms --
    which made an earlier detector report "no enclosed region" for a planted ring.
    """
    lip = np.concatenate(mols)
    X = X - X[lip].mean(axis=0) + L / 2.0
    n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (np.asarray(X[lip]) / L * n).astype(int) % n
    # Stamp each bead as a DISC of its own radius, not a single cell. `_lumen.py` marked one cell per
    # bead, which works at DPD's density (rho = 4) but not here: at cell = 0.5 with beads about 1 sigma
    # apart the membrane becomes a dotted line and the flood-fill leaks straight through it, so a planted
    # ring scored 0 on its own positive control.
    r = max(1, int(round(bead / (2 * cell))))
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                occ[(gi[:, 0] + dx) % n, (gi[:, 1] + dy) % n] = True
    free = ~occ
    seen = np.zeros_like(free)
    stack = [(i, j) for i in range(n) for j in (0, n - 1) if free[i, j]]
    stack += [(i, j) for j in range(n) for i in (0, n - 1) if free[i, j]]
    for a, b in stack:
        seen[a, b] = True
    while stack:
        a, b = stack.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p, q = a + da, b + db
            if 0 <= p < n and 0 <= q < n and free[p, q] and not seen[p, q]:
                seen[p, q] = True
                stack.append((p, q))
    interior = free & ~seen
    best, visited = 0, np.zeros_like(interior)
    for i in range(n):
        for j in range(n):
            if interior[i, j] and not visited[i, j]:
                st, c = [(i, j)], 0
                visited[i, j] = True
                while st:
                    a, b = st.pop()
                    c += 1
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        p, q = a + da, b + db
                        if 0 <= p < n and 0 <= q < n and interior[p, q] and not visited[p, q]:
                            visited[p, q] = True
                            st.append((p, q))
                best = max(best, c)
    return best if best >= min_cells else 0


def lumen_headed(X, mols, L, cell=0.5, bead=1.0, min_cells=40):
    """Fraction of lipids lining the enclosure whose HEAD faces it. The vesicle test.

    `lumen_cells` measures only geometry, so it cannot tell a membrane-bounded lumen from a packing gap
    in a crowded aggregate -- and the obvious null (randomizing lipid orientations in place) does not
    discriminate either, because rotating a lipid about its own centre barely moves its beads: the planted
    vesicle scored 4014 against a 4049 null.

    What separates the two is whether the lining lipids point INTO the pocket. A bilayer lumen is faced by
    heads; a gap between jammed aggregates is faced by whatever happens to abut it, i.e. about half.
    Returns NaN when there is no enclosure above threshold.
    """
    lip = np.concatenate(mols)
    Xs = X - X[lip].mean(axis=0) + L / 2.0
    n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (np.asarray(Xs[lip]) / L * n).astype(int) % n
    r = max(1, int(round(bead / (2 * cell))))
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                occ[(gi[:, 0] + dx) % n, (gi[:, 1] + dy) % n] = True
    free = ~occ
    seen = np.zeros_like(free)
    st = [(i, j) for i in range(n) for j in (0, n - 1) if free[i, j]]
    st += [(i, j) for j in range(n) for i in (0, n - 1) if free[i, j]]
    for a, b in st:
        seen[a, b] = True
    while st:
        a, b = st.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p, q = a + da, b + db
            if 0 <= p < n and 0 <= q < n and free[p, q] and not seen[p, q]:
                seen[p, q] = True
                st.append((p, q))
    interior = free & ~seen
    best, vis = None, np.zeros_like(interior)
    for i in range(n):
        for j in range(n):
            if interior[i, j] and not vis[i, j]:
                stk, cells = [(i, j)], []
                vis[i, j] = True
                while stk:
                    a, b = stk.pop()
                    cells.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        p, q = a + da, b + db
                        if 0 <= p < n and 0 <= q < n and interior[p, q] and not vis[p, q]:
                            vis[p, q] = True
                            stk.append((p, q))
                if best is None or len(cells) > len(best):
                    best = cells
    if best is None or len(best) < min_cells:
        return float("nan")
    centre = np.array([np.mean([c[0] for c in best]), np.mean([c[1] for c in best])]) * cell
    faced = tot = 0
    for m in mols:
        h = Xs[m[0]]
        t = Xs[m[1:]].mean(axis=0)
        mid = 0.5 * (h + t)
        if np.linalg.norm(mid - centre) > 0.5 * L:
            continue
        dh = np.linalg.norm(h - centre)
        dt = np.linalg.norm(t - centre)
        # Only the INNER leaflet. Including both leaflets forces ~0.5 by construction, since a bilayer's
        # outer leaflet faces away from the lumen -- which is why a planted vesicle first scored 0.60,
        # BELOW a packing gap's 0.69. The inner leaflet is the shell within one lipid length of the
        # lumen boundary.
        Rl = np.sqrt(len(best) * cell * cell / np.pi)
        if Rl <= min(dh, dt) < Rl + 3.5:
            tot += 1
            if dh < dt:
                faced += 1
    return faced / tot if tot else float("nan")


def lumen_head_enrichment(X, species, mols, L, cell=0.5, bead=1.0, min_cells=40, shell=1.6):
    """Head enrichment in the layer immediately lining the enclosure. THE vesicle test.

    A lumen is bounded by a bilayer, so the first layer outside it is HEADS. A packing gap between jammed
    aggregates is lined by whatever abuts it, i.e. the bulk head:tail ratio.

    Per BEAD, not per lipid: the two previous attempts assigned lipids to leaflets and both failed their
    positive control (a planted vesicle scored 0.54 against a jumble's 0.70), because a bilayer's outer
    leaflet faces away by construction and any shell wide enough to catch the inner leaflet also catches
    the outer one.

    Returns (head fraction in the lining shell) / (head fraction overall). ~1 = packing gap; > 1 = heads
    line the pocket, i.e. a membrane boundary. NaN if there is no enclosure above threshold.
    """
    from _lumen_field import lumen_cells as _lc
    lip = np.concatenate(mols)
    Xs = X - X[lip].mean(axis=0) + L / 2.0
    n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (np.asarray(Xs[lip]) / L * n).astype(int) % n
    r = max(1, int(round(bead / (2 * cell))))
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                occ[(gi[:, 0] + dx) % n, (gi[:, 1] + dy) % n] = True
    free = ~occ
    seen = np.zeros_like(free)
    st = [(i, j) for i in range(n) for j in (0, n - 1) if free[i, j]]
    st += [(i, j) for j in range(n) for i in (0, n - 1) if free[i, j]]
    for a, b in st:
        seen[a, b] = True
    while st:
        a, b = st.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p, q = a + da, b + db
            if 0 <= p < n and 0 <= q < n and free[p, q] and not seen[p, q]:
                seen[p, q] = True
                st.append((p, q))
    interior = free & ~seen
    best, vis = None, np.zeros_like(interior)
    for i in range(n):
        for j in range(n):
            if interior[i, j] and not vis[i, j]:
                stk, cells = [(i, j)], []
                vis[i, j] = True
                while stk:
                    a, b = stk.pop()
                    cells.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        p, q = a + da, b + db
                        if 0 <= p < n and 0 <= q < n and interior[p, q] and not vis[p, q]:
                            vis[p, q] = True
                            stk.append((p, q))
                if best is None or len(cells) > len(best):
                    best = cells
    if best is None or len(best) < min_cells:
        return float("nan")
    pts = np.array(best, dtype=float) * cell            # lumen cells in real units
    P = Xs[lip]
    is_head = np.isin(lip, np.concatenate([m[:1] for m in mols]))
    # distance from each lipid bead to the NEAREST lumen cell
    d = np.min(np.linalg.norm(P[:, None, :] - pts[None, :, :], axis=2), axis=1)
    inshell = d < shell
    if inshell.sum() < 10:
        return float("nan")
    f_shell = is_head[inshell].mean()
    f_all = is_head.mean()
    return float(f_shell / f_all)


def percolates(X, mols, L, cut=1.4):
    """Does the cluster connect to its own PERIODIC IMAGE?

    The only discriminator here that passes its control. A vesicle is a FINITE closed object; a sponge
    phase's "lumen" is a compartment between the arms of a network that wraps the box. Five geometric
    tests failed to separate them -- head-facing, head enrichment, orientation-randomisation, water
    content, span/L -- because the compartments genuinely are amphiphile-lined and water-filled. The
    difference is topological.

    Unwraps the cluster by breadth-first search, accumulating minimum-image displacements. If any bead is
    reached with two inconsistent unwrapped positions, the cluster wraps.
    """
    from collections import deque
    beads = np.concatenate(mols)
    P = X[beads]
    d = P[:, None, :] - P[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    pos = {0: np.zeros(P.shape[1])}
    q = deque([0])
    while q:
        i = q.popleft()
        for j in np.flatnonzero(adj[i]):
            off = P[j] - P[i]
            off -= L * np.round(off / L)
            new = pos[i] + off
            if j in pos:
                if np.linalg.norm(pos[j] - new) > 0.5 * L:
                    return True
            else:
                pos[j] = new
                q.append(j)
    return False
