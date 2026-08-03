"""First use of the new tooling: does annealing break the nucleation trap?

The phase is proven stable (planted bilayer holds at splay 0.071, packing 0.95, repel 48) and
fixed-kT self-assembly orders only slowly (splay 0.685 -> 0.614 -> 0.352 over 60k steps). If cooling
is the missing ingredient, the annealed runs should beat the hot==cold control, which is included as
the honest baseline rather than assumed.
"""
from bicelle2d import build
from experiment import sweep

LOG = "/home/rbao/quorum-thermolife/projects/vivarium/docs/sweeps_stage3.tsv"
BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, bound=11.0, n_water=250, plant="clump")

def mk(**p):
    return build(7, **{**BASE, **p})

for hot, tag in ((0.02, "control-fixed-kT"), (0.25, "anneal-0.25"), (0.60, "anneal-0.60")):
    sweep(mk, {"repel": [48.0], "n_lip": [44, 63]}, steps=60000, log_path=LOG,
          hot=hot, cold=0.02, samples=(20000, 40000, 60000), label=tag)
