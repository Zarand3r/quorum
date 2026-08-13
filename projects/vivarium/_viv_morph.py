"""Emergent morphologies from the REAL Vivarium engine, rendered in Vivarium's own style.

Uses `bicelle2d.build` -- the same builder every 2-D result in this project was produced with, and
the one behind the four-micelle figure -- and `fig2d.render`, so the appearance (faint blue water
behind, blue heads, orange tails, metrics in the caption) is unchanged.

The only new variable is `curvature`, the spontaneous-curvature term added to PackEngine. Everything
else is fig2d.py's published configuration. The sweep is the experiment: with the term at zero this
engine has only ever produced micelles and open bilayer ribbons, because nothing in it could prefer
one face of a membrane over the other.

Starting configuration is DISPERSED (plant=False), so every structure below is self-assembled rather
than planted.
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import render

BASE = dict(n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
            satt=0.30, n_tail=2, bond_span=2.0, n_water=250,
            polarity=0.80, head_q=1.2, hydrophobic=0.6)


def run(curvature, attract, steps, seed=0, tag="viv"):
    e = build(seed, plant=False, attract=attract, **BASE)
    e.curvature = float(curvature)
    for _ in range(steps):
        e.step()
    return e


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    cases = [
        # (curvature, attract, label, filename)
        (0.00, 1.0, "curvature 0.00 (baseline: the engine as it was)", "viv_c000"),
        (0.15, 1.0, "curvature 0.15", "viv_c015"),
        (0.30, 1.0, "curvature 0.30", "viv_c030"),
        (0.15, 1.5, "curvature 0.15, attract 1.5", "viv_c015_a15"),
    ]
    for cv, at, label, name in cases:
        e = run(cv, at, steps)
        render(e, f"VIVARIUM, dispersed start, t={steps} -- {label}", name)
        print(f"{name}: rendered", flush=True)
