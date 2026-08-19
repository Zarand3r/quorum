"""The shell-CV metric must report the shell, not the cluster's position or the population's spread.

Shell CV is the number the 3-D conclusions rest on, and it carried two defects that a planted control
exposed (`_cvcontrol.py`). Both are gated here because both biased real readings:

  * a cluster straddling a periodic boundary read 0.035 against a true 0.117 -- 70% LOW, i.e. toward
    the value that reads as a tight vesicle;
  * a shell surrounded by dispersed lipids read 0.595 against 0.117 -- 411% HIGH.

The planted shell's CV is known analytically: three bead layers at radii R, R+1, R+2, so
std/mean of that spread. A metric that cannot recover a number it was handed cannot be trusted on a
structure nobody planted.
"""

from __future__ import annotations

import numpy as np

from _cvcontrol import NB, _shell, score

L = 40.0
R = 6.0
N = int(4 * np.pi * R ** 2 / 1.2)
TRUE_CV = float(np.std([R, R + 1, R + 2]) / np.mean([R, R + 1, R + 2]))


def _rng():
    return np.random.default_rng(0)


def test_centred_shell_recovers_its_analytic_cv():
    cv = score(*_shell(N, R, np.array([L / 2] * 3), _rng()), L)
    assert abs(cv - TRUE_CV) / TRUE_CV < 0.10, f"{cv} vs {TRUE_CV}"


def test_straddling_shell_scores_the_same_as_a_centred_one():
    """Translation invariance under periodic boundaries. The old centroid failed this by 70%."""
    a = score(*_shell(N, R, np.array([L / 2] * 3), _rng()), L)
    b = score(*_shell(N, R, np.array([0.0, 0.0, 0.0]), _rng()), L)
    assert abs(a - b) / a < 0.10, f"centred {a}, straddling {b}"


def test_dispersed_lipids_elsewhere_do_not_change_the_shell_cv():
    """The metric scores the largest cluster. The old one averaged every lipid and inflated 4.1x."""
    rng = _rng()
    X, mols = _shell(N, R, np.array([L / 2] * 3), rng)
    X, mols = list(X), list(mols)
    for _ in range(180):
        c = rng.uniform(0, L, 3)
        base = len(X)
        for b in range(NB):
            X.append(c + np.array([0.0, 0.0, b * 1.0]))
        mols.append(np.arange(base, base + NB))
    cv = score(X, mols, L)
    assert abs(cv - TRUE_CV) / TRUE_CV < 0.10, f"{cv} vs {TRUE_CV}"
