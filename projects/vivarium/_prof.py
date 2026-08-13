"""Where does a step actually go at realistic N? Profile before optimising.

Earlier in this project an optimisation was aimed at np.add.at on the strength of a guess and bought
nothing; the real cost was elsewhere. Same discipline here.
"""
import cProfile, io, pstats
from bicelle2d import build

BASE = dict(n_lip=63, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
            n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6)
e = build(0, plant="clump", attract=1.5, n_water=630, bound=15.0, **BASE)
e.curvature = 0.15
for _ in range(3):
    e.step()
pr = cProfile.Profile(); pr.enable()
for _ in range(10):
    e.step()
pr.disable()
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(12)
print("\n".join(s.getvalue().split("\n")[4:20]))
