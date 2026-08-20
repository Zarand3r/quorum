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
