"""Reviewer experiment B: does a FINITE bilayer patch bend and close on its own?

Now runnable for the first time, because the two physical prerequisites are fixed:
  * excluded volume -- `repel_sharp=8` keeps non-bonded beads at 0.96 of contact instead of 0.36;
  * molecular shape -- `head_sigma > 1` makes the lipid a cone, which is where spontaneous curvature
    comes from in a fundamental-force model rather than from an added coarse-grained term.

A spanning bilayer cannot curve; it is flat by boundary condition. A finite ribbon has two exposed
edges, and edge tension is what drives closure -- curvature only sets the preferred radius. So this
is the experiment that actually tests closure.

HYPOTHESIS     with the steric core fixed, a finite ribbon bends; with a cone-shaped lipid it bends
               more, and at some head_sigma it closes into a ring.
FALSIFICATION  if the ribbon stays flat or dissolves at every head_sigma, edge tension in this model
               is too weak to drive closure regardless of shape.
"""
import sys
import numpy as np
from bicelle2d import build
from fig2d import render, largest_cluster, measure
from ring_assay import classify

# k_bond must scale WITH the steric core. The historical 30.0 was tuned against a repulsion now known
# to be ~4x too weak; at the corrected core it loses to it and the molecule is pulled apart (bond mean
# 1.20 vs rest 1.0, DISQUALIFIED). A coupling the steric fix created, not a free knob.
BASE = dict(n_lip=60, bound=13.0, kt=0.02, speed=0.001, k_bond=120.0, satt=0.30,
            n_tail=2, bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2,
            hydrophobic=0.6, attract=1.5)


# NOTE. The first version of this file scored closure as end-to-end distance over contour length,
# with the molecules ordered by polar angle about the centroid. That is degenerate: sorting by angle
# produces a cycle for ANY compact aggregate, so a shapeless blob scores 0.02 exactly like a closed
# ring. It read 0.02 and 0.04 here while the renders showed wavy OPEN ribbons. Same centroid-based
# failure mode as the four false HOLLOW verdicts. Closure is now read by ring_assay.classify, the
# only topology instrument here with positive, negative and adversarial gates that pass.


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    for hs in (1.0, 1.4, 1.8, 2.2):
        e = build(0, plant="ribbon", span_frac=0.55, repel=12.0, sharp=8.0,
                  head_sigma=hs, **BASE)
        e.curvature = 0.0
        for _ in range(steps):
            e.step()
        m = measure(e)
        v, d = classify(e)
        render(e, f"finite ribbon, head_sigma={hs}, sharp core, t={steps}", f"patch_h{int(hs*10)}")
        print(f"head_sigma={hs:>4}  largest {len(largest_cluster(e)):>3}/60  bond {m['bond_mean']:.2f}  "
              f"ring_assay {v:<10} lumen/bulk {d.get('lumen_ratio', 0):.2f}  align {m['align']:.3f}  "
              f"{'ADMISSIBLE' if m['ok'] else m['why'][:26]}", flush=True)
