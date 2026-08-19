"""`hollow` must separate a vesicle from a blob AT THE SIZE THIS PROJECT RUNS.

shell CV does not. Measured on planted structures (`_cvdegenerate.py`), the gap between a hollow shell
and a solid ball of the same beads:

    our 4-tail lipid, R_mid 5.71     CV gap 0.016     hollow gap 1.035
    thin shell, R_mid 12             CV gap 0.185     hollow gap 0.850
    oracle-like, R_mid 20            CV gap 0.220     hollow gap 1.047

CV works only while the membrane is thin compared with the radius: a thin shell of thickness t at
radius R scores t/(sqrt(12) R), while a solid ball scores 0.258 at ANY radius. At R_mid 5.71 with a
5-bead lipid the thickness and the radius are the same size, so a PERFECT vesicle scores 0.248 against
a ball's 0.264 and the metric is blind. The oracle's 0.045 is reproduced here by geometry alone at
R_mid 20, which makes it a signature of vesicle SIZE rather than of vesicle quality, and makes it
unreachable at N = 300 in L = 25 no matter what the physics does.
"""

from __future__ import annotations

import numpy as np

from _cvcontrol import _shell, score
from _cvdegenerate import _ball, hollowness


def _planted(NB, R_mid, seed=0):
    rng = np.random.default_rng(seed)
    L = 4.0 * (R_mid + NB)
    centre = np.array([L / 2] * 3)
    n = int(4 * np.pi * R_mid ** 2 / 1.2)
    shell = _shell(n, R_mid - (NB - 1) / 2.0, centre, rng, NB=NB)
    ball = _ball(n, R_mid + (NB - 1) / 2.0, centre, rng, NB=NB)
    return L, shell, ball


def test_hollowness_separates_shell_from_ball_at_our_system_size():
    L, (Xs, ms), (Xb, mb) = _planted(NB=5, R_mid=5.71)
    hs, hb = hollowness(Xs, ms, L), hollowness(Xb, mb, L)
    assert hs < 0.15, f"planted vesicle should read empty, got {hs}"
    assert hb > 0.60, f"solid ball should read filled, got {hb}"


def test_shell_cv_is_blind_at_our_system_size():
    """The negative result that motivates `hollow`. If this ever fails, CV recovered its power."""
    L, (Xs, ms), (Xb, mb) = _planted(NB=5, R_mid=5.71)
    assert abs(score(Xs, ms, L) - score(Xb, mb, L)) < 0.05


def test_hollowness_still_separates_in_the_thin_shell_regime():
    L, (Xs, ms), (Xb, mb) = _planted(NB=3, R_mid=12.0)
    assert hollowness(Xb, mb, L) - hollowness(Xs, ms, L) > 0.5
