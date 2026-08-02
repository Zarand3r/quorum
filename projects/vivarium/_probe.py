"""Verify the sigma fix: exact where it must be, effective where it was broken."""
import numpy as np
from bilayer3d import build

FIG = dict(kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.55, spol=0.90, attract=1.0,
           polarity=0.80, head_q=1.2, n_tail=2, bond_span=2.0)

def contact_of(**kw):
    e = build(3, n_lip=20, bound=4.5, plant=False, **{**FIG, **kw})
    C = e._contour(); d, d2 = e._periodic_delta(); dist = np.sqrt(d2 + 1e-4)
    return e, e._contact_distance(C, d, dist)

# 1. head_sigma must now MATTER at aniso>0 (it previously did not)
e_s, cd_s = contact_of(head_sigma=0.5)
e_b, cd_b = contact_of(head_sigma=1.0)
print(f"  head_sigma 0.5 vs 1.0 now differs? {not np.allclose(cd_s, cd_b)}  "
      f"(max delta {np.max(np.abs(cd_s - cd_b)):.4f})", flush=True)
hi = np.where(e_s.species == 5)[0]
print(f"  head-head contact:  small heads {cd_s[np.ix_(hi,hi)].mean():.3f}   "
      f"normal heads {cd_b[np.ix_(hi,hi)].mean():.3f}", flush=True)

# 2. BASE CASE must be untouched: uniform sigma -> identical trajectory
def run(n, uniform):
    e = build(3, n_lip=20, bound=4.5, plant=False, **FIG)
    if uniform:
        e.sigma = None                       # the no-species base case
    for _ in range(n):
        e.step()
    return e.X.copy()

a = run(120, uniform=True)
b = run(120, uniform=True)
print(f"  base case reproducible: {np.array_equal(a, b)}", flush=True)

# 3. and with uniform sigma equal to repel_contact/2 the new expression must equal the old one
e = build(3, n_lip=20, bound=4.5, plant=False, **FIG)
e.sigma = np.full(len(e.X), 0.5 * e.repel_contact)
C = e._contour(); d, d2 = e._periodic_delta(); dist = np.sqrt(d2 + 1e-4)
new = e._contact_distance(C, d, dist)
shaped = (e.stiff.max(axis=1) > 0.0)[:, None]
nf = np.tanh(e._bearing_nf(C, d, dist)) * shaped
half = 0.5 * e.repel_contact
old = half * (1.0 + e.aniso * nf) + half * (1.0 + e.aniso * nf.T)
print(f"  uniform sigma reduces to the old expression exactly: {np.array_equal(new, old)}", flush=True)
