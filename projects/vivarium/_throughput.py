"""End-to-end throughput at 3-D vesicle scale, so the speedup claimed is the one actually delivered.

Rebuild cost and per-step force cost are different things. The cell list attacks the rebuild, which
happens only every few hundred steps; the integrator attacks the number of steps needed per unit of
physical time. Reporting either alone overstates the result.
"""
import time

import numpy as np

from _sizing3d import plant_flat
from field import Field
from integrate import Inertial, Overdamped

if __name__ == "__main__":
    n_side, L, kT = 12, 44.0, 0.17
    X0, species, bonds, mol = plant_flat(n_side, 2, L, 1.15)
    n = len(X0)
    print(f"3-D system, {n} beads, L={L}")
    print(f"{'integrator':>12}{'dt':>9}{'ms/step':>10}{'steps/sec':>11}"
          f"{'reduced time per minute':>26}")
    for name, cls, dt in (("overdamped", Overdamped, 2e-4), ("inertial", Inertial, 8e-3)):
        X = X0.copy()
        f = Field(species, bonds, L)
        ig = cls(f, kT, dt, seed=1)
        ig.step(X)                                  # warm the neighbour list
        t0 = time.perf_counter()
        N = 200
        for _ in range(N):
            X = ig.step(X)
        ms = (time.perf_counter() - t0) * 1000.0 / N
        sps = 1000.0 / ms
        print(f"{name:>12}{dt:>9.1e}{ms:>10.2f}{sps:>11.0f}{sps * 60 * dt:>26.1f}")

    # SKIN TRADEOFF. A larger skin puts more pairs in the list (raising per-step cost) but triggers
    # fewer rebuilds. The default 0.6 was chosen when steps were 40x smaller; at dt = 8e-3 beads cross
    # it far more often, which is why inertial costs MORE per step despite doing the same single force
    # evaluation. The optimum moves with the timestep.
    print()
    print(f"{'skin':>8}{'ms/step':>10}{'reduced time per minute':>26}")
    best = (None, 0.0)
    for skin in (0.6, 1.0, 1.5, 2.0, 3.0):
        X = X0.copy()
        f = Field(species, bonds, L)
        f.SKIN = skin
        ig = Inertial(f, kT, 8e-3, seed=1)
        ig.step(X)
        t0 = time.perf_counter()
        for _ in range(200):
            X = ig.step(X)
        ms = (time.perf_counter() - t0) * 1000.0 / 200
        rate = (1000.0 / ms) * 60 * 8e-3
        print(f"{skin:>8.1f}{ms:>10.2f}{rate:>26.1f}")
        if rate > best[1]:
            best = (skin, rate)
    print(f"\nbest skin {best[0]} at {best[1]:.1f} reduced time/min, "
          f"against 4.3 for the overdamped baseline -> {best[1] / 4.3:.0f}x end to end")
