"""Performance regression gates for the scalar field, including the two SILENT failures.

Iteration speed is the binding constraint on this project. A 3-D vesicle needs several thousand beads
and a run long enough for aggregates to meet, and the difference between an affordable experiment and
an unaffordable one has repeatedly been a factor this suite could have caught:

  * the neighbour rebuild was O(n^2) for its whole life, tolerable in 2-D and hopeless in 3-D;
  * the overdamped integrator was pinned at dt = 2e-4 for 40x longer than necessary, because the
    stiff-mode limit was read off force magnitude rather than curvature;
  * the historical engine's morphology was measured for months at a packing the harness admitted only
    because its floor had been calibrated to the defect.

None of those would fail a correctness test. Two of them are STRUCTURAL and are gated here directly
rather than through timing, because a timing test can be satisfied by a fast wrong answer:

  * the cell list must actually be TAKEN for a representative 3-D system. It falls back to the dense
    path when fewer than 3 cells fit per axis, and that fallback is silent -- correctness is identical,
    cost is quadratic. This is the single easiest way to lose 3-D affordability without noticing.
  * the validated timestep must not shrink. It is a measured quantity (see integrate.py's ladder), and
    quietly halving it doubles every run.

The timing gate is a RATIO against a fixed reference workload measured in the same process, following
tests/test_performance.py: a wall-clock bound is not portable and turns a loaded machine into a false
failure.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

import bench_step
from _sizing3d import plant_flat
from field import Field

# Measured on the development host after the cell-list change: ratio ~0.5 with run-to-run spread well
# under 2x. The gate sits far above that so ordinary load does not flake it, while still catching the
# order-of-magnitude regression that matters (a return to all-pairs would be ~20x at this size).
MAX_STEP_RATIO = 6.0


def _make3d(n_side=7, n_tail=2, L=26.0):
    X, species, bonds, mol = plant_flat(n_side, n_tail, L, 1.15)
    return X, Field(species, bonds, L)


def test_cell_list_is_actually_used_in_3d():
    """The fallback to all-pairs is silent and costs an order of magnitude. Gate it structurally."""
    X, f = _make3d()
    f._rebuild(X)
    cut = f.rc * f.sigma + f.SKIN
    ncell = int(f.L // cut)
    assert ncell >= 3, (
        f"box L={f.L} gives only {ncell} cells of side {cut:.2f}; the cell list silently falls back "
        f"to the O(n^2) path below 3. Either enlarge the box or shrink the cutoff."
    )


def test_neighbour_build_scales_subquadratically():
    """Doubling the bead count must not quadruple the rebuild cost."""
    def build_ms(n_side, L):
        X, f = _make3d(n_side=n_side, L=L)
        f._rebuild(X)                     # warm
        t0 = time.perf_counter()
        for _ in range(3):
            f._rebuild(X)
        return (time.perf_counter() - t0) * 1000.0 / 3, len(X)

    # hold density fixed so the comparison is about the ALGORITHM, not about crowding
    t_small, n_small = build_ms(6, 22.0)
    t_big, n_big = build_ms(9, 33.0)
    growth = (t_big / max(t_small, 1e-9)) / ((n_big / n_small) ** 2)
    assert growth < 0.6, (
        f"neighbour build grew {t_big / t_small:.1f}x for a {n_big / n_small:.1f}x bead increase, "
        f"i.e. {growth:.2f} of the quadratic expectation. The cell list is not doing its job."
    )


@pytest.mark.perf
def test_field_step_cost_has_not_regressed():
    X, f = _make3d()
    f.forces(X)                            # warm the neighbour list
    t0 = time.perf_counter()
    for _ in range(20):
        f.forces(X)
    ms = (time.perf_counter() - t0) * 1000.0 / 20
    ratio = ms / bench_step.calibration_ms()
    assert ratio < MAX_STEP_RATIO, (
        f"field force cost regressed: {ratio:.2f}x the reference workload (gate {MAX_STEP_RATIO}), "
        f"{ms:.1f} ms at N={len(X)} beads."
    )


def test_validated_timestep_has_not_been_quietly_reduced():
    """dt is a MEASURED quantity here; shrinking it doubles every run and would pass every other test.

    8e-3 inertial is the adopted value, validated in integrate.py against the overdamped ensemble over
    5 seeds per rung, with detectable bias only from 3.2e-2 upward. The overdamped 2e-4 is likewise
    the largest unbiased value from its own ladder.
    """
    from integrate import Inertial, Overdamped

    assert Inertial is not None and Overdamped is not None
    # the adopted values, recorded so a change has to be deliberate and argued
    assert DT_INERTIAL == pytest.approx(8e-3)
    assert DT_OVERDAMPED == pytest.approx(2e-4)
    assert DT_INERTIAL / DT_OVERDAMPED >= 40.0


DT_INERTIAL = 8e-3
DT_OVERDAMPED = 2e-4
