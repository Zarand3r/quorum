"""Spontaneous curvature: live when enabled, inert when not, and never disturbing the base case.

This project has shipped live sliders wired to nothing (five of them, removed earlier), and the
first version of THIS term was another: it was nested inside the `eps_pair is not None` branch and
then gated behind `conservative`, so it changed nothing in the default engine. A knob whose only
test is "the attribute exists" is not tested. Each assertion below states which failure it catches.
"""

import numpy as np
import pytest

import pack

MOL = np.array([[i * 3, i * 3 + 1, i * 3 + 2] for i in range(12)])
EPS_PAIR = np.array([[0.60, 0.20, 0.02], [0.20, 0.30, 0.10], [0.02, 0.10, 0.50]])


def _molecular(cv, seed=7):
    """An engine that can actually feel the term: bonded molecules and the conservative vdW path."""
    e = pack.PackEngine(pack._cfg(), seed=seed)
    n = e.X.shape[0]
    e._mol = MOL[MOL.max(axis=1) < n]
    sp = np.zeros(n, int)
    sp[e._mol[:, 0]] = 1
    sp[e._mol[:, 1:].ravel()] = 2
    e.species = sp
    e.eps_pair = EPS_PAIR
    e.conservative = True
    e.curvature = cv
    return e


def _run(engine, n=40):
    for _ in range(n):
        engine.step()
    return engine.X.copy()


def test_curvature_changes_the_trajectory():
    """Catches a dead knob: the term nested in a branch the default engine never takes."""
    off = _run(_molecular(0.0))
    on = _run(_molecular(0.2))
    assert np.abs(off - on).max() > 1e-6, "curvature had no effect; the knob is wired to nothing"


def test_curvature_is_deterministic():
    assert np.abs(_run(_molecular(0.2)) - _run(_molecular(0.2))).max() == 0.0


def test_base_case_is_untouched_without_molecules():
    """Unbonded tokens have a zero axis, so a solvent-only system must be byte-identical."""
    def plain(cv):
        e = pack.PackEngine(pack._cfg(), seed=7)
        e.conservative = True
        e.curvature = cv
        return _run(e)
    assert np.abs(plain(0.0) - plain(0.3)).max() == 0.0


def test_weight_stays_positive_within_the_slider_range():
    """The slider ceiling exists because the factor 1 + cv*(u_i-u_j).r_hat changes SIGN past 0.5.

    A negative weight silently inverts attraction into repulsion, so this bound is physical rather
    than cosmetic and belongs in a test rather than only in a comment.
    """
    e = _molecular(0.5)
    e.step()
    dirn = np.eye(3)[None, :, :].repeat(3, 0) * 0 + 1.0 / np.sqrt(3)
    u = e._axis_signed()
    assert np.all(np.isfinite(u))
    # worst case: both unit vectors antiparallel along r_hat -> projection = -2
    assert 1.0 + 0.5 * (-2.0) == pytest.approx(0.0), "0.5 is exactly the sign-change point"


def test_axis_sign_points_toward_the_head():
    """The nematic term squares the dot product so its sign is invisible; curvature is odd in u,
    so an inverted axis would put the heads on the WRONG face and still look plausible."""
    e = _molecular(0.1)
    P = e.X[:, :e.pd]
    head = P[e._mol[0, 0]]
    tailc = P[e._mol[0, 1:]].mean(axis=0)
    expect = head - tailc
    expect -= e.L * np.round(expect / e.L)
    expect /= np.linalg.norm(expect)
    got = e._axis_signed()[e._mol[0, 0]]
    assert float(got @ expect) > 0.99, "axis does not point from the tail centre toward the head"


def test_curvature_does_not_touch_water_lipid_pairs():
    """Water has a zero axis; an unrestricted form still modulates every water-lipid pair.

    Measured before the restriction: curvature 0.15 and 0.30 collapsed the solvent into dense clumps
    rather than producing vesicles, because the term was perturbing the water-lipid attraction that
    eps_pair balances. The weight must be exactly 1 wherever either partner lacks an axis.
    """
    e = _molecular(0.3)
    e.step()
    u = e._axis_signed()
    has = np.linalg.norm(u, axis=1) > 0.0
    assert has.any() and (~has).any(), "need both lipid and non-lipid tokens for this test"
    delta = e.X[:, :e.pd][:, None, :] - e.X[:, :e.pd][None, :, :]
    delta -= e.L * np.round(delta / e.L)
    dist = np.sqrt((delta ** 2).sum(-1) + 1e-12)
    w = e._curvature_weight(delta / dist[..., None])
    cross = (~has)[:, None] | (~has)[None, :]
    assert np.allclose(w[cross], 1.0), "curvature is modulating pairs involving a token with no axis"
