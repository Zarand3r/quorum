"""
market — news-impact market state estimator.

See ``PLAN.md`` for the system design (vertical Slice 0 first; milestones
M1–M6 after) and ``docs/constitution.md`` for the invariants the elves Judge
enforces every batch.

Subpackages:
- ``market.config``  — environment-driven configuration.
- ``market.scoring`` — abnormal-return computation and outcome scoring (PLAN.md §11.4).
- ``market.legacy``  — pre-refinement sentiment-vector pipeline; preserved
  for reference but not on the path for Slice 0.
"""

__version__ = "0.2.0"
__author__ = "Richard Bao"
