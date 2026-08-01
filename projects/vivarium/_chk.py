import time
import numpy as np
from bicelle2d import build

for tag, kw in (("no water,  polarity 0", dict(n_water=0, polarity=0.0, head_q=0.0)),
                ("water,     polarity 0", dict(n_water=120, polarity=0.0, head_q=0.0)),
                ("water,   polarity 0.8", dict(n_water=120, polarity=0.80, head_q=1.2))):
    e = build(0, n_lip=30, bound=7.5, kt=0.02, speed=0.004, repel=12.0, k_bond=80.0,
              satt=0.30, plant="clump", n_tail=4, attract=5.0, bond_span=2.0,
              branched=True, **kw)
    for _ in range(20): e.step()
    t0 = time.perf_counter()
    for _ in range(200): e.step()
    dt = time.perf_counter() - t0
    print(f"  N={e.cfg.N:4d}  {tag}:  {200/dt:7.1f} steps/s   ({dt*1000/200:.1f} ms/step)", flush=True)
