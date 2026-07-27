# Archive — superseded plans

These documents record how the project was *going* to work at various points. They are kept because
the reasoning is often still useful, but every one of them has been superseded, and where they
conflict with the current code the code wins.

They were all retired by the same shift: the decision that membrane behaviour must emerge from
**Pauli exclusion + van der Waals + electrostatics only**, which retracted the explicit per-species
lipid force laws these plans were built around. See [`../BILAYER_REVIEW.md`](../BILAYER_REVIEW.md).

| file | what it planned | why it is retired |
|---|---|---|
| `IMPLEMENTATION_PLAN.md` | M0–M2 execution checklist | milestones completed; layout formulas predate `pos_dim` and the radius channel |
| `EXPERIMENT_PLAN.md` | species → shape → membranes → fission → genes | species affinity was planned as a learned per-type matrix; the shipped design has no per-species force law |
| `MEMBRANE_PLAN.md` | membrane self-assembly via an explicit lipid law | that law (`k_hydro` / `k_tail`) is exactly what was retracted |
