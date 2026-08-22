"""The guard that would have caught a ten-tick regression.

`VIVARIUM_CHI_HT` was dropped when the `chi_TW` scan began. Runs afterwards inherited the +0.20 default,
at which `chi_HT == chi_HH` and `field.py:91` records -- as a measurement, not an opinion -- that the
ordered bilayer is not a local minimum. Ten ticks of "baseline" work ran on a chemistry that does not
make bilayers, and the analysis never noticed because nothing read the chemistry back out.

`_env_tag` had written it into every filename. These tests assert the loop is now closed.
"""

import pytest

from chemistry import AMPHIPHILE, assert_chemistry, chemistry_of

VESICLE_RUN = ("mix2d_random_N160_L65_exp_kT0.45_fs0.0_checkpoint_every20000"
               "_ht-0.25_ww0.50_enginetransformer_sd8105.npz")
DEGRADED_RUN = "mix2d_random_N160_L65_exp_kT0.45_fs0.0_checkpoint_every20000_ww0.50_sd8500.npz"


def test_parses_the_overrides_env_tag_wrote():
    assert chemistry_of(VESICLE_RUN) == {"ht": -0.25, "ww": 0.50}


def test_missing_key_is_absent_not_defaulted():
    """A missing `ht` must read as absent. Substituting the +0.20 default would re-hide the bug."""
    assert "ht" not in chemistry_of(DEGRADED_RUN)


def test_accepts_the_amphiphile_chemistry():
    assert assert_chemistry(VESICLE_RUN) == {"ht": -0.25, "ww": 0.50}


def test_rejects_the_file_that_actually_fooled_me():
    """This exact filename was analysed as 'baseline' for ten ticks."""
    with pytest.raises(ValueError, match="chemistry mismatch"):
        assert_chemistry(DEGRADED_RUN)


def test_rejects_a_wrong_value_not_only_a_missing_one():
    with pytest.raises(ValueError, match="ht: expected -0.25, file has -0.75"):
        assert_chemistry("mix2d_ring_N70_L60_exp_kT0.45_fs0.0_ht-0.75_ww0.50_sd40.npz")


def test_amphiphile_requires_negative_head_tail():
    """The invariant behind the constant: a head must PREFER a tail neighbour to a head neighbour."""
    assert AMPHIPHILE["ht"] < 0.20, "chi_HT must beat chi_HH or leaflets do not hold together"
