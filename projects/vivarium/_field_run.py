"""Self-assembly under the single-scalar field. Does a membrane form when nothing tells it to?

The field has one energy scale, one length scale, no orientation term and no curvature term. Bead
orientation never enters the energy, so any curved or closed structure that appears did so from shape
and packing alone.

INTEGRATOR
    Overdamped Brownian dynamics, X += (F/gamma) dt + sqrt(2 kT dt / gamma) * N(0,1). Overdamped
    because the question is which structure is preferred, not what the dynamics look like on the way.
    The per-step displacement is REPORTED rather than capped: a cap would hide an unstable timestep by
    silently changing the equations, which is exactly the class of defect this rewrite exists to
    remove.

MEASUREMENT
    Topology is read by `ring_assay.classify`, whose positive, negative and adversarial gates pass. It
    is the only topology instrument in this project that has survived calibration. Packing is reported
    as median non-bonded separation over contact, the quantity whose value of 0.36 in the old engine
    turned out to explain the collapsed rings, and whose value of 0.15 showed that the historical
    "bilayers" were interpenetrating piles.
"""

from __future__ import annotations

import os
import sys

import numpy as np

from _shot import disc, write_png
from field import Field, HEAD, TAIL, WATER
from ring_assay import classify

W, H = 760, 560


def shot(X, species, L, title, sub, tag):
    """Draw the state. A structural claim in this project is not allowed without looking at it."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    img[:, :] = (14, 16, 22)
    scale = min(W, H) * 0.92 / L
    cx, cy = W * 0.5, H * 0.5
    order = [(WATER, (46, 72, 92), 0.55, 1.6), (TAIL, (232, 150, 62), 1.0, 3.0),
             (HEAD, (86, 160, 240), 1.0, 3.6)]
    for sp, rgb, alpha, rad in order:
        P = X[species == sp]
        for x, y in P:
            disc(img, cx + x * scale, cy - y * scale, rad, rgb, alpha)
    # `bazel run` executes in a runfiles tree, so a relative path lands somewhere unreachable and,
    # worse, silently different between invocation styles. BUILD_WORKSPACE_DIRECTORY is the source
    # tree bazel was invoked from.
    root = os.environ.get("BUILD_WORKSPACE_DIRECTORY", ".")
    out = os.path.join(root, "projects", "vivarium", "docs", "images", f"{tag}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_png(out, img)
    return out


class View:
    """Adapter exposing the field's state the way `ring_assay` expects an engine to look."""

    def __init__(self, X, mol, wi, L, pd):
        self.X, self._mol, self._wi, self.L, self.pd = X, mol, wi, L, pd


def build(n_lip, n_water, L, seed=0, n_tail=2, ribbon=True):
    rng = np.random.default_rng(seed)
    nb = 1 + n_tail
    n = n_lip * nb + n_water
    X = np.zeros((n, 2))
    species = np.empty(n, dtype=np.int64)
    mol = np.arange(n_lip * nb).reshape(n_lip, nb)
    species[mol[:, 0]] = HEAD
    species[mol[:, 1:]] = TAIL
    wi = np.arange(n_lip * nb, n)
    species[wi] = WATER

    if ribbon:
        # a finite double row: two leaflets, tails meeting, spanning about half the box
        per = n_lip // 2
        xs = (np.arange(per) - (per - 1) / 2.0) * 1.0
        for leaf, sgn in ((0, +1.0), (1, -1.0)):
            idx = mol[leaf * per:(leaf + 1) * per]
            for bead in range(nb):
                off = 0.5 + (nb - 1 - bead) * 1.0
                X[idx[:, bead], 0] = xs[:len(idx)]
                X[idx[:, bead], 1] = sgn * off
        rest = mol[2 * per:]
        if len(rest):
            X[rest.ravel()] = rng.uniform(-L / 2, L / 2, size=(rest.size, 2))
    else:
        for m in range(n_lip):
            c = rng.uniform(-L / 2, L / 2, size=2)
            u = rng.normal(size=2)
            u /= np.linalg.norm(u)
            for bead in range(nb):
                X[mol[m, bead]] = c + u * bead

    X[wi] = rng.uniform(-L / 2, L / 2, size=(n_water, 2))
    X -= L * np.round(X / L)
    bonds = np.concatenate([np.stack([mol[:, b], mol[:, b + 1]], 1) for b in range(nb - 1)])
    return X, species, bonds, mol, wi


def packing(X, mol, L):
    """Median nearest NON-BONDED lipid separation, over contact. 1.0 = beads just touching."""
    beads = mol.ravel()
    P = X[beads]
    d = P[:, None, :] - P[None, :, :]
    d -= L * np.round(d / L)
    r = np.linalg.norm(d, axis=2)
    same = np.repeat(np.arange(len(mol)), mol.shape[1])
    bonded = same[:, None] == same[None, :]
    r[bonded] = np.inf
    return float(np.median(r.min(axis=1)))


def head_outward(X, mol, L):
    """Fraction of lipids whose head points away from the aggregate centre. 1.0 = heads out."""
    P = X[mol]
    head, tail = P[:, 0, :], P[:, 1:, :].mean(axis=1)
    cen = P.reshape(-1, 2).mean(axis=0)
    u = head - tail
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    rel = head - cen
    rel -= L * np.round(rel / L)
    rn = np.linalg.norm(rel, axis=1)
    ok = rn > 1e-9
    return float((np.einsum("ic,ic->i", u[ok], rel[ok] / rn[ok][:, None]) > 0).mean())


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 200000
    n_lip = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    kT = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35
    ribbon = (sys.argv[4] if len(sys.argv) > 4 else "ribbon") == "ribbon"
    # n_tail sets the PACKING PARAMETER P = v / (a0 * l), the textbook determinant of phase: below
    # ~1/3 micelles, 1/2 to 1 bilayers. One head and two tails puts this lipid in the micelle band,
    # which is what N=60 produced at every box size -- one micelle when concentrated, several when
    # dilute. Lengthening the tail raises P through molecular composition, not through any imported
    # curvature, and is the emergent lever the oracle's beta was standing in for.
    n_tail = int(sys.argv[7]) if len(sys.argv) > 7 else 2

    # Box size from a physical AREA FRACTION, not from the old engine's token density. That density
    # (430 tokens / 13^2 = 2.544) was calibrated when beads sat at 0.15-0.36 of contact, and it puts
    # 300 unit-diameter beads above 2-D close packing (~1.155 per sigma^2), so overlap is forced by
    # the box before any force acts. Inheriting it is the same error as MIN_PACKING = 0.35.
    # SIZING. The oracle's mass-balance rule decides morphology by what the lipid count can AFFORD:
    # a spanning bilayer stripe costs 2L/s lipids, a closed ring of radius R costs 4 pi R / s, with
    # s the spacing per lipid along one leaflet. A ring only wins when the stripe is UNAFFORDABLE, so
    # the box is set from a target L and the water is whatever fills it at the chosen area fraction.
    # Holding water at 4x the lipid count instead pins L near the stripe threshold, which is why
    # N=60 at L=24.5 (stripe needs ~49) gave a micelle.
    phi = float(sys.argv[5]) if len(sys.argv) > 5 else 0.55       # liquid-like area fraction
    L = float(sys.argv[6]) if len(sys.argv) > 6 else float(np.sqrt(7 * n_lip * np.pi * 0.25 / phi))
    n_water = int(round(phi * L * L / (np.pi * 0.25))) - (1 + n_tail) * n_lip
    if n_water < 0:
        raise ValueError(f"L={L} too small to hold {n_lip} lipids at area fraction {phi}")
    n_beads = (1 + n_tail) * n_lip + n_water
    X, species, bonds, mol, wi = build(n_lip, n_water, L, n_tail=n_tail, ribbon=ribbon)
    f = Field(species, bonds, L)

    gamma, dt = 1.0, 2e-4
    rng = np.random.default_rng(1)
    amp = np.sqrt(2.0 * kT * dt / gamma)
    print(f"single-scalar field: N={n_lip} lipids (1 head + {n_tail} tails) + {n_water} water, L={L:.1f}, "
          f"area fraction {phi}, kT={kT} eps, dt={dt}, "
          f"start={'ribbon' if ribbon else 'random'}", flush=True)
    print(f"affordability: spanning stripe needs ~{2 * L:.0f} lipids, "
          f"closed ring of R={n_lip / (4 * np.pi):.1f} needs {n_lip} -- "
          f"{'RING favoured' if n_lip < 2 * L else 'stripe affordable'}", flush=True)
    print(f"gradient check {__import__('field').check_gradients():.2e}   "
          f"chi factorization {f.check_identity():.1e}", flush=True)
    print(f"{'step':>9}{'E/lipid':>10}{'packing':>9}{'headOut':>9}{'maxdisp':>9}   ring_assay",
          flush=True)
    every = max(steps // 10, 1)
    for t in range(steps + 1):
        F = f.forces(X)
        dX = (F / gamma) * dt + amp * rng.normal(size=X.shape)
        X += dX
        X -= L * np.round(X / L)
        if t % every == 0:
            v, d = classify(View(X, mol, wi, L, 2))
            print(f"{t:>9}{f.energy(X) / n_lip:>10.3f}{packing(X, mol, L):>9.2f}"
                  f"{head_outward(X, mol, L):>9.2f}{np.abs(dX).max():>9.4f}   {v} "
                  f"lumen/bulk {d.get('lumen_ratio', 0):.2f} frac {d.get('frac', 0):.2f}", flush=True)
            shot(X, species, L, "", "", f"field_N{n_lip}_t{n_tail}_s{t:07d}")
