"""
Abnormal-return computation and outcome scoring (PLAN.md §11.4).

Enforces the time-discipline invariants:
- I8: ``abnormal_return_{i, t+h} = return_{i, t+h} - sector_return_{i, t+h}``
  uses only returns realized in the window ``(t, t+h]``.
- I10: a prediction at ``t`` is scored only with realized data in ``(t, t+h]``.
"""

from .abnormal_return import (
    abnormal_return,
    cumulative_abnormal_return,
    score_prediction,
    LookAheadError,
)

__all__ = [
    'abnormal_return',
    'cumulative_abnormal_return',
    'score_prediction',
    'LookAheadError',
]
