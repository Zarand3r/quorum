"""Is the inverted topology a water-poor artefact? Sweep hydration at constant token density.

The engine's lipid configuration runs at 4.0 waters per lipid. Membrane simulations normally use
10-30, and below roughly 8 a water-in-oil (reverse) structure is the thermodynamically expected
phase rather than a defect. The observed structure -- heads lining an interior water pocket, tails
facing outward -- is exactly a reverse micelle, so the hypothesis is that full submersion inverts it.

Box size grows with the water count so TOKEN DENSITY is held at its original 0.907 per unit area.
Changing hydration and density together would confound the test.

Reported per run: whether heads face the aggregate's outside (the quantity actually in question),
the largest cluster, and solvent homogeneity.
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster

BASE = dict(n_lip=63, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
            n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6)
DENSITY = 439.0 / (2 * 11.0) ** 2          # tokens per unit area in the published configuration


def head_outward(e, comp):
    """Fraction of lipids in the largest cluster whose head points away from its centre.

    1.0 = normal (heads solvated, tails buried). 0.0 = inverted (reverse micelle).
    """
    mol = e._mol[comp]
    P = e.X[:, :e.pd]
    head, tailc = P[mol[:, 0]], P[mol[:, 1:]].mean(axis=1)
    u = head - tailc
    u -= e.L * np.round(u / e.L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    cen = P[mol.ravel()].mean(axis=0)
    rel = head - cen
    rel -= e.L * np.round(rel / e.L)
    r = np.linalg.norm(rel, axis=1)
    ok = r > 1e-9
    return float((np.einsum("ic,ic->i", u[ok], rel[ok] / r[ok][:, None]) > 0).mean())


def solvent_homogeneity(e, cells=6):
    w = e.X[e._wi, :e.pd]
    idx = (w / e.L * cells).astype(int) % cells
    flat = (idx * (cells ** np.arange(e.pd)[::-1])).sum(axis=1)
    n = np.bincount(flat, minlength=cells ** e.pd).astype(float)
    return float(n.std() / max(n.mean(), 1e-9))


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    cv = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
    for wpl in (4, 10, 20):
        nw = wpl * BASE["n_lip"]
        N = 3 * BASE["n_lip"] + nw
        bound = (N / DENSITY) ** 0.5 / 2.0
        e = build(0, plant="clump", attract=1.5, n_water=nw, bound=bound, **BASE)
        e.curvature = cv
        for _ in range(steps):
            e.step()
        comp = largest_cluster(e)
        render(e, f"VIVARIUM t={steps} curvature {cv} -- {wpl} waters/lipid", f"vivw_w{wpl:02d}")
        print(f"  {wpl:>2} waters/lipid (n_water {nw}, bound {bound:.1f}): "
              f"heads outward {head_outward(e, comp):.2f}  largest {len(comp)}/63  "
              f"solvent homog {solvent_homogeneity(e):.2f}", flush=True)
