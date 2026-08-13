"""The three morphologies from the REAL Vivarium engine, in Vivarium's own rendering.

Uses `bicelle2d.build` -- the builder behind every 2-D result here -- and `fig2d.render`, so the
appearance is unchanged: faint blue water behind, blue heads, orange tails, metrics in the caption.

Why the attract value differs per row. The engine has two known regimes, both from fig2d.py:
attract 1.0 gives MICELLES and attract 1.5 gives BILAYERS. Curvature cannot turn a micelle into a
vesicle -- a micelle is already closed, just filled -- so the closure term is only meaningful in the
bilayer regime. The first sweep applied it at attract 1.0 and unsurprisingly changed nothing.

Start is `plant="clump"`, matching fig2d.py's published runs. The dispersed start is a harder and
slower problem; it produced micelles at 20k steps with the largest aggregate stuck at 19 of 63.
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster

BASE = dict(n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
            satt=0.30, n_tail=2, bond_span=2.0, n_water=250,
            polarity=0.80, head_q=1.2, hydrophobic=0.6)


def solvent_homogeneity(e, cells=6):
    """std/mean of water cell occupancy. Random null for 250 points on a 6x6 grid is 0.38."""
    w = e.X[e._wi, :e.pd]
    idx = (w / e.L * cells).astype(int) % cells
    flat = (idx * (cells ** np.arange(e.pd)[::-1])).sum(axis=1)
    n = np.bincount(flat, minlength=cells ** e.pd).astype(float)
    return float(n.std() / max(n.mean(), 1e-9))


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    cases = [
        (1.0, 0.00, "MICELLES  attract 1.0, curvature 0", "vivm_micelle"),
        (1.5, 0.00, "BILAYER   attract 1.5, curvature 0", "vivm_bilayer"),
        (1.5, 0.15, "attract 1.5, curvature 0.15", "vivm_cv015"),
        (1.5, 0.30, "attract 1.5, curvature 0.30", "vivm_cv030"),
    ]
    for at, cv, label, name in cases:
        e = build(0, plant="clump", attract=at, **BASE)
        e.curvature = cv
        for _ in range(steps):
            e.step()
        render(e, f"VIVARIUM t={steps} -- {label}", name)
        print(f"{name}: largest {len(largest_cluster(e))}/63 lipids, "
              f"solvent homogeneity {solvent_homogeneity(e):.2f} (null 0.38)", flush=True)
