"""The implicit-solvent chi must reproduce the hydrophobic effect the deleted water was carrying.

Amphiphilicity in this model lives entirely in `chi`, and a head goes to the surface because it gains
`chi_HW` from water. Deleting the water at `phi = 0` therefore deletes the drive, and the corrected 3-D
renders showed the result: heads scattered through the tail mass. `solvent_averaged_chi` integrates the
solvent out via the exchange energy instead of dropping it.

These gates pin the ORDERING, which is the physics, rather than the three numbers, which follow from
whatever `default_chi` happens to be.
"""

from __future__ import annotations

import numpy as np

from field import HEAD, TAIL, WATER, default_chi, qk_factors, solvent_averaged_chi


def test_tails_are_the_most_cohesive_pair():
    e = solvent_averaged_chi()
    assert e[TAIL, TAIL] > e[HEAD, TAIL] > e[HEAD, HEAD]


def test_heads_repel_each_other_once_the_solvent_is_integrated_out():
    """The sign flip is the point: with explicit water head-head is +0.20 and attractive."""
    assert default_chi()[HEAD, HEAD] > 0
    assert solvent_averaged_chi()[HEAD, HEAD] < 0


def test_water_row_is_empty_because_there_are_no_water_beads():
    e = solvent_averaged_chi()
    assert np.allclose(e[WATER, :], 0.0) and np.allclose(e[:, WATER], 0.0)


def test_symmetric_and_still_a_query_key_inner_product():
    """A negative affinity must stay representable, or the transformer-only constraint breaks."""
    e = solvent_averaged_chi()
    assert np.allclose(e, e.T)
    q, k = qk_factors(e)
    assert np.abs(q @ k.T - e).max() < 1e-12


def test_burying_a_head_costs_energy_relative_to_burying_a_tail():
    """The single fact the explicit water used to supply, stated directly."""
    e = solvent_averaged_chi()
    assert e[HEAD, TAIL] < e[TAIL, TAIL]
