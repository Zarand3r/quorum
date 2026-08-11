import time, numpy as np, sys
sys.path.insert(0, "/home/rbao/quorum-thermolife/projects/vivarium")
from dpd_reference import DPD
for n in (1200, 6000):
    L = np.sqrt(n / 4.0)
    d = DPD(n, L, kT=1.0, a=25.0, seed=0)
    for _ in range(5): d.step()
    t0 = time.perf_counter()
    for _ in range(20): d.step()
    ms = (time.perf_counter() - t0) * 50
    print(f"  N={n:>5}  L={L:>5.1f}  {ms:>7.1f} ms/step   12k steps = {ms*12/1000:>5.1f} min")
