"""Validate this DPD implementation against the PUBLISHED equation of state before trusting physics.

Groot-Warren give p = rho*kT + alpha*a*rho^2 with alpha ~ 0.101 for a standard 3-D DPD fluid at
rho >= 3. That is a hard number my implementation must reproduce. Every membrane result so far --
planted bilayers melting at literature parameters -- is uninterpretable until this passes, because a
mis-scaled conservative force or virial would look exactly like "the membrane is unstable".

Also scans dt: at a = 80 the standard dt = 0.02 may be too large, which shows up as T drifting above
target rather than as a physical melt.
"""
import numpy as np
from dpd_reference import DPD

ALPHA, KT = 0.101, 1.0
print("Groot-Warren 3-D EOS check:  p = rho*kT + alpha*a*rho^2,  alpha ~ 0.101")
print(f"{'rho':>5}{'a':>5}{'p_pred':>9}{'p_meas':>9}{'ratio':>8}{'T':>7}   verdict")
for rho in (3.0, 4.0, 6.0):
    for a in (25.0, 50.0):
        n = 3000
        L = (n / rho) ** (1.0 / 3.0)
        d = DPD(n, L, kT=KT, a=a, dt=0.02, seed=0, dim=3)
        for _ in range(1500):
            d.step()
        P = np.mean([d.pressure() for _ in range(20) if not d.step()])
        pred = rho * KT + ALPHA * a * rho ** 2
        r = P / pred
        print(f"{rho:>5.1f}{a:>5.0f}{pred:>9.2f}{P:>9.2f}{r:>8.3f}{d.temperature():>7.2f}   "
              f"{'MATCHES' if 0.9 < r < 1.1 else '*** implementation disagrees ***'}", flush=True)

print()
print("timestep stability at strong repulsion (a=80), pure solvent:")
print(f"{'dt':>7}{'T@4k':>8}   verdict")
for dt in (0.04, 0.02, 0.01, 0.005):
    d = DPD(3000, (3000 / 3.0) ** (1.0 / 3.0), kT=KT, a=80.0, dt=dt, seed=0, dim=3)
    for _ in range(4000):
        d.step()
    T = d.temperature()
    print(f"{dt:>7.3f}{T:>8.2f}   {'ok' if abs(T - 1) < 0.15 else '*** UNSTABLE ***'}", flush=True)
