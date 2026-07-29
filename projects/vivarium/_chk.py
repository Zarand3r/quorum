import time
from bilayer3d import build
for pol in (0.80, 0.0):
    e = build(seed=0, n_lip=231, bound=5.0, kt=0.0, speed=0.005, repel=12.0, k_bond=40.0,
              satt=0.30, spol=0.90, plant=True, n_tail=2, head_q=0.0, rad_head=0.0,
              no_water=True, aniso=0.0, polarity=pol)
    for _ in range(20): e.step()
    t0=time.perf_counter()
    for _ in range(200): e.step()
    dt=time.perf_counter()-t0
    print(f"polarity={pol}: {200/dt:.1f} steps/s ({dt*1000/200:.1f} ms/step)")
