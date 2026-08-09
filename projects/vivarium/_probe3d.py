"""Test the two-tail requirement in 3-D, where it is physically grounded.

In 3-D a single tail is a CONE -- head area scales as r^2 against a fixed tail cross-section -- which
is exactly why nature needs two tails to make a cylinder. In strict 2-D a linear chain is already a
rectangle (measured: head width 1.00, tail width 1.14, ratio 0.87), so the requirement inverts and the
branched double tail becomes a wedge (ratio 0.52). Every 2-D result is consistent with that.

Falsifiable prediction: in 3-D the DOUBLE tail should beat the single tail on bilayer_frac -- the
reverse of the 2-D ordering. If it does not, the dimensional-inversion explanation is wrong.

The 3-D builder fills water to ~45% packing by construction, so these runs are submerged by design.
"""
import sys
import numpy as np
from bilayer3d import build
from harness import measure

tag, kw = sys.argv[1], eval(sys.argv[2])
steps = int(kw.pop("steps", 20000))
e = build(0, bound=4.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.55, spol=0.90,
          attract=1.0, polarity=0.80, head_q=1.2, bond_span=2.0, plant=False, **kw)
print(f"  {tag}: N={e.X.shape[0]} tokens, pd={e.pd}", flush=True)
for _ in range(steps):
    e.step()
m = measure(e)
print(f"RESULT {tag:<12}packing={m['packing']:<7.3f}splay={m['splay']:<7.3f}"
      f"wet={m['wet_frac']:<7.3f}solv={m['solvent_packing']:<7.3f}"
      f"bilayer_f={m['bilayer_frac']:<7.3f}head_enr={m['head_enrich']:<6.2f}", flush=True)
np.savez_compressed(
    f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/{tag}.npz",
    X=e.X, sigma=e.sigma, mol=e._mol, L=e.L, pd=e.pd)
