"""Timestep convergence: does the planted bilayer still disorder as dt -> 0?

Comparing runs at fixed STEP COUNT is meaningless because steps*speed is the physical time, so a
small-timestep run has simply evolved less. Held at the SAME physical time, a real phase instability
survives dt -> 0 while a numerical blowup vanishes. This is the test that decides whether every
"melts at kT=0" result was physics or arithmetic.
"""
import numpy as np
from bilayer3d import build, metrics

T = 16.0
print(f"  physical time T={T}, kT=0 (velocity MUST stay ~0)")
print(f"  {'speed':>8} {'steps':>7} {'|v|':>8} {'bond':>6} {'r13':>6} {'nematic':>8}")
for speed in (0.02, 0.005, 0.001, 0.0002):
    n = int(round(T / speed))
    e = build(seed=0, n_lip=142, bound=3.9, kt=0.0, speed=speed, repel=12.0, k_bond=8.0,
              satt=0.30, spol=0.90, plant=True, n_tail=2, head_q=0.0, rad_head=0.05, no_water=True)
    mol = e._mol
    for _ in range(n):
        e.step()
    b = np.linalg.norm(e.X[mol[:,0],:3]-e.X[mol[:,1],:3], axis=1).mean()
    r13 = np.linalg.norm(e.X[mol[:,0],:3]-e.X[mol[:,2],:3], axis=1).mean()
    v = float(np.linalg.norm(e.vel, axis=1).mean())
    print(f"  {speed:>8.4f} {n:>7d} {v:>8.4f} {b:>6.3f} {r13:>6.3f} {metrics(e)[2]:>+8.3f}", flush=True)
