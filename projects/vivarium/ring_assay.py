"""Ring topology from RADIAL PROFILES, with mandatory calibration gates.

Five of eight retractions in this project were measurement artefacts, four of them from one
centroid-based lumen detector. So this module refuses to report a verdict until its own gates pass,
and the gates include the adversarial case that produced the last failure.

WHAT IS MEASURED
    Radial densities about the aggregate centre: rho_H(r), rho_T(r), rho_W(r). A hollow bilayer ring
    must show, reading outward:

        lumen water  ->  inner heads  ->  tail core  ->  outer heads  ->  bulk water

    That five-band signature is the definition used here. It is structural and local, so it does not
    depend on any scalar order parameter -- `align` reads 0.000 on a correctly planted ring, and a
    centroid-based lumen radius reads positive on a filled micelle.

THE FOUR GATES (see `self_test`)
    positive     a planted hollow ring            -> must be called HOLLOW
    negative     a planted filled micelle          -> must NOT be called HOLLOW
    adversarial  two separated aggregates whose centroid lies between them, so the inter-fragment
                 solvent sits exactly where a lumen would be -> must NOT be called HOLLOW
    spanning     a membrane that percolates the box and therefore has no centre -> must NOT be called
                 HOLLOW. Added after a spanning branched network was called HOLLOW when the render
                 showed a pore; the other three gates all use compact aggregates, so none of them
                 tested what a centroid-radial profile does to a structure with no centre.

The adversarial gate is the one that matters: it is the exact configuration that produced four false
HOLLOW verdicts at N = 65, 80, 100 and 120.
"""

from __future__ import annotations

import numpy as np

from polar_pack import BOND_REST


def _mic(d, L):
    return d - L * np.round(d / L)


def largest_cluster_mols(e, cut=1.4):
    """Indices of molecules in the largest connected aggregate, linked BEAD-to-bead.

    Molecule-centre connectivity is wrong for a bilayer: the two leaflets of a planted ring have
    centres ~2.0 apart (each centre sits a molecule-length inside its own head), so a 1.6 cutoff
    splits a perfectly intact bilayer into two clusters and reports frac = 0.66. The leaflets touch
    at their TAILS, not their centres, so connectivity must be evaluated on beads. This was caught by
    the positive gate below.
    """
    from collections import deque
    mol = e._mol
    P = e.X[:, :e.pd]
    nb = mol.shape[1]
    beads = mol.ravel()
    owner = np.repeat(np.arange(len(mol)), nb)
    d = _mic(P[beads][:, None, :] - P[beads][None, :, :], e.L)
    close = np.linalg.norm(d, axis=2) < cut
    n = len(mol)
    adj = np.zeros((n, n), bool)
    bi, bj = np.nonzero(close)
    adj[owner[bi], owner[bj]] = True
    np.fill_diagonal(adj, False)
    lab = -np.ones(n, int)
    k = 0
    for s in range(n):
        if lab[s] >= 0:
            continue
        q = deque([s])
        lab[s] = k
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = k
                    q.append(j)
        k += 1
    sizes = np.bincount(lab)
    return np.flatnonzero(lab == sizes.argmax())


def radial_profiles(e, sel=None, nbins=40, rmax=None):
    """rho_H(r), rho_T(r), rho_W(r) about the centre of the selected molecules.

    Densities are per unit area (the 2-D shell), so a flat profile means uniform, not merely equal
    counts. Water is measured over the WHOLE box, since the lumen and the bulk are both water.
    """
    mol = e._mol if sel is None else e._mol[sel]
    P = e.X[:, :e.pd]
    cen = P[mol].mean(axis=1).mean(axis=0)
    rmax = rmax or (0.5 * e.L)

    def prof(idx):
        d = _mic(P[idx] - cen, e.L)
        r = np.linalg.norm(d, axis=1)
        h, edges = np.histogram(r, bins=nbins, range=(0.0, rmax))
        area = np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)
        return h / area

    rr = np.linspace(0, rmax, nbins + 1)
    rr = 0.5 * (rr[1:] + rr[:-1])
    return rr, prof(mol[:, 0]), prof(mol[:, 1:].ravel()), prof(e._wi), cen


def classify(e, sel=None, min_frac=0.90, lumen_min=3.0):
    """Return (verdict, detail). HOLLOW requires the full five-band radial signature."""
    big = largest_cluster_mols(e)
    frac = len(big) / len(e._mol)
    if frac < min_frac:
        return "fragmented", dict(frac=frac)

    # SPANNING CHECK, before any radial reasoning. A centroid-radial profile assumes a COMPACT
    # aggregate with an inside and an outside. A network that percolates the periodic box has neither,
    # and its pores sit exactly where a lumen would be -- which produced a HOLLOW verdict on an
    # obvious percolating network (the fifth false positive from this assay). The fourth gate was
    # supposed to catch this but plants a CLEAN stripe, which classify already handled, so it never
    # exercised a network with pores.
    P = e.X[:, :e.pd]
    ext = P[e._mol[big]].reshape(-1, e.pd)
    span = np.array([_mic(ext[:, k][:, None] - ext[:, k][None, :], e.L).max() for k in range(e.pd)])
    if (span > 0.45 * e.L).any():
        return "spanning", dict(frac=frac, span=float(span.max() / e.L))

    rr, rh, rt, rw, cen = radial_profiles(e, sel=big)
    if rt.max() <= 0:
        return "no tails", dict(frac=frac)

    i_core = int(np.argmax(rt))
    r_core = rr[i_core]

    inner = slice(0, i_core)
    outer = slice(i_core + 1, len(rr))
    # Both slices can be EMPTY: `inner` when the tail peak is in the first radial bin, `outer` when it
    # is in the last. The second case crashed a 150000-step assembly run at 18750 steps with
    # "zero-size array to reduction operation maximum", losing the run. It fires whenever the aggregate
    # reaches rmax, which a dispersed or spanning configuration does routinely.
    have_inner_heads = bool(i_core > 0 and rh[inner].size and rh[inner].max() > 0.25 * rh.max())
    have_outer_heads = bool(rh[outer].size and rh[outer].max() > 0.25 * rh.max())

    # lumen: water inside the innermost head band, expressed against bulk water density
    bulk = np.median(rw[rw > 0]) if (rw > 0).any() else 0.0
    if have_inner_heads:
        i_head_in = int(np.argmax(rh[inner]))
        lumen_r = rr[max(i_head_in - 1, 0)]
        lumen_w = rw[:max(i_head_in - 1, 1)].max()
    else:
        lumen_r, lumen_w = 0.0, 0.0
    lumen_ratio = lumen_w / bulk if bulk > 0 else 0.0

    detail = dict(frac=frac, r_core=float(r_core), inner_heads=bool(have_inner_heads),
                  outer_heads=bool(have_outer_heads), lumen_r=float(lumen_r),
                  lumen_ratio=float(lumen_ratio))
    if have_inner_heads and have_outer_heads and lumen_ratio >= 0.30 and lumen_r > lumen_min:
        return "HOLLOW", detail
    if have_outer_heads and not have_inner_heads:
        return "filled", detail
    return "other", detail


# ---------------- calibration gates ----------------

def _mk(n_lip=80, n_water=400, bound=12.0):
    from bicelle2d import build
    return build(0, plant=False, n_lip=n_lip, n_water=n_water, bound=bound, kt=0.02, speed=0.001,
                 repel=12.0, k_bond=30.0, satt=0.30, n_tail=2, bond_span=2.0,
                 polarity=0.80, head_q=1.2, hydrophobic=0.6, attract=1.0)


def plant_ring(e, R_mid=6.0):
    mol, nb = e._mol, e._mol.shape[1]
    lip = (nb - 1) * BOND_REST
    R_out, R_in = R_mid + lip, R_mid - lip
    n = len(mol)
    n_out = int(round(n * R_out / (R_out + R_in)))
    k = 0
    for count, R_head, sgn in ((n_out, R_out, +1.0), (n - n_out, R_in, -1.0)):
        th = (np.arange(count) + 0.5) / count * 2 * np.pi
        rh = np.stack([np.cos(th), np.sin(th)], 1)
        idx = mol[k:k + count]
        for bead in range(nb):
            e.X[idx[:, bead], :2] = rh * (R_head - sgn * bead * BOND_REST)
        k += count
    # water into the lumen so the positive control actually has one
    lum = np.linalg.norm(e.X[e._wi, :2], axis=1) < R_in - lip
    return lum.sum()


def plant_micelle(e, R=4.0):
    mol, nb = e._mol, e._mol.shape[1]
    n = len(mol)
    th = (np.arange(n) + 0.5) / n * 2 * np.pi
    rh = np.stack([np.cos(th), np.sin(th)], 1)
    for bead in range(nb):
        e.X[mol[:, bead], :2] = rh * (R - bead * BOND_REST)


def plant_spanning_stripe(e):
    """A bilayer stripe spanning the periodic box: heads out along +/-y, tails meeting at y=0.

    The FOURTH gate, added after `classify` returned HOLLOW on a spanning branched network whose
    render showed a pore rather than a lumen. The first three gates all use COMPACT aggregates, so
    nothing tested what a radial profile about a centroid does to a structure that has no centre. A
    spanning membrane is exactly that case: it percolates, its centroid is arbitrary, and water lying
    beyond it in any direction can occupy the radii where a lumen would be.
    """
    mol, nb = e._mol, e._mol.shape[1]
    per = len(mol) // 2
    xs = (np.arange(per) - (per - 1) / 2.0) * (e.L / per)
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for bead in range(nb):
            off = 0.5 + (nb - 1 - bead) * BOND_REST
            e.X[idx[:len(idx), bead], 0] = xs[:len(idx)]
            e.X[idx[:len(idx), bead], 1] = sgn * off


def plant_two_fragments(e, sep=9.0, R=3.0):
    """The adversarial case: two micelles whose CENTROID lies between them, in solvent."""
    mol, nb = e._mol, e._mol.shape[1]
    half = len(mol) // 2
    for grp, cx in ((mol[:half], -sep / 2), (mol[half:], +sep / 2)):
        th = (np.arange(len(grp)) + 0.5) / len(grp) * 2 * np.pi
        rh = np.stack([np.cos(th), np.sin(th)], 1)
        for bead in range(nb):
            e.X[grp[:, bead], :2] = rh * (R - bead * BOND_REST) + np.array([cx, 0.0])


def self_test(verbose=True):
    results = []
    e = _mk()
    nlum = plant_ring(e)
    v, d = classify(e)
    results.append(("positive: planted hollow ring", v == "HOLLOW", v, d))

    e = _mk()
    plant_micelle(e)
    v, d = classify(e)
    results.append(("negative: planted filled micelle", v != "HOLLOW", v, d))

    e = _mk()
    plant_two_fragments(e)
    v, d = classify(e)
    results.append(("adversarial: two fragments, centroid between", v != "HOLLOW", v, d))

    e = _mk()
    plant_spanning_stripe(e)
    v, d = classify(e)
    results.append(("adversarial: spanning stripe, no centre at all", v != "HOLLOW", v, d))

    if verbose:
        for name, ok, v, d in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name:<46} -> {v:<11} "
                  f"frac={d.get('frac', 0):.2f} lumen_ratio={d.get('lumen_ratio', 0):.2f}")
    return all(r[1] for r in results)


if __name__ == "__main__":
    print("RING ASSAY CALIBRATION")
    ok = self_test()
    print(f"\nGATES: {'PASS -- assay may be used' if ok else 'FAIL -- assay must not be used'}")
