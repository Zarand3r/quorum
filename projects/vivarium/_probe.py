"""Calibrate the packing guard against planted references BEFORE trusting it.
A threshold that rejects a known-good bilayer is worse than no threshold at all.
"""
from harness import measure
from bicelle2d import build as build2d
from bilayer3d import build as build3d

print(f"  {'structure':<34}{'packing':>9}{'ok':>7}   why", flush=True)
cases = [
    ("2-D planted ribbon, t=0", lambda: build2d(0, n_lip=63, bound=11.0, kt=0.02, speed=0.0002,
        repel=6.0, k_bond=60.0, satt=0.30, n_tail=2, attract=2.0, bond_span=2.0, polarity=0.0,
        head_q=0.0, hydrophobic=0.6, n_water=250, plant="ribbon"), 0),
    ("2-D planted ribbon, relaxed", lambda: build2d(0, n_lip=63, bound=11.0, kt=0.02, speed=0.0002,
        repel=6.0, k_bond=60.0, satt=0.30, n_tail=2, attract=2.0, bond_span=2.0, polarity=0.0,
        head_q=0.0, hydrophobic=0.6, n_water=250, plant="ribbon"), 6000),
    ("3-D planted bilayer, t=0", lambda: build3d(seed=1, n_lip=48, bound=3.4, kt=0.02, speed=0.08,
        repel=12.0, k_bond=8.0, satt=0.55, spol=0.90, plant=True), 0),
    ("2-D collapsed run (repel 6)", lambda: build2d(0, n_lip=63, bound=11.0, kt=0.02, speed=0.0002,
        repel=6.0, k_bond=60.0, satt=0.30, n_tail=2, attract=2.0, bond_span=2.0, polarity=0.0,
        head_q=0.0, hydrophobic=0.6, n_water=250, plant="clump"), 60000),
    ("2-D repel 12 (pre-softening)", lambda: build2d(0, n_lip=63, bound=11.0, kt=0.02, speed=0.0002,
        repel=12.0, k_bond=60.0, satt=0.30, n_tail=2, attract=2.0, bond_span=2.0, polarity=0.0,
        head_q=0.0, hydrophobic=0.6, n_water=250, plant="clump"), 60000),
]
for name, mk, steps in cases:
    e = mk()
    for _ in range(steps):
        e.step()
    m = measure(e)
    print(f"  {name:<34}{m['packing']:>9.3f}{str(m['ok']):>7}   {m['why']}", flush=True)
