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


def build(n_short, n_long, n_water, L, d, tails=(2, 4), seed=0, plant="random"):
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
        for b in range(1 + t):
            X[idx[b]] = c + u * b
        mols.append(idx)
        bonds += [[idx[b], idx[b + 1]] for b in range(t)]
        k += 1 + t
    if plant == "ring":
        _plant_ring(X, mols, np.array(chains), d)
    elif plant == "sphere":
        _plant_sphere(X, mols, np.array(chains), d)
    elif plant.startswith("arc"):
        # `arc0.75` plants three quarters of a ring: a bilayer with TWO EXPOSED ENDS at the same
        # curvature the closed state prefers. The question is whether edge tension pulls the ends
        # together. This is only meaningful now that the closed ring is known to be stable -- run
        # before that, a failure to close could not be distinguished from the target not existing.
        _plant_ring(X, mols, np.array(chains), d, span=float(plant[3:] or 0.75))
    wi = np.arange(k, n)
    species[wi] = WATER
    X[wi] = rng.uniform(-L / 2, L / 2, size=(n_water, d))
    X -= L * np.round(X / L)
    return X, species, np.array(bonds), mols, wi, np.array(chains)


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
    # area per lipid measured on a spanning slab in the reference model
    a = 1.5
    R_mid = float(np.sqrt(n * a / (4.0 * np.pi)))
    R_out, R_in = R_mid + lip / 2, max(R_mid - lip / 2, 0.8)
    n_out = int(round(n * (R_out ** 2) / (R_out ** 2 + R_in ** 2)))
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

    n_short = int(round(n_lip * frac_short))
    n_long = n_lip - n_short
    lip_beads = n_short * 3 + n_long * 5
    n_water = int(round(phi * L ** d / C_D[d] * (2 ** d))) - lip_beads
    if n_water < 0:
        raise ValueError(f"L={L} too small for {n_lip} lipids at packing fraction {phi}")

    X, species, bonds, mols, wi, chains = build(n_short, n_long, n_water, L, d, plant=plant)
    f = Field(species, bonds, L)
    gamma, dt = 1.0, 2e-4
    rng = np.random.default_rng(1)
    amp = np.sqrt(2.0 * kT * dt / gamma)

    print(f"MIXTURE {d}-D: {n_short} short (2 tails) + {n_long} long (4 tails) + {n_water} water, "
          f"L={L}, packing fraction {phi}, kT={kT}, start={plant}", flush=True)
    print("enrichment = (short fraction of OUTER leaflet) - (short fraction of INNER leaflet); "
          "0 = no partitioning", flush=True)
    print(f"{'step':>8}{'E/lip':>9}{'largest':>9}{'R_mid':>7}{'shellCV':>9}{'lumen':>7}"
          f"{'lumenW':>8}{'shortOUT':>10}{'shortIN':>9}   enrichment", flush=True)
    every = max(steps // 20, 1)
    for t in range(steps + 1):
        X += (f.forces(X) / gamma) * dt + amp * rng.normal(size=X.shape)
        X -= L * np.round(X / L)
        if t % every == 0:
            g = geometry(X, mols, wi, chains, L, d)
            enr = g["f_out"] - g["f_in"]
            print(f"{t:>8}{f.energy(X) / n_lip:>9.2f}{largest_cluster(X, mols, L):>9}"
                  f"{g['R_mid']:>7.2f}{g['shell_cv']:>9.3f}{g['lumen']:>7.2f}{g['lumen_w']:>8}"
                  f"{g['f_out']:>10.2f}{g['f_in']:>9.2f}   {enr:+.3f}", flush=True)
            shot(X, species, L, f"mix{d}d_{plant}_N{n_lip}_s{t:07d}")
