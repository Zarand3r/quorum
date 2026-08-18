"""Verify the elastic-stiffness flexibility model against real statistical mechanics.

The claim being tested is a physics claim, not a code claim: how much a molecule deforms must be a
CONSEQUENCE of its stiffness competing with temperature (equipartition), not a tuning knob. If the
variance does not come out as S·kT/k, the model is not doing physics and the species-level rigidity
differences mean nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from config import DEFAULTS, VivariumConfig
from pack import _SHAPE_THERMAL, PackEngine
from polar_pack import (AMPHI, STIFF_AMPHI_SPLAY, STIFF_RIGID, WATER, PolarPackEngine)


def _cfg(**over):
    return VivariumConfig(**{**DEFAULTS, "N": 24, **over})


def _cfg3(**over):
    return VivariumConfig(**{**DEFAULTS, "N": 24, "pos_dim": 3, "n_harmonics": 2,
                             "pos_bound": 3.0, **over})


# ------------------------------------------------------------------ the physics

@pytest.mark.parametrize("k", [1.0, 0.5, 0.1, 0.02])
def test_equipartition_variance_is_kT_over_k(k):
    """Overdamped update C ← C_rest + (1−k)(C−C_rest) + σξ with σ² = S·kT·(2−k) has stationary
    variance exactly S·kT/k. That is equipartition: a stiff mode barely moves, a soft mode
    fluctuates a lot, both from ONE temperature. Tested on the mechanism in isolation so no other
    dynamics can contaminate it."""
    T = 0.05
    e = PackEngine(_cfg(N=64), 0)
    e.temperature = T
    e.stiff = np.full((e.cfg.N, e.tK), k)
    e.c_rest = np.zeros((e.cfg.N, e.tK))

    z = np.zeros((e.cfg.N, e.cfg.d - e.pd))
    samples = []
    for t in range(4000):
        e.t = t
        z = e._apply_stiffness(z)
        if t > 500:                                   # discard the burn-in
            samples.append(z[:, :e.tK].copy())
    var = float(np.var(np.stack(samples)))
    want = _SHAPE_THERMAL * T / k
    assert var == pytest.approx(want, rel=0.10), f"k={k}: var {var:.5f} vs kT/k {want:.5f}"


def test_stiffer_modes_fluctuate_less():
    """The ordering that makes the model meaningful: doubling stiffness must halve the variance."""
    T = 0.05
    out = {}
    for k in (0.1, 0.2):
        e = PackEngine(_cfg(N=64), 0)
        e.temperature = T
        e.stiff = np.full((e.cfg.N, e.tK), k)
        e.c_rest = np.zeros((e.cfg.N, e.tK))
        z = np.zeros((e.cfg.N, e.cfg.d - e.pd))
        acc = []
        for t in range(3000):
            e.t = t
            z = e._apply_stiffness(z)
            if t > 500:
                acc.append(z[:, :e.tK].copy())
        out[k] = float(np.var(np.stack(acc)))
    assert out[0.1] / out[0.2] == pytest.approx(2.0, rel=0.15)


def test_free_modes_get_no_thermal_kick():
    """k=0 has no equilibrium, so its variance would diverge. Such modes must be left purely
    attention-driven rather than being random-walked by the thermostat."""
    e = PackEngine(_cfg(), 0)
    e.temperature = 0.5
    e.stiff = np.zeros((e.cfg.N, e.tK))
    e.c_rest = np.zeros((e.cfg.N, e.tK))
    z = np.zeros((e.cfg.N, e.cfg.d - e.pd))
    z[:, :e.tK] = 0.7
    out = e._apply_stiffness(z.copy())
    assert np.allclose(out[:, :e.tK], 0.7), "a free mode must not be thermally kicked"


# ------------------------------------------------------------------ species behaviour

def test_rigid_species_hold_their_rest_conformation():
    """At k=1 and zero temperature a rigid molecule sits exactly on its rest shape — reproducing
    the old hard overwrite, so rigidity is now the stiff LIMIT of one mechanism, not a special case."""
    for cfg in (_cfg(N=40), _cfg3(N=40)):
        e = PolarPackEngine(cfg, 0, water_frac=0.6, amphi_frac=0.4, polarity=1.0)
        e.temperature = 0.0
        for _ in range(30):
            e.step()
        C = e._contour()
        assert np.allclose(C[e._wi], e.c_rest[e._wi], atol=1e-9), "water drifted off its rest shape"


def test_amphiphile_head_is_rigid_but_splay_is_floppy():
    """The physically-motivated split: the l=1 head dipole is the molecule's chemical identity and
    stays rigid, while the higher modes (axial elongation = tail splay) are soft. Real lipid tails
    are the most flexible component of a membrane."""
    e = PolarPackEngine(_cfg3(N=40), 0, water_frac=0.5, amphi_frac=0.5, polarity=1.0)
    order = e.mode_orders()
    k = e.stiff[e._ai]
    assert np.allclose(k[:, order == 1], STIFF_RIGID)
    assert np.allclose(k[:, order >= 2], STIFF_AMPHI_SPLAY)
    assert STIFF_AMPHI_SPLAY < STIFF_RIGID

    e.temperature = 0.05
    for _ in range(400):
        e.step()
    dev = np.abs(e._contour()[e._ai] - e.c_rest[e._ai])
    head, splay = dev[:, order == 1].mean(), dev[:, order >= 2].mean()
    assert splay > head, f"splay {splay:.4f} should exceed head {head:.4f}"


def test_water_is_stiffer_than_the_amphiphile_tail():
    """Cross-species ordering, the whole point of per-species stiffness."""
    e = PolarPackEngine(_cfg3(N=40), 0, water_frac=0.5, amphi_frac=0.5, polarity=1.0)
    order = e.mode_orders()
    assert e.stiff[e._wi].min() == STIFF_RIGID
    assert e.stiff[e._ai][:, order >= 2].max() < e.stiff[e._wi].min()


# ------------------------------------------------------------------ structure / faithfulness

def test_mode_orders_match_the_channel_layout():
    e2 = PackEngine(_cfg(), 0)
    assert list(e2.mode_orders()) == [1, 1, 2, 2, 3, 3]        # (a_k, b_k) per k
    e3 = PackEngine(_cfg3(), 0)
    assert list(e3.mode_orders()) == [1, 1, 1, 2, 2, 2, 2, 2]  # (2l+1) per l
    for e in (e2, e3):
        assert len(e.mode_orders()) == e.tK


def test_stiffness_is_a_diagonal_linear_map():
    """Faithfulness: the restoring step must be a per-channel (diagonal) linear map on the shape
    channels — a structured linear op — not a force kernel. Verified by linearity + separability."""
    e = PackEngine(_cfg(N=12), 0)
    e.temperature = 0.0
    e.stiff = np.tile(np.linspace(0.1, 0.9, e.tK), (e.cfg.N, 1))
    e.c_rest = np.zeros((e.cfg.N, e.tK))
    rng = np.random.default_rng(0)
    a = np.zeros((e.cfg.N, e.cfg.d - e.pd)); a[:, :e.tK] = rng.standard_normal((e.cfg.N, e.tK))
    b = np.zeros_like(a);                    b[:, :e.tK] = rng.standard_normal((e.cfg.N, e.tK))
    fa = e._apply_stiffness(a.copy())[:, :e.tK]
    fb = e._apply_stiffness(b.copy())[:, :e.tK]
    fab = e._apply_stiffness((2.0 * a + 3.0 * b).copy())[:, :e.tK]
    assert np.allclose(fab, 2.0 * fa + 3.0 * fb), "restoring step is not linear"
    # diagonal: perturbing one channel must not move any other
    c = np.zeros_like(a)
    out0 = e._apply_stiffness(c.copy())[:, :e.tK]
    c[:, 2] = 1.0
    out1 = e._apply_stiffness(c.copy())[:, :e.tK]
    d = np.abs(out1 - out0)
    assert d[:, 2].min() > 0 and np.allclose(np.delete(d, 2, axis=1), 0.0), "map is not diagonal"


def test_base_case_identity_survives_the_stiffness_mechanism():
    for cfg in (_cfg(), _cfg3()):
        a = PolarPackEngine(cfg, 5, water_frac=0.0, polarity=0.0)
        b = PackEngine(cfg, 5)
        for _ in range(80):
            a.step()
            b.step()
        assert np.max(np.abs(a.X - b.X)) == 0.0, f"pos_dim={cfg.pos_dim} diverged"
