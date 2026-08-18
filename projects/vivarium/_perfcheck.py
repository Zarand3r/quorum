import time
import numpy as np
from _sizing3d import plant_flat
from field import Field

def build_ms(n_side, L, dense=False):
    X, species, bonds, mol = plant_flat(n_side, 2, L, 1.15)
    f = Field(species, bonds, L)
    fn = f._rebuild_dense if dense else f._rebuild
    fn(X)
    t0 = time.perf_counter()
    for _ in range(3):
        fn(X)
    return (time.perf_counter() - t0) * 1000.0 / 3, len(X)

for label, dense in (("cell list", False), ("dense (the regression)", True)):
    ts, ns = build_ms(6, 22.0, dense)
    tb, nb = build_ms(9, 33.0, dense)
    growth = (tb / ts) / ((nb / ns) ** 2)
    print(f"{label:>24}: {ns:>4} beads {ts:6.2f} ms -> {nb:>4} beads {tb:7.2f} ms   "
          f"time x{tb/ts:5.2f} for size x{nb/ns:.2f}   quadratic fraction {growth:.2f}   "
          f"{'PASSES gate' if growth < 0.6 else 'TRIPS gate'}")

print()
print("at 3-D vesicle scale:")
for n_side, L in ((10, 37.0), (14, 51.0)):
    tc, n = build_ms(n_side, L, dense=False)
    td, _ = build_ms(n_side, L, dense=True)
    print(f"  {n:>5} beads:  cell list {tc:7.2f} ms   all-pairs {td:8.2f} ms   speedup x{td/tc:5.1f}")
