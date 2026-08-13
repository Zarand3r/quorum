"""How does the engine scale with token count, and where does the time go?

Hydration sweeps are the immediate motivation: going from 4 to 20 waters per lipid raises N from
439 to 1449, and the engine builds dense (N, N) and (N, N, pd) tensors every step.
"""
import time
import numpy as np
from bicelle2d import build

BASE = dict(n_lip=63, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
            n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6)
DENSITY = 439.0 / 22.0 ** 2

print(f"{'w/lipid':>8}{'N':>7}{'ms/step':>10}{'steps/s':>9}{'vs N=439':>10}{'dense MB/step':>15}")
base = None
for wpl in (4, 10, 20, 30):
    nw = wpl * 63
    N = 189 + nw
    bound = (N / DENSITY) ** 0.5 / 2.0
    e = build(0, plant="clump", attract=1.5, n_water=nw, bound=bound, **BASE)
    e.curvature = 0.15
    for _ in range(3):
        e.step()
    t0 = time.time()
    for _ in range(20):
        e.step()
    ms = (time.time() - t0) / 20 * 1000
    base = base or ms
    # dense per-step traffic: delta (N,N,pd), d2/dist/mask/g/S_direct/S_comp (N,N) each
    mb = (N * N * e.pd * 8 + 6 * N * N * 8) / 1e6
    print(f"{wpl:>8}{N:>7}{ms:>10.1f}{1000/ms:>9.1f}{ms/base:>10.1f}x{mb:>14.0f}")
