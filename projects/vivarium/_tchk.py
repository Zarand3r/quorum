import sys
sys.path.insert(0, "/home/rbao/quorum-thermolife/projects/vivarium")
import numpy as np
from _lit_dpd import make, order, SETS
print(f"{'set':>4}{'dt':>7}{'T@2k':>8}{'T@8k':>8}{'order@8k':>10}   note")
for pset in ("B",):
    for dt in (0.02, 0.01, 0.005):
        N, dim = 9000, 3
        L = (N / 3.0) ** (1.0 / 3.0)
        n_amph = int(2 * L * L / 1.30)
        d = make(n_amph, N, pset, dim, 1, planted=True)
        d.dt = dt
        for _ in range(2000): d.step()
        t2 = d.temperature()
        for _ in range(6000): d.step()
        print(f"{pset:>4}{dt:>7.3f}{t2:>8.2f}{d.temperature():>8.2f}{order(d, n_amph, 4, dim):>10.2f}"
              f"   {'UNSTABLE (T>>1)' if d.temperature() > 1.3 else 'thermostat ok'}", flush=True)
