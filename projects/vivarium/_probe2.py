"""Lower the nucleation barrier by shrinking the box.

Why this should work. In a periodic box BOTH the droplet and the spanning bilayer are edge-free, so
neither pays edge energy -- but the path between them runs through a growing RIBBON, which does have
edges. That is the barrier, and its height scales with how long the ribbon has to be before it
closes on itself. A smaller box needs a shorter ribbon.

Lipid count follows the box, as always: a spanning bilayer needs box_width/contact molecules per
leaflet. Water is scaled to hold token density constant at the value the width-22 runs used (0.79
tokens per unit area), so concentration is not silently varying alongside size.

Smaller boxes are also much cheaper, which is why this is worth trying before more annealing.
"""
from bicelle2d import build
from experiment import sweep

LOG = "/home/rbao/quorum-thermolife/projects/vivarium/docs/sweeps_stage3.tsv"
DENS = 382 / (22.0 ** 2)          # tokens per unit area in the runs that stall
BASE = dict(kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, n_tail=2, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, plant="clump", repel=24.0)

def mk(bound):
    n_lip = int(round(2 * (2 * bound)))                    # 2 leaflets x width/contact
    n_water = max(8, int(round(DENS * (2 * bound) ** 2 - 3 * n_lip)))
    return build(7, bound=bound, n_lip=n_lip, n_water=n_water, **BASE)

sweep(mk, {"bound": [5.0, 6.5, 8.0]}, steps=60000, log_path=LOG, hot=0.02, cold=0.02,
      samples=(20000, 60000), label="smallbox")
