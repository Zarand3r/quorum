"""Render the ORACLE at beta = 0 with our own renderer, for a like-for-like morphology comparison.

The synthesis reached this tick is that our model reproduces the reference model's behaviour at
beta = 0: correct bilayers, correct curvature response, no closure. Coalescence, line tension,
fluidity and cluster diffusion are all now measured as comparable.

But the two are described differently in their own logs. The oracle at beta = 0 is classified "flat
sheet/disc"; ours is described as a branched network. Those may be the same object under two
classifiers, or a real remaining difference. The only way to tell is to look at both through the SAME
renderer, which has never been done -- every oracle result so far has been read from its shape column.

FALSIFICATION, STATED BEFORE THE RUN
    If the oracle at beta = 0 renders as a branched network of bilayer strands like ours, the synthesis
    holds and the two models agree at beta = 0. If it renders as large clean flat sheets where ours
    makes strands and micelles, then our model does NOT match the reference even at beta = 0, and the
    remaining gap is morphological rather than about spontaneous curvature.
"""

import sys

import numpy as np

from _mixture import shot
from bilipid import BiLipid
from field import HEAD, TAIL

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 400000
    beta = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    N, L = 300, 25.0

    s = BiLipid(N, L, beta=beta, seed=1)
    print(f"oracle at beta={beta}, N={N}, L={L}, {steps} steps", flush=True)
    every = max(steps // 8, 1)
    for t in range(steps + 1):
        if t % every == 0:
            x, _ = s.positions_species()
            # COORDINATE CONVENTION. bilipid wraps positions into [0, L); our renderer assumes them
            # centred on zero and cuts a slab about z = 0. Passing them through unchanged put the slab
            # in a corner of the box and rendered ~20 beads out of 600. Recentre on the aggregate's
            # own centre of mass under the minimum image, then slab through THAT -- a slab through a
            # fixed plane is meaningless for a structure free to sit anywhere in a periodic box.
            c = x - L * np.round((x - x[0]) / L)          # unwrap relative to one bead
            com = c.mean(axis=0)
            c = c - com
            sp = np.empty(len(c), dtype=np.int64)
            sp[0::2], sp[1::2] = HEAD, TAIL
            shot(c, sp, L, f"oracle_beta{int(beta * 100)}_s{t:07d}", slab=2.0)
            print(f"  t={t:>8}  rendered", flush=True)
        s.step()
