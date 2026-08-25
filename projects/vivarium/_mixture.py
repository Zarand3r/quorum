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
import pathlib
import sys

import numpy as np

from _shot import disc, write_png
from _lumen_field import count_vesicles, n_enclosed, percolates
from field import Field, HEAD, TAIL, WATER, solvent_averaged_chi
from integrate import Inertial

W, H = 760, 560


def _env_tag():
    """Every VIVARIUM_* override, in the filename. Seven times a swept variable has been missing from a
    tag -- L, n_tail, seed, kT, frac_short, chi_HT, chi_HH -- and each time the arms silently overwrote
    one another's frames and states. Enumerating the environment removes the failure mode instead of
    patching it once more."""
    return "".join(f"_{k.replace('VIVARIUM_', '').replace('CHI_', '').lower()}{v}"
                   for k, v in sorted(os.environ.items()) if k.startswith("VIVARIUM_"))


def _save_state(X, species, chains, mols, L, d, phi, kT, frac_short, plant, n_lip, seed, steps):
    """Write the current configuration, overwriting any previous one for this run."""
    # A restart's plant string is a filesystem path; using it verbatim in the output name produced a
    # nonsense nested path. Restarts are tagged by their origin instead.
    if plant.startswith("state:"):
        plant = "restart" + pathlib.Path(plant.split(":", 1)[1]).stem.split("_sd")[-1]
    root = os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    out = pathlib.Path(root) / "projects" / "vivarium" / "docs" / "states"
    out.mkdir(parents=True, exist_ok=True)
    # HAZARD, learned the expensive way on 2026-08-23: this name carries no STEP and no RUN identity,
    # so re-running the same parameters overwrites the previous run's state in place. Relaunching five
    # known vesicle-forming seeds as a reproducibility control destroyed the five historical states
    # those seeds' closure sizes had been measured from. `_env_tag` fixed the missing-swept-variable
    # half of this; the missing-run half is still open. Copy anything you need to keep into
    # docs/states_protected/ BEFORE relaunching a seed, or set VIVARIUM_SAVE_ALL, which writes
    # step-tagged files that never collide.
    tag = (f"mix{d}d_{plant}_N{n_lip}_L{L:g}_{'sac' if phi == 0.0 else 'exp'}"
           f"_kT{kT}_fs{frac_short}{_env_tag()}_sd{seed}.npz")
    np.savez_compressed(out / tag, X=X, species=species, chains=chains, L=L, d=d, phi=phi, steps=steps,
                        mols=np.array([m for m in mols], dtype=object), allow_pickle=True)


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
    # RECENTRE ON THE AGGREGATE before slabbing. The slab was cut about a FIXED plane (z = 0) while
    # the structure is free to sit anywhere in a periodic box, so it caught whatever happened to be
    # near the origin -- at seed 1 step 220000 that was nothing at all and the frame came out empty.
    # Worse than empty: an OFF-CENTRE slab through a hollow shell looks like a filled disc, so every
    # "filled blob, not a shell" reading from a 3-D render here is suspect until re-rendered.
    # This is the same fix applied to the oracle renderer two ticks ago and not propagated here.
    if X.shape[1] >= 3:
        ref = X - L * np.round((X - X[0]) / L)          # unwrap relative to one bead
        X = ref - ref.mean(axis=0)
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


def build(n_short, n_long, n_water, L, d, tails=None, seed=0, plant="random", branched=False):
    """`random` disperses everything; `ring` plants a curved two-leaflet bilayer.

    The ring start exists because partitioning and nucleation are different questions. From a random
    start at these concentrations the largest aggregate after 100 000 steps is 6-12 lipids out of 70,
    so nothing has an inner or outer leaflet yet and enrichment is unmeasurable. Planting a CURVED
    bilayer supplies the geometry and asks the actual mechanism question: given a curvature, does a
    mixture sort itself between the leaflets? Species are assigned at random to positions, so any
    sorting that appears happened during the run.
    """
    rng = np.random.default_rng(seed)
    # The default (2, 4) pairs a DETERGENT with a bilayer former: a 2-tail lipid sits near P ~ 1/3, the
    # micelle band, so mixing it in dissolves the ribbon -- measured, at largest 20-49 of 80 shuffled
    # and 33-79 sorted. Testing leaflet asymmetry needs two species that BOTH form bilayers, which is
    # what VIVARIUM_TAILS is for.
    if tails is None:
        tails = tuple(int(t) for t in os.environ.get("VIVARIUM_TAILS", "2,4").split(","))
    chains = [tails[0]] * n_short + [tails[1]] * n_long
    # Shuffled by default so leaflet assignment is not correlated with species. Skipping the shuffle
    # does the opposite deliberately: the flat and ring plants fill one leaflet before the other, so an
    # UNSHUFFLED chain list puts every short lipid on one face and every long lipid on the other. That
    # is an imposed leaflet asymmetry, and it is the only remaining candidate source of spontaneous
    # curvature -- chi_TW (lambda +2.8 +- 2.8 vs -5.2 +- 4.2), chi_HH (0/5 over ten runs) and lipid
    # shape (2-tail dissolves to micelles) are all excluded, and no SYMMETRIC pair term can produce a
    # curvature, which is by definition a difference between the two leaflets.
    if os.environ.get("VIVARIUM_SORT_LEAFLETS", "0") != "1":
        rng.shuffle(chains)
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
    elif plant in ("flat", "span"):
        # A FLAT ribbon separates the two steps that emergence conflates. Nucleation must produce one
        # large aggregate; closure must then bend it shut. Planting an ARC hands the system its
        # curvature and tests only the second step; planting FLAT hands it a single aggregate with no
        # curvature at all, so whether it curls is the closure question asked cleanly.
        _plant_flat_ribbon(X, mols, np.array(chains), d, L=L, spanning=(plant == "span"))
    elif plant.startswith("arc"):
        # `arc0.75` plants three quarters of a ring: a bilayer with TWO EXPOSED ENDS at the same
        # curvature the closed state prefers. The question is whether edge tension pulls the ends
        # together. This is only meaningful now that the closed ring is known to be stable -- run
        # before that, a failure to close could not be distinguished from the target not existing.
        _plant_ring(X, mols, np.array(chains), d, span=float(plant[3:] or 0.75))
    wi = np.arange(k, n)
    species[wi] = WATER
    # Water on a jittered lattice with lipid sites EXCLUDED, not uniformly at random. Random placement
    # drops water on top of the planted membrane -- minimum separation 0.007 sigma -- and the steric
    # push-off then resolves those overlaps by DEFORMING the membrane: a planted N=300 ring came out at
    # R_mid 58.3 against a planted 47.7, inflated 22%, already missing 10 lipids at step 0, and
    # fragmented to largest=50 by step 3000. The structure has to be intact before dynamics starts, or
    # the run measures the plant's destruction rather than the physics.
    if n_water:
        # oversample so that excluding the membrane's sites still leaves enough free ones
        # Oversample enough that excluding the membrane's sites still leaves room. 1.6x was sufficient
        # at moderate density but not at L = 38, where lipids cover ~42% of the box: four of five runs
        # died with "only 394 free water sites for 411 waters". Scaling with the lipid fraction rather
        # than a fixed factor makes the placement work at any concentration.
        _occ = min(0.9, n_lip_beads / max(L ** d / C_D[d] * (2 ** d), 1.0))
        per = int(np.ceil((n_water * (1.6 + 3.0 * _occ)) ** (1.0 / d))) + 2
        grid = np.stack(np.meshgrid(*[np.linspace(-L / 2, L / 2, per, endpoint=False)] * d,
                                    indexing="ij"), axis=-1).reshape(-1, d)
        grid = grid + rng.uniform(-0.15, 0.15, size=grid.shape)
        lip = X[:n_lip_beads] if n_lip_beads else np.zeros((0, d))
        if len(lip):
            dd = grid[:, None, :] - lip[None, :, :]
            dd -= L * np.round(dd / L)
            free = np.linalg.norm(dd, axis=2).min(axis=1) > 0.9
        else:
            free = np.ones(len(grid), bool)
        cand = grid[free]
        if len(cand) < n_water:
            raise ValueError(f"only {len(cand)} free water sites for {n_water} waters at L={L}")
        X[wi] = cand[rng.choice(len(cand), n_water, replace=False)]
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


def _fill_lumen_grid(X, wi, mols, L, rng, cell=0.5, bead=1.0):
    """Fill the FLOOD-FILLED enclosed region to bulk density, not a radial disc.

    _fill_lumen targets r_in = median(radius) - lipid_length about the centroid, which is a circle. The
    region a vesicle actually encloses is the irregular one n_enclosed flood-fills, and it is the region
    lumen_water_density measures. Filling the circle left the real lumen at 0.594 of bulk when the
    original state held 0.916, so the two must be the same region or the fill does not fix the confound.

    Waters are taken from those furthest from the aggregate, so the bulk thins evenly. Returns the
    number moved.
    """
    from _lumen_field import _interior_mask

    if len(wi) == 0:
        return 0
    interior = _interior_mask(X, mols, L, cell, bead)
    n_cells = int(interior.sum())
    if n_cells == 0:
        return 0
    n = interior.shape[0]
    step = L / n
    lip = np.concatenate(mols)
    shift = -X[lip].mean(axis=0) + L / 2.0
    gw = ((X[wi] + shift) / L * n).astype(int) % n
    inside = interior[gw[:, 0], gw[:, 1]]
    have = int(inside.sum())
    # Same deflation lever as `_fill_lumen`. THIS is the call site that actually decides the lumen's
    # water content for a planted ring: `_fill_lumen` runs inside `build`, and then this grid version
    # runs again afterwards and tops the lumen back up to bulk. Patching only the first one changed
    # nothing at all, verified across fill = 1.0 / 0.6 / 0.35 giving byte-identical trajectories.
    want = int(round((len(wi) / L ** 2) * n_cells * step * step
                     * float(os.environ.get("VIVARIUM_LUMEN_FILL", "1.0"))))
    if want <= have:
        return 0
    cells = np.argwhere(interior)
    # Candidate positions: cell centres in the interior, far enough from any lipid bead to be legal.
    pos = (cells + 0.5) * step
    dd = pos[:, None, :] - (X[lip] + shift)[None, :, :]
    dd -= L * np.round(dd / L)
    ok = np.linalg.norm(dd, axis=2).min(axis=1) > 0.9
    pos = pos[ok]
    if len(pos) == 0:
        return 0
    need = min(want - have, len(pos))
    outer = wi[~inside]
    if len(outer) == 0:
        return 0
    r = np.linalg.norm(_wrap(X[outer] - X[lip].mean(axis=0), L), axis=1)
    take = outer[np.argsort(r)[::-1][:need]]
    chosen = pos[rng.choice(len(pos), len(take), replace=False)] - shift
    X[take] = chosen
    return len(take)


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
    # OSMOTIC DEFLATION, the only protein-free route to vesicle fission. A closed membrane has a fixed
    # circumference set by its lipid count and an enclosed area set by how much water is inside. Filling
    # the lumen to bulk density (fill = 1.0) makes the taut circle, which is what every run so far has
    # planted, and a taut circle has no excess membrane to buckle with. Under-filling leaves the same
    # circumference around a smaller area, which is the reduced-volume axis of the standard vesicle
    # shape sequence: circle, then ellipse, then dumbbell, then a neck that may pinch. Fission in real
    # protein-free vesicles is driven exactly this way, by osmotic deflation or by feeding lipid in
    # faster than volume grows, so this is the lever and not a trick.
    fill = float(os.environ.get("VIVARIUM_LUMEN_FILL", "1.0"))
    want = int(round(bulk * C_D[d] * r_in ** d * fill))
    rw = np.linalg.norm(_wrap(X[wi] - cen, L), axis=1)
    have = int((rw < r_in).sum())
    need = want - have
    if need < 0 and fill < 1.0:
        # DEFLATION. The grid placement already leaves the lumen near bulk, because the lumen interior
        # sits far from any lipid and the lattice only rejects sites within 0.9 of one. So `need` is
        # already ~0 at fill = 1.0, and a fill BELOW 1.0 makes it negative. A function that only adds
        # water therefore cannot deflate anything: the first attempt at this lever gave byte-identical
        # trajectories at fill 1.0, 0.6 and 0.35. Removing the surplus is the half that does the work.
        surplus = wi[rw < r_in][np.argsort(rw[rw < r_in])[:-need]]
        r_out = float(np.max(rt)) + 1.0
        if r_out < L / 2.0 - 1.0:
            u = rng.random(len(surplus))
            rad = np.sqrt(r_out ** 2 + u * ((L / 2.0 - 0.5) ** 2 - r_out ** 2))
            v = rng.normal(size=(len(surplus), d))
            v /= np.linalg.norm(v, axis=1, keepdims=True)
            X[surplus] = _wrap(cen + v * rad[:, None], L)
        return -len(surplus)
    if need <= 0:
        # BACKWARD COMPATIBILITY, deliberately. At fill = 1.0 a lumen that is already ABOVE bulk keeps
        # its surplus, exactly as before this lever existed. Normalising it down would be defensible on
        # its own terms and would silently change every planted-ring run ever recorded, so it is gated
        # behind fill < 1.0. Verified: fill = 1.0 reproduces lumH2O 1.035 at step 0, unchanged.
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


def _plant_flat_ribbon(X, mols, chains, d, gap=1.05, L=None, branched=True, spanning=False):
    """Two flat leaflets, tails meeting, heads out on both faces. No curvature planted.

    MUST BE FINITE. The point of this plant is to give the aggregate two exposed ENDS whose edge
    energy closure can recover. A ribbon wider than the periodic box wraps and has NO ends at all, so
    there is nothing to gain by closing and the experiment measures nothing. The first version did
    exactly that -- N = 200 gives width 100 * 1.05 = 105 sigma in a box of L = 52 -- and the run
    faithfully reported that a spanning ribbon stays flat, which was never in question.
    """
    n = len(mols)
    nb = len(mols[0])
    if branched and nb - 1 >= 2:
        gap = max(gap, 2.05)                # lateral footprint of a two-tailed lipid
    per = n // 2
    if spanning:
        # A ribbon that wraps the box seamlessly has NO ends. Comparing it with a finite ribbon of the
        # same lipid count at the same spacing gives 2*lambda as a direct paired difference: the bulk
        # term cancels exactly, so there is no extrapolation and no intercept to fit. The finite-minus-
        # spanning difference is the cleanest estimator of edge cost available here.
        gap = L / per
    width = per * gap
    if (not spanning) and L is not None and width > 0.8 * L:
        raise ValueError(f"flat ribbon of {n} lipids is {width:.1f} wide and would span a box of "
                         f"L={L}: it would have no ends, so closure has nothing to gain. "
                         f"Need L > {width / 0.8:.0f}.")
    # LEAFLET AREA ASYMMETRY. Both leaflets span the same length, so putting more lipids in one packs
    # it tighter -- smaller area per lipid -- and it wants to expand relative to the other. That
    # differential is the classic source of spontaneous curvature, and it is a difference in AREA, not
    # in thickness. The 4-tail against 6-tail test varied leaflet THICKNESS and came back flat 0/5 with
    # the ribbon fully intact, which is why area is what this varies rather than repeating that.
    width_fixed = per * gap
    _f = float(os.environ.get("VIVARIUM_LEAFLET_SPLIT", "0.5"))
    _hi = int(round(n * _f))
    per_side = (_hi, n - _hi)
    xs_side = [((np.arange(m) - (m - 1) / 2.0) * (width_fixed / m)) if m > 1 else np.zeros(max(m, 0))
               for m in per_side]
    nt = nb - 1
    half = nt // 2 if branched and nt >= 2 else nt
    k = 0
    for _si, sgn in enumerate((+1.0, -1.0)):
        per, xs = per_side[_si], xs_side[_si]
        for j in range(per):
            idx = mols[k]
            # Tail count comes from THIS molecule, not from one scalar for the ribbon. A mixed
            # short/long population has 3-bead and 5-bead lipids in the same plant, and deriving
            # `half` once from the first molecule indexed a 3-bead lipid as if it had 5
            # (IndexError: index 3 is out of bounds for axis 0 with size 3).
            nt = len(idx) - 1
            half = nt // 2 if branched and nt >= 2 else nt
            # Head on the outer face, tails pointing inward. For a BRANCHED lipid the two tails go SIDE
            # BY SIDE (lateral +-0.5, first bead 0.866 in), not end to end: laying all beads along one
            # line put the bond from the head to the second branch 3 sigma from it against a rest length
            # of 1, which is the same defect that left the ring plant at ~800 eps/lipid of spring strain.
            # This function was missed when the ring plant was fixed, so its "planted bilayer" reference
            # was still an exploding configuration.
            reach = (0.866 + (half - 1)) if (branched and nt >= 2) else float(nt)
            head_off = 0.5 + reach
            pos = np.zeros(d)
            pos[0] = xs[j]
            pos[1] = sgn * head_off
            X[idx[0]] = pos
            if not branched or nt < 2:
                for b in range(1, len(idx)):
                    p2 = np.zeros(d)
                    p2[0] = xs[j]
                    p2[1] = sgn * (head_off - b)
                    X[idx[b]] = p2
            else:
                for c in range(2):
                    for b in range(half):
                        p2 = np.zeros(d)
                        p2[0] = xs[j] + (c - 0.5)
                        p2[1] = sgn * (head_off - (0.866 + b))
                        X[idx[1 + c * half + b]] = p2
            k += 1


def _plant_ring(X, mols, chains, d, span=1.0, branched=True):
    """Two leaflets sharing a tail core. Heads out on the outside, heads in on the inside.

    The mid-surface radius is set so both leaflets sit at roughly one bead of arc per lipid, and the
    split between leaflets follows the ratio of their radii so neither is over-packed.
    """
    if d != 2:
        raise ValueError("ring planting is 2-D; use plant='random' in 3-D")
    n = len(mols)
    # `chains` counts TAILS (4), but a lipid occupies 1 + n_tail = 5 beads. Using the tail count put
    # the outer leaflet's innermost bead at R_mid + 4 - 4 = R_mid and the inner leaflet's at
    # R_mid - 4 + 4 = R_mid, i.e. BOTH exactly on the mid-surface, so the two leaflets' tail tips
    # coincided wherever their angles happened to line up: 25 pairs of beads at separation 0.000 and
    # 225 pairs inside 0.8 sigma, giving a planted energy of ~+800 eps/lipid against an equilibrium
    # near -20. No relaxation can repair exactly coincident beads, because the push direction d/r is
    # 0/0, so this had to be fixed in the geometry.
    nb = int(max(len(m) for m in mols))
    nt = nb - 1
    # How far the lipid actually reaches INWARD from its head. A branched lipid has nt//2 beads per
    # branch, so it reaches 0.866 + (half - 1), not nb - 1. Using nb - 1 for a 4-tail branched lipid put
    # the leaflets 5.26 sigma apart, leaving the two annuli disconnected: largest read 178/300 and the
    # leaflet metric collapsed to 0.137 because it was measuring half a ring off-centre.
    half = nt // 2 if branched and nt >= 2 else nt
    reach = (0.866 + (half - 1)) if (branched and nt >= 2) else float(nt)
    half_gap = 0.5                                  # tail tips of the two leaflets TOUCH, not overlap
    # A branched lipid puts its two tails side by side at +-0.5, so its lateral footprint is about
    # 2 sigma, not 1. Spacing the leaflets for a single-file chain left neighbouring lipids' tails
    # 0.03-0.05 sigma apart -- 600 pairs inside 0.8 sigma on the ring -- which the push-off then fought
    # against the attractive well, driving E/lipid from 21 to 1548 on the flat plant.
    lat = 2.0 if (branched and nt >= 2) else 1.0
    # An arc spreads the same lipid count over `span` of the circle, so its radius must grow by 1/span
    # or the lipids are compressed: at span 0.75 the arc still had 596 pairs inside 0.8 sigma when the
    # ring had none.
    R_mid = n * lat / (4.0 * np.pi * max(span, 1e-9))
    R_out = R_mid + half_gap + reach
    R_in = max(R_mid - half_gap - reach, 0.6)
    n_out = int(round(n * R_out / (R_out + R_in)))
    k = 0
    for count, R_head, sgn in ((n_out, R_out, +1.0), (n - n_out, R_in, -1.0)):
        if count <= 0:
            continue
        # the arc keeps the SAME arc spacing as the closed ring, so a shorter span means a smaller
        # subtended angle at the same radius, not a stretched membrane
        # stagger the inner leaflet by half a spacing so the two leaflets never land on the same ray
        th = ((np.arange(count) + 0.5) / count * 2 * np.pi * span
              + (np.pi / count if sgn < 0 else 0.0))
        rhat = np.stack([np.cos(th), np.sin(th)], axis=1)
        that = np.stack([-np.sin(th), np.cos(th)], axis=1)          # tangent, for the second tail
        for j in range(count):
            idx = mols[k + j]
            nt = len(idx) - 1
            half = nt // 2 if branched else nt
            X[idx[0]] = rhat[j] * R_head
            if not branched or nt < 2:
                for b in range(1, len(idx)):
                    X[idx[b]] = rhat[j] * (R_head - sgn * b)
                continue
            # Two tails SIDE BY SIDE, not end to end. Laying all beads along one ray made the bond from
            # the head to the first bead of the SECOND branch span 3 sigma against a rest length of 1,
            # so every planted lipid carried ~800 eps of spring strain and the run began by snapping
            # back rather than by doing dynamics. The 0.866 radial offset with a +-0.5 lateral one puts
            # both first tail beads at exactly 1 sigma from the head.
            for c in range(2):
                for b in range(half):
                    X[idx[1 + c * half + b]] = (rhat[j] * (R_head - sgn * (0.866 + b))
                                                + that[j] * (c - 0.5))
        k += count


def _unwrapped_centroid(P, L, rounds=2):
    """Centroid of a compact cluster under periodic boundaries.

    A plain mean of WRAPPED coordinates is not the centroid: a cluster straddling a boundary has half
    its beads near 0 and half near L, so the mean lands at L/2, in empty space. Every radius is then
    measured from a point outside the object, and minimum-image wrapping of the displacement HIDES it
    because each radius still comes out below L/2 and still looks plausible.

    Measured on a planted shell (`_cvcontrol.py`): a straddling copy of a shell whose true CV is 0.121
    scored 0.053, because the radii all became about L/2*sqrt(3) and the spread was divided by that
    inflated mean. The bias is toward LOW CV, which is the direction that reads as a tight vesicle.

    Unwrapping relative to one bead and re-centring twice is exact for any cluster smaller than half
    the box, which is the regime every aggregate here is in.
    """
    c = P[0]
    for _ in range(rounds):
        c = (c + _wrap(P - c, L).mean(axis=0))
    return c


def relax_overlaps(X, f, L, target=0.85, max_iter=4000, cap=0.02):
    """Push coincident beads apart BEFORE dynamics starts, using the repulsive core only.

    Every planted structure in this project was built with beads on top of one another: minimum
    non-bonded separation 0.000 for the ring and the arc, 0.057 for the sphere, with 225, 1441 and 622
    pairs inside 0.8 sigma. Planted energy was about +800 eps/lipid against an equilibrium near -20, so
    the first few hundred steps were an explosion rather than dynamics -- which is enough on its own to
    scramble the leaflets, and every planted-structure result had that confound baked in.

    This is steepest descent on the CORE term alone with a per-step displacement cap: it separates
    overlaps without letting the attractive well pull the structure into a new shape, so the planted
    geometry is preserved while the artefact is removed. Attraction is excluded deliberately -- relaxing
    the full energy would let the structure reorganize, which is the thing the experiment is supposed to
    measure rather than to prearrange.
    """
    for _ in range(max_iter):
        d, r, (pi, pj) = f._pairs(X)
        bad = r < target
        if not bad.any():
            break
        _, duc = _core_only(r[bad] / f.sigma, f.core_height)
        step = np.clip(-duc / f.sigma, -cap, cap)[:, None] * (d[bad] / np.maximum(r[bad], 1e-12)[:, None])
        # d = X[pi] - X[pj], so d/r points from j toward i: i moves ALONG it, j against it. The first
        # version had these reversed, which pulled overlapping beads together and took planted energy
        # from +800 to +2674 eps/lipid.
        np.add.at(X, pi[bad], step)
        np.add.at(X, pj[bad], -step)
    return X


def _core_only(s, height):
    from field import _core
    return _core(s, height)


def geometry(X, mols, wi, chains, L, d, members=None):
    """Shell geometry, leaflet assignment, lumen occupancy and per-leaflet composition.

    Scored on the LARGEST CLUSTER, not on every lipid. Averaging over all lipids reports how spread
    out the whole population is rather than whether the aggregate is a shell: in the 3-D emergence
    runs the largest cluster held 119-126 of 300 lipids, so two thirds of the beads scored sat in
    other aggregates. On a planted shell with 180 loose lipids added elsewhere that inflated CV by
    4.2x (`_cvcontrol.py`). Where the system IS one aggregate -- every planted ring and vesicle -- the
    largest cluster is all of it and this changes nothing, so the planted numbers carry over.
    """
    if members is None:
        members = largest_members(X, mols, L)
    mols = [mols[i] for i in members]
    chains = chains[members]
    heads = np.array([m[0] for m in mols])
    tailc = np.array([X[m[1:]].mean(axis=0) for m in mols])
    lipid_beads = np.concatenate(mols)
    cen = _unwrapped_centroid(X[lipid_beads], L)

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

    rel_all = _wrap(X[lipid_beads] - cen, L)
    rt = np.linalg.norm(rel_all, axis=1)
    rt_all = np.linalg.norm(_wrap(X - cen, L), axis=1)      # per-bead radii, indexed by global id
    R_mid = float(np.median(rt))

    # A cluster wider than half the box has no unambiguous centroid under periodic boundaries: the
    # minimum image cannot tell "one big ring" from "two pieces near opposite faces". Returning a
    # number anyway is how a planted, obviously hollow ring came back as hollow = 1.556 in a box of
    # L = 70 with a diameter of 50.7. Fail loudly instead of plausibly.
    #
    # The test is the cluster's SPAN per axis, not 2*max(radius). The first version used the radius of
    # the furthest bead, which one lipid poking out of an otherwise intact ring is enough to trip: it
    # rejected 3 of 5 explicit seeds whose rings were whole at largest = 300, R_mid 25.98. The span is
    # what unwrapping actually needs to be unambiguous.
    # `core` and `burial` are computed from PAIRWISE distances only -- no centroid, no radius, no
    # mid-surface -- so the centroid ambiguity this guard exists for cannot affect them. NaN-ing them
    # alongside the centroid-dependent quantities discarded exactly the LARGEST aggregates (85, 89, 62,
    # 58, 95 lipids) and biased every reported mean toward the small ones, which matters because
    # thickening is size-dependent. They are now computed before the guard and returned through it.
    _hb = np.concatenate([m[:1] for m in mols])
    _tb = np.concatenate([m[1:] for m in mols])
    _d = np.linalg.norm(_wrap(X[_tb][:, None, :] - X[_hb][None, :, :], L), axis=2)
    core_pre = float(_d.min(axis=1).mean())
    _P = X[lipid_beads]
    _nn = (np.linalg.norm(_wrap(_P[:, None, :] - _P[None, :, :], L), axis=2) < 2.0).sum(axis=1) - 1
    _hm = np.isin(lipid_beads, _hb)
    burial_pre = float(_nn[~_hm].mean() - _nn[_hm].mean())

    span = (rel_all.max(axis=0) - rel_all.min(axis=0)) if len(rel_all) else np.zeros(1)
    if float(span.max()) > 0.5 * L:
        return dict(f_out=f_out, f_in=f_in, n_out=int(outer.sum()), n_in_leaf=int(inner.sum()),
                    R_mid=R_mid, shell_cv=float("nan"), hollow=float("nan"), mix=float("nan"),
                    seg=float("nan"), burial=burial_pre, core=core_pre,
                    lumen=float("nan"), lumen_w=0, r_in=float("nan"))
    shell_cv = float(rt.std() / max(rt.mean(), 1e-9))

    # Density in the inner third over density in the shell region: 0 = empty centre, ~1 = filled.
    # shell_cv is kept for continuity with the logged history but it is BLIND at this system size --
    # a planted hollow shell of this lipid at R_mid 5.71 scores 0.248 against a solid ball's 0.264,
    # a separation of 0.016 (`_cvdegenerate.py`). CV only discriminates while the membrane is thin
    # compared with the radius, and here they are the same size. `hollow` asks the question directly
    # and separates the two by about 1.0 at every radius tested.
    R95 = float(np.percentile(rt, 95))
    r_third = R95 / 3.0
    v_in = r_third ** d
    v_out = max(R95 ** d - v_in, 1e-12)
    n_core = float((rt < r_third).sum())
    n_shell = float(((rt >= r_third) & (rt < R95)).sum())
    hollow = float((n_core / v_in) / max(n_shell / v_out, 1e-12))

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
    # BILAYER ORDER, measured rather than eyeballed. For every head bead in the aggregate, the
    # fraction of its close non-bonded neighbours that are TAIL beads, divided by the tail fraction of
    # the aggregate. 1.0 = heads and tails randomly mixed; well below 1 = heads excluded from the tail
    # core, which is what a bilayer means. Needed because the implicit-solvent renders showed condensed
    # aggregates whose heads and tails were intermixed, and "it looks scrambled" is not a measurement.
    hb = np.concatenate([m[:1] for m in mols])
    tb = np.concatenate([m[1:] for m in mols])
    Pc = X[lipid_beads]
    dmat = _wrap(X[hb][:, None, :] - Pc[None, :, :], L)
    close = np.linalg.norm(dmat, axis=2) < 1.5
    is_tail = np.isin(lipid_beads, tb)
    own = np.isin(lipid_beads, hb)                       # do not count a head as its own neighbour
    close[:, own] &= ~np.eye(len(hb), len(lipid_beads), dtype=bool)[:, own]
    n_nb = close.sum(axis=1)
    n_tail_nb = (close & is_tail[None, :]).sum(axis=1)
    frac = n_tail_nb[n_nb > 0].sum() / max(n_nb[n_nb > 0].sum(), 1)
    mix = float(frac / max(is_tail.mean(), 1e-9))

    # LEAFLET ORDER as a LENGTH, in sigma: the signed radial offset of each head from its own tails,
    # with the leaflet taken from the MOLECULE centre. Calibrated against two controls -- a planted
    # bilayer reads 1.534 and is unchanged (1.518) under 1 sigma of positional jitter, while rigidly
    # rotating every lipid about its own centre reads 0.028.
    #
    # This replaces `mix` as the order observable. `mix` counts head-tail contacts, and the same jitter
    # control moves it 0.615 -> 0.840 with leaflet order fully intact, so it cannot separate a rough
    # bilayer from a disordered one. `mix` is still reported, but conclusions come from `seg`.
    #
    # Assigning the leaflet by the HEAD's own radius and then measuring the head's offset is circular:
    # a first version did that and its scrambled control scored 2.950 against an ordered 1.534.
    # BURIAL: are tails inside and heads at the surface? Geometry-agnostic -- no mid-surface, no radius,
    # no centre. Local neighbour count within 2 sigma for every aggregate bead; interior beads have more
    # neighbours than boundary ones, so <n_tail> - <n_head> is positive for ANY amphiphile aggregate:
    # ring, ribbon, micelle or vesicle. Calibrated: planted bilayer 7.178, still 5.220 under 1 sigma of
    # jitter, and 0.673 with every lipid rigidly rotated about its own centre.
    #
    # Needed because `seg` assumes a radial mid-surface and is therefore undefined for a flat RIBBON,
    # which is the morphology the corrected field actually produces, and meaningless for small solid
    # micelles (it returned negative values of -0.24 to -0.45 for 13-20 lipid clusters).
    Pc_all = X[lipid_beads]
    dd_b = _wrap(Pc_all[:, None, :] - Pc_all[None, :, :], L)
    nnb = (np.linalg.norm(dd_b, axis=2) < 2.0).sum(axis=1) - 1
    head_mask = np.isin(lipid_beads, np.concatenate([m[:1] for m in mols]))
    burial = float(nnb[~head_mask].mean() - nnb[head_mask].mean())

    # CORE DEPTH: mean distance from each TAIL bead to the nearest HEAD bead, in sigma. This is a LOCAL
    # thickness, so it is unaffected by the aggregate's overall shape. A bilayer keeps every tail within
    # about one lipid length of a head no matter how the sheet bends; a multilayer slab buries tails
    # deeper. The PCA minor-axis measure it replaces takes the whole aggregate's narrow extent, which
    # spans the entire arc for a CURVED ribbon -- it reported 16.8 against 11.3 for structures the render
    # shows to be dramatically thinner and cleaner.
    hb_all = np.concatenate([m[:1] for m in mols])
    tb_all = np.concatenate([m[1:] for m in mols])
    dht = np.linalg.norm(_wrap(X[tb_all][:, None, :] - X[hb_all][None, :, :], L), axis=2)
    core_depth = float(dht.min(axis=1).mean())

    rc_mol = np.array([rt_all[m].mean() for m in mols])
    rh_mol = np.array([rt_all[m[0]] for m in mols])
    rtl_mol = np.array([rt_all[m[1:]].mean() for m in mols])
    seg = float((np.where(rc_mol > R_mid, 1.0, -1.0) * (rh_mol - rtl_mol)).mean())

    return dict(f_out=f_out, f_in=f_in, n_out=int(outer.sum()), n_in_leaf=int(inner.sum()),
                R_mid=R_mid, shell_cv=shell_cv, hollow=hollow, mix=mix, seg=seg, burial=burial, core=core_depth,
                lumen=lumen, lumen_w=n_in, r_in=r_in)


def _wrap(v, L):
    return v - L * np.round(v / L)


def _cluster_labels(X, mols, L, cut=1.4):
    """Connected-component label per molecule, linked BEAD to bead.

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
    return lab


def largest_cluster(X, mols, L, cut=1.4):
    """Size of the largest aggregate, in molecules."""
    return int(np.bincount(_cluster_labels(X, mols, L, cut)).max())


def largest_members(X, mols, L, cut=1.4):
    """Indices of the molecules in the largest aggregate."""
    lab = _cluster_labels(X, mols, L, cut)
    return np.flatnonzero(lab == int(np.bincount(lab).argmax()))


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

    X, species, bonds, mols, wi, chains = build(n_short, n_long, n_water, L, d,
                                                plant=("random" if plant.startswith("state:") else plant),
                                                branched=True, seed=seed)
    if plant.startswith("state:"):
        # Continue from a saved configuration. Needed to measure PERSISTENCE: the only enclosure this
        # project has found appeared at one checkpoint and was absent at the previous one, and waiting
        # for a fresh run to produce another takes 400000 steps. Restarting from the state that HAS the
        # enclosure, with different thermal seeds, measures directly how long it survives.
        _z = np.load(plant.split(":", 1)[1], allow_pickle=True)
        _lipn = lip_beads
        if len(_z["X"]) == len(X):
            X = _z["X"].copy()
        elif len(_z["X"]) >= _lipn:
            # Different bead count means a different BOX: water scales with area, so a state saved at
            # L = 60 has 1021 waters where L = 120 needs 8584. Transplant the LIPIDS and keep the freshly
            # placed water -- i.e. re-solvate the same membrane in a larger volume, which is what a
            # dilution quench physically is. The lipid configuration is carried over exactly.
            # UNWRAP with the state's OWN box before transplanting. Saved coordinates are wrapped into
            # the old box, so a molecule whose bonds crossed the old periodic boundary is torn apart by
            # ~L_old in the new, larger box -- the minimum image no longer reconnects it, and the bond
            # springs then dominate everything (E/lipid came out at 37578).
            _Lold = float(_z["L"])
            _Xs = _z["X"][:_lipn].copy()
            for _m in mols:
                _ref = _Xs[_m[0]]
                _Xs[_m] = _ref + (_Xs[_m] - _ref) - _Lold * np.round((_Xs[_m] - _ref) / _Lold)
            # No further wrapping. A per-BEAD shift about the centroid re-tears the molecules that were
            # just unwrapped (E/lipid only fell 37578 -> 29631). Recentre rigidly instead, by molecule.
            _c = _Xs.mean(axis=0)
            _Xs = _Xs - _c
            X[:_lipn] = _Xs
            # The water was placed to avoid the ORIGINAL random lipids, so after transplanting it now
            # overlaps them -- E/lipid came out at 37634. Re-place it on a jittered lattice avoiding the
            # TRANSPLANTED positions, which is the same routine `build` uses.
            _nw = len(X) - _lipn
            if _nw:
                _rng = np.random.default_rng(seed + 991)
                _occ = min(0.9, _lipn / max(L ** d / C_D[d] * (2 ** d), 1.0))
                _per = int(np.ceil((_nw * (1.6 + 3.0 * _occ)) ** (1.0 / d))) + 2
                _g = np.stack(np.meshgrid(*[np.linspace(-L / 2, L / 2, _per, endpoint=False)] * d,
                                          indexing="ij"), axis=-1).reshape(-1, d)
                _g = _g + _rng.uniform(-0.15, 0.15, size=_g.shape)
                _dd = _g[:, None, :] - X[:_lipn][None, :, :]
                _dd -= L * np.round(_dd / L)
                _free = np.linalg.norm(_dd, axis=2).min(axis=1) > 0.9
                _cand = _g[_free]
                if len(_cand) < _nw:
                    raise ValueError(f"only {len(_cand)} free water sites for {_nw} after transplant")
                X[_lipn:] = _cand[_rng.choice(len(_cand), _nw, replace=False)]
            # The lattice rejects any site within 0.9 of a lipid, and a small lumen is mostly within
            # 0.9 of its OWN shell, so re-solvation leaves it systematically dry: the 41-lipid vesicle
            # measured lumen water 0.916 of bulk in its original state and 0.363 after transplanting.
            # A two-thirds-empty lumen collapses for osmotic reasons that have nothing to do with the
            # question any restart is asking, so fill it to bulk the same way a planted shell is.
            _moved = _fill_lumen_grid(X, wi, mols, L, np.random.default_rng(seed + 993))
            print(f"re-solvated: {_lipn} lipid beads transplanted, {_nw} fresh waters placed around them "
                  f"(state had {len(_z['X']) - _lipn}); {_moved} waters moved into the lumen", flush=True)
        else:
            raise ValueError(f"state has {len(_z['X'])} beads, fewer than {_lipn} lipid beads")
    # With phi = 0 there are no water beads, so the explicit chi is the WRONG table: it puts the
    # hydrophobic drive in head-water, and with the water deleted nothing makes a buried head costly.
    # The solvent-averaged (exchange-energy) chi restores that drive by integrating the solvent out
    # instead of dropping it. See `solvent_averaged_chi`.
    chi = solvent_averaged_chi() if phi == 0.0 else None
    f = Field(species, bonds, L, chi=chi)
    if plant != "random" and not plant.startswith("state:"):
        e0, r0 = f.energy(X) / n_lip, float(f._pairs(X)[1].min())
        X = relax_overlaps(X, f, L)
        print(f"steric push-off: E/lipid {e0:.1f} -> {f.energy(X) / n_lip:.1f}, "
              f"min non-bonded r {r0:.3f} -> {float(f._pairs(X)[1].min()):.3f}", flush=True)
    # INERTIAL at the validated dt = 8e-3: same energy, same equilibrium ensemble (verified against
    # the overdamped run over 5 seeds per rung), 28x more reduced time per minute end to end.
    dt = 8e-3
    # VIVARIUM_ENGINE=transformer runs the step as a transformer forward pass instead of calling the
    # integrator directly. The interaction term is then a sum of masked attention heads whose scores are
    # a query-key inner product with a distance bias, and the velocity-Verlet update is the residual
    # structure around it. Verified elsewhere to reproduce Inertial.step bit-for-bit on one step and to
    # match field.forces() to 1e-16 relative on this exact production topology; this flag is what lets
    # the same claim be tested on a full emergent run rather than on a single step.
    _engine = os.environ.get("VIVARIUM_ENGINE", "integrator")
    if _engine == "transformer":
        from transformer import VivariumTransformer
        _tf = VivariumTransformer(f)
        class _TransformerEngine:
            def __init__(self, tf, X, kT, dt, seed):
                self.tf, self.kT, self.dt = tf, kT, dt
                self.rng = np.random.default_rng(seed)
                self.v = self.rng.normal(size=X.shape) * np.sqrt(kT)
                self.F = tf.attention(X)

            def step(self, X):
                X, self.v, self.F = self.tf.forward(X, self.v, self.dt, self.kT,
                                                    rng=self.rng, F=self.F)
                return X

            def temperature(self):
                return float((self.v ** 2).mean())

        ig = _TransformerEngine(_tf, X, kT, dt, 1 + seed)
    else:
        # WHY THE SEED MATTERS -- separable at last. One argv seed has always fixed BOTH the initial
        # placement (`build(..., seed=seed)`) and the entire thermal-noise realisation (here), so no
        # experiment could tell which one decides whether a run forms a vesicle. Twelve seeds reproduce
        # their formation step exactly and nothing measurable at the eligibility crossing predicts the
        # lag, which leaves exactly this question open. VIVARIUM_NOISE_SEED overrides only the noise, so
        # placement and noise can be varied one at a time. Unset, behaviour is bit-identical to before.
        _noise = int(os.environ.get("VIVARIUM_NOISE_SEED", 1 + seed))
        ig = Inertial(f, kT, dt, seed=_noise)

    print(f"MIXTURE {d}-D: {n_short} short (2 tails) + {n_long} long (4 tails) + {n_water} water, "
          f"L={L}, packing fraction {phi}, kT={kT}, start={plant}", flush=True)
    # THE EFFECTIVE INTERACTION, NOT THE ONE YOU TYPED. chi scales an attractive well, so chi > 0 is
    # attraction and chi < 0 is repulsion -- but with explicit water the pair actually feels the
    # EXCHANGE energy chi_ij + chi_WW - chi_iW - chi_jW, because contact also creates a water-water
    # pair and destroys two solute-water pairs. The two can point OPPOSITE WAYS as a parameter is
    # swept: raising chi_HH from 0.20 to 0.60 at chi_WW = 0.50 moves effective head-head from -0.800
    # to -0.400, i.e. it HALVES the repulsion while looking like it raises it. Two ticks of a
    # multiplicity experiment were run backwards on exactly that misreading, so the effective matrix
    # is now printed next to the raw one at every launch.
    if phi > 0.0:
        _eff = solvent_averaged_chi(f.chi)
        print(f"  chi RAW      HH {f.chi[0,0]:+.2f}  HT {f.chi[0,1]:+.2f}  TT {f.chi[1,1]:+.2f}  "
              f"HW {f.chi[0,2]:+.2f}  TW {f.chi[1,2]:+.2f}  WW {f.chi[2,2]:+.2f}", flush=True)
        print(f"  chi EFFECTIVE (solvent-averaged, this is what the beads feel): "
              f"HH {_eff[0,0]:+.3f}  HT {_eff[0,1]:+.3f}  TT {_eff[1,1]:+.3f}   "
              f"[negative = repulsive]", flush=True)
    print("enrichment = (short fraction of OUTER leaflet) - (short fraction of INNER leaflet); "
          "0 = no partitioning", flush=True)
    print(f"{'step':>8}{'E/lip':>9}{'largest':>9}{'R_mid':>7}{'shellCV':>9}{'hollow':>8}{'mix':>7}{'seg':>7}{'burial':>8}{'core':>7}{'lumen_c':>9}{'nenc':>6}{'perc':>6}"
          f"{'lumen':>7}{'lumenW':>8}{'shortOUT':>10}{'shortIN':>9}   enrichment{'  nves':>6}{'  lumH2O':>8}", flush=True)
    # Checkpoint spacing was hardwired at steps/20, which ties resolution to run length: a 1.6M-step
    # run could only resolve a vesicle lifetime to 80 000 steps, and 8 of 12 measured episodes came out
    # at exactly one checkpoint -- the resolution floor rather than a measurement. Overridable so
    # lifetime and run length can be chosen independently.
    every = max(int(os.environ.get("VIVARIUM_CHECKPOINT_EVERY", steps // 20)), 1)
    for t in range(steps + 1):
        X = ig.step(X)
        if t % every == 0:
            g = geometry(X, mols, wi, chains, L, d)
            enr = g["f_out"] - g["f_in"]
            _sub = [mols[i] for i in largest_members(X, mols, L)]
            # One flood-fill, two readings: the largest enclosed pocket AND how many pockets
            # there are. A vesicle encloses exactly one; a finite branched tangle encloses
            # several and is non-percolating for the trivial reason that it fits in the box.
            _nenc, _sizes = n_enclosed(X, _sub, L)
            # Count vesicles across ALL clusters, not just the largest. The 48-lipid vesicle in seed 80
            # was only ever seen because it happened to BE the largest cluster; a small vesicle sitting
            # beside a bigger network was invisible to every rate measurement in this project. Closure
            # is encounter-limited, so small ribbons close soonest -- exactly the case being missed.
            _nves, _lumw = count_vesicles(X, mols, L, wi=wi)
            # Water occupancy of the enclosure, in units of bulk. Independent of the geometric lumen
            # ratio, which a planted vesicle can fail (0.118) while a marginal emergent case passes
            # (0.151). Appended LAST so no existing column index shifts.
            _lumh2o = max(_lumw) if _lumw else float("nan")
            print(f"{t:>8}{f.energy_solute(X) / n_lip:>9.2f}{largest_cluster(X, mols, L):>9}"
                  f"{g['R_mid']:>7.2f}{g['shell_cv']:>9.3f}{g['hollow']:>8.3f}{g['mix']:>7.3f}{g['seg']:>7.3f}{g['burial']:>8.3f}{g['core']:>7.3f}"
                  f"{(_sizes[0] if _sizes else 0):>9d}{_nenc:>6}{('Y' if percolates(X, _sub, L) else 'n'):>6}"
                  f"{g['lumen']:>7.2f}{g['lumen_w']:>8}"
                  f"{g['f_out']:>10.2f}{g['f_in']:>9.2f}   {enr:+.3f}{_nves:>6}{_lumh2o:>8.3f}", flush=True)
            _ptag = ("restart" + pathlib.Path(plant.split(":", 1)[1]).stem.split("_sd")[-1]
                     if plant.startswith("state:") else plant)
            shot(X, species, L, f"mix{d}d_{_ptag}_N{n_lip}_L{L:g}_{'sac' if phi == 0.0 else 'exp'}"
                 f"_kT{kT}_fs{frac_short}{_env_tag()}_sd{seed}_s{t:07d}")
            # Save state at EVERY checkpoint, overwriting. State was previously written only at the end,
            # so any new observable could be applied to a running experiment only by waiting for it to
            # finish -- which has cost several ticks. Overwriting keeps one file per run rather than
            # hundreds, and the render series already records the history.
            _save_state(X, species, chains, mols, L, d, phi, kT, frac_short, plant, n_lip, seed, steps)
            # VIVARIUM_SAVE_ALL preserves a tagged state at EVERY checkpoint, regardless of the gate.
            # Needed because hits are saved only when the detector FIRES, so any positive set built
            # from them is selected on the detector's own output -- which invalidated a detector ROC
            # attempted from hit files. Measuring a miss rate requires the misses to be on disk.
            if os.environ.get("VIVARIUM_SAVE_ALL"):
                _ad = pathlib.Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")) / "projects" / "vivarium" / "docs" / "allstates"
                _ad.mkdir(parents=True, exist_ok=True)
                _atag = "random" if plant.startswith("state:") else plant
                np.savez_compressed(_ad / f"all_{_atag}_N{n_lip}_L{L:g}{_env_tag()}_sd{seed}_s{t:07d}.npz",
                                    X=X, species=species, mols=np.array(mols, dtype=object),
                                    L=L, nves=_nves, largest=_largest_now if "_largest_now" in dir() else -1)
            if _nves > 0:
                # PRESERVE the state at every gate hit, tagged by step. The rolling checkpoint file is
                # overwritten, and hits are transient -- sd8003 hit at 360k-420k and by 480k its
                # aggregate enclosed nothing at any dilation, so the hit could not be adjudicated from a
                # state at all, only from a 760px render in which the responsible cluster could not be
                # identified. Without this, "every hit is render-adjudicated" is not a protocol that can
                # actually be run.
                _hd = pathlib.Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")) / "projects" / "vivarium" / "docs" / "hits"
                _hd.mkdir(parents=True, exist_ok=True)
                # Tag hits with plant and environment. Previously `hit_N{n}_L{L}_sd{seed}_s{step}`,
                # which collides across experiments: the reverse-closure arm and a random-start arm
                # both used N=160, L=65, seeds 9300-9309, so their hits shared a namespace and a
                # count taken from filenames over-reported formations by 5x. The log's `nves` column
                # was unaffected, but the filename is the provenance record and it was incomplete.
                np.savez_compressed(_hd / f"hit_{_ptag}_N{n_lip}_L{L:g}{_env_tag()}_sd{seed}_s{t:07d}.npz",
                                    X=X, species=species, chains=chains, L=L, d=d, phi=phi, steps=t,
                                    mols=np.array([m for m in mols], dtype=object))
    # Save the final state. Post-hoc analysis has had to RE-RUN the simulation three times in this
    # project because only images and printed metrics survived; a new observable then cannot be applied
    # to a finished experiment. Coordinates plus species and topology are enough to score anything.
    _save_state(X, species, chains, mols, L, d, phi, kT, frac_short, plant, n_lip, seed, steps)
