# Autonomous run log

Append-only. Newest entry at the bottom. Every entry records what was run, what was measured, what was
concluded, and what was RETRACTED. A conclusion with no falsification criterion stated in advance does
not belong here.

Standing rules for this log, learned the hard way in this project:
* No structural claim without a render AND a metric. Each has flattered the other in turn.
* No single-seed difference reported as an effect. Error bars or it is a fluctuation.
* Read a trend only at the end of a run. Early checkpoints of a PLANTED structure mostly show what
  was planted.
* Record retractions in full. Roughly a dozen results have been withdrawn here and most were
  instrument artefacts, so the retraction list is the most useful part of the record.

---

## 2026-08-18 — the membrane has been a gel

**Standing question.** Why does no vesicle emerge, in either dimension, when the closed state is
stable and energetically preferred?

**Measured.** Planted flat bilayer, 98 lipids, vacuum, dt = 8e-3, 30000 steps after equilibration.
Two observables: in-plane MSD of lipid centres with the sheet's drift removed, in units of area per
lipid; and the fraction of each lipid's initial six nearest in-leaflet neighbours still nearest at the
end (which collective drift cannot fake).

| kT | thickness | a/lipid | MSD/a | nbr kept | phase |
|---|---|---|---|---|---|
| **0.17** | 3.34 | 1.249 | **0.29** | **0.80** | **GEL — every run in this project** |
| 0.35 | 3.18 | 1.742 | 0.80 | 0.57 | intermediate |
| 0.55 | 3.22 | 1.339 | 5.57 | 0.21 | FLUID |
| 0.75 | 3.10 | 1.429 | 4.93 | 0.14 | FLUID |
| 1.00 | 2.89 | 1.298 | 6.79 | 0.12 | FLUID |

**Concluded.** The bilayer has been a solid sheet throughout. A gel cannot merge patches, heal edges
or change topology, so it cannot form a vesicle however long it runs. The transition sits between
0.35 and 0.55 and the membrane survives on the fluid side, so this is not solid-versus-dissolved.

**One cause, several previously separate failures:** no leaflet exchange in 200k steps; coarsening
stalling; a planted arc sitting open beside a state 74 kT lower; extended tails at a/lipid 1.15 (which
IS the gel signature); and the solvent phase-separating, since at kT/eps = 0.17 every species is far
below critical.

**Prediction to attack next.** At kT = 0.55 the kinetic failures should relax: arcs should close,
coarsening should proceed, leaflet exchange should become observable. If they do not, the gel
diagnosis is wrong and something else is blocking.

**Also established this round.** Inertial integrator = 28x end to end at the same equilibrium ensemble
(validated, 5 seeds/rung). Cell list exact against dense. Performance regression gates that were
verified to FIRE. Pre-oracle engine recovered as an independent implementation: reproduces 38/63
exactly and fails its OWN contemporaneous admissibility bar.

**Retracted this round.** The 2-D edge-scaling argument (ring is 74 kT BELOW arc, so 2-D closure is
favoured and 3-D is not required). "3-D solvent" at phi 0.15-0.35 is fragmented droplets, voiding
every 3-D result. "2-D is not implicated" was half right: it percolates at phi 0.55, but with vapour
voids, and the instrument conflated fragmentation with inhomogeneity.
