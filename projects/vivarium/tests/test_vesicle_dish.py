"""The hosted dish must be the system the results came from.

This suite exists because it was not. `--lipid2d` served `polar_pack` at the micelle configuration
(63 lipids, 250 water) while every vesicle result in docs/PAPER.md came from `_mixture` + `field` at
160 lipids in L = 65, and `server.py` imported none of those modules -- so no flag could have shown
the vesicle system. A viewer that silently serves a different system than the paper is worse than no
viewer, so each property below pins one way that drift happened or could happen again.
"""

from __future__ import annotations

import numpy as np
import pytest

import _mixture
import vesicle
from chemistry import AMPHIPHILE
from field import HEAD, TAIL, WATER


def test_engine_factory_is_importable():
    """The regression that caused all of this: the production engine was defined inside `__main__`.

    An unimportable engine is why the viewer could not run the real system. If this ever moves back
    into the script body, the viewer silently falls back to a different dish again.
    """
    assert callable(_mixture.make_step_engine)


def test_dish_matches_the_production_topology():
    """160 lipids, 2,959 beads, L = 65 -- the composition the saved states carry."""
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    assert e.L == 65.0
    assert len(e.X) == 2959
    counts = np.bincount(np.asarray(e.species), minlength=3)
    assert counts[HEAD] == 160     # one head per lipid
    assert counts[TAIL] == 640     # four tails per lipid
    assert counts[WATER] == 2159


def test_chemistry_is_the_amphiphile_not_the_bare_defaults():
    """`field.default_chi` is NOT the production chemistry.

    At the bare defaults chi_HT = +0.20 == chi_HH, a head is indifferent between a head and a tail
    neighbour, and the ordered bilayer is not even a local minimum. Running the viewer there would
    look like the model and behave like a different one.
    """
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    assert e.chi[HEAD, TAIL] == AMPHIPHILE["ht"] == -0.25
    assert e.chi[WATER, WATER] == AMPHIPHILE["ww"] == 0.50
    vesicle.assert_production_chemistry(e.chi)


def test_production_chemistry_guard_actually_fires():
    """A guard that has never failed is not evidence."""
    bad = vesicle.production_chi(chi_ht=0.20)      # the bare default: not an amphiphile
    with pytest.raises(ValueError, match="chi_HT"):
        vesicle.assert_production_chemistry(bad)


def test_transformer_is_the_default_engine():
    """The dish is served through the transformer path, not the integrator."""
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    assert isinstance(e.ig, _mixture._TransformerEngine)


def test_heads_reproduce_field_forces_on_the_served_topology():
    """The assertion the paper calls the one that matters most, on the dish the VIEWER builds.

    `tests/test_transformer.py` already gates the bit-for-bit step identity, so that is not repeated
    here. What is not covered there is this construction path: branched lipids and explicit water
    populated exactly as the served dish populates them. A refactor exact on toy chains and wrong on
    the real topology would pass every other test and still hand the viewer a different physics.
    """
    e = vesicle.VesicleEngine(seed=3, start="dispersed", engine="transformer")
    heads = e.ig.tf.attention(e.X)
    direct = e.field.forces(e.X)
    scale = max(1.0, float(np.abs(direct).max()))
    assert np.abs(heads - direct).max() / scale < 1e-13


def test_integrator_engine_is_selectable_and_steps():
    """The `engine=` switch must actually reach `_mixture.make_step_engine`, so the viewer can be
    run against the integrator as a control without a second code path."""
    from integrate import Inertial

    e = vesicle.VesicleEngine(seed=3, start="dispersed", engine="integrator")
    assert isinstance(e.ig, Inertial)
    e.step()
    assert e.t == 1 and np.all(np.isfinite(e.X))


def test_step_advances_and_stays_finite():
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    x0 = e.X.copy()
    for _ in range(5):
        e.step()
    assert e.t == 5
    assert np.all(np.isfinite(e.X))
    assert not np.array_equal(x0, e.X)


def test_snapshot_speaks_the_viewer_dialect():
    """viewer.html colours chain lipids by species 5 (head) / 6 (tail) / 0 (solvent).

    field.py uses HEAD=0/TAIL=1/WATER=2, and the two schemes collide on 0 -- an offset instead of an
    explicit map would paint every water bead as a lipid head.
    """
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    snap = e.snapshot()
    assert set(snap["species"]) == {0, 5, 6}
    assert sum(1 for s in snap["species"] if s == 5) == 160
    assert sum(1 for s in snap["species"] if s == 0) == 2159
    assert len(snap["tokens"]) == len(snap["species"]) == 2959
    assert snap["pos_bound"] == pytest.approx(32.5)   # integrate.py wraps to [-L/2, L/2)
    # every token needs a contour or the viewer's paint path throws on `.c.length`
    assert all(len(t["c"]) == 2 for t in snap["tokens"][:50])


def test_chi_knob_rebuilds_and_takes_effect():
    """chi knobs must rebuild: the transformer factors Wq/Wk out of chi at construction, so mutating
    the matrix in place would leave the heads computing the OLD chemistry while the field reports the
    new one -- exactly the class of silent desync this project keeps catching."""
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    get, setr = e.pseudo_knobs()["chi_TW"]
    assert get() == 0.0
    setr(-0.30)
    assert get() == -0.30
    assert e.chi[TAIL, WATER] == -0.30
    assert e.field.chi[TAIL, WATER] == -0.30
    assert isinstance(e.ig, _mixture._TransformerEngine)   # rebuilt, still the transformer


def test_negative_chi_survives_the_knob_path():
    """chi_HT is -0.25, and `Sim.set_knobs` clamps REAL knobs to >= 0. These must be pseudo-knobs or
    the production chemistry is unreachable from the UI."""
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    names = set(e.pseudo_knobs())
    assert {"chi_HT", "chi_TW", "chi_HH", "chi_WW", "kT"} <= names


def test_kT_knob_is_live_and_reaches_the_thermostat():
    e = vesicle.VesicleEngine(seed=0, start="dispersed")
    get, setr = e.pseudo_knobs()["kT"]
    assert get() == pytest.approx(0.45)
    setr(0.60)
    assert e.kT == pytest.approx(0.60)
    assert e.ig.kT == pytest.approx(0.60)   # the engine reads kT every step


def test_default_start_is_dispersed_and_claims_nothing():
    """The default must not imply a vesicle.

    An earlier draft of this module defaulted to loading `former_sd45007_s0960000.npz` and calling it
    the emergent vesicle. Measured, that state has n_enclosed [0, 0, 0, 0] -- no lumen at all -- so
    the default would have served a non-vesicle labelled as the headline result, which is the exact
    failure this whole module exists to correct.
    """
    e = vesicle.VesicleEngine(seed=0)
    assert e.start == "dispersed"
    assert e.snapshot()["gate"] is None


def test_formed_start_reports_the_gate_verdict_rather_than_asserting_one():
    """No saved 2-D production state passes `vesicle_call`. The viewer must say so, not hide it."""
    if not vesicle.FORMED_STATE.exists():
        pytest.skip("docs/controls/ not present")
    e = vesicle.VesicleEngine(seed=0, start="formed")
    gate = e.snapshot()["gate"]
    assert gate is not None
    assert set(gate) >= {"source", "steps", "vesicle_call", "reason", "largest", "n_mol"}
    assert isinstance(gate["vesicle_call"], bool)
    assert gate["reason"]                      # a verdict always carries its reason
    assert len(e.X) == 2959
    assert np.all(np.isfinite(e.X))
    assert np.abs(e.X).max() <= 32.5 + 1e-6


def test_formed_start_differs_from_dispersed():
    """Guards against the load silently no-op'ing and serving a random start as 'a saved state'."""
    if not vesicle.FORMED_STATE.exists():
        pytest.skip("docs/controls/ not present")
    formed = vesicle.VesicleEngine(seed=0, start="formed")
    disp = vesicle.VesicleEngine(seed=0, start="dispersed")
    assert not np.allclose(formed.X, disp.X)


def test_bad_start_is_a_construction_error():
    with pytest.raises(ValueError, match="start must be"):
        vesicle.VesicleEngine(seed=0, start="planted")
