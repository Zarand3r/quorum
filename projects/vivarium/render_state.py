"""Render a saved engine state to a cross-section, with its metrics in the caption.

Every experiment probe saves an .npz of the final state. Looking at those states is not optional here:
this project has ~25 measurement defects, and three claims were retracted in a single session because
a metric moved and nobody rendered the structure. The reading protocol is that a structural claim
needs an image AND validated metrics AND the planted reference on the same axes.

The caption carries `bilayer_frac` (planted ribbon 0.984, planted micelle 0.000) alongside splay and
head enrichment, so the picture and the numbers are never separated.

Usage:
    bazel run //projects/vivarium:render_state -- --state docs/runs/states/P_h10.npz \
        --lipids 63 --water 250 --out docs/images/P_h10
"""

from __future__ import annotations

import argparse
import os

import numpy as np

from bicelle2d import build
from bilayer3d import build as build3d
from harness import measure
from xsection import cross_section

BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, plant=False)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", required=True, help="path to a saved .npz state")
    p.add_argument("--out", required=True, help="output path WITHOUT extension")
    p.add_argument("--lipids", type=int, default=63)
    p.add_argument("--water", type=int, default=250)
    p.add_argument("--bound", type=float, default=11.0)
    p.add_argument("--repel", type=float, default=12.0)
    p.add_argument("--head-sigma", type=float, default=1.0)
    p.add_argument("--tails", type=int, default=2)
    p.add_argument("--branched", action="store_true")
    p.add_argument("--title", default="")
    p.add_argument("--dim3", action="store_true", help="state came from bilayer3d")
    a = p.parse_args()

    z = np.load(a.state)
    if a.dim3:
        e = build3d(0, n_lip=a.lipids, bound=a.bound, repel=a.repel, satt=0.55, spol=0.90,
                    head_sigma=a.head_sigma, n_tail=a.tails, branched=a.branched,
                    kt=0.02, speed=0.001, k_bond=30.0, attract=1.0, polarity=0.80,
                    head_q=1.2, bond_span=2.0, plant=False)
    else:
        e = build(7, n_lip=a.lipids, n_water=a.water, bound=a.bound, repel=a.repel,
                  head_sigma=a.head_sigma, n_tail=a.tails, branched=a.branched, **BASE)
    if e.X.shape != z["X"].shape:
        raise SystemExit(
            f"state shape {z['X'].shape} does not match a dish built with "
            f"{a.lipids} lipids and {a.water} water ({e.X.shape}). The geometry flags must match the "
            f"run that produced the state, or the render shows a different molecule than the metrics.")
    e.X[:] = z["X"]
    m = measure(e)
    title = a.title or os.path.basename(a.state).rsplit(".", 1)[0]
    cross_section(e, a.out, title=title,
                  sub=(f"bilayer_frac {m['bilayer_frac']:.3f} (ribbon 0.984 / micelle 0.000)   "
                       f"splay {m['splay']:.3f}   packing {m['packing']:.3f}   "
                       f"wet_frac {m['wet_frac']:.2f}"))
    print(f"{title}: bilayer_frac {m['bilayer_frac']:.3f}  splay {m['splay']:.3f}  "
          f"packing {m['packing']:.3f}  wet_frac {m['wet_frac']:.2f}  -> {a.out}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
