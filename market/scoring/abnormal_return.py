"""
Abnormal-return computation and outcome scoring.

Reference: PLAN.md §11.4.

Discipline (constitution / PLAN.md):
- I8: ``abnormal_return_{i, t+h}`` is built only from returns realized in
  ``(t, t+h]``. The functions here take a ``window_start`` (exclusive) and a
  ``window_end`` (inclusive) and raise ``LookAheadError`` if any provided
  return timestamp falls outside that window.
- I10: ``score_prediction`` is called with ``prediction_time_utc`` and
  ``horizon_days``; it accepts a series of realized post-prediction returns
  and rejects any datapoint at or before the prediction time.

These functions are pure (numpy-only) and have no I/O.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

import numpy as np


class LookAheadError(ValueError):
    """Raised when scoring inputs include data from outside the legal window.

    Catching this means a caller tried to score a prediction at ``t`` with a
    return realized at ``t`` or earlier — a violation of I8/I10.
    """


def _require_utc(ts: datetime, name: str) -> datetime:
    if ts.tzinfo is None:
        raise LookAheadError(
            f"{name}={ts!r} is timezone-naive; constitution requires UTC-aware datetimes."
        )
    return ts.astimezone(timezone.utc)


def abnormal_return(
    ticker_return: float,
    sector_return: float,
) -> float:
    """``abnormal_return = ticker_return - sector_return``.

    Pure arithmetic; no time discipline to enforce at this layer (callers
    are responsible for sourcing the inputs from the legal window).
    """
    return float(ticker_return) - float(sector_return)


def cumulative_abnormal_return(
    ticker_returns: Sequence[float],
    sector_returns: Sequence[float],
) -> float:
    """Sum of per-period abnormal returns over a window.

    Both sequences must have equal length and represent the same time grid;
    a length mismatch is a programmer bug, not an environmental failure.
    """
    tr = np.asarray(ticker_returns, dtype=float)
    sr = np.asarray(sector_returns, dtype=float)
    if tr.shape != sr.shape:
        raise ValueError(
            f"ticker and sector return shapes differ: {tr.shape} vs {sr.shape}"
        )
    return float(np.sum(tr - sr))


@dataclass(frozen=True)
class ScoreResult:
    """Outcome of scoring one prediction."""
    cumulative_abnormal_return: float
    horizon_days: int
    n_periods: int


def score_prediction(
    prediction_time_utc: datetime,
    horizon_days: int,
    realized_timestamps_utc: Iterable[datetime],
    realized_ticker_returns: Sequence[float],
    realized_sector_returns: Sequence[float],
) -> ScoreResult:
    """Score a prediction made at ``prediction_time_utc`` using returns realized
    in the half-open window ``(prediction_time_utc, prediction_time_utc + horizon_days]``.

    Raises:
        LookAheadError: if any realized timestamp is ≤ ``prediction_time_utc``
            or > ``prediction_time_utc + horizon_days`` — i.e. if the caller
            attempted I8 or I10 look-ahead.

    The timestamps and the return sequences must align element-wise; index
    ``i`` of ``realized_timestamps_utc`` is the time at which return ``i``
    was realized. The function does *not* sort — it enforces strict
    monotonic increase, so the caller passes data in time order.
    """
    if horizon_days <= 0:
        raise ValueError(f"horizon_days must be positive, got {horizon_days}")

    t0 = _require_utc(prediction_time_utc, "prediction_time_utc")
    t_end = t0 + timedelta(days=horizon_days)

    timestamps = list(realized_timestamps_utc)
    ticker = list(realized_ticker_returns)
    sector = list(realized_sector_returns)

    if not (len(timestamps) == len(ticker) == len(sector)):
        raise ValueError(
            "timestamps, ticker_returns, and sector_returns must align: "
            f"got {len(timestamps)}, {len(ticker)}, {len(sector)}"
        )

    prev_ts: datetime | None = None
    for i, ts in enumerate(timestamps):
        ts_utc = _require_utc(ts, f"realized_timestamps_utc[{i}]")
        if ts_utc <= t0:
            raise LookAheadError(
                f"I10 violation: realized_timestamps_utc[{i}]={ts_utc.isoformat()} "
                f"is at or before prediction_time={t0.isoformat()}"
            )
        if ts_utc > t_end:
            raise LookAheadError(
                f"I8/I10 violation: realized_timestamps_utc[{i}]={ts_utc.isoformat()} "
                f"is past horizon end {t_end.isoformat()} (horizon_days={horizon_days})"
            )
        if prev_ts is not None and ts_utc <= prev_ts:
            raise ValueError(
                f"realized_timestamps_utc must strictly increase; "
                f"index {i}={ts_utc.isoformat()} ≤ index {i - 1}={prev_ts.isoformat()}"
            )
        prev_ts = ts_utc

    car = cumulative_abnormal_return(ticker, sector)
    return ScoreResult(
        cumulative_abnormal_return=car,
        horizon_days=horizon_days,
        n_periods=len(timestamps),
    )
