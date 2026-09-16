"""The flat-ribbon planter's branched-lipid spacing is a NAMED constant, and the override works.

`_plant_flat_ribbon` clamped branched lipids to a bare `2.05`, justified by a comment calling it the
"lateral footprint of a two-tailed lipid" -- an assertion, where the repo rule is "derive constants
from the configuration; do not pick them". ROADMAP.md D9 records a relaxed ribbon settling at
1.7651 sigma instead, i.e. the planted sheet is ~16% more dilute than equilibrium.

The value is NOT yet derived, so these tests pin the current behaviour and the override that the D9
experiment needs -- they are not an endorsement of 2.05.
"""
import os

import numpy as np
import pytest

import _mixture


def _spacing(X, mols):
    """Median in-leaflet nearest-neighbour head separation along the ribbon."""
    heads = X[np.array([m[0] for m in mols])]
    mid = heads[:, 1].mean()
    per_leaflet = [np.median(np.diff(np.sort(side[:, 0])))
                   for side in (heads[heads[:, 1] > mid], heads[heads[:, 1] <= mid])]
    return float(np.mean(per_leaflet))


def _plant(seed=0, n=40, L=90.0):
    X, species, bonds, mols, wi, chains = _mixture.build(
        n // 2, n - n // 2, 0, L, 2, tails=(4, 4), seed=seed, plant="flat", branched=True)
    return X, mols


def test_metric_recovers_a_known_spacing():
    """Validate the instrument before trusting it: it must read back what the planter was told.

    Without this the other two tests could both pass against a metric that returns a constant.
    """
    for want in (2.05, 2.50, 3.00):
        os.environ["VIVARIUM_RIBBON_GAP"] = str(want)
        try:
            assert _spacing(*_plant()) == pytest.approx(want, abs=1e-6)
        finally:
            del os.environ["VIVARIUM_RIBBON_GAP"]


def test_default_branched_spacing_is_the_named_constant():
    """Default behaviour is unchanged by naming the constant."""
    assert _mixture.RIBBON_GAP_BRANCHED == 2.05
    assert _spacing(*_plant()) == pytest.approx(_mixture.RIBBON_GAP_BRANCHED, abs=1e-6)


def test_override_reaches_the_planter_without_a_reload():
    """Read at call time. An import-time read would need importlib.reload and silently ignore this."""
    os.environ["VIVARIUM_RIBBON_GAP"] = "1.7651"
    try:
        assert _spacing(*_plant()) == pytest.approx(1.7651, abs=1e-6)
    finally:
        del os.environ["VIVARIUM_RIBBON_GAP"]
    assert _spacing(*_plant()) == pytest.approx(2.05, abs=1e-6), "env leaked out of the test"
