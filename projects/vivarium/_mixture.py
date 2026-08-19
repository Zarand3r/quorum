"""Leaflet compositional asymmetry: can curvature emerge from PARTITIONING rather than a parameter?

THE IDEA
    A cone-shaped lipid does not close a bilayer -- measured here, and for a reason: a symmetric
    bilayer gives both leaflets the same enlarged head, so the two spontaneous curvatures cancel and
    only lateral frustration is left (alignment 0.856 -> 0.400 -> 0.165 -> 0.117 as the head grows).

    Cells do not work that way. They generate curvature from a MIXTURE whose components partition
    unevenly between the inner and outer leaflet. The asymmetry is then a property of the composition,
    not of any molecule, and it is a packing outcome rather than an input. That is the one route to
    spontaneous curvature we have not tested that is not equivalent to importing the oracle's `beta`.

    Here the two components differ in TAIL LENGTH, which needs no change to the force field: a short
    lipid has a larger head-to-tail ratio and prefers the convex (outer) leaflet, a long lipid the
    concave (inner) one.

HYPOTHESIS     in a mixture, short lipids enrich the outer leaflet and long lipids the inner one, and
               the resulting asymmetry produces curvature that a single-component membrane lacks.
FALSIFICATION  if the leaflet compositions stay equal to within noise -- enrichment ~ 0.5 either side
               -- then partitioning does not happen in this model and the mechanism is dead, whatever
               the topology does.

The enrichment measurement is reported ALONGSIDE topology and is the primary readout, because it tests
the mechanism directly. Topology without enrichment would be a coincidence, and enrichment without
topology is still an informative positive.

DIMENSION
    Runs in 2-D and 3-D from the same code. `frac_short = 0` gives a single-component control, which in
    3-D is also this project's first 3-D self-assembly run under the scalar field.
"""

from __future__ import annotations

import os
import sys

import numpy as np

from _shot import disc, write_png
from field import Field, HEAD, TAIL, WATER
from integrate import Inertial

W, H = 760, 560


def shot(X, species, L, tag, slab=1.2):
    """A structural claim in this project is not allowed without looking at the picture.

    A 3-D box drawn as a flat projection is a solid wall of beads that hides everything inside it, so
    3-D states are cut to a slab through the centre thick enough to show one membrane cross-section.
    A slab too thick manufactures apparent density and one too thin manufactures apparent holes, and
    the first attempt here demonstrated the former: at slab = 3.0 through a vesicle of R = 4.35 the cut
    contained most of the sphere, so the front and back caps projected into the middle and a hollow
    shell rendered as a filled ball. 1.2 is thinner than the bilayer itself, so the cross-section of a
    vesicle is a genuine ring.
    """
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:, :] = (14, 16, 22)
    scale = min(W, H) * 0.92 / L
    keep = np.ones(len(X), bool) if X.shape[1] < 3 else (np.abs(X[:, 2]) < slab)
    for sp, rgb, rad in ((WATER, (46, 72, 92), 1.7), (TAIL, (232, 150, 62), 3.0),
                         (HEAD, (86, 160, 240), 3.6)):
        for x, y in X[keep & (species == sp)][:, :2]:
            disc(img, W * 0.5 + x * scale, H * 0.5 - y * scale, rad, rgb, 1.0)
    root = os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    out = os.path.join(root, "projects", "vivarium", "docs", "images", f"{tag}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_png(out, img)

C_D = {2: np.pi, 3: 4.0 * np.pi / 3.0}


def chain_bonds(idx, n_tail, branched):
    """Bond list for one molecule.

    LINEAR is a single chain: head-t1-t2-... A single-chain amphiphile is a DETERGENT. Its packing
    parameter P = v/(a0*l) has both v and l proportional to the tail bead count, so P is INDEPENDENT
    of tail length -- which is why lengthening the tail from 2 to 4 to 6 never moved the phase. Single
    chains sit near P ~ 1/3, the micelle band, and micelles are what this project keeps producing.

    BRANCHED is two chains from one head, which is what a real phospholipid is. It doubles v at fixed
    l and puts P in the 1/2 to 1 bilayer band. `polar_pack.py` already carried this distinction
    ("two tails from one head (a real lipid) vs a linear chain"); the rewrite to `field.py` dropped it.
    """
    if not branched or n_tail < 2:
        return [[idx[b], idx[b + 1]] for b in range(len(idx) - 1)]
    half = n_tail // 2
    out, head = [], idx[0]
    for c in range(2):
        prev = head
        for k in range(half):
            nxt = idx[1 + c * half + k]
            out.append([prev, nxt])
            prev = nxt
    return out


def build(n_short, n_long, n_water, L, d, tails=(2, 4), seed=0, plant="random", branched=False):
    """`random` disperses everything; `ring` plants a curved two-leaflet bilayer.

    The ring start exists because partitioning and nucleation are different questions. From a random
    start at these concentrations the largest aggregate after 100 000 steps is 6-12 lipids out of 70,
    so nothing has an inner or outer leaflet yet and enrichment is unmeasurable. Planting a CURVED
    bilayer supplies the geometry and asks the actual mechanism question: given a curvature, does a
    mixture sort itself between the leaflets? Species are assigned at random to positions, so any
    sorting that appears happened during the run.
    """
    rng = np.random.default_rng(seed)
    chains = [tails[0]] * n_short + [tails[1]] * n_long
    rng.shuffle(chains)                       # so leaflet assignment is not correlated with species
    n_lip_beads = sum(1 + t for t in chains)
    n = n_lip_beads + n_water
    X = np.zeros((n, d))
    species = np.empty(n, dtype=np.int64)
    mols, bonds, k = [], [], 0
    for t in chains:
        idx = np.arange(k, k + 1 + t)
        species[idx[0]] = HEAD
        species[idx[1:]] = TAIL
        c = rng.uniform(-L / 2, L / 2, size=d)
        u = rng.normal(size=d)
        u /= np.linalg.norm(u)
        if branched and t >= 2:
            half = t // 2
            perp = np.array([-u[1], u[0]] + [0.0] * (d - 2))[:d]
            X[idx[0]] = c
            for ch in range(2):
                sgn = 1.0 if ch == 0 else -1.0
                # NOT `k`: that is the outer bead counter, and shadowing it left the water index
                # range 344 beads short. It crashed here; with a different bead count it would have
                # silently mislabelled species instead.
                for j in range(half):
                    X[idx[1 + ch * half + j]] = c + u * (j + 1) + perp * sgn * 0.45
        else:
            for b in range(1 + t):
                X[idx[b]] = c + u * b
        mols.append(idx)
        bonds += chain_bonds(idx, t, branched)
        k += 1 + t
    if plant == "ring":
        _plant_ring(X, mols, np.array(chains), d)
    elif plant == "sphere":
        _plant_sphere(X, mols, np.array(chains), d)
    elif plant == "flat":
        # A FLAT ribbon separates the two steps that emergence conflates. Nucleation must produce one
        # large aggregate; closure must then bend it shut. Planting an ARC hands the system its
        # curvature and tests only the second step; planting FLAT hands it a single aggregate with no
        # curvature at all, so whether it curls is the closure question asked cleanly.
        _plant_flat_ribbon(X, mols, np.array(chains), d, L=L)
    elif plant.startswith("arc"):
        # `arc0.75` plants three quarters of a ring: a bilayer with TWO EXPOSED ENDS at the same
        # curvature the closed state prefers. The question is whether edge tension pulls the ends
        # together. This is only meaningful now that the closed ring is known to be stable -- run
        # before that, a failure to close could not be distinguished from the target not existing.
        _plant_ring(X, mols, np.array(chains), d, span=float(plant[3:] or 0.75))
    wi = np.arange(k, n)
    species[wi] = WATER
    X[wi] = rng.uniform(-L / 2, L / 2, size=(n_water, d))
    if plant in ("ring", "sphere"):
        # FILL THE LUMEN AT BULK DENSITY. Water placed uniformly at random almost never lands inside a
        # planted vesicle: in 3-D at packing fraction 0.10 a lumen of radius 3.7 should hold ~16 waters
        # and caught 4, so the interior was under-pressurised and the shell was crushed from outside --
        # lumen 4 -> 0 within 7500 steps. Real vesicle-construction protocols solvate the interior
        # explicitly for this reason. This also explains the 2-D/3-D contrast seen here: the 2-D runs
        # used packing fraction 0.55, where the lumen caught ~50 waters by chance and was properly
        # filled, while the 3-D runs used 0.10 and were not.
        _fill_lumen(X, wi, mols, np.array(chains), L, d, rng)
    X -= L * np.round(X / L)
    return X, species, np.array(bonds), mols, wi, np.array(chains)


def _fill_lumen(X, wi, mols, chains, L, d, rng):
    """Move enough water inside the planted shell that the lumen sits at the BULK number density.

    Waters are taken from the ones currently furthest from the centre, so the bulk is thinned evenly
    rather than a hole being cut in it. If the lumen already holds its share, nothing moves.
    """
    lipid_beads = np.concatenate(mols)
    cen = X[lipid_beads].mean(axis=0)
    rt = np.linalg.norm(_wrap(X[lipid_beads] - cen, L), axis=1)
    lip = float(chains.mean())
    r_in = float(np.median(rt)) - lip
    if r_in <= 1.0:
        return 0
    bulk = len(wi) / L ** d
    want = int(round(bulk * C_D[d] * r_in ** d))
    rw = np.linalg.norm(_wrap(X[wi] - cen, L), axis=1)
    have = int((rw < r_in).sum())
    need = want - have
    if need <= 0:
        return 0
    outer = wi[np.argsort(rw)[::-1][:need]]
    # uniform in the ball: radius scales as u^(1/d) so density is flat, not centre-heavy
    u = rng.random(need) ** (1.0 / d)
    v = rng.normal(size=(need, d))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    X[outer] = cen + v * (u * (r_in - 0.5))[:, None]
    return need


def _plant_sphere(X, mols, chains, d):
    """A 3-D vesicle: two concentric leaflets, heads out on the outside and in on the inside.

    The 3-D analogue of the planted ring, and for the same reason. Self-assembly in 3-D coarsens far
    too slowly to reach a vesicle in an affordable run -- after 200000 steps the largest aggregate is
    50 of 300 lipids, many small micelles that have not ripened -- while the reference model needed
    625k to 1M steps at this size with implicit solvent. Planting separates STABILITY, which is cheap
    to test, from REACHABILITY, which is not. In 2-D that separation is what showed the ring phase
    exists at all.

    Points are placed by the Fibonacci sphere so both leaflets are evenly covered without the pole
    crowding a latitude-longitude grid produces.
    """
    if d != 3:
        raise ValueError("sphere planting is 3-D")
    n = len(mols)
    lip = float(chains.mean())
    # area per lipid, MEASURED for this force field on a planted flat 3-D bilayer relaxed 30000 steps
    # (_sizing3d.py): 1.400 for a 2-tail lipid, 1.364 for 4-tail, against the reference model's 1.50.
    # The planted radius follows from it, so the vesicle starts at the size the lipid actually wants
    # rather than at a borrowed constant.
    a = 1.364 if chains.mean() >= 3 else 1.400
    R_mid = float(np.sqrt(n * a / (4.0 * np.pi)))
    R_out, R_in = R_mid + lip / 2, max(R_mid - lip / 2, 0.8)
    # CONSTANT VOLUME PER LIPID, not constant area. Splitting the leaflets by the AREA of each head
    # surface (R_out^2 : R_in^2) is the standard packing mistake: vesicle-building work reports that
    # constant-volume packing is markedly more stable than constant-area, ESPECIALLY FOR SMALL
    # vesicles, and that an improper leaflet split produces stress-induced instability, pore formation
    # and collapse during equilibration. A preassembled vesicle should not need flip-flop to relax --
    # and flip-flop is measured as forbidden here (enrichment never drifts off its planted value), so
    # a mis-split vesicle has no route to the right ratio except to collapse. Each leaflet gets the
    # lipids its own SHELL VOLUME can hold.
    v_out = R_out ** 3 - R_mid ** 3
    v_in = R_mid ** 3 - max(R_in - lip, 0.0) ** 3
    n_out = int(round(n * v_out / (v_out + v_in)))
    k = 0
    for count, R_head, sgn in ((n_out, R_out, +1.0), (n - n_out, R_in, -1.0)):
        if count <= 0:
            continue
        i = np.arange(count) + 0.5
        phi = np.arccos(1.0 - 2.0 * i / count)
        theta = np.pi * (1.0 + 5.0 ** 0.5) * i
        u = np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], axis=1)
        for j in range(count):
            idx = mols[k + j]
            for b in range(len(idx)):
                X[idx[b]] = u[j] * (R_head - sgn * b)
        k += count


def _plant_flat_ribbon(X, mols, chains, d, gap=1.05, L=None):
    """Two flat leaflets, tails meeting, heads out on both faces. No curvature planted.

    MUST BE FINITE. The point of this plant is to give the aggregate two exposed ENDS whose edge
    energy closure can recover. A ribbon wider than the periodic box wraps and has NO ends at all, so
    there is nothing to gain by closing and the experiment measures nothing. The first version did
    exactly that -- N = 200 gives width 100 * 1.05 = 105 sigma in a box of L = 52 -- and the run
    faithfully reported that a spanning ribbon stays flat, which was never in question.
    """
    n = len(mols)
    nb = len(mols[0])
    per = n // 2
    width = per * gap
    if L is not None and width > 0.8 * L:
        raise ValueError(f"flat ribbon of {n} lipids is {width:.1f} wide and would span a box of "
                         f"L={L}: it would have no ends, so closure has nothing to gain. "
                         f"Need L > {width / 0.8:.0f}.")
    xs = (np.arange(per) - (per - 1) / 2.0) * gap
    k = 0
    for sgn in (+1.0, -1.0):
        for j in range(per):
            idx = mols[k]
            for b in range(len(idx)):
                off = 0.5 + (len(idx) - 1 - b) * 1.0
                pos = np.zeros(d)
                pos[0] = xs[j]
                pos[1] = sgn * off
                X[idx[b]] = pos
            k += 1


def _plant_ring(X, mols, chains, d, span=1.0):
    """Two leaflets sharing a tail core. Heads out on the outside, heads in on the inside.

    The mid-surface radius is set so both leaflets sit at roughly one bead of arc per lipid, and the
    split between leaflets follows the ratio of their radii so neither is over-packed.
    """
    if d != 2:
        raise ValueError("ring planting is 2-D; use plant='random' in 3-D")
    n = len(mols)
    lip = float(chains.mean())
    R_mid = n / (4.0 * np.pi)
    R_out, R_in = R_mid + lip, max(R_mid - lip, 0.6)
    n_out = int(round(n * R_out / (R_out + R_in)))
    k = 0
    for count, R_head, sgn in ((n_out, R_out, +1.0), (n - n_out, R_in, -1.0)):
        if count <= 0:
            continue
        # the arc keeps the SAME arc spacing as the closed ring, so a shorter span means a smaller
        # subtended angle at the same radius, not a stretched membrane
        th = (np.arange(count) + 0.5) / max(count / span, 1e-9) * 2 * np.pi / (2 * np.pi) * 2 * np.pi
        th = (np.arange(count) + 0.5) / count * 2 * np.pi * span
        rhat = np.stack([np.cos(th), np.sin(th)], axis=1)
        for j in range(count):
            idx = mols[k + j]
            for b in range(len(idx)):
                X[idx[b]] = rhat[j] * (R_head - sgn * b)
        k += count


def geometry(X, mols, wi, chains, L, d):
    """Shell geometry, leaflet assignment, lumen occupancy and per-leaflet composition."""
    heads = np.array([m[0] for m in mols])
    tailc = np.array([X[m[1:]].mean(axis=0) for m in mols])
    lipid_beads = np.concatenate(mols)
    cen = X[lipid_beads].mean(axis=0)

    u = X[heads] - tailc                       # tail -> head, derived, never stored
    u -= L * np.round(u / L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    rel = X[heads] - cen
    rel -= L * np.round(rel / L)
    rn = np.linalg.norm(rel, axis=1)
    s = np.einsum("ic,ic->i", u, rel / np.maximum(rn, 1e-9)[:, None])

    outer, inner = s > 0, s < 0
    short = chains == chains.min()
    # enrichment: fraction of the OUTER leaflet that is short, vs fraction of the INNER leaflet.
    # Equal fractions = no partitioning = mechanism dead.
    f_out = float(short[outer].mean()) if outer.any() else float("nan")
    f_in = float(short[inner].mean()) if inner.any() else float("nan")

    rt = np.linalg.norm(_wrap(X[lipid_beads] - cen, L), axis=1)
    R_mid = float(np.median(rt))
    shell_cv = float(rt.std() / max(rt.mean(), 1e-9))

    lip_len = float(chains.mean())
    r_in = max(R_mid - lip_len, 0.0)
    # With IMPLICIT solvent there are no water beads, so lumen occupancy is undefined rather than
    # zero. Reporting 0 would read as "lumen collapsed" when in fact nothing was measured, which is
    # exactly the kind of silent-zero this project has been caught by before.
    if len(wi) == 0:
        n_in, lumen = 0, float("nan")
    else:
        rw = np.linalg.norm(_wrap(X[wi] - cen, L), axis=1)
        n_in = int((rw < r_in).sum())
        lumen = 0.0
        if r_in > 0.5:
            lumen = (n_in / (C_D[d] * r_in ** d)) / (len(wi) / L ** d)
    return dict(f_out=f_out, f_in=f_in, n_out=int(outer.sum()), n_in_leaf=int(inner.sum()),
                R_mid=R_mid, shell_cv=shell_cv, lumen=lumen, lumen_w=n_in, r_in=r_in)


def _wrap(v, L):
    return v - L * np.round(v / L)


def largest_cluster(X, mols, L, cut=1.4):
    """Molecules in the largest aggregate, linked BEAD to bead.

    Molecule-CENTRE connectivity is wrong for a bilayer and wrong again for a long chain: the two
    leaflets touch at their tails, not their centres, and a 4-bead lipid puts its centre two units
    from either end. Centre connectivity at cut=1.6 reported `largest = 4` on a system whose energy
    per lipid had already fallen to -20, i.e. it called a condensed system dispersed. `ring_assay`
    carries the same warning for the same reason.
    """
    from collections import deque
    nm = len(mols)
    beads = np.concatenate(mols)
    owner = np.concatenate([np.full(len(m), i) for i, m in enumerate(mols)])
    P = X[beads]
    dd = _wrap(P[:, None, :] - P[None, :, :], L)
    close = np.linalg.norm(dd, axis=2) < cut
    adj = np.zeros((nm, nm), bool)
    bi, bj = np.nonzero(close)
    adj[owner[bi], owner[bj]] = True
    np.fill_diagonal(adj, False)
    n = nm
    lab = -np.ones(n, int)
    c = 0
    for s0 in range(n):
        if lab[s0] >= 0:
            continue
        q = deque([s0])
        lab[s0] = c
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = c
                    q.append(j)
        c += 1
    return int(np.bincount(lab).max())


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 150000
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    n_lip = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    frac_short = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    L = float(sys.argv[5]) if len(sys.argv) > 5 else 50.0
    kT = float(sys.argv[6]) if len(sys.argv) > 6 else 0.35
    phi = float(sys.argv[7]) if len(sys.argv) > 7 else (0.55 if d == 2 else 0.35)
    plant = sys.argv[8] if len(sys.argv) > 8 else "random"
    # SEED was hardcoded in both the builder and the integrator, so every 3-D result so far is ONE
    # trajectory and the 1.2M "long run" is a deterministic replay of the 400k one -- it reproduces
    # largest = 126 at step 60000 exactly. Duration and seed variability are different questions and
    # this makes the second one askable.
    seed = int(sys.argv[9]) if len(sys.argv) > 9 else 0

    n_short = int(round(n_lip * frac_short))
    n_long = n_lip - n_short
    lip_beads = n_short * 3 + n_long * 5
    # phi = 0 means IMPLICIT SOLVENT: no water beads at all, which is what the oracle does. It also
    # removes the 3-D solvent defect entirely -- at phi 0.15-0.35 our explicit water is fragmented
    # droplets rather than a liquid, which voided every previous 3-D run here. Without water the
    # hydrophobic ordering still holds through chi, since tails attract tails (0.70) more than heads
    # attract heads (0.20), which is the Cooke-Deserno construction.
    n_water = 0 if phi <= 0.0 else int(round(phi * L ** d / C_D[d] * (2 ** d))) - lip_beads
    if n_water < 0:
        raise ValueError(f"L={L} too small for {n_lip} lipids at packing fraction {phi}")

    X, species, bonds, mols, wi, chains = build(n_short, n_long, n_water, L, d, plant=plant,
                                                branched=True, seed=seed)
    f = Field(species, bonds, L)
    # INERTIAL at the validated dt = 8e-3: same energy, same equilibrium ensemble (verified against
    # the overdamped run over 5 seeds per rung), 28x more reduced time per minute end to end.
    dt = 8e-3
    ig = Inertial(f, kT, dt, seed=1 + seed)

    print(f"MIXTURE {d}-D: {n_short} short (2 tails) + {n_long} long (4 tails) + {n_water} water, "
          f"L={L}, packing fraction {phi}, kT={kT}, start={plant}", flush=True)
    print("enrichment = (short fraction of OUTER leaflet) - (short fraction of INNER leaflet); "
          "0 = no partitioning", flush=True)
    print(f"{'step':>8}{'E/lip':>9}{'largest':>9}{'R_mid':>7}{'shellCV':>9}{'lumen':>7}"
          f"{'lumenW':>8}{'shortOUT':>10}{'shortIN':>9}   enrichment", flush=True)
    every = max(steps // 20, 1)
    for t in range(steps + 1):
        X = ig.step(X)
        if t % every == 0:
            g = geometry(X, mols, wi, chains, L, d)
            enr = g["f_out"] - g["f_in"]
            print(f"{t:>8}{f.energy(X) / n_lip:>9.2f}{largest_cluster(X, mols, L):>9}"
                  f"{g['R_mid']:>7.2f}{g['shell_cv']:>9.3f}{g['lumen']:>7.2f}{g['lumen_w']:>8}"
                  f"{g['f_out']:>10.2f}{g['f_in']:>9.2f}   {enr:+.3f}", flush=True)
            shot(X, species, L, f"mix{d}d_{plant}_N{n_lip}_sd{seed}_s{t:07d}")
