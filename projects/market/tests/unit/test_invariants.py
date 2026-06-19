"""
Invariant tests — PLAN.md §5 promises, verified on synthetic data.

These tests intentionally do not touch network, LLM, or filesystem; they
exercise pure functions in ``market.scoring`` against deterministic inputs
so a regression in time-discipline shows up on a fresh checkout.

The tests are the verification anchors named in ``PLAN.md`` §14 and the
``docs/ELVES_SETUP.md`` batch-1 checklist for the first elves run.
"""

from datetime import datetime, timedelta, timezone

import pytest

from market.scoring.abnormal_return import (
    LookAheadError,
    abnormal_return,
    cumulative_abnormal_return,
    score_prediction,
)


# ---------- I8: no look-ahead in abnormal return ----------


@pytest.mark.unit
class TestInvariantI8:
    """``abnormal_return_{i, t+h}`` uses only returns realized in ``(t, t+h]``."""

    def test_synthetic_flat_sector_returns_zero_abnormal(self):
        # When ticker == sector for every period, abnormal return is zero.
        ticker = [0.005, 0.001, -0.002, 0.003]
        sector = [0.005, 0.001, -0.002, 0.003]
        assert cumulative_abnormal_return(ticker, sector) == 0.0

    def test_synthetic_trending_sector_subtracted_cleanly(self):
        # A 1%/period sector trend should be perfectly subtracted out.
        ticker = [0.015, 0.012, 0.010]
        sector = [0.010, 0.010, 0.010]
        car = cumulative_abnormal_return(ticker, sector)
        assert abs(car - (0.005 + 0.002 + 0.000)) < 1e-12

    def test_synthetic_jumpy_sector_negative_abnormal(self):
        ticker = [0.001, 0.001, 0.001, 0.001]
        sector = [0.030, -0.020, 0.010, 0.005]   # net sector +0.025
        car = cumulative_abnormal_return(ticker, sector)
        assert abs(car - (0.004 - 0.025)) < 1e-12

    def test_shape_mismatch_is_a_programmer_bug(self):
        with pytest.raises(ValueError, match="shapes differ"):
            cumulative_abnormal_return([0.01, 0.02], [0.01])

    def test_pairwise_arithmetic(self):
        # Anchor for I8: the per-period operation is exactly ticker − sector.
        assert abnormal_return(0.012, 0.010) == pytest.approx(0.002)
        assert abnormal_return(-0.005, 0.001) == pytest.approx(-0.006)


# ---------- I10: monotonic-in-time scoring ----------


def _utc(*args, **kwargs) -> datetime:
    return datetime(*args, tzinfo=timezone.utc, **kwargs)


@pytest.mark.unit
class TestInvariantI10:
    """A prediction at ``t`` is scored only with realized data in ``(t, t+h]``."""

    def test_in_window_score_succeeds(self):
        t0 = _utc(2026, 6, 1, 15, 0)
        result = score_prediction(
            prediction_time_utc=t0,
            horizon_days=5,
            realized_timestamps_utc=[
                t0 + timedelta(days=1),
                t0 + timedelta(days=2),
                t0 + timedelta(days=5),  # inclusive upper bound
            ],
            realized_ticker_returns=[0.01, 0.005, -0.002],
            realized_sector_returns=[0.005, 0.005, 0.001],
        )
        assert result.n_periods == 3
        assert result.cumulative_abnormal_return == pytest.approx(
            (0.01 - 0.005) + (0.005 - 0.005) + (-0.002 - 0.001)
        )

    def test_at_prediction_time_is_rejected(self):
        # A realized return AT t (not after t) is look-ahead — t is the
        # observation closed at the prediction moment, not after.
        t0 = _utc(2026, 6, 1, 15, 0)
        with pytest.raises(LookAheadError, match="at or before prediction_time"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=5,
                realized_timestamps_utc=[t0, t0 + timedelta(days=1)],
                realized_ticker_returns=[0.0, 0.01],
                realized_sector_returns=[0.0, 0.005],
            )

    def test_before_prediction_time_is_rejected(self):
        t0 = _utc(2026, 6, 1, 15, 0)
        with pytest.raises(LookAheadError, match="at or before prediction_time"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=5,
                realized_timestamps_utc=[t0 - timedelta(hours=1)],
                realized_ticker_returns=[0.01],
                realized_sector_returns=[0.005],
            )

    def test_past_horizon_is_rejected(self):
        t0 = _utc(2026, 6, 1, 15, 0)
        with pytest.raises(LookAheadError, match="past horizon end"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=5,
                realized_timestamps_utc=[t0 + timedelta(days=6)],
                realized_ticker_returns=[0.01],
                realized_sector_returns=[0.005],
            )

    def test_unordered_timestamps_rejected(self):
        t0 = _utc(2026, 6, 1, 15, 0)
        with pytest.raises(ValueError, match="strictly increase"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=5,
                realized_timestamps_utc=[
                    t0 + timedelta(days=2),
                    t0 + timedelta(days=1),
                ],
                realized_ticker_returns=[0.01, 0.02],
                realized_sector_returns=[0.005, 0.01],
            )

    def test_naive_datetime_rejected(self):
        # Constitution: "No row that influences a prediction stores a
        # local-time string, a naive timestamp, or an unparseable date."
        # The scoring path rejects naive datetimes outright.
        naive = datetime(2026, 6, 1, 15, 0)  # no tzinfo
        with pytest.raises(LookAheadError, match="timezone-naive"):
            score_prediction(
                prediction_time_utc=naive,
                horizon_days=5,
                realized_timestamps_utc=[_utc(2026, 6, 2)],
                realized_ticker_returns=[0.01],
                realized_sector_returns=[0.005],
            )

    def test_naive_realized_timestamp_rejected(self):
        t0 = _utc(2026, 6, 1)
        with pytest.raises(LookAheadError, match="timezone-naive"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=5,
                realized_timestamps_utc=[datetime(2026, 6, 3)],  # no tzinfo
                realized_ticker_returns=[0.01],
                realized_sector_returns=[0.005],
            )

    def test_horizon_must_be_positive(self):
        t0 = _utc(2026, 6, 1)
        with pytest.raises(ValueError, match="horizon_days must be positive"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=0,
                realized_timestamps_utc=[],
                realized_ticker_returns=[],
                realized_sector_returns=[],
            )

    def test_array_length_mismatch_rejected(self):
        t0 = _utc(2026, 6, 1)
        with pytest.raises(ValueError, match="must align"):
            score_prediction(
                prediction_time_utc=t0,
                horizon_days=5,
                realized_timestamps_utc=[t0 + timedelta(days=1), t0 + timedelta(days=2)],
                realized_ticker_returns=[0.01],
                realized_sector_returns=[0.005, 0.001],
            )
