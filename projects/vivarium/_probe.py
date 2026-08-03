"""Stage 3, testing both blockers at once against a control we already have.

Fixed-kT control at repel 24, 44 lipids plateaus at splay 0.352 / spanning 0.68 -- short of the
0.30 / 0.80 thresholds and no longer improving between t=30k and t=60k. Two reasons it can stall
there, and they are independent:

  KINETIC TRAP. It condenses before it orders and then cannot rearrange. Annealing is the standard
  escape and has never been used in this project.

  NO MARGIN TO SPAN. 44 lipids is EXACTLY the minimum for a spanning bilayer -- 22 per leaflet at
  contact across a width-22 box -- so a single defect leaves a permanent gap and `spanning` cannot
  reach 0.80 however well ordered the rest is. A modest excess gives the membrane slack.

Runs at 60k, where the control had already flattened, so the comparison is like-for-like.
"""
from bicelle2d import build
from experiment import sweep

LOG = "/home/rbao/quorum-thermolife/projects/vivarium/docs/sweeps_stage3.tsv"
BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, bound=11.0, n_water=250, plant="clump",
            repel=24.0)

def mk(**p):
    return build(7, **{**BASE, **p})

# margin alone, then margin + annealing: which of the two blockers actually binds
sweep(mk, {"n_lip": [52]}, steps=60000, log_path=LOG, hot=0.02, cold=0.02,
      samples=(30000, 60000), label="margin-only")
sweep(mk, {"n_lip": [52]}, steps=60000, log_path=LOG, hot=0.30, cold=0.02,
      samples=(30000, 60000), label="margin+anneal")
