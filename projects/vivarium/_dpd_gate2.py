"""Stage D gate 2: can the DPD model express hydrophobicity (species incompatibility)?

Before bonding beads into amphiphiles, the two species must actually demix. In DPD this is set by the
CROSS repulsion: with a_AA = a_BB fixed, raising a_AB drives segregation, and the Flory-Huggins chi
scales with da = a_AB - a_AA. This is the calibration step Vivarium never performed -- its
hydrophobicity came from an eps_pair matrix chosen by hand, never checked against a demixing curve.

Order parameter: for each bead, the fraction of its within-rc neighbours of the SAME species.
  0.5  -> perfectly mixed (50:50 composition)
  1.0  -> fully segregated
A random-placement null is measured, not assumed, so "0.62" can be read as something.
"""
import numpy as np
from dpd_reference import DPD

RHO, KT, N = 4.0, 1.0, 500

def like_fraction(d):
    x, L, s = d.x, d.L, d.species
    dd = x[:, None, :] - x[None, :, :]
    dd -= L * np.round(dd / L)
    r = np.linalg.norm(dd, axis=2)
    np.fill_diagonal(r, np.inf)
    near = r < d.rc
    same = (s[:, None] == s[None, :]) & near
    cnt = near.sum(axis=1)
    ok = cnt > 0
    return float((same.sum(axis=1)[ok] / cnt[ok]).mean())

L = np.sqrt(N / RHO)
sp = np.zeros(N, int); sp[N // 2:] = 1

# null: same composition, random positions, no demixing possible
null = DPD(N, L, kT=KT, a=25.0, species=sp, seed=1)
print(f"random-placement null (no interaction bias): like-fraction {like_fraction(null):.3f}")
print()
print(f"{'a_AB':>6}{'da':>5}{'like-frac':>11}{'T':>7}{'homog':>8}   verdict")
for a_ab in (25.0, 30.0, 35.0, 45.0, 65.0):
    m = np.array([[25.0, a_ab], [a_ab, 25.0]])
    d = DPD(N, L, kT=KT, a_matrix=m, species=sp, dt=0.02, seed=1)
    for _ in range(4000):
        d.step()
    lf = like_fraction(d)
    print(f"{a_ab:>6.0f}{a_ab-25:>5.0f}{lf:>11.3f}{d.temperature():>7.2f}"
          f"{d.density_homogeneity():>8.2f}   "
          f"{'SEGREGATED' if lf > 0.75 else 'partially demixed' if lf > 0.60 else 'mixed'}")
