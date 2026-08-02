"""Do micelles form in 3-D? Affordable version.

The cost wall is solvent: N ~ L^3 and forces are O(N^2), so a big box is unaffordable. But water
DOMINATES N, so cutting the LIPID count is nearly free -- and one well-formed micelle surrounded by
solvent answers "does radial organisation happen in 3-D" as well as five would. The previous 3-D run
put all 48 lipids in a single aggregate touching itself across the box, which could not have shown a
micelle phase whatever the physics did.

Also checks a suspected bug first: in _contact_distance, `base` (which carries per-species sigma) is
computed and then DISCARDED when aniso > 0, so the 3-D runs (aniso=0.95) may have no per-species
steric radius at all while the 2-D runs (aniso=0) do.
"""
import numpy as np
from bilayer3d import build
from harness import bond_stats, measure
from references import micelle_3d, relax

MOM, KB, SPEED = 0.30, 30.0, 0.001
assert SPEED * KB / (1 - MOM) < 0.05
FIG = dict(kt=0.02, speed=SPEED, repel=12.0, k_bond=KB, satt=0.55, spol=0.90, attract=1.0,
           polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)

# --- does per-species sigma reach the contact distance in 3-D? ---
e = build(3, n_lip=20, bound=4.5, plant=False, head_sigma=0.5, **FIG)
C = e._contour(); delta, d2 = e._periodic_delta(); dist = np.sqrt(d2 + 1e-4)
cd_small = e._contact_distance(C, delta, dist)
e2 = build(3, n_lip=20, bound=4.5, plant=False, head_sigma=1.0, **FIG)
C2 = e2._contour(); d2_, dd2 = e2._periodic_delta(); dist2 = np.sqrt(dd2 + 1e-4)
cd_big = e2._contact_distance(C2, d2_, dist2)
print(f"  aniso={e.aniso}  head_sigma 0.5 vs 1.0 -> contact identical? "
      f"{np.allclose(cd_small, cd_big)}  (sigma differs: {not np.allclose(e.sigma, e2.sigma)})",
      flush=True)

# --- reference band ---
ref = relax(micelle_3d(build, n_lip=30, bound=6.0, **FIG), 500)
mr = measure(ref)
print(f"  REFERENCE relaxed 3-D micelle n=30: splay {mr['splay']:.3f}  packing {mr['packing']:.3f}",
      flush=True)

# --- self-assembly with few lipids, so one micelle can form with solvent around it ---
print(f"  {'n_lip':>6}{'N':>6}{'t':>8}{'splay':>7}{'pack':>7}{'align':>7}{'bond':>7}  call", flush=True)
for n_lip in (16, 30):
    e = build(3, n_lip=n_lip, bound=4.5, plant=False, **FIG)
    for t in (5000, 20000, 50000):
        while getattr(e, "_t", 0) < t:
            e.step(); e._t = getattr(e, "_t", 0) + 1
        m = measure(e); mean, _, _ = bond_stats(e)
        call = ("BILAYER" if m["splay"] < 0.30 else
                "MICELLE" if 0.45 <= m["splay"] <= 0.85 else "disordered")
        print(f"  {n_lip:>6}{len(e.X):>6}{t:>8}{m['splay']:>7.3f}{m['packing']:>7.3f}"
              f"{m['align']:>7.3f}{mean:>7.3f}  {call} {'ok' if m['ok'] else m['why'][:16]}",
              flush=True)
