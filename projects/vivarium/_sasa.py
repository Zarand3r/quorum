"""Solvent-accessible exposure of a bead, computed exactly in 2-D. No free parameters.

WHY THIS EXISTS

`docs/RESULTS.md` states the blocker structurally: chi terms are symmetric PAIR interactions, and
spontaneous curvature is by definition a difference between the two leaflets, so no chi tuning can
curve a bilayer. Every candidate curvature source came back a measured null, including imposed leaflet
asymmetry (0/5).

Escaping that needs a MANY-BODY term -- something that depends on an aggregate over a bead's
neighbourhood rather than on any pair. This is the one such quantity that is derivable rather than
chosen: how much of a bead's surface a solvent molecule can actually touch.

THE DERIVATION

Solvation energy scales with solvent-accessible surface area. That is the standard SASA model in
biophysics, not an invention for this project. In 2-D "surface" is the perimeter of a disc, so:

    a bead i of radius R_i is expanded by the PROBE radius r_p, and the accessible fraction is the
    arc of that expanded circle which lies inside no neighbour's expanded circle.

Every quantity is already in the model. R_i is the bead's own `sigma_species / 2`. The probe is a
water bead, so r_p = sigma_water / 2. **Nothing is fitted and nothing is tuned.**

WHY THIS IS NOT SMUGGLING IN THE ANSWER

It says only "a buried bead is less solvated than an exposed one", which is true independently of
vesicles and mentions neither curvature nor leaflets. On a FLAT bilayer both leaflets are equally
exposed, so it generates no asymmetry and cannot produce spontaneous curvature -- it can only respond
to curvature that already exists. Whether it amplifies or damps that curvature is not known at the
time of writing, which is the point. `specs/2026-09-07_mlp_many_body.md` registers that as gate G2.
"""
from __future__ import annotations

import numpy as np


def exposure(X, radii, L, probe, subject=None, cut=None, occluders=None):
    """Accessible perimeter fraction per bead, in [0, 1]. 2-D only.

    Exact interval arithmetic on the circle rather than point sampling: a sampled estimator has noise
    that would enter the forces, and this quantity feeds the dynamics.

    `subject` restricts the computation to a subset of beads (the heads, in practice) and returns a
    full-length array with 1.0 elsewhere -- an unsolvated bead is, trivially, fully exposed.

    `occluders` restricts WHICH beads can block access, and it is not optional in an explicit-solvent
    system. The probe REPRESENTS a solvent molecule, so solvent beads cannot block solvent access --
    they are the thing being granted access. Counting them as occluders reports a head in a normal
    flat bilayer as 85% buried and destroys the signal: measured, the spurious flat-sheet asymmetry
    (0.022) then exceeds the real curvature signal from a ring (0.009).
    """
    X = np.asarray(X, dtype=np.float64)
    radii = np.asarray(radii, dtype=np.float64)
    n = len(X)
    out = np.ones(n)
    idx = np.arange(n) if subject is None else np.asarray(subject)
    if len(idx) == 0:
        return out
    Ri = radii + probe                       # expanded radii
    reach = float(Ri.max() * 2.0) if cut is None else float(cut)
    occ = np.arange(n) if occluders is None else np.asarray(occluders)
    Xo, Ro = X[occ], Ri[occ]

    for i in idx:
        d = Xo - X[i]
        d -= L * np.round(d / L)
        r = np.sqrt(np.einsum("ij,ij->i", d, d))
        # a neighbour occludes only if its expanded circle actually reaches ours
        near = np.where((r > 1e-12) & (r < Ri[i] + Ro))[0]
        if len(near) == 0:
            continue
        rn, Rn = r[near], Ro[near]
        # A neighbour that swallows us entirely leaves nothing accessible.
        if np.any(Rn >= rn + Ri[i]):
            out[i] = 0.0
            continue
        # Half-angle of the arc of circle i occluded by neighbour j, by the law of cosines on the
        # intersection of two circles. Clipped because a neighbour we contain occludes nothing.
        cosang = (rn * rn + Ri[i] * Ri[i] - Rn * Rn) / (2.0 * rn * Ri[i])
        keep = np.abs(cosang) <= 1.0
        if not keep.any():
            continue
        half = np.arccos(cosang[keep])
        centre = np.arctan2(d[near][keep, 1], d[near][keep, 0])
        lo, hi = centre - half, centre + half
        # union of arcs on a circle: unwrap to [0, 2pi), split wrapping intervals, sweep
        segs = []
        for a, b in zip(lo, hi):
            a %= 2 * np.pi
            b %= 2 * np.pi
            if b < a:
                segs.append((a, 2 * np.pi))
                segs.append((0.0, b))
            else:
                segs.append((a, b))
        segs.sort()
        covered, cur_a, cur_b = 0.0, None, None
        for a, b in segs:
            if cur_a is None:
                cur_a, cur_b = a, b
            elif a <= cur_b:
                cur_b = max(cur_b, b)
            else:
                covered += cur_b - cur_a
                cur_a, cur_b = a, b
        if cur_a is not None:
            covered += cur_b - cur_a
        out[i] = max(0.0, 1.0 - covered / (2 * np.pi))
    return out


def validate() -> int:
    """Known-answer cases the estimator must SEPARATE, not merely score plausibly."""
    R, probe, L = 0.5, 0.5, 100.0
    r = np.full(4, R)
    cases = []

    # 1. an isolated bead is fully exposed
    cases.append(("isolated bead", np.array([[50.0, 50.0]]), np.array([R]), 1.0, 1.0))
    # 2. a bead with one touching neighbour loses exactly the arc that neighbour subtends.
    #    Two expanded circles of radius 1.0 whose centres are 1.0 apart: half-angle = arccos(1/2) =
    #    60 deg, so 120 of 360 degrees are occluded and 2/3 remains.
    cases.append(("one neighbour at d=1", np.array([[50.0, 50.0], [51.0, 50.0]]),
                  np.array([R, R]), 2.0 / 3.0, 2.0 / 3.0))
    # 3. a bead ringed by neighbours is fully buried
    th = np.linspace(0, 2 * np.pi, 9)[:-1]
    ring = np.column_stack([50 + np.cos(th), 50 + np.sin(th)])
    cases.append(("ringed by 8", np.vstack([[[50.0, 50.0]], ring]),
                  np.full(9, R), 0.0, 0.05))
    # 4. a bead far from everything is unaffected by distant beads
    cases.append(("neighbour far away", np.array([[50.0, 50.0], [70.0, 50.0]]),
                  np.array([R, R]), 1.0, 1.0))

    print(f"  {'case':>22} {'exposure':>10} {'expected range':>18}")
    ok = True
    got = []
    for name, P, rr, lo, hi in cases:
        e = exposure(P, rr, L, probe, subject=[0])[0]
        got.append(e)
        good = lo - 1e-6 <= e <= hi + 1e-6
        ok &= good
        print(f"  {name:>22} {e:>10.4f} {f'[{lo:.3f}, {hi:.3f}]':>18}{'' if good else '   <-- MISS'}")
    sep = got[0] > got[1] > got[2]
    print(f"\n  every case in range:                        {ok}")
    print(f"  isolated > one-neighbour > buried (SEPARATES): {sep}")
    print(f"  INSTRUMENT USABLE: {ok and sep}")
    return 0 if (ok and sep) else 1


if __name__ == "__main__":
    raise SystemExit(validate())
