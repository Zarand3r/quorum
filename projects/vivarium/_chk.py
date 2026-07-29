import time
import numpy as np
from config import DEFAULTS, VivariumConfig
from polar_pack import PolarPackEngine
cfg = VivariumConfig(**{**DEFAULTS, "N": 380, "pos_dim": 3, "n_harmonics": 2, "pos_bound": 4.0})
e = PolarPackEngine(cfg, 0, water_frac=0.6, chain_frac=0.4, polarity=0.8, repel=12.0)
for _ in range(5): e.step()
def t(fn, n=20):
    fn(); t0=time.perf_counter()
    for _ in range(n): fn()
    return (time.perf_counter()-t0)*1000/n
print(f"  full snapshot()      {t(e.snapshot):6.1f} ms")
print(f"  _binding_edges()     {t(e._binding_edges):6.1f} ms   <- recomputed on EVERY poll")
print(f"  _contour()           {t(e._contour):6.1f} ms")
print(f"  one step()           {t(e.step):6.1f} ms")
