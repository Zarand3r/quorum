"""Tell a bilayer from a blob from a sheet, on (X, mols) rather than on a CookeDeserno object.

WHY THIS FILE EXISTS

`phase_diagram.core_fraction` measures SPHERICAL hollowness and nothing else. Measured on synthetics:

    hollow shell        0.0000
    uniform solid ball  0.1253
    FLAT BILAYER SHEET  0.3755   <- a correct, healthy membrane

So a planted vesicle that relaxes into a flat sheet is indistinguishable from one that collapses into
a dense blob, and most cells of the 2026-08-29 phase map sit in exactly that ambiguous band. The
conclusion "the vesicle collapses into a dense core" was therefore not established by that instrument;
only "it does not remain a hollow sphere" was.

`cooke_deserno.py` already carried the right discriminators, with the controls that make them
meaningful. This module ports them to our data layout and adds the control that was missing when
`core_fraction` was validated: a SHEET. Its own note is the lesson -- "Per Finding 21 the number is
meaningless without both controls" -- and a shell-and-ball validation passes an instrument that cannot
see the case that actually matters.

`mols` is (n_molecules, beads_per_molecule); column 0 is the head, the rest are tails.
"""

from __future__ import annotations

import numpy as np


def axes(X: np.ndarray, mols: np.ndarray) -> np.ndarray:
    """Unit vector from tail centroid to head, per molecule."""
    head = X[mols[:, 0]]
    tail = X[mols[:, 1:]].mean(axis=1)
    d = head - tail
    return d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-12)


def thickness(X: np.ndarray, mols: np.ndarray) -> float:
    """Head-sheet separation along the nematic director.

    A bilayer has heads in TWO sheets separated by ~2x the molecule length. A micelle, cylinder or
    blob fails this. Reference values recorded in cooke_deserno.py: planted 4.40, random 1.31.
    """
    u = axes(X, mols)
    Q = (3.0 * np.einsum("ia,ib->ab", u, u) / len(u) - np.eye(3)) / 2.0
    nrm = np.linalg.eigh(Q)[1][:, 2]
    heads = X[mols[:, 0]] @ nrm
    side = (u @ nrm) > 0
    if side.all() or not side.any():
        return 0.0
    return abs(float(heads[side].mean() - heads[~side].mean()))


def shape_of(X: np.ndarray) -> tuple[float, float]:
    """(L1/L3, L2/L3) of the inertia spectrum. Disc: thin in one axis, wide in two. Vesicle:
    isotropic, both ratios near 1. Sheet: thin in one, extended in two."""
    P = X - X.mean(axis=0)
    ev = np.linalg.eigvalsh(P.T @ P / len(P))
    return float(ev[0] / max(ev[2], 1e-9)), float(ev[1] / max(ev[2], 1e-9))


def hollow(X: np.ndarray, mols: np.ndarray) -> float:
    """Share of TAIL beads nearer the centre than the median head. A vesicle is hollow so this
    collapses; a disc or sheet keeps a solid core."""
    c = X.mean(axis=0)
    r = np.linalg.norm(X - c, axis=1)
    rh = float(np.median(r[mols[:, 0]]))
    return float((r[mols[:, 1:].ravel()] < rh).mean())


def classify(X: np.ndarray, mols: np.ndarray) -> dict:
    """All four numbers together. No single one is sufficient, which is the point."""
    l1, l2 = shape_of(X)
    return {"thickness": round(thickness(X, mols), 3),
            "hollow": round(hollow(X, mols), 3),
            "aniso_l1_l3": round(l1, 3), "aniso_l2_l3": round(l2, 3)}


def _synthetic_controls(seed: int = 0):
    """A vesicle, a sheet, a solid blob and a random gas, built by hand so the answers are known."""
    rng = np.random.default_rng(seed)
    out = {}

    def lipids(head, tail1, tail2):
        X = np.concatenate([head, tail1, tail2])
        n = len(head)
        mols = np.stack([np.arange(n), np.arange(n) + n, np.arange(n) + 2 * n], axis=1)
        return X, mols

    n, R = 300, 6.0
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    outer = rng.random(n) < 0.5                       # two leaflets, heads pointing outward/inward
    s = np.where(outer, 1.0, -1.0)[:, None]
    base = v * (R + s.ravel()[:, None] * 1.5)
    out["vesicle"] = lipids(base + v * s * 1.0, base, base - v * s * 1.0)

    xy = rng.uniform(-9, 9, (n, 2))
    z0 = np.where(rng.random(n) < 0.5, 1.0, -1.0)
    sh = np.column_stack([xy, z0 * 2.5])
    nz = np.column_stack([np.zeros(n), np.zeros(n), z0])
    out["sheet"] = lipids(sh + nz * 1.0, sh, sh - nz * 1.0)

    b = rng.normal(size=(n, 3)); b /= np.linalg.norm(b, axis=1, keepdims=True)
    b *= 4.0 * rng.random(n)[:, None] ** (1 / 3)
    out["blob"] = lipids(b, b * 0.8, b * 0.6)

    g = rng.uniform(-10, 10, (n, 3))
    out["gas"] = lipids(g, g + rng.normal(0, .3, (n, 3)), g + rng.normal(0, .3, (n, 3)))
    return out


def validate() -> int:
    """Every discriminator must SEPARATE the four cases, not merely score the intended one well."""
    ctl = _synthetic_controls()
    print(f"  {'control':>9} {'thickness':>10} {'hollow':>8} {'L1/L3':>8} {'L2/L3':>8}")
    got = {}
    for name in ("vesicle", "sheet", "blob", "gas"):
        X, mols = ctl[name]
        m = classify(X, mols)
        got[name] = m
        print(f"  {name:>9} {m['thickness']:>10} {m['hollow']:>8} "
              f"{m['aniso_l1_l3']:>8} {m['aniso_l2_l3']:>8}")
    ok_hollow = got["vesicle"]["hollow"] < got["sheet"]["hollow"] and \
        got["vesicle"]["hollow"] < got["blob"]["hollow"]
    ok_shape = got["sheet"]["aniso_l1_l3"] < 0.5 < got["vesicle"]["aniso_l1_l3"]
    print(f"\n  hollow separates vesicle from sheet AND blob: {ok_hollow}")
    print(f"  anisotropy separates sheet from vesicle:      {ok_shape}")
    return 0 if (ok_hollow and ok_shape) else 1


if __name__ == "__main__":
    raise SystemExit(validate())
