"""thermolife.env — the physical substrate (PLAN.md §5, §10.3, §12).

The ONLY layer allowed to mutate physical channels. Knows nothing about neural
nets. Owns diffusion, conservation (I1), non-negativity (I2), no-free-energy
(I3), dead-cell inertness (I4), and per-action cost (I12).

Planned modules (PLAN.md §12): fields, diffusion, transactions, lifecycle,
invariants. No implementation yet — Slice 0 (§15.1) lands these first.
"""
