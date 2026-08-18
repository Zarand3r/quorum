"""Guard the cost of a simulation step against regression.

Iteration speed is a real constraint here: 60k steps is the standard experiment unit, so the step
cost sets how many hypotheses fit in a day, and full-submersion runs need roughly 4x the solvent
tokens against an O(N^2) force. A silent 2x regression would not fail any correctness test and would
quietly halve the research rate.

The threshold is on a RATIO, not on milliseconds. A wall-clock bound is not portable and turns a
loaded machine into a false failure; dividing by a fixed reference workload measured in the same
process cancels most of the machine and most of the load. The measurement code is imported from
`bench_step` rather than copied, so the number the test guards is the number the tool reports.
"""
from __future__ import annotations

import pytest

import bench_step

# Measured on the development host over repeated runs after the 2026-08-06 optimisation:
# ratio 7.19 / 7.34 / 8.30, i.e. ~7.6 with a ~15% spread. The gate sits at roughly 2x that, so it
# catches a doubling (the size of regression that matters) while tolerating ordinary noise.
#
# History, for anyone tempted to relax it: the step was 51.2 ms before trig sharing (which removed a
# duplicated (N,N) transcendental evaluation and a 9.3 MB per-step temporary, bit-identically) and
# 27.5 ms after adding the Chebyshev recurrence. Raising this bound should require the same kind of
# evidence that lowering it did.
MAX_RATIO = 15.0


@pytest.mark.perf
def test_step_cost_has_not_regressed() -> None:
    engine = bench_step.make(lipids=63, water=250)
    ms = bench_step.step_ms(engine, steps=40)
    cal = bench_step.calibration_ms()
    ratio = ms / cal
    assert ratio < MAX_RATIO, (
        f"step cost regressed: {ratio:.2f}x the reference workload (gate {MAX_RATIO}), "
        f"{ms:.1f} ms/step at N={engine.X.shape[0]}. Run "
        f"`bazel run //projects/vivarium:bench_step -- --profile` for the per-function breakdown."
    )


@pytest.mark.perf
def test_step_cost_scales_no_worse_than_quadratic() -> None:
    """The force law is all-pairs, so cost must track N^2 and not something steeper.

    A neighbour-list or chunking bug shows up here as a rising cost-per-N^2 long before it shows up as
    a wrong structure, and full-submersion runs quadruple N -- where a hidden N^3 term turns a
    30-minute run into a day.

    BOTH points sit above the cache transition, which an earlier version of this test did not. At
    N=339 the (N,N) matrices fit in cache and at N=789 they do not, so cost-per-N^2 rose 2.01x for
    memory-hierarchy reasons and failed a threshold meant to catch algorithmic blowup. Measured
    ms/step/N^2 across sizes: 136 (N=289), 142 (439), 154 (689), 151 (1189) -- rising across the
    transition, flat above it. Comparing 689 against 1189 isolates the exponent, which is the thing
    under test; a genuine N^3 term would show 2-3x here, far outside the noise.
    """
    small = bench_step.make(lipids=63, water=500)
    large = bench_step.make(lipids=63, water=1000)
    n_s, n_l = small.X.shape[0], large.X.shape[0]
    per_small = bench_step.step_ms(small, 15) / n_s ** 2
    per_large = bench_step.step_ms(large, 15) / n_l ** 2
    assert per_large < per_small * 1.6, (
        f"cost per N^2 grew {per_large / per_small:.2f}x from N={n_s} to N={n_l}; "
        f"the step is scaling worse than quadratic"
    )
