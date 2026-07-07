"""thermolife.train — the outer loop (PLAN.md §9, §10.4, §12, §13).

Truncated BPTT with random-length chunks and DETACHED boundaries (I9), the
continuing average-reward viability objective (§10.4, no order term — I10), and
the nonstationarity curriculum (§16 M5).

Planned modules (PLAN.md §12): rollout, truncated_bptt, objective, curriculum.
No implementation yet — enters at M2.
"""
