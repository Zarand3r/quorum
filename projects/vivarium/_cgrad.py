"""Does the curvature force equal -dU/dx of its own scalar term? Numerical gradient check."""
import numpy as np
from bicelle2d import build

e = build(0, plant="clump", attract=1.5, n_water=0, n_lip=20, bound=6.0, kt=0.02, speed=0.001,
          repel=12.0, k_bond=30.0, satt=0.30, n_tail=2, bond_span=2.0,
          polarity=0.80, head_q=1.2, hydrophobic=0.6)
e.curvature = 0.20
e.bend = 1.0
U0, F = e._curvature_energy_and_force()
h = 1e-6
worst = 0.0
for k in range(8):
    for c in range(e.pd):
        e.X[k, c] += h; up = e._curvature_energy_and_force()[0]
        e.X[k, c] -= 2 * h; dn = e._curvature_energy_and_force()[0]
        e.X[k, c] += h
        worst = max(worst, abs((-(up - dn) / (2 * h)) - F[k, c]))
print(f"U = {U0:.6f}")
print(f"max |analytic force - numerical -dU/dx| = {worst:.3e}")
print("PASS" if worst < 1e-4 else "*** GRADIENT CHECK FAILED ***")
