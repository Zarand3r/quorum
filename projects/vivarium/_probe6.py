"""Is `speed` a playback rate, as the viewer tooltip claims, or does it change the physics?

viewer.html advertises speed as "TIME-STEP / playback rate -- NOT physics; just how fast you watch the
same dynamics." In pack.py the deterministic displacement is scaled by speed:

    p = X + self.speed * self.vel                                   # drift  ~ speed
    p = p + _THERMAL * self.temperature * randn(...)                # noise  ~ speed^0

The thermal kick is NOT scaled by speed, so speed sets the drift-to-diffusion ratio, i.e. the
effective temperature. Correct Brownian scaling is drift ~ dt and noise ~ sqrt(dt); here noise is
constant per STEP rather than per unit time.

Falsifiable test at matched PHYSICAL time (speed * steps held constant):
  - at kT = 0 the two speeds should agree, because with no noise speed IS a pure time rescale;
  - at kT > 0 they should diverge, and the SLOWER run should look hotter (relatively more noise per
    unit physical time).
If both pairs agree the tooltip is right and this file is wrong.
"""
import sys
import numpy as np
from bicelle2d import build
from harness import measure

BASE = dict(bound=11.0, kt=0.02, speed=0.001, k_bond=30.0, satt=0.30, attract=1.0, bond_span=2.0,
            polarity=0.80, head_q=1.2, hydrophobic=0.6, repel=12.0, n_water=250, plant=False,
            n_lip=63, n_tail=2)

def exposed(e):
    mol = e._mol
    tails, water = mol[:, 1:].ravel(), np.setdiff1d(np.arange(e.X.shape[0]), mol.ravel())
    d = e.X[tails][:, None, :e.pd] - e.X[water][None, :, :e.pd]
    d -= e.L * np.round(d / e.L)
    cut = 1.3 * (e.sigma[tails][:, None] + e.sigma[water][None, :])
    return float((np.linalg.norm(d, axis=2) < cut).any(axis=1).mean())

tag, kw = sys.argv[1], eval(sys.argv[2])
steps = int(kw.pop("steps"))
e = build(7, **{**BASE, **kw})
for _ in range(steps):
    e.step()
m = measure(e)
print(f"RESULT {tag:<14}kt={kw.get('kt', BASE['kt']):<6}speed={kw.get('speed', BASE['speed']):<8}"
      f"steps={steps:<7}phys={kw.get('speed', BASE['speed'])*steps:<7.1f}"
      f"splay={m['splay']:<8.3f}packing={m['packing']:<8.3f}align={m['align']:<8.3f}"
      f"exposed={exposed(e):<7.3f}", flush=True)
