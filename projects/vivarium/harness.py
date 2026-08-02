"""One validated measurement chokepoint. Nothing else should compute geometry on a periodic system.

Seven measurement defects in this project came from geometry computed on raw coordinates. The worst
were: an order parameter that correlated with itself (null +0.669 where 0 was assumed), and bond
lengths measured without minimum image, which reported 13.3 in a box of 10 and sent three separate
diagnoses down the wrong path. The engine's own forces were always right; only the measurements were
wrong.

So every quantity here goes through two rules:

  1. UNWRAP FIRST. On a periodic axis, a raw difference is meaningless: an aggregate straddling the
     boundary yields a covariance, a midplane and a bond length that are all garbage. `unwrap()` is
     the only place a periodic difference is taken.
  2. DISQUALIFY, DO NOT INTERPRET. If the molecule is deformed or the integrator is overshooting, the
     structural numbers describe nothing, so `measure()` returns `ok=False` and the caller must throw
     the sample away rather than read `aspect` off a broken configuration.

Every metric here has been calibrated against BOTH controls -- a planted structure must score high AND
a random configuration must score at the null. A positive control alone cannot catch a self-correlated
statistic, which is how three micelle claims survived for a day.

    lamellar  fraction of lipids whose HEAD lies farther from the aggregate midplane than its OWN
              tails. Planted bilayer ~1.0, random ~0.5. NOTE it reads 1.0 on a collapsed droplet too,
              so it is necessary and NOT sufficient -- always read it with `aspect`.
    aspect    L1/L3 of the largest cluster's covariance, unwrapped. A slab or ribbon is thin in one
              axis (low); a droplet is round (~0.8+). A droplet cannot fake it, but a FRAGMENT can,
              so it is only admissible when the cluster holds most of the system (MIN_CLUSTER_FRAC).
    edge      fraction of lipids whose TAIL beads still touch water: the exposed rim, i.e. L_edge in
              G_edge = 2*pi*R*gamma. This is what separates the stages of the vesicle pathway, which
              `aspect` and `hollow` cannot do on their own:

                  stage 2  BICELLE   flat (aspect low) WITH a rim   -> edge > 0
                  stage 3  CUP       curving, rim shrinking          -> edge falling
                  stage 4  VESICLE   sealed, no boundary at all      -> edge ~ 0 AND hollow low

              A flat patch and a sealed vesicle are both "ordered", so without this the pathway is
              invisible: the whole thermodynamic story is edge energy being traded for bending energy,
              and edge length is the quantity actually being traded.
    align     nematic order S of the lipid axes: S = (3<(u.n)^2> - 1)/2 against the director n.
              A BILAYER puts every lipid along +/-n, so S -> 1. A MICELLE or VESICLE points its lipids
              radially in all directions, so S -> 0. This is the metric that actually separates
              lamellar from radial order, and `lamellar` never did: on a planted sphere `lamellar`
              reads 0.967, because "head farther out than its own tails" is true of any heads-out
              structure, and the sphere's covariance eigenvalues are near-degenerate so its "thin
              axis" is arbitrary noise.
    enclosed  water density INSIDE the aggregate's shell, relative to the bulk water density. ~1
              means the lumen is filled with solvent at normal density (a sealed vesicle); 0 means no
              solvent inside (a filled micelle). Defined as a DENSITY RATIO, not a fraction of all
              water: a vesicle lumen is a tiny share of the box (~0.2%), so a fraction reads 0.000
              even for a perfectly water-filled vesicle. This is what makes a
              vesicle a vesicle rather than a hollow shell in vacuum, and it is the stage-4 signature:
              a sealed shell traps solvent. A filled micelle has tails in the middle and encloses
              nothing; a bicelle is open on both faces so its "interior" is continuous with the bulk.
              Requires explicit solvent, like `edge`; NaN without it.
    hollow    tail density at the CORE divided by tail density in the shell. ONLY DEFINED FOR A
              ROUGHLY SPHERICAL aggregate: "core versus shell" is a radial decomposition, so on a slab
              it is nonsense (a planted bilayer scored 22.27). Returns NaN unless the shape is round,
              which is exactly the regime where it is needed -- separating a filled micelle from a
              sealed vesicle, the one pair `align` and `lamellar` cannot tell apart. A VESICLE is closed, so
              its centre is empty and this goes to ~0; a filled droplet keeps tails all the way in and
              it stays near 1. This is the one structure `aspect` is blind to: a vesicle is spherical,
              so aspect ~1 and lamellar high -- exactly a droplet's signature. Searching on aspect
              alone would have DISCARDED a vesicle as a droplet, and a vesicle is what a finite amount
              of lipid actually forms, since unlike a bicelle it has no rim to pay for.
"""

from __future__ import annotations

import numpy as np

BOND_REST = 1.0
BOND_MAX = 1.25          # beyond this the molecule is deformed and nothing structural is admissible
DISP_MAX = 0.05          # per-step displacement above which the integrator is overshooting
MIN_PACKING = 0.35       # median nearest non-bonded LIPID neighbour, as a fraction of contact.
#   Matter has to occupy space, and nothing else here checks that it does: `bond_stats` reads
#   INTRAMOLECULAR distances, so molecules stacked on one point each report a perfect bond of 1.0,
#   while `lamellar` and `align` come from DIRECTIONS, which stay well defined at any density, and a
#   collapsed pile is maximally connected so `cluster_frac` reads its BEST value.
#
#   The threshold is DERIVED from planted references measured in the solvated regime, not chosen:
#
#       spanning bilayer, planted at contact   1.000
#       spanning bilayer, relaxed              0.713
#       MICELLE, planted                       0.683
#       MICELLE, relaxed                       0.436   <- tightest LEGITIMATE structure
#       genuine collapse                       0.150
#
#   A micelle cannot reach a bilayer's packing by geometry: its lipids converge radially, so the
#   inner tail beads sit closer than contact by construction. That is the packing parameter showing
#   up as a floor on the metric. An earlier gate of 0.70, calibrated on the bilayer alone, therefore
#   rejected real micelles -- and did reject one, which is how a correct result was called a
#   collapse. 0.35 sits below the tightest legitimate structure and well above true collapse.
MIN_CLUSTER_FRAC = 0.60  # the largest cluster must hold this share of all lipids, or `aspect`
#   describes a FRAGMENT rather than the system. A search minimising aspect will otherwise win by
#   shattering the aggregate: 23 lipids out of 120 scored 0.189, beating a planted bilayer's 0.231,
#   while looking nothing like a membrane. Guarding the molecule and the integrator was not enough --
#   the objective also has to be denied its cheapest degenerate route.


def _periodic_axes(e):
    walls = tuple(getattr(e, "wall_axes", ()) or ())
    return np.array([ax not in walls for ax in range(e.pd)])


def delta(e, a, b):
    """The ONLY place a periodic difference is taken. Minimum image on periodic axes only."""
    d = e.X[a, :e.pd] - e.X[b, :e.pd]
    free = _periodic_axes(e)
    d[:, free] -= e.L * np.round(d[:, free] / e.L)
    return d


def unwrap(e, idx, ref=None):
    """Positions of `idx` made contiguous, by BFS over the molecule graph.

    Unwrapping every bead against ONE reference is only valid when the whole structure lies within
    L/2 of it. A real aggregate is routinely wider than that, and the far side then folds onto the
    near side: measured directly, a rod of true span 8.0 in a box of 10 reported 9.79, a hollow
    vesicle read as filled, and a flat bilayer read as round. Walking the connectivity graph and
    unwrapping each molecule against an ALREADY-UNWRAPPED neighbour has no size limit.
    """
    idx = np.asarray(idx)
    mol = e._mol
    free = _periodic_axes(e)
    if mol.size == 0:
        return e.X[idx, :e.pd].copy()
    nb = mol.shape[1]
    # which molecule each requested bead belongs to
    owner = np.full(e.cfg.N, -1, dtype=int)
    owner[mol.ravel()] = np.repeat(np.arange(len(mol)), nb)

    cen = e.X[mol[:, nb // 2], :e.pd]
    d = cen[:, None, :] - cen[None, :, :]
    d[..., free] -= e.L * np.round(d[..., free] / e.L)
    near = np.einsum("ijc,ijc->ij", d, d) < (2.6 * BOND_REST) ** 2
    np.fill_diagonal(near, False)

    start = owner[idx[0]] if owner[idx[0]] >= 0 else 0
    shift = np.zeros((len(mol), e.pd))
    seen = np.zeros(len(mol), dtype=bool)
    seen[start] = True
    stack = [start]
    while stack:
        a = stack.pop()
        for b in np.where(near[a] & ~seen)[0]:
            dd = cen[b] - (cen[a] + shift[a])
            dd[free] -= e.L * np.round(dd[free] / e.L)
            shift[b] = cen[a] + shift[a] + dd - cen[b]
            seen[b] = True
            stack.append(b)
    # anything not reached by the graph falls back to a single-reference shift
    if not seen.all():
        dd = cen[~seen] - cen[start]
        dd[:, free] -= e.L * np.round(dd[:, free] / e.L)
        shift[~seen] = cen[start] + dd - cen[~seen]

    out = e.X[idx, :e.pd].copy()
    own = owner[idx]
    ok = own >= 0
    out[ok] += shift[own[ok]]
    return out


def bond_stats(e):
    """(mean, max, fraction stretched) over the engine's ACTUAL backbone bonds, with minimum image.

    Read the bond list, never infer it from column order. The previous version walked
    mol[:,k] -> mol[:,k+1], which is only the topology of a LINEAR chain: on a BRANCHED lipid that
    steps from arm 1's tip to arm 2's base, two beads that are not bonded and sit far apart, and it
    reported 25% of bonds broken at t=0 on a perfectly built molecule. Measuring only the first bond
    hid a different problem earlier, since bonds stretch unevenly along a chain.
    """
    if not e._mol.size or not getattr(e, "_bond_i", np.zeros(0)).size:
        return 0.0, 0.0, 0.0
    backbone = np.isclose(e._bond_r0, BOND_REST)      # exclude the 1-3 straighteners
    if not backbone.any():
        return 0.0, 0.0, 0.0
    d = np.linalg.norm(delta(e, e._bond_i[backbone], e._bond_j[backbone]), axis=1)
    return float(d.mean()), float(d.max()), float((d > BOND_MAX).mean())


def packing(e):
    """Median nearest NON-BONDED neighbour distance, as a fraction of the contact distance.

    Bonded pairs are excluded because a bond legitimately holds beads at BOND_REST, which is inside
    contact for any sigma above 0.5; including them would report healthy overlap on every chain.
    Uses the same DERIVED contact distance as `largest_cluster` rather than a chosen constant.

    LIPID-TO-LIPID only: both the bead measured and its neighbour must be lipid. Counting solvent as
    a neighbour measures SOLVATION, not structure, and in a solvated box the nearest bead to a lipid
    is nearly always a water -- so the metric reported how close the water was and ignored the
    membrane entirely. Measured on a 2-D bilayer planted at exactly contact spacing, that read 0.637
    for a perfect structure and made MIN_PACKING reject the very thing it was calibrated to accept.
    The 3-D reference scored a clean 1.000 only because it happens to carry no solvent.

    ~1.0 for a properly packed structure, falling toward 0 as an aggregate collapses through itself.
    A median, so a handful of genuinely close pairs cannot condemn a good structure and a collapse
    (which moves every bead at once) cannot hide in a tail.
    """
    sig = getattr(e, "sigma", None)
    contact = float(2.0 * np.median(sig)) if sig is not None else 1.0
    lip = np.asarray(e.species) != 0
    if not lip.any():
        return float("nan")
    d = e.X[:, : e.pd][:, None, :] - e.X[:, : e.pd][None, :, :]
    free = _periodic_axes(e)
    d[:, :, free] -= e.L * np.round(d[:, :, free] / e.L)
    dist = np.linalg.norm(d, axis=2)
    np.fill_diagonal(dist, np.inf)
    bi, bj = getattr(e, "_bond_i", None), getattr(e, "_bond_j", None)
    if bi is not None and len(bi):
        dist[bi, bj] = np.inf
        dist[bj, bi] = np.inf
    return float(np.median(dist[np.ix_(lip, lip)].min(axis=1)) / contact)


def solvation(e):
    """Median lipid-to-nearest-SOLVENT distance over contact. The other half of `packing`.

    Split out rather than folded in, because the two answer different questions and a single number
    conflated them: `packing` asks whether the membrane interpenetrates ITSELF, this asks whether
    solvent is jammed into it. Freshly planted water is random and legitimately overlaps, so this is
    diagnostic rather than a gate -- it should RISE over the first few hundred steps as the solvent
    relaxes out of the structure.
    """
    sig = getattr(e, "sigma", None)
    contact = float(2.0 * np.median(sig)) if sig is not None else 1.0
    sp = np.asarray(e.species)
    lip, wat = sp != 0, sp == 0
    if not lip.any() or not wat.any():
        return float("nan")
    d = e.X[:, : e.pd][:, None, :] - e.X[:, : e.pd][None, :, :]
    free = _periodic_axes(e)
    d[:, :, free] -= e.L * np.round(d[:, :, free] / e.L)
    dist = np.linalg.norm(d, axis=2)
    return float(np.median(dist[np.ix_(lip, wat)].min(axis=1)) / contact)


def splay(e, cutoff=None):
    """Median angle between a lipid's axis and its SAME-LEAFLET neighbours' axes, in radians.

    This is the local, scale-free discriminator between a bilayer and a micelle, and it exists
    because every global metric here is ambiguous in the middle of the range. `align` reads 1.0 for a
    flat bilayer and ~0.09 for a micelle, but a mixture or a curved patch lands between and cannot be
    told from a dense pile; `packing` distinguishes matter from collapse and says nothing about shape.

    The geometry is unambiguous though. In a BILAYER, neighbouring lipids in the same leaflet are
    PARALLEL, so the splay goes to 0. In a MICELLE of n lipids they fan out around the circle, so
    neighbours differ by ~2*pi/n -- about 0.5 rad for the n~12 aggregates seen here. Curvature is the
    actual difference between the two structures, and this measures curvature directly instead of
    inferring it from a whole-aggregate average.

    Same-leaflet is defined by u_i . u_j > 0: two lipids in opposing leaflets point antiparallel, and
    including them would report ~pi for a perfect bilayer, which is the structure's OWN signature
    mistaken for disorder.
    """
    mol = e._mol
    if len(mol) < 3:
        return float("nan")
    nb = mol.shape[1]
    u = np.zeros((len(mol), e.pd))
    for k in range(1, nb):
        u += -delta(e, mol[:, 0], mol[:, k])
    u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
    if cutoff is None:
        sig = getattr(e, "sigma", None)
        contact = float(2.0 * np.median(sig)) if sig is not None else 1.0
        cutoff = 2.2 * contact          # first shell of neighbouring molecules
    cen = e.X[mol[:, 0], :e.pd]
    d = cen[:, None, :] - cen[None, :, :]
    free = _periodic_axes(e)
    d[:, :, free] -= e.L * np.round(d[:, :, free] / e.L)
    near = np.linalg.norm(d, axis=2) < cutoff
    np.fill_diagonal(near, False)
    dots = np.clip(u @ u.T, -1.0, 1.0)
    same = near & (dots > 0.0)
    vals = [float(np.median(np.arccos(dots[i, same[i]]))) for i in range(len(mol)) if same[i].any()]
    return float(np.median(vals)) if vals else float("nan")


def largest_cluster(e, cutoff=None):
    """Molecule indices of the biggest connected aggregate, joined with minimum image.

    Shape must be measured PER CLUSTER: a global covariance over several droplets reports the
    arrangement of droplets, not the shape of any of them.
    """
    mol = e._mol
    n = len(mol)
    if n == 0:
        return np.zeros(0, dtype=int)
    if cutoff is None:
        # DERIVED, not chosen. Two beads are in contact at sigma_i + sigma_j; anything appreciably
        # beyond that is separated by solvent. A constant was wrong in BOTH directions within hours:
        # 2.2 merged distinct micelles (a cluster of them then read as a vesicle) and 1.4 split a
        # bilayer's leaflets (the harness then rejected a real membrane). Scaling the actual contact
        # distance removes the guesswork and adapts to per-species radii.
        sig = getattr(e, "sigma", None)
        contact = float(2.0 * np.median(sig)) if sig is not None else 1.0
        cutoff = 1.6 * contact
    # Connect on ANY bead pair, not the middle bead: a bilayer's leaflets meet TAIL to TAIL ~1 apart
    # while their middle beads are ~5 apart, so middle-bead clustering split every bilayer in half and
    # the harness rejected it as "fragmented".
    #
    # The cutoff is bounded from BOTH sides and 2.2 was too generous. Four separate micelles, each a
    # distinct aggregate with 2-3 units of water between them, were merged into a single "cluster" of
    # 63/63 lipids; the water BETWEEN them then read as a lumen, giving hollow 0.06 and enclosed 2.96
    # -- above bulk density, which is impossible for a real interior -- and the classifier called it a
    # VESICLE. A screenshot showed four micelles. 1.4 still joins leaflets in contact (~1.0) but no
    # longer bridges aggregates separated by open solvent.
    P = e.X[mol.ravel(), :e.pd].reshape(n, -1, e.pd)
    d = P[:, None, :, None, :] - P[None, :, None, :, :]
    free = _periodic_axes(e)
    d[..., free] -= e.L * np.round(d[..., free] / e.L)
    near = (np.einsum("ijabc,ijabc->ijab", d, d) < cutoff ** 2).any(axis=(2, 3))
    np.fill_diagonal(near, False)
    seen, best = set(), []
    for s in range(n):
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            comp.append(k)
            stack.extend(np.where(near[k])[0].tolist())
        if len(comp) > len(best):
            best = comp
    return np.array(sorted(best), dtype=int)


def measure(e, prev_X=None):
    # prev_X MUST be from exactly one step earlier: DISP_MAX is a per-step bound.
    """All admissible structure in one call.

    Returns a dict. `ok` is False when the molecule is deformed or the integrator is overshooting; in
    that case the structural fields describe nothing and must not be read.
    """
    mol = e._mol
    bmean, bmax, bfrac = bond_stats(e)
    out = {"bond_mean": bmean, "bond_max": bmax, "bond_frac": bfrac,
           "disp": 0.0, "ok": True, "why": "", "n_cluster": 0,
           "lamellar": float("nan"), "aspect": float("nan"), "aspect2": float("nan"),
           "cluster_frac": 0.0, "hollow": float("nan"), "edge": float("nan"),
           "align": float("nan"), "thick_mol": float("nan"), "enclosed": float("nan"),
           "packing": float("nan"), "solvation": float("nan"),
           "splay": float("nan")}

    if prev_X is not None:
        d = e.X[:, :e.pd] - prev_X[:, :e.pd]
        free = _periodic_axes(e)
        d[:, free] -= e.L * np.round(d[:, free] / e.L)
        out["disp"] = float(np.linalg.norm(d, axis=1).max())

    out["packing"] = packing(e)
    out["solvation"] = solvation(e)
    out["splay"] = splay(e)
    if out["packing"] < MIN_PACKING:
        # FIRST, ahead of every shape metric. A collapsed pile still has well-defined bond lengths and
        # well-defined directions, so it scores as a flawless membrane on everything else here.
        out["ok"], out["why"] = False, (f"collapsed (nearest non-bonded neighbour at "
                                        f"{out['packing']:.2f} of contact)")
    elif bfrac > 0.02:
        out["ok"], out["why"] = False, f"molecule deformed (bond mean {bmean:.2f}, {bfrac:.0%} > {BOND_MAX})"
    elif out["disp"] > DISP_MAX:
        out["ok"], out["why"] = False, f"integrator overshooting ({out['disp']:.3f}/step)"

    comp = largest_cluster(e)
    out["n_cluster"] = int(len(comp))
    out["cluster_frac"] = float(len(comp) / max(len(mol), 1))
    if len(comp) < 6:
        out["ok"], out["why"] = False, "no aggregate"
        return out
    if out["ok"] and out["cluster_frac"] < MIN_CLUSTER_FRAC:
        # only if nothing more fundamental already failed: a torn molecule also fragments the cluster,
        # and reporting "fragmented" there hides the ROOT CAUSE behind its own consequence.
        out["ok"], out["why"] = False, (f"fragmented ({len(comp)}/{len(mol)} lipids = "
                                        f"{out['cluster_frac']:.0%} in the largest cluster)")

    idx = mol[comp]
    P = unwrap(e, idx.ravel(), ref=idx[0, 0])
    c = P - P.mean(0)
    ev = np.linalg.eigvalsh(c.T @ c / len(c))
    out["aspect"] = float(ev[0] / max(ev[-1], 1e-12))
    if e.pd == 3:
        out["aspect2"] = float(ev[1] / max(ev[-1], 1e-12))

    # exposed rim: tail beads with water in contact range. Requires explicit solvent -- with none,
    # gamma = 0 by construction and the closure the pathway depends on cannot happen.
    wi = getattr(e, "_wi", np.zeros(0, dtype=int))
    if wi.size:
        # deepest tail bead only -- see bicelle2d.edge_frac for why "any wet tail bead" saturates
        tips = idx[:, -1]
        dw = e.X[tips, :e.pd][:, None, :] - e.X[wi, :e.pd][None, :, :]
        free = _periodic_axes(e)
        dw[..., free] -= e.L * np.round(dw[..., free] / e.L)
        out["edge"] = float((np.einsum("ijc,ijc->ij", dw, dw) < 1.2 ** 2).any(axis=1).mean())

    # enclosed solvent: water nearer the aggregate centre than the lipid shell it sits inside.
    # A sealed vesicle traps water; a micelle fills the same volume with tails; an open disc does not
    # separate an interior at all.
    if wi.size:
        cen0 = P.mean(0)
        dwc = e.X[wi, :e.pd] - cen0
        free2 = _periodic_axes(e)
        dwc[:, free2] -= e.L * np.round(dwc[:, free2] / e.L)
        rw = np.linalg.norm(dwc, axis=1)
        rl = np.linalg.norm(P - cen0, axis=1)
        r_inner = np.percentile(rl, 15)          # inner face of the lipid shell
        if r_inner <= 0.5:
            # no lumen at all (a FILLED aggregate): definitively zero trapped solvent, not undefined
            out["enclosed"] = 0.0
        else:
            v_in = (4.0 / 3.0 * np.pi * r_inner ** 3) if e.pd == 3 else (np.pi * r_inner ** 2)
            v_box = float(np.prod(e.L)) if np.ndim(e.L) else float(e.L) ** e.pd
            dens_in = float((rw < r_inner).sum()) / max(v_in, 1e-9)
            dens_bulk = len(wi) / max(v_box, 1e-9)
            out["enclosed"] = float(dens_in / max(dens_bulk, 1e-12))

    nb = idx.shape[1]
    Pm = P.reshape(len(comp), nb, e.pd)

    # nematic order of the lipid axes: 1 for a bilayer, 0 for a radial (micelle/vesicle) structure.
    # Computed from INTRAMOLECULAR vectors via minimum image, never from unwrapped positions: a
    # molecule is always smaller than L/2 so this is exact, whereas unwrapping is ill-defined for a
    # structure that PERCOLATES the box (BFS unrolls it arbitrarily). That makes `align` the one
    # orientational metric that is valid for spanning and finite structures alike.
    u = np.zeros((len(comp), e.pd))
    for k in range(1, nb):
        u += -delta(e, idx[:, 0], idx[:, k])
    u /= max(nb - 1, 1)
    u /= np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1e-9)
    Q = np.einsum("ia,ib->ab", u, u) / len(u)
    lam_max = float(np.linalg.eigvalsh(Q)[-1])
    out["align"] = float((e.pd * lam_max - 1.0) / (e.pd - 1.0))

    # thickness along the director, in molecule lengths. Unlike `aspect` this does not depend on the
    # BOX: the same membrane measured aspect 0.245 at bound=6 and 0.109 at bound=9, because a spanning
    # structure inherits its lateral extent from the container.
    nrm = np.linalg.eigh(Q)[1][:, -1]
    proj = (P - P.mean(0)) @ nrm
    mol_len = max(nb - 1, 1) * BOND_REST
    out["thick_mol"] = float((np.percentile(proj, 97) - np.percentile(proj, 3)) / (2 * mol_len))

    # hollowness, guarded: radial core-vs-shell is only meaningful for a round aggregate. On a slab
    # the "core" is a disc through the membrane and the ratio means nothing.
    round_enough = out["aspect"] > 0.55
    cen = P.mean(0)
    rt = np.linalg.norm(Pm[:, 1:].reshape(-1, e.pd) - cen, axis=1)
    R = np.percentile(rt, 95)
    if R > 1e-9 and round_enough:
        core = float((rt < 0.35 * R).sum())
        shell = float(((rt >= 0.35 * R) & (rt < R)).sum())
        v_core = (0.35 * R) ** e.pd
        v_shell = R ** e.pd - v_core
        dens_core = core / max(v_core, 1e-9)
        dens_shell = shell / max(v_shell, 1e-9)
        out["hollow"] = float(dens_core / max(dens_shell, 1e-9))
    thin = np.linalg.eigh(c.T @ c / len(c))[1][:, 0]
    mid = P.mean(0)
    h = np.abs((Pm[:, 0] - mid) @ thin)
    t = np.abs((Pm[:, 1:] - mid[None, None, :]) @ thin).mean(axis=1)
    out["lamellar"] = float((h > t).mean())
    return out


def header():
    return ("   step  lamellar  aspect  hollow  edge  n_clu  frac  bond  disp   status")


def line(t, m):
    st = "ok" if m["ok"] else f"DISQUALIFIED: {m['why']}"
    lam = "  n/a " if np.isnan(m["lamellar"]) else f"{m['lamellar']:6.3f}"
    a1 = "  n/a" if np.isnan(m["aspect"]) else f"{m['aspect']:5.2f}"
    a2 = "  n/a" if np.isnan(m.get("hollow", float("nan"))) else f"{m['hollow']:5.2f}"
    ed = " n/a " if np.isnan(m.get("edge", float("nan"))) else f"{m['edge']:5.2f}"
    return (f"  {t:6d}  {lam}  {a1}   {a2}  {ed}  {m['n_cluster']:4d}  "
            f"{m.get('cluster_frac', 0):.2f}  {m['bond_mean']:.2f}  {m['disp']:.3f}  {st}")
