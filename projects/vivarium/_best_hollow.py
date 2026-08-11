"""Find the single most vesicle-like EMERGENT aggregate anywhere in the saved data.

"Closest to a vesicle" should be decided by measurement, not by picking the render that looks best.
For every aggregate in every emergent state, this asks the two questions that define a vesicle and
reports the winner with its location so it can be rendered:

    does it enclose solvent the exterior cannot reach?   (sealed lumen, water-containing)
    is its shell a paired bilayer rather than a blob?    (paired fraction)

Enclosure is evaluated per aggregate on a local grid around that aggregate, not on a whole-box grid,
because a box-wide grid coarse enough to be cheap cannot resolve a lumen a few rc across.
"""

import sys

import numpy as np

from _pairing import _mic

RHO_BULK = 3.0      # DPD standard density, used to normalise lumen occupancy

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


def load(tag):
    """Load a DPD state. Older Vivarium-engine states use a different schema and are skipped."""
    z = np.load(f"{ST}/{tag}.npz")
    keys = set(z.keys())
    if not {"x", "species", "L"} <= keys:
        raise KeyError("not a DPD state")
    x, sp, L = z["x"], z["species"], float(z["L"])
    if "nb" in set(z.keys()):
        nb, nh, n = int(z["nb"]), int(z.get("nh", 1)), int(z["n_amph"])
        b0 = np.arange(n) * nb
    else:
        b0 = np.flatnonzero(sp == 1)
        nb, nh = int(np.median(np.diff(b0))), 1
    return x, sp, L, b0, nb, nh


def aggregates(x, L, b0, nb, cut=1.2):
    n = len(b0)
    beads = np.concatenate([b0 + t for t in range(nb)])
    owner = np.concatenate([np.arange(n) for _ in range(nb)])
    D = np.linalg.norm(_mic(x[beads], x[beads], L), axis=2)
    i, j = np.nonzero(D < cut)
    par = np.arange(n)

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for a, b in zip(owner[i], owner[j]):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    root = np.array([find(k) for k in range(n)])
    return [np.flatnonzero(root == r) for r in np.unique(root)]


def unwrap_cluster(x, L, sel_b0, nb, cut=1.2):
    """Unwrap a cluster through its own contact graph, and detect whether it PERCOLATES.

    Minimum-image unwrapping around one bead is wrong for anything wider than L/2, and the failure is
    not subtle: a box-spanning aggregate then has its molecules at similar distance from a centroid
    that lands in empty solvent, which reads as a low shell CV and a lumen filled to bulk density.
    The 180-molecule `sl_f18` aggregate scored as the best emergent vesicle candidate that way, and
    the render shows scattered material around the box edges.

    BFS along contacts, accumulating the periodic offset actually used on each hop. If any edge later
    disagrees with the accumulated positions by a box vector, the cluster connects to its own image:
    it percolates, it is not finite, and 'inside' is undefined for it.
    """
    m = len(sel_b0)
    com = np.stack([x[sel_b0 + t] for t in range(nb)]).mean(axis=0)
    D = _mic(com, com, L)
    dist = np.linalg.norm(D, axis=2)
    adj = dist < (cut + 1.5)
    np.fill_diagonal(adj, False)

    pos = np.full((m, x.shape[1]), np.nan)
    pos[0] = com[0]
    order = [0]
    seen = {0}
    while order:
        i = order.pop()
        for j in np.flatnonzero(adj[i]):
            if j in seen:
                continue
            seen.add(j)
            pos[j] = pos[i] + D[i, j] * -1.0 if False else pos[i] - D[i, j]
            order.append(int(j))
    if len(seen) < m:                       # disconnected at this cutoff; treat as finite
        pos[np.isnan(pos[:, 0])] = com[np.isnan(pos[:, 0])]
    ii, jj = np.nonzero(np.triu(adj, 1))
    if len(ii):
        disc = np.linalg.norm((pos[ii] - pos[jj]) - (-D[ii, jj]), axis=1)
        percolates = bool((disc > 0.5 * L).any())
    else:
        percolates = False
    return pos, percolates


def lumen_filling(x, sp, L, mols, b0, nb):
    """Is there solvent INSIDE the shell, at bulk density? A watertightness-free lumen measure.

    Grid flood fill proved too fragile to trust. It requires the shell to be watertight at the grid
    resolution, so the planted R=9 vesicle -- which has lost 30% of its amphiphiles and has thin
    spots -- read zero, while the deformed R=7.5 sealed off 461 cells, several times more than its
    lumen can physically hold. Four successive repairs (dilation, contiguity, per-pocket water,
    local vs whole-box grids) each fixed one control and broke another.

    This asks the question directly instead. Take the aggregate's centroid, measure how far its
    molecules sit from it, and count the water actually present well inside that shell radius,
    against how much bulk solvent that region would hold:

        filling = N_water(r < f*R_shell) / (rho * V(f*R_shell))

    A vesicle holds solvent at roughly bulk density inside, so filling -> 1. A filled micelle or a
    collapsed blob has amphiphile there instead, so filling -> 0. Nothing depends on whether the
    shell has a hole, which is the property that made flood fill unusable.

    This measure alone cannot tell a vesicle from a flat sheet -- a disc's centroid also has solvent
    'inside' its mean radius -- so it is only meaningful in conjunction with shell_cv, which
    separates a shell (CV ~ 0.1) from a disc (CV ~ 0.35 analytically).
    """
    dim = x.shape[1]
    beads = np.concatenate([b0[mols] + t for t in range(nb)])
    P = x[beads]
    ref = P[0]
    rel = P - ref
    rel -= L * np.round(rel / L)
    centre = (ref + rel.mean(axis=0)) % L

    com = np.stack([x[b0[mols] + t] for t in range(nb)]).mean(axis=0)
    d = com - centre
    d -= L * np.round(d / L)
    R = np.linalg.norm(d, axis=1)
    R_shell = float(R.mean())
    if R_shell < 1.0:
        return 0.0, centre, R_shell

    f = 0.55                                   # comfortably inside the inner leaflet
    rin = f * R_shell
    w = x[sp == 0] - centre
    w -= L * np.round(w / L)
    n_in = int((np.linalg.norm(w, axis=1) < rin).sum())
    vol = (4.0 / 3.0 * np.pi * rin ** 3) if dim == 3 else (np.pi * rin ** 2)
    expected = RHO_BULK * vol
    return float(n_in / max(expected, 1e-9)), centre, R_shell


def shell_quality(x, L, sel_b0, nb, nh, centre):
    """Is the enclosing material a SHELL, or a sprawling network that happens to trap a pocket?

    A sealed lumen alone does not mean a vesicle. The 88-molecule 2-D aggregate scores a sealed,
    water-containing lumen, but the render shows the pocket is a gap BETWEEN three or four ribbon
    arms -- bounded by the sides of separate branches, not by the inside of one closed membrane. That
    is the same failure that retired the old `enclosed` metric, which scored 19 on branch-point
    pockets; requiring the pocket to contain water fixed the tail-core false positive but not this one.

    Locally the two are indistinguishable: a ribbon face bounding a gap is head-lined just as a
    vesicle's inner leaflet is. The difference is global. In a vesicle essentially EVERY molecule of
    the aggregate sits in the shell at a similar radius from the lumen. In a branched network the
    pocket is a small feature of a much larger object, so molecular distance from the lumen centroid
    is spread over a wide range.

    Returns:
      shell_cv    std/mean of molecular distance from the lumen centre. Low for a shell.
      inward      fraction of INNER-half molecules whose head points toward the lumen, which is what
                  an inner leaflet means.
    """
    com = np.stack([x[sel_b0 + t] for t in range(nb)]).mean(axis=0)
    rel = com - centre
    rel -= L * np.round(rel / L)
    r = np.linalg.norm(rel, axis=1)
    cv = float(r.std() / max(r.mean(), 1e-9))

    head = np.stack([x[sel_b0 + t] for t in range(nh)]).mean(axis=0)
    tail = np.stack([x[sel_b0 + t] for t in range(nh, nb)]).mean(axis=0)
    u = head - tail
    u -= L * np.round(u / L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    rhat = rel / np.maximum(r, 1e-9)[:, None]
    # The molecules LINING the lumen, not the inner half by count. A vesicle is leaflet-asymmetric
    # (R=9 is 616 outer against 121 inner), so a median split lands inside the OUTER leaflet and
    # reports ~0.43 inward on a perfectly good inner leaflet.
    inner = r < np.percentile(r, 20)
    inward = float((np.einsum("ic,ic->i", u[inner], -rhat[inner]) > 0).mean()) if inner.any() else 0.0
    return cv, inward


def paired_of(x, L, sel_b0, nb, nh, rcut=1.5):
    head = np.stack([x[sel_b0 + t] for t in range(nh)]).mean(axis=0)
    tail = np.stack([x[sel_b0 + t] for t in range(nh, nb)]).mean(axis=0)
    tip = x[sel_b0 + (nb - 1)]
    u = head - tail
    u -= L * np.round(u / L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    D = np.linalg.norm(_mic(tip, tip, L), axis=2)
    np.fill_diagonal(D, np.inf)
    H = np.linalg.norm(_mic(head, head, L), axis=2)
    return float(((D < rcut) & ((u @ u.T) < -0.5) & (H > D)).any(axis=1).mean())


if __name__ == "__main__":
    print(f"{'state':32s}{'aggs':>5}{'big':>6}{'in agg':>8}{'paired':>8}{'shellCV':>9}"
          f"{'inward':>8}{'filling':>9}{'R':>7}{'score':>8}   verdict")
    for tag in sys.argv[1:]:
        try:
            x, sp, L, b0, nb, nh = load(tag)
        except (FileNotFoundError, KeyError, ValueError):
            continue
        # nb is inferred from head spacing on legacy states and can come out degenerate
        if len(b0) < 8 or x.shape[1] not in (2, 3) or len(b0) > 3000 or nb < 2 or nb <= nh:
            continue
        try:
            aggs = [a for a in aggregates(x, L, b0, nb) if len(a) >= 8]
            best = None
            for a in aggs:
                _, perc = unwrap_cluster(x, L, b0[a], nb)
                if perc:
                    continue          # box-spanning: finite-vesicle geometry is undefined
                fill, ctr, R_shell = lumen_filling(x, sp, L, a, b0, nb)
                cv, inw = shell_quality(x, L, b0[a], nb, nh, ctr)
                score = fill * max(0.0, 1.0 - cv / 0.45) * inw
                if best is None or score > best[0]:
                    best = (score, len(a), paired_of(x, L, b0[a], nb, nh), cv, inw, fill, R_shell)
            big = max((len(a) for a in aggs), default=0)
        except (ValueError, IndexError):
            continue
        if best is None:
            continue
        sc, na, pa, cv, inw, fill, rs = best
        verdict = ("VESICLE-LIKE" if cv < 0.25 and inw > 0.6 and fill > 0.5 else
                   "hollow-ish" if fill > 0.3 and cv < 0.35 else
                   "shell, no lumen" if cv < 0.25 else "not vesicle-like")
        print(f"{tag:32s}{len(aggs):>5}{big:>6}{na:>8}{pa:>8.2f}{cv:>9.3f}{inw:>8.2f}"
              f"{fill:>9.2f}{rs:>7.1f}{sc:>8.3f}   {verdict}")
