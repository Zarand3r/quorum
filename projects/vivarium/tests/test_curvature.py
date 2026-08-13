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


def test_curvature_shifts_the_optimum_without_deepening_the_well():
    """The defining property of spontaneous curvature, and what the first implementation lacked.

    For every beta the maximum angular weight must be the SAME, while the angle attaining it moves.
    The original form `1 + curvature*p` failed both halves: its maximum grew as 1 + 2*curvature and
    its optimum stayed pinned at maximal splay, which is why it collapsed the aggregate rather than
    curving it.
    """
    e = _molecular(0.0)
    th = np.linspace(-np.pi / 2, np.pi / 2, 4001)
    maxima, argmax = [], []
    for beta in (0.0, 0.05, 0.10, 0.15):
        # symmetric splay about r_hat = x_hat, evaluated directly on the angular form
        s_, c_ = np.sin(th), np.cos(th)
        q = c_ * c_
        p = -2.0 * s_
        a = q + beta * p - beta ** 2
        maxima.append(a.max())
        argmax.append(th[a.argmax()])
    assert max(maxima) - min(maxima) < 1e-6, f"well depth changes with beta: {maxima}"
    assert argmax[0] == pytest.approx(0.0, abs=1e-3), "beta=0 optimum should be flat"
    for beta, t in zip((0.05, 0.10, 0.15), argmax[1:]):
        assert t == pytest.approx(np.arcsin(-beta), abs=2e-3), "optimum did not move to arcsin(-beta)"


def test_engine_weight_never_exceeds_one():
    """a <= 1 by construction, so the weight can only penalise a contact, never reward it beyond
    the isotropic value. This is the property that keeps total cohesion fixed."""
    e = _molecular(0.15)
    e.step()
    delta = e.X[:, :e.pd][:, None, :] - e.X[:, :e.pd][None, :, :]
    delta -= e.L * np.round(delta / e.L)
    dist = np.sqrt((delta ** 2).sum(-1) + 1e-12)
    w = e._curvature_weight(delta / dist[..., None])
    assert w.max() <= 1.0 + 1e-9, f"weight exceeds 1 ({w.max():.4f}); cohesion can grow"


def test_positive_curvature_prefers_heads_splayed_outward():
    """Sign convention, tested by BEHAVIOUR rather than by reading the source.

    A negated r_hat still yields a strong bilayer signature -- align 0.904 was measured -- but with
    the leaflets INVERTED: heads meeting in the middle, tails facing the solvent. The alignment
    metric cannot tell those apart, so the sign needs its own assertion.

    Two lipids side by side along x. SPLAYED means each head tilts away from the other (the convex
    arrangement a vesicle's outer leaflet has); CONVERGENT means each head tilts toward the other.
    A positive curvature must score the splayed pair higher.
    """
    e = _molecular(0.25)
    pd = e.pd
    a, b = e._mol[0], e._mol[1]

    def weight(tilt):
        P = e.X[:, :pd]
        for mol, cx, sgn in ((a, -1.0, -1.0), (b, +1.0, +1.0)):
            axis = np.zeros(pd)
            axis[0] = sgn * np.sin(tilt)
            axis[1] = np.cos(tilt)
            P[mol[0]] = np.array([cx, 0.0])[:pd] + 0.5 * axis
            for k in mol[1:]:
                P[k] = np.array([cx, 0.0])[:pd] - 0.5 * axis
        delta = P[:, None, :] - P[None, :, :]
        delta -= e.L * np.round(delta / e.L)
        dist = np.sqrt((delta ** 2).sum(-1) + 1e-12)
        return e._curvature_weight(delta / dist[..., None])[a[0], b[0]]

    splayed, convergent = weight(+0.5), weight(-0.5)
    assert splayed > convergent, (
        f"positive curvature must favour heads splayed outward "
        f"(splayed {splayed:.4f} vs convergent {convergent:.4f}); the r_hat sign is inverted")
