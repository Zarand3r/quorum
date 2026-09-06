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


def _mol_centroids(X, mols, L):
    """Per-molecule centroids computed AFTER unwrapping each molecule about its own first bead.

    The mean of WRAPPED coordinates is meaningless for a molecule straddling the periodic boundary: it
    lands in the middle of the box, nowhere near either fragment. On one N=80/L=46 endpoint state, 13 of
    80 molecules straddled, and a centroid<8.0 prefilter built on those means rejected 35 bead-contacts
    that are real (bead separations 0.88-1.12 at centroid distances 8.1-20.2). The driver's own
    _cluster_labels goes bead to bead and is immune, which is why it read one cluster of 80 where the
    analysis path read 27.
    """
    out = np.empty((len(mols), X.shape[1]))
    for i, m in enumerate(mols):
        p = X[m]
        ref = p[0]
        out[i] = (ref + (p - ref) - L * np.round((p - ref) / L)).mean(axis=0)
    return out


def _interior_mask(X, mols, L, cell=0.5, bead=1.0):
    """Boolean grid of free cells the aggregate cuts off from the box boundary.

    The aggregate is shifted to the box centre by its RAW centroid first: the plant centres structures
    on the origin, and wrapping with `% L` alone splits them across the edge so no closed curve forms --
    which made an earlier detector report "no enclosed region" for a planted ring.
    """
    lip = np.concatenate(mols)
    # UNWRAP BY CONNECTIVITY before centring. Centring on the raw wrapped centroid is not enough: for an
    # aggregate straddling the boundary that centroid is itself meaningless, and the same planted ring
    # scored n_enclosed 1 centred and 0 when moved onto the edge. Every nves=0 in this project predating
    # this fix could therefore hide a vesicle that merely sat on a boundary.
    P = unwrap_cluster(X, mols, L)
    if P is None:
        P = np.asarray(X[lip])                      # disconnected: nothing to unwrap along
    P = P - P.mean(axis=0) + L / 2.0
    n = max(8, int(L / cell))
    occ = np.zeros((n, n), bool)
    gi = (P / L * n).astype(int) % n
    # `bead` is the DILATION DIAMETER, and it is a calibrated quantity, not the physical bead size.
    # It must be wide enough to seal the gaps between neighbouring beads along a leaflet and narrow
    # enough to leave a genuine opening open. Measured window, on synthetic rings of R = 43 in L = 120
    # (columns are the in-leaflet bead spacing; a correct detector reads 1 for a ring and 0 for a gap):
    #
    #     bead   1.0s 1.4s 1.8s 2.2s | 4s gap  6s gap
    #     1.0      1    0    0    0  |   0       0      <- leaks on anything but a dense ring
    #     2.0      1    1    1    0  |   0       0
    #     3.0      1    1    1    1  |   0       0
    #     3.5      1    1    1    1  |   1       0      <- seals a real opening into a false lumen
    #
    # 1.0 is kept because the real membranes here sit at a MEASURED median nearest-neighbour distance
    # of 0.95 sigma, well inside where 1.0 works, and raising it would change every historical lumen_c.
    #
    # What the sweep does NOT license is reading the returned COUNT as exact. On the quench tangles the
    # count runs 5/4/4/3 and 8/6/6/4 across bead 1.0/1.5/2.0/3.0 -- thin necks seal and unseal. The
    # 1-versus-many CALL is stable across that whole range and is the only thing to report; the count
    # is an ordinal, not a measurement.
    #
    # Stamp each bead as a DISC, not a single cell. `_lumen.py` marked one cell per
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
    return free & ~seen


def lumen_cells(X, mols, L, cell=0.5, min_cells=40, bead=1.0):
    """Largest contiguous interior pocket, in grid cells. 0 if below `min_cells`."""
    _, sizes = n_enclosed(X, mols, L, cell=cell, bead=bead, min_cells=min_cells)
    return sizes[0] if sizes else 0


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

def n_enclosed(X, mols, L, cell=0.5, bead=1.0, min_cells=40):
    """How many SEPARATE regions does the aggregate enclose?

    A vesicle encloses exactly one. A finite branched tangle encloses several, and passes the
    percolation test for the trivial reason that it sits inside a box larger than itself. Percolation
    alone cannot tell the two apart; this can. The flood-fill in lumen_cells() already finds every
    interior component -- it just returned the largest and discarded the rest.

    Returns (count, sizes) with sizes sorted descending.
    """
    interior = _interior_mask(X, mols, L, cell, bead)
    n = interior.shape[0]
    sizes, vis = [], np.zeros_like(interior)
    for i in range(n):
        for j in range(n):
            if not interior[i, j] or vis[i, j]:
                continue
            stack, count = [(i, j)], 0
            vis[i, j] = True
            while stack:
                a, b = stack.pop()
                count += 1
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    p, q = a + da, b + db
                    if 0 <= p < n and 0 <= q < n and interior[p, q] and not vis[p, q]:
                        vis[p, q] = True
                        stack.append((p, q))
            if count >= min_cells:
                sizes.append(count)
    sizes.sort(reverse=True)
    return len(sizes), sizes


def vesicle_call(X, mols, L, cell=0.5):
    """Is this aggregate a VESICLE? Returns (bool, reason).

    Two gates, both needed, because each has passed something the other rejects.

    1. n_enclosed == 1 at every dilation in 1.0-3.0. The count is dilation-sensitive, so only a call
       stable across the knob is reportable. This alone rejected a 69-cell pocket that read 1 at bead
       1.0 and 0 above it.

    2. The lumen must be the right SIZE for the lipid count. A closed vesicle of n lipids has contour n,
       hence R = n/2pi and interior pi*R^2. A branched network that happens to enclose one incidental
       pocket passes gate 1 and fails here. Calibration, all verified against renders:

           planted vesicle N=120          ratio 0.876   vesicle
           planted ring    N=300          ratio 0.882   vesicle
           implicit arc    N=80, closed   ratio 0.295   vesicle (irregular, so well under 1)
           emergent N=160 branched net    ratio 0.028   NOT a vesicle

       The threshold is 0.10: three times below the weakest true vesicle and three and a half times
       above the branched network, inside a tenfold gap.

    Gate 2 exists because the pre-registered emergence criterion had only gate 1, and a 160-lipid
    branched network passed it. The render caught that, not the metric.
    """
    counts = [n_enclosed(X, mols, L, cell=cell, bead=b)[0] for b in (1.0, 1.5, 2.0, 3.0)]
    if not all(c == 1 for c in counts):
        return False, f"n_enclosed unstable across dilation: {counts}"
    lumen = n_enclosed(X, mols, L, cell=cell)[1][0]
    # SIZE THE EXPECTED LUMEN FROM THE ENCLOSING CLUSTER, NOT THE WHOLE SYSTEM.
    #
    # This was `n = len(mols)`, which is the total lipid count. A vesicle made of a SUBSET of the
    # lipids -- with the rest still dispersed or hanging off as appendages -- was then compared against
    # the lumen a vesicle of ALL of them would have, and penalised by (n_cluster / n_total)**2.
    #
    # The project's own emergent 2-D vesicle is the case in point. docs/RESULTS.md records it at step
    # 360000 as "largest 116, n_enclosed 1, lumen 2145, ratio 0.501" -- and 0.501 is reproduced only by
    # normalising with the CLUSTER (116). With len(mols) = 160 the same state reads 0.263. Both clear
    # the 0.10 threshold, so no verdict changes here, but the two numbers differ by 1.9x and the
    # analysis in RESULTS.md and the gate in this file were computing different quantities under the
    # same name.
    #
    # This does NOT loosen the gate against the failure it exists to catch: a branched network spans
    # essentially all the lipids, so cluster == system and its ratio is unchanged (sd313: 0.020 either
    # way, still rejected).
    n = largest_lipid_cluster(X, mols, L)
    expected = np.pi * (n / (2.0 * np.pi)) ** 2 / (cell * cell)
    ratio = lumen / expected
    if ratio < 0.10:
        return False, (f"lumen {lumen} is {ratio:.3f} of the {expected:.0f} expected for the "
                       f"{n}-lipid enclosing cluster")
    return True, (f"lumen {lumen}, {ratio:.3f} of expected for the {n}-lipid cluster "
                  f"({n}/{len(mols)} of the system), n_enclosed stable at 1")


def largest_lipid_cluster(X, mols, L, cut=1.4) -> int:
    """Lipids in the largest connected aggregate.

    Matches the `largest` column of the emergence trajectory tables in docs/RESULTS.md, which is what
    the recorded lumen ratios were normalised by. A lipid belongs to a cluster if ANY of its beads is
    within `cut` of any bead of that cluster.
    """
    beads = np.asarray(mols)
    flat = beads.ravel()
    P = np.asarray(X)[flat]
    nb = beads.shape[1]
    m = len(P)
    lab = -np.ones(m, dtype=np.int64)
    best = 0
    cur = 0
    for start in range(m):
        if lab[start] >= 0:
            continue
        stack, lab[start] = [start], cur
        size = 0
        while stack:
            i = stack.pop()
            size += 1
            d = P - P[i]
            d -= L * np.round(d / L)
            near = np.where((np.einsum("ij,ij->i", d, d) < cut * cut) & (lab < 0))[0]
            lab[near] = cur
            stack.extend(near.tolist())
        best = max(best, size)
        cur += 1
    return int(round(best / nb))


def shell_split(X, mols, L, cell=0.5, reach=5.0):
    """Split an aggregate into the lipids that line its lumen (the SHELL) and the rest (APPENDAGES).

    Returns (n_shell, n_appendage, lumen_cells).

    Why this exists: the raw lumen ratio divides by an expectation built from EVERY lipid in the
    cluster, so material hanging off the vesicle inflates the denominator and understates how good the
    shell is. The first emergent vesicle reads 0.269-0.285 raw; ~59 of its 160 lipids line no lumen, and
    the shell alone reads 0.662-0.714 against 0.876 for a planted vesicle.

    `reach` is CALIBRATED, not guessed: a bilayer has two leaflets and only the inner one touches the
    lumen, so the reach must span the membrane. Measured on a planted N=120 vesicle, which has no
    appendages and must therefore return (120, 0):

        reach 2.5 -> 98 shell, 22 appendage   (finds only the inner leaflet)
        reach 4.0 -> 119 shell,  1 appendage
        reach 5.0 -> 120 shell,  0 appendage   <- chosen, and corrected ratio == raw ratio there
        reach 6.0 -> 120 shell,  0 appendage

    Only the LARGEST interior component counts. Using every interior cell folds in unrelated pockets:
    it reported lumen 2605 where n_enclosed gives 2320 for the same state.
    """
    interior = _interior_mask(X, mols, L, cell=cell)
    n = interior.shape[0]
    vis = np.zeros_like(interior)
    best = None
    for a in range(n):
        for b in range(n):
            if not interior[a, b] or vis[a, b]:
                continue
            stack, comp = [(a, b)], []
            vis[a, b] = True
            while stack:
                p, q = stack.pop()
                comp.append((p, q))
                for dp, dq in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    r, t = p + dp, q + dq
                    if 0 <= r < n and 0 <= t < n and interior[r, t] and not vis[r, t]:
                        vis[r, t] = True
                        stack.append((r, t))
            if best is None or len(comp) > len(best):
                best = comp
    if not best:
        return 0, len(mols), 0
    pts = np.array(best, dtype=float) * (L / n)
    lip = np.concatenate(mols)
    Xs = X - X[lip].mean(axis=0) + L / 2.0
    shell = 0
    for m in mols:
        d = Xs[m][:, None, :] - pts[None, :, :]
        d -= L * np.round(d / L)
        if np.linalg.norm(d, axis=2).min() < reach:
            shell += 1
    return shell, len(mols) - shell, len(best)


def lumen_water_density(X, mols, wi, L, cell=0.5, bead=1.0):
    """Water number density inside the enclosed region, in units of the BULK density.

    The `lumenW` column in the driver is not this. That one is radial: it counts waters within
    R_mid - lip_len of the centroid of the whole aggregate, which is only meaningful for a single
    roughly-round vesicle sitting at that centroid. For a small vesicle beside a branched network it
    measures water near the NETWORK's centre and returns 0, which reads as "dry lumen" when nothing
    about the vesicle was measured at all.

    This version counts waters in the same interior cells that n_enclosed flood-fills, so it is defined
    for any cluster anywhere in the box. A real lumen holds solvent at roughly bulk density; a hole in
    a tangle that the dilation happened to seal holds little or none.

    Returns nan for implicit solvent (no water beads) rather than 0 -- reporting 0 would be the same
    silent-zero this project has been caught by before.
    """
    if len(wi) == 0:
        return float("nan")
    interior = _interior_mask(X, mols, L, cell, bead)
    n_cells = int(interior.sum())
    if n_cells == 0:
        return float("nan")
    n = interior.shape[0]
    lip = np.concatenate(mols)
    # The SAME shift _interior_mask applies, or the water grid and the interior grid disagree.
    shift = -X[lip].mean(axis=0) + L / 2.0
    gw = ((np.asarray(X[wi]) + shift) / L * n).astype(int) % n
    n_in = int(interior[gw[:, 0], gw[:, 1]].sum())
    step = L / n
    rho_in = n_in / (n_cells * step * step)
    rho_bulk = len(wi) / (L * L)
    return float(rho_in / rho_bulk)


def count_vesicles(X, mols, L, cut=1.4, min_lipids=20, wi=None):
    """How many DISTINCT clusters are vesicles by the full gate.

    vesicle_call was only ever applied to the largest cluster, which made a small vesicle beside a
    bigger network invisible. Since closure is encounter-limited, short ribbons close soonest, so the
    small ones are exactly the case that was being missed.

    Cheap first: a cluster is only put through the four-dilation gate if it encloses anything at all
    at the default dilation. Most clusters fail that immediately.

    With `wi` (water indices) it returns (count, [lumen_water_density per passing cluster]) instead of
    a bare count. Kept OPTIONAL and additive so every existing caller and every historical number is
    untouched: the geometric lumen ratio turned out to be a weak discriminator -- a planted vesicle
    scored 0.118 against an emergent marginal case at 0.151 -- while water occupancy separated cleanly.
    """
    from collections import deque

    cen = _mol_centroids(X, mols, L)
    d = cen[:, None, :] - cen[None, :, :]
    d -= L * np.round(d / L)
    near = np.linalg.norm(d, axis=2) < 8.0
    seen = np.zeros(len(mols), bool)
    total = 0
    waters = []
    for start in range(len(mols)):
        if seen[start]:
            continue
        comp, q = [start], deque([start])
        seen[start] = True
        while q:
            i = q.popleft()
            for j in np.flatnonzero(near[i]):
                if seen[j]:
                    continue
                dd = X[mols[i]][:, None, :] - X[mols[j]][None, :, :]
                dd -= L * np.round(dd / L)
                if np.linalg.norm(dd, axis=2).min() < cut:
                    seen[j] = True
                    comp.append(j)
                    q.append(j)
        if len(comp) < min_lipids:
            continue
        sub = [mols[i] for i in comp]
        if n_enclosed(X, sub, L)[0] != 1:
            continue
        if vesicle_call(X, sub, L)[0]:
            total += 1
            waters.append(lumen_water_density(X, sub, wi, L) if wi is not None else float("nan"))
    return (total, waters) if wi is not None else total


def unwrap_cluster(X, mols, L, cut=1.4):
    """Unwrap a periodic cluster by BFS along contacts, accumulating offsets. None if disconnected.

    Minimum-image centring is NOT a substitute. It failed here even for clusters spanning only ~0.36 of
    the box: a 3-D aggregate scored 1.000 : 0.036 : 0.028 on its gyration tensor -- an extreme rod --
    and unwrapping by connectivity gave 1.000 : 0.859 : 0.642, an ordinary isotropic blob. Two of five
    shape verdicts flipped. The same failure mode broke the enclosure detector earlier in this project.
    """
    from collections import deque

    beads = np.concatenate(mols)
    P = X[beads]
    d = P[:, None, :] - P[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    pos = {0: P[0].copy()}
    q = deque([0])
    while q:
        i = q.popleft()
        for j in np.flatnonzero(adj[i]):
            if j in pos:
                continue
            off = P[j] - P[i]
            off -= L * np.round(off / L)
            pos[j] = pos[i] + off
            q.append(j)
    if len(pos) < 0.9 * len(P):
        return None
    return np.array([pos[k] for k in sorted(pos)])


def shape_anisotropy(X, mols, L, cut=1.4):
    """Gyration-tensor eigenvalues, normalised, largest first. None if the cluster is disconnected.

    Discriminates aggregate morphology where a 3-D slab render cannot:
        micelle / sphere      1 : ~1  : ~1
        flat bilayer patch    1 : ~1  : << 1
        rod / cylinder        1 : << 1 : << 1
    """
    U = unwrap_cluster(X, mols, L, cut=cut)
    if U is None:
        return None
    Q = U - U.mean(axis=0)
    w = np.sort(np.linalg.eigvalsh((Q.T @ Q) / len(Q)))[::-1]
    return w / w[0]


def largest_cluster_fraction(P, L, cut=1.4):
    """Largest connected component of a point set, as a fraction of all points.

    This is the measurement that retired the project's standing known-void ("3-D explicit solvent is
    fragmented droplets"): applied to the water beads it reads 1.000 at chi_WW = 0.50 and 0.202-0.252 at
    chi_WW = 1.00, against a recorded 0.27-0.48. It lived in a scratch script with no tests while that
    conclusion rested on it, which is why it is here now.

    A grid of cells of side >= `cut` bounds the neighbour search, so a point's contacts can only lie in
    the 27 cells around it. Distances use the minimum image, so a cluster wrapping the periodic boundary
    stays one cluster.
    """
    from collections import deque

    P = np.asarray(P) % L
    n = len(P)
    if n == 0:
        return 0, 0.0
    g = max(4, int(L / cut))
    cs = L / g
    gi = (P / cs).astype(int) % g
    cells = {}
    for i, key in enumerate(map(tuple, gi)):
        cells.setdefault(key, []).append(i)
    seen = np.zeros(n, bool)
    best = 0
    for start in range(n):
        if seen[start]:
            continue
        q = deque([start])
        seen[start] = True
        size = 0
        while q:
            i = q.popleft()
            size += 1
            a, b, c = gi[i]
            for da in (-1, 0, 1):
                for db in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        for j in cells.get(((a + da) % g, (b + db) % g, (c + dc) % g), ()):
                            if seen[j]:
                                continue
                            d = P[i] - P[j]
                            d -= L * np.round(d / L)
                            if d @ d < cut * cut:
                                seen[j] = True
                                q.append(j)
        best = max(best, size)
    return best, best / n
