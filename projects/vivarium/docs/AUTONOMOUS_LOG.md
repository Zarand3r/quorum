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

---

## 2026-08-18 — two falsifications: temperature alone fails, chain flexibility fails

**Prediction under test (stated last entry).** At kT = 0.55 the kinetic failures relax and a planted
arc closes.

**Run.** Planted arc0.75, 70 four-tail lipids, L = 40, phi = 0.55, inertial dt = 8e-3, 100000 steps
(1600 reduced time, ~32x the original arc run). Temperature the ONLY change from the kT = 0.17 arc.

| step | largest | R_mid | shell CV | lumen |
|---|---|---|---|---|
| 5000 | 64/70 | 10.73 | 0.282 | 0.51 |
| 25000 | 70/70 | 11.18 | 0.208 | 0.36 |
| 55000 | 70/70 | 11.71 | 0.178 | 0.30 |
| 85000 | **38/70** | 12.20 | 0.187 | 0.27 |

**PREDICTION FALSIFIED.** The arc did not close. It expanded from R_mid 6.73 to 12.2 and then TORE IN
TWO -- the render at 95000 shows two separate fragments with clear gaps. Moving away from closure, not
toward it. At kT = 0.55 tail-tail cohesion is only 1.27 kT per contact, so a finite ribbon has too
little line tension to hold itself together, let alone close.

**Second hypothesis, also falsified.** Proposed that `bend_frac = 1.0` (the 1-3 stiffener as stiff as
the backbone) made a rigid rod that packs into a gel, and that floppier tails would fluidise at fixed
cohesion. Swept at kT = 0.17, planted flat bilayer, vacuum:

| bend_frac | MSD/a | nbr kept | phase |
|---|---|---|---|
| 1.00 | 0.29 | 0.80 | gel |
| 0.50 | 0.19 | 0.82 | gel |
| 0.25 | 0.13 | 0.88 | gel |
| 0.10 | 0.24 | 0.84 | gel |
| 0.00 (freely jointed) | 0.33 | 0.77 | gel/intermediate |

Even a completely freely jointed chain is caged at kT = 0.17. The gel is NOT caused by chain
stiffness; it is the cohesion-to-temperature ratio itself -- chi_TT = 0.70 eps at kT = 0.17 is 4.1 kT
per contact and roughly 25 kT of binding per lipid.

**What this leaves.** Fluidity needs eps/kT low; holding a finite patch together needs the SUMMED
binding per lipid high. Those conflict at fixed tail length, and the two obvious single-knob fixes are
now both dead. The remaining route is more contacts at weaker individual contacts -- i.e. longer
tails at higher temperature -- which changes two things at once and must be swept as a plane, not a
line.

**Next, with falsification stated first.** Sweep the (kT, n_tail) plane on a planted FINITE ribbon,
scoring both fluidity (MSD/a, neighbours kept) and integrity (largest cluster). Falsification: if no
cell is simultaneously fluid (MSD/a > 1) and intact (largest > 0.9), then this force field has no
fluid-membrane regime and the vesicle target is unreachable without changing the interaction form,
not its parameters.

**Also corrected.** The wide-open C at 30000 steps was PLANTED (`plant="arc0.75"`), not emergent, and
was a failure in progress rather than a promising intermediate. No emergent vesicle exists in this
project in any dimension.

---

## 2026-08-18 — a fluid-and-intact regime exists, at short tails and kT = 0.45

**Falsification stated last entry.** If no (kT, n_tail) cell is simultaneously fluid and intact, the
force field has no fluid-membrane regime and the target is unreachable by parameters.

**NOT falsified — one cell qualifies.** Planted finite 2-D ribbon, 60 lipids, vacuum, 20000 steps:

| kT | tails | nbr kept | largest | verdict |
|---|---|---|---|---|
| 0.45 | **2** | **0.42** | 0.98 | **FLUID + INTACT** |
| 0.17/0.30 | 2 | 0.83 / 0.80 | 1.00 | intact but gel |
| 0.17/0.30/0.45 | 4 | 0.83 / 0.73 / 0.74 | 1.00 | intact but gel |
| 0.17/0.30/0.45 | 6 | 0.93 / 0.75 / 0.83 | 1.00 | intact but gel |

Shorter tails fluidise because binding per lipid scales with tail length; two tails at kT = 0.45 give
enough exchange (58% of neighbours lost) while the patch still holds at 0.98.

**INSTRUMENT ERROR CAUGHT, by having two observables disagree.** The first pass judged fluidity on
MSD/a and called every cell FLUID + INTACT, including kT = 0.17 at MSD/a = 11.57 where the spanning
3-D bilayer reads 0.29. Neighbour retention stayed at 0.83 there, i.e. gel. A finite aggregate in
vacuum translates AND rotates, and subtracting the mean displacement removes only translation.
Kabsch alignment was added, but it barely moved the number (11.53), so the residual is some other
collective mode -- ribbon curl or breathing -- that MSD cannot separate from real diffusion. MSD is
now reported only as a cross-check; the criterion is neighbour exchange, which no collective motion
can produce. Verdicts from the first pass are withdrawn.

**Next, falsification first.** Planted arc0.75 at kT = 0.45 with TWO-tail lipids -- the one qualifying
cell -- 100000 inertial steps. Prediction: it closes, or at least the ends approach rather than tear.
Falsification: if it tears like the kT = 0.55 four-tail arc (largest 70 -> 38) or sits open like the
kT = 0.17 one, then fluidity is not sufficient for closure and the blocker is elsewhere.

---

## 2026-08-18 tick — two runs in flight in the fluid regime

**Verified the planted initial condition by render.** `mix2d_arc0.75_N70_s0000000.png` shows a clean
three-quarter bilayer ring: heads on both the outer and inner surfaces, tails between. The plant is
what it claims to be, which matters because the arc result depends on starting from a real bilayer.

**Running, both at the one qualifying regime (kT = 0.45, two tails):**

1. Planted arc0.75, 70 lipids, L = 40, 100000 inertial steps. Falsification stated last entry: if it
   tears like the kT = 0.55 four-tail arc (70 -> 38) or sits open like the kT = 0.17 one, fluidity is
   not sufficient for closure. At 40000 steps R_mid has gone 5.68 -> 7.96 and shell CV 0.283 -> 0.455,
   i.e. expanding and losing shell character, with largest fluctuating 47-70. NOT read as a trend --
   this is a planted structure and early checkpoints mostly show the plant relaxing.

2. Self-assembly from dispersed, 70 lipids, L = 28, 150000 inertial steps. This is the actual target
   rather than a diagnostic. At 15000 steps: largest 53/70, fragmented, no ring.

**Fixed.** `_emerge2d` still carried the hand-rolled overdamped loop and would have run 28x slower
than necessary. Switched to the validated inertial integrator, as `_mixture` and `_sizing3d` already
were.

**Falsification for the assembly run, stated now.** If no checkpoint in 150000 steps (1200 reduced
time, ~15x the longest previous 2-D assembly run) is classified HOLLOW, and the largest aggregate
stays below 0.9 of the lipids, then fluidity alone does not produce emergence either, and the next
question is nucleation rate rather than membrane phase.

---

## 2026-08-18 tick — third closure failure, and a crash that killed a run

**Arc at the fluid regime (kT = 0.45, two tails), 100000 steps — PREDICTION FALSIFIED.**

| step | largest | R_mid | shell CV | lumen water |
|---|---|---|---|---|
| 0 | 70/70 | 5.68 | 0.283 | 22 |
| 50000 | 68/70 | 7.53 | 0.510 | 5 |
| 100000 | 68/70 | 8.93 | 0.412 | 4 |

The render at 100000 shows the arc UNROLLED into a broad shallow band with the ends far apart and one
detached fragment. It did not close; it flattened. Lumen water 22 -> 4.

Three closure attempts have now failed in three different regimes -- gel (kT 0.17, sits open), too hot
(kT 0.55, tears in two), fluid-and-intact (kT 0.45, unrolls). **Fluidity is not sufficient for
closure.** In every case the arc EXPANDED, which is what a membrane does when its preferred curvature
is flatter than the planted one.

**RUN LOST TO A LATENT CRASH.** The 150000-step assembly run died at 18750 steps:
`ring_assay.classify` does `rh[outer].max()` where `outer = slice(i_core + 1, len(rr))`, which is
EMPTY when the tail-density peak lands in the outermost radial bin -- routine for any aggregate that
reaches rmax, i.e. dispersed or spanning configurations. Latent for the whole life of the assay
because its three calibration gates all use COMPACT aggregates whose tail peak is never at the edge.
Guarded, and gated by a new test that plants exactly that geometry.

**Next, falsification stated first.** The 74 kT preference for the closed ring was measured at
kT = 0.17 with FOUR-tail lipids -- in the gel, with a different lipid, one seed per arm. Re-measuring
ring vs arc at (kT = 0.45, two tails) over 5 seeds. If E(ring) - E(arc) is not resolvably negative at
2 sigma, then closure is NOT preferred for this lipid at this temperature, the three failures need no
kinetic explanation, and the earlier 74 kT is a property of the gel phase rather than of the model.

---

## 2026-08-18 tick — the ring-vs-arc comparison is blind; switching to measuring the constant

**Falsification stated last entry.** If E(ring) - E(arc) is not resolvably negative at 2 sigma,
closure is not preferred for this lipid at this temperature.

**Result, and the criterion does NOT apply.** 70 two-tail lipids, L = 40, kT = 0.45, 5 seeds,
30000 steps:

|  | E/lipid |
|---|---|
| ring | -59.620 +- 0.491 |
| arc0.75 | -59.620 +- 0.181 |
| difference | **-0 +- 81 kT** |

The error bar is LARGER than the 74 kT effect it was built to detect, so this does not show that
closure is unfavourable -- it shows the measurement is blind to it. Seed-to-seed structural variation
dominates: the ring's per-lipid spread alone is about 1.1 eps, and resolving 0.48 eps/lipid at that
spread needs of order 80 seeds. **No conclusion is drawn from this run in either direction.**

The failure is one of experimental design rather than of sampling: differencing two large per-lipid
energies of structures that relax differently is a bad estimator no matter how many seeds are thrown
at it.

**Next, and it is what the reviewer recommended before the three closure attempts were spent.**
Measure the CONSTANT, not the difference. Closure trades edge energy saved against bending energy
paid, and the edge term isolates exactly:

    lambda = [ E(finite flat ribbon) - E(spanning flat ribbon) ] / 2

Both flat, so bending contributes to neither; the spanning ribbon is periodic and has NO ends, which
is the control that makes the difference mean only "two exposed ends". Smaller, better-posed, and
cheaper than ring-versus-arc.

**Falsification, stated before the run.** lambda must be POSITIVE and resolvable at 2 sigma, because
an exposed edge puts tails against water. If it is not, the model does not penalise an edge at all,
and every closure failure is explained directly -- there would be nothing to gain by closing.

---

## 2026-08-18 tick — line tension in progress, spanning control measured

**Running.** lambda = [E(finite flat ribbon) - E(spanning flat ribbon)] / 2, 60 two-tail lipids,
L = 30, kT = 0.45, 5 seeds, 20000 steps each arm.

Spanning arm complete: **E = -2115.13 +- 6.04**, i.e. 0.3% precision on an absolute energy of ~2115.
That matters for feasibility: if lambda is of order 10 eps per end the difference between arms is
~20 eps against a combined error near 8.5, which is resolvable at about 2.4 sigma. If lambda is much
smaller than that, this estimator will be blind too and the result must be reported as blind rather
than as zero -- the same failure the ring-versus-arc run made, and the reason its -0 +- 81 kT was
recorded as uninformative rather than as evidence against closure.

Finite arm still running. Nothing concluded yet.

**No new render this tick.** The energy runs do not render; the newest image remains the arc endpoint
already examined (`mix2d_arc0.75_N70_s0100000.png`, the unrolled band). Noted rather than skipped,
because "looked at the render" should mean an actual look, not a box ticked.

**Standing falsification, unchanged.** lambda must be positive and resolvable at 2 sigma. If it is
not resolvable, that is a statement about the instrument. If it is resolvable and NEGATIVE or zero,
the model does not penalise an exposed edge and all three closure failures are explained without any
kinetic argument.

---

## 2026-08-18 tick — line tension measured; kappa attempt RETRACTED, gate was too weak

**Line tension, the falsification did NOT fire.** 60 two-tail lipids, L = 30, kT = 0.45, 5 seeds:

| | E |
|---|---|
| spanning (no ends) | -2115.13 +- 6.04 |
| finite (two ends) | -2078.50 +- 12.79 |
| **lambda** | **+18.31 +- 7.07 eps = +40.7 +- 15.7 kT per end** |

Positive and resolvable at 2.6 sigma. An exposed edge costs energy, so closure has about **81 kT** to
gain from removing two ends -- independently confirming the earlier, noisy 74 kT ring-versus-arc
figure by a much better-posed route. This is the first number in this line of work that has survived
its own error bar.

That reduced the problem to one unknown: closing our ribbon costs about `pi*kappa/R ~ 0.54*kappa`, so
closure is favoured whenever kappa < ~150 kT. Real membranes are 10-30 kT.

**kappa attempt: RESULT RETRACTED.** The undulation spectrum gave slope 19.8 with R^2 = 0.961 and
kappa = 0.7 kT, which was reported as "favoured, failures are kinetic". It is wrong. Extracting kappa
from each mode separately:

| mode | q | kappa |
|---|---|---|
| 1 | 0.209 | 10.42 kT |
| 2 | 0.419 | 2.78 kT |
| 3 | 0.628 | 0.62 kT |
| 4 | 0.838 | 0.74 kT |

**16.7x spread.** The spectrum is not q^-4 and no kappa exists to extract. R^2 = 0.961 passed because
a linear fit of 1/<|u_q|^2> against q^4 spanning 2.5 decades in x is dominated by its single largest
point -- R^2 is a poor test of a power law. The preregistered falsification ("the spectrum must follow
q^-4") DID fire; the instrument chosen to test it was too blunt to notice.

Also visible in that table is why: mode 4 has wavelength ~7 sigma, near the molecular size where
continuum bending does not apply, and mode 1 is the box itself. At 60 lipids there may be no clean
modes at all.

**Fixed and relaunched.** The gate is now per-mode consistency (spread < 2x), which cannot be passed
by a fit dominated by one point. Membrane doubled to 120 lipids in L = 60 with 24 bins and 6 modes,
because the fix for too few clean wavelengths is a bigger membrane, not a longer run.

**Falsification, restated.** If per-mode kappa still spreads by more than 2x at 120 lipids, kappa is
not measurable by undulations at any size we can afford, and the closure question must be settled by
a different route -- e.g. direct buckling, or simply testing nucleation directly.
