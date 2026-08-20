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

---

## 2026-08-18 tick — kappa rerun in flight; the size test that does not need kappa

**Running.** Undulation spectrum on the doubled membrane, 120 two-tail lipids, L = 60, 24 bins,
6 modes, 60000 steps, kT = 0.45. Gate is per-mode consistency (spread < 2x), which the previous R^2
test could not enforce. No output yet -- it prints only at completion.

**No new render this tick.** The spectrum run does not render; the newest image is still
`mix2d_arc0.75_N70_s0100000.png`, the unrolled band, already examined. Recorded rather than skipped.

**Prepared next, and it is deliberately independent of kappa.** The closure criterion is a competition
between a constant and a size-dependent term:

    edge saved   = 2 * lambda                    (independent of ribbon length)
    bending paid = pi * kappa / R,  R = L_c/2pi  (falls as the ribbon grows)

so whatever kappa turns out to be, there is a CRITICAL SIZE above which closure wins. That converts an
awkward absolute measurement into a threshold, which is much easier to see: sweep planted arc length
at the fluid regime and look for the size at which arcs stop unrolling and start closing.

This also re-reads the three closure failures usefully. All three used ~70 lipids. If the critical
size is larger than that, they were all run below threshold and their failure says nothing about the
model -- exactly the sort of thing that should have been computed before spending three runs.

**Falsification, stated before the run.** If arcs of 70, 120, 200 and 300 lipids ALL unroll at
kT = 0.45, then either lambda does not act as measured or the bending cost does not fall with size,
and the continuum picture used to interpret every result in this line is wrong. If instead there is a
threshold, its location gives kappa directly via `pi*kappa/R = 2*lambda`, without any spectrum.

---

## 2026-08-18 tick — kappa is NOT measurable by undulations; emergence run past the crash point

**kappa on the doubled membrane: the gate fired, correctly this time.** 120 two-tail lipids, L = 60,
24 bins, 6 modes, 399 samples, kT = 0.45.

| mode | q | <\|u_q\|^2> | kappa |
|---|---|---|---|
| 1 | 0.105 | 0.282 | 491.9 kT |
| 2 | 0.209 | 0.547 | 15.8 kT |
| 3 | 0.314 | 0.830 | 2.1 kT |
| 4 | 0.419 | 0.479 | 1.1 kT |
| 5 | 0.524 | 0.772 | 0.3 kT |
| 6 | 0.628 | 0.255 | 0.4 kT |

Spread **1712x**, WORSE than the 16.7x at 60 lipids. The diagnosis is in the raw column, not the
derived one: `<|u_q|^2>` is FLAT in q (0.25-0.83 across a sixfold range of q), where a genuine q^-4
spectrum would fall by 6^4 = 1296x. A flat spectrum is white noise, i.e. the estimator is measuring
its own sampling error rather than undulations -- with 120 lipids in 24 bins each bin mean carries the
scatter of only 5 lipids.

**Conclusion: kappa cannot be obtained from undulations at any system size affordable here, and
doubling the membrane made it worse rather than better.** No kappa is reported. The earlier
kappa = 0.7 kT stands retracted.

**Emergence run cleared the crash point.** The `ring_assay` empty-slice fix works: the run passed
18750 steps, where the previous one died, and at that checkpoint the largest aggregate reached
**70/70** from a dispersed start (was 53/70). The render shows a percolating tail network with heads
at the interfaces -- not a vesicle, not a clean bilayer, but the first fully connected EMERGENT
aggregate in the fluid regime. Sent to the user.

**Loop updated.** The tick prompt now requires showing the user an EMERGENT screenshot each cycle
(self-assembly frames only, never a planted ring/arc/sphere) and keeping at least one emergence run in
flight so there is always something emergent to show. Old job 12d0ce06 cancelled, replaced by c072ec5e.

**Next, falsification unchanged.** The critical-size test: sweep planted arc length 70/120/200/300 at
kT = 0.45. Edge saved is constant at 2*lambda, bending paid falls as pi*kappa/R, so a threshold must
exist. If ALL sizes unroll, the continuum picture behind every interpretation in this line is wrong.
That test also yields kappa via pi*kappa/R = 2*lambda at the threshold -- which now matters more,
since the spectrum route is dead.

---

## 2026-08-19 — the lipid has been a DETERGENT, not a bilayer former

**Structural assumption never questioned.** Every molecule in `field.py` is a single linear chain,
HEAD-TAIL-TAIL-... The packing parameter is `P = v / (a0 * l)`, and for a SINGLE chain both `v` and
`l` are proportional to the tail bead count, so **P is independent of tail length**. Lengthening the
tail from 2 to 4 to 6 was moving a knob that mathematically cannot move the phase, which is exactly
what the (kT, n_tail) sweep showed: every tail length gel or micelle, none bilayer.

Single-chain amphiphiles sit near P ~ 1/3, the MICELLE band. That is a detergent. Real bilayer formers
are phospholipids with TWO chains per head, doubling `v` at fixed `l` and putting P in the 1/2 to 1
bilayer band.

`polar_pack.py` already carried this: `branched=False  # two tails from one head (a real lipid) vs a
linear chain`. The rewrite to `field.py` dropped it, and nothing since has questioned it -- micelles
and percolating networks are precisely what a detergent should give.

**Implemented** as a Y-topology: head with two chains of `n_tail/2`. The controlled comparison is
1 head + 2 chains of 2 against 1 head + 4 linear -- IDENTICAL bead count, different topology, so any
difference is the branching and not the size.

**Bug caught in the process.** The branched placement loop used `for k in range(half)`, shadowing the
outer bead counter `k`, which left the water index range 344 beads short. It crashed; with a different
bead count it would have silently mislabelled species instead.

**Falsification, stated before the run.** If branched and linear at matched bead count give the same
morphology, fluidity and aggregate statistics, then the packing-parameter argument does not apply to
this force field and the detergent framing is wrong. If branched gives extended bilayer sheets where
linear gives micelles and networks, the tail-length sweeps were searching a parameter that could not
have worked.

**Running.** 150000 steps, 70 branched lipids (1 head + 2x2 tails), dispersed start, kT = 0.45.

---

## 2026-08-19 tick — my own branched-vs-linear comparison was confounded

**Both emergence runs finished, and neither is usable as a comparison.**

| run | topology | n_tail | beads/lipid | HOLLOW | end state |
|---|---|---|---|---|---|
| em45b | linear | 2 | 3 | 1/41 (2%) | other, 70/70 |
| embr | branched | 4 | 5 | 12/41 (29%) | filled, 70/70 |

**Confounded twice over.** The two runs differ in BEAD COUNT (3 vs 5 per lipid) as well as topology,
so the 2% against 29% cannot be attributed to branching -- which is precisely the matched-bead-count
control I designed one entry earlier and then failed to run. And both predate the spanning-network
fix, so every HOLLOW verdict in both is suspect by construction.

Recording this as an error of mine rather than a result: having written down that the clean comparison
is "1 head + 2 chains of 2 against 1 head + 4 linear, IDENTICAL bead count", I then launched
`n_tail=2 linear` against `n_tail=4 branched`.

**Relaunched properly.** Both arms at n_tail = 4 (5 beads per lipid), 70 lipids, L = 28, kT = 0.45,
150000 steps, dispersed start, with the fixed assay that rejects spanning aggregates before any radial
reasoning. Branched first, then linear, sequentially so they do not contend for CPU -- which is also
what made the performance gate flake earlier this session.

**Falsification, stated before the run.** If branched and linear at matched bead count give the same
HOLLOW fraction and the same final morphology, the packing-parameter argument does not apply to this
force field and the detergent framing is wrong. If branched gives materially more closed structures,
then the tail-length sweeps were searching a parameter that mathematically could not have worked, and
the topology is the lever.

**No new emergent render this tick.** The newest is the branched endpoint already sent last cycle;
not resending it, and not substituting a planted frame.

---

## 2026-08-19 tick — the box has been excluding closure all along, and the banner said so

**Matched branched-vs-linear, both n_tail = 4 (5 beads/lipid), fixed assay, 150000 steps:**

| topology | R_mid | shell CV | HOLLOW | end |
|---|---|---|---|---|
| linear | 11.70 | 0.283 | **0 of 41** | spanning |
| branched | 9.15 | 0.446 | **0 of 41** | spanning |

**The 29% HOLLOW reported for branched last cycle was entirely the spanning-network artefact.** With
the corrected assay it is 0%, cleanly confirming both that the fix works and that the earlier signal
was nothing. Retracted in full.

Morphology does differ -- branched is markedly more compact (R_mid 9.15 against 11.70) and less
shell-like -- so topology is doing something, but neither closes.

**THE ACTUAL BLOCKER, and it has been printed at the top of every emergence run in this project:**

    "a spanning stripe costs about 56 lipids, so a ring is affordable ABOVE -- stripe wins this count"

At N = 70 in L = 28, a spanning stripe is affordable, so it WINS. A ring cannot form because a stripe
is cheaper. That is geometric and independent of lipid topology, temperature, chain length, fluidity
or the assay -- every variable this project has spent weeks sweeping. The banner has stated the
diagnosis on every run and was never acted on.

This also re-reads the whole emergence series: every 2-D assembly run at L = 28 with N >= 56 was in
the stripe-favoured regime, so none of them could have produced a ring and none of them says anything
about whether this force field can.

**Relaunched in the ring-favourable regime.** N = 70, L = 40, so a stripe needs 80 lipids and is
UNAFFORDABLE; the banner now reads "a ring is affordable BELOW this count". Branched lipid, kT = 0.45,
fixed assay, 150000 steps, dispersed start. Every known fix applied at once for the first time.

**Falsification, stated before the run.** If no checkpoint is HOLLOW in the ring-favourable regime
with the branched lipid at fluid temperature, then geometry was not the blocker either, and the
remaining candidates are nucleation rate and the critical-size threshold. If a ring does appear, it
will be the first emergent closed structure in this project and must be confirmed by render before it
is claimed -- five false HOLLOW verdicts precede it.

---

## 2026-08-19 tick — ring-favourable geometry also fails; the window may not exist

**Ring-favourable run, every known fix applied at once** (N = 70 branched, L = 40 so a stripe needs 80
and is unaffordable, kT = 0.45 fluid, fixed assay, 150000 steps, dispersed):

**HOLLOW 0 of 41**, and still classified "spanning" at the end (R_mid 15.24 in L = 40).

Two things follow.

**The affordability formula is too crude.** It costs a stripe at 2L lipids, assuming one lipid per unit
arc per leaflet. The system spanned with 70 anyway, so real packing is tighter than that or the
spanning object is a thin percolating network rather than a two-leaflet stripe. The estimate should
come from the MEASURED area per lipid, not from an assumed spacing -- the same lesson as every other
inherited constant in this project.

**The morphology is macroscopic demixing, not a membrane.** The render shows dense lipid blobs with
water pushed to one side. So: too concentrated gives a spanning stripe, too dilute gives a droplet,
and neither is a ring. The window between them may be very narrow at this system size, or absent.

That is consistent with the 2-D literature found earlier -- in 2-D lattice amphiphile models, above the
CMC monomers form circular micelles and adding more amphiphile "simply results in more micelles, the
micelles retaining their characteristic size".

**Bug fixed.** Render filenames omitted L and kT, so the L = 40 run OVERWROTE the L = 28 branched
frames and the two could not be told apart. Now `em2d_{topology}_N{n}_L{L}_kT{kT}_s{step}`.

**Next: the standing critical-size test, at last.** Planted arcs at N = 70, 120, 200, 300, branched,
kT = 0.45, fixed assay, 60000 steps each. Edge saved is constant at 2*lambda; bending paid falls as
pi*kappa/R; so a threshold must exist unless the continuum picture is wrong.

**Falsification, stated before the run.** If all four sizes unroll, then either lambda does not act as
measured or bending does not fall with size, and the continuum framing behind every interpretation in
this line is wrong -- which would also mean the +40.7 kT line tension, the one number that survived its
error bar, does not do what we think it does. If instead there is a threshold, its location gives kappa
directly via pi*kappa/R = 2*lambda, with no spectrum.

**Approaching the stuck criterion.** Closure has now failed in five distinct regimes (gel, too hot,
fluid, stripe-favoured, ring-favourable), each time with a NEW mechanism proposed, so criterion (b)
-- same hypothesis falsified three times with no new mechanism -- has not strictly fired. But the
critical-size test is the last idea in the current frame. If it fails too, this warrants a reviewer
prompt rather than a sixth regime.

---

## 2026-08-19 tick — A CRITICAL SIZE APPEARS. Planted arcs stop unrolling above ~120 lipids

**Critical-size test, planted arc0.75, branched, kT = 0.45, L = 40, 60000 steps:**

| N | R_mid | shell CV | lumen ratio | lumen water | outcome |
|---|---|---|---|---|---|
| 70 | 9.79 | 0.370 | **0.00** | 0 | lumen lost, unrolls |
| 120 | 11.72 | 0.353 | 1.40 | 85 | lumen retained |
| **200** | 17.04 | **0.218** | 1.12 | 45 | lumen retained, most shell-like |
| 300 | — | — | — | — | CRASHED: box too small |

**The prediction is supported.** The render at N = 200 shows a nearly closed thick annulus with a
large central lumen, heads lining BOTH the inner and outer boundaries, and a remaining seam at the
lower right. At N = 70 the identical plant unrolls flat. This is the first arc in the project to hold
its curvature rather than flatten, and the threshold sits between 70 and 120.

That also retroactively explains the three earlier closure failures: **all used ~70 lipids, which is
below the threshold.** They were run in a regime where unrolling is the correct behaviour, so none of
them was evidence about the model -- exactly the risk flagged when this test was designed, and the
reason it should have been run before them.

**Planted, not emergent.** This is closure of a planted arc, i.e. a statement about which states are
stable, not about reachability.

**Emergence is unchanged.** 45 branched lipids, dispersed, L = 28: HOLLOW 0 of 41, all 45 in one
aggregate, dense slab with water expelled -- the same demixing phenotype as every other condition
tried. Emergence has now given the same answer at N = 45, 70 (L = 28 and L = 40), linear and branched,
kT = 0.17/0.45/0.55.

**Bug.** N = 300 crashed on `L=40.0 too small for 300 lipids at packing fraction 0.55`. The sweep
hard-coded one box size across a 4x range in lipid count, so the largest arm was unrunnable. Relaunched
with the box scaled to the lipid count (N = 300 at L = 52, plus N = 150 at L = 44 to tighten the
threshold).

**Falsification for the next run, stated first.** If N = 300 and N = 150 also retain their lumen, the
threshold is confirmed between 70 and 120 and kappa follows from `pi*kappa/R = 2*lambda` at that
radius. If N = 300 unrolls where N = 200 did not, the ordering is non-monotonic and the continuum
picture fails -- which would put the +40.7 kT line tension in question too.

**Also queued:** an emergence run at N = 200, L = 52 -- ABOVE the newly found critical size. Every
emergence run so far has been below it, so none of them could have closed. That is the single most
important consequence of this tick.

---

## 2026-08-19 tick — kappa from the threshold, and a DIMENSIONAL ERROR in the standing criterion

**Runs in flight.** N = 300 planted arc is at 36000 of 60000 (shell CV 0.183-0.192, the lowest yet,
lumen water ~180). NOT read as a trend -- planted structure, read at the end. `crit_150` and the
above-critical emergence run `em_big` have not started; the script is sequential.

**No new emergent render this tick**, so none sent and no planted frame substituted.

**kappa, derived from the threshold rather than from a spectrum.** At the critical size the two terms
balance, `2*lambda = pi*kappa/R`, so `kappa = 2*lambda*R/pi`. With lambda = 18.31 eps and the
threshold bracketed between N = 70 and N = 120:

| N | contour | R | kappa |
|---|---|---|---|
| 70 | 35.0 | 5.57 | 64.9 eps*sigma |
| 95 (midpoint) | 47.5 | 7.56 | 88.1 eps*sigma |
| 120 | 60.0 | 9.55 | 111.3 eps*sigma |

So kappa ~ 90 eps*sigma, bracketed 65-111. That is the first estimate of the bending rigidity in this
project, and it came from a threshold rather than from the undulation spectrum that failed twice.

**DIMENSIONAL ERROR, and it invalidates the criterion this whole line has been steering by.** The
standing rule "closure is favoured whenever kappa < ~150 kT" compared a 2-D kappa against real
membrane values of 10-30 kT. Those are not the same quantity:

    2-D:  E = (kappa/2) * integral (u'')^2 dx    ->  [kappa] = energy * LENGTH
    3-D:  E = (kappa/2) * integral (2H)^2 dA     ->  [kappa] = energy

An energy*length cannot be compared to an energy. **Every statement of the form "our kappa is
enormous / ordinary compared with real membranes" is withdrawn**, including the framing in the
reviewer prompt `HANDOFF_KAPPA_STUCK.md`, which asks the reviewer to help measure a quantity while
comparing it to a dimensionally different one.

The critical-size logic itself is unaffected -- it is self-consistent within 2-D, balancing two 2-D
energies -- and the retracted kappa = 0.7 kT from the spectrum was doubly wrong, being both a bad fit
and mislabelled in units.

**Falsification for the run in flight, restated.** If N = 300 retains its lumen at the end and N = 150
brackets the threshold consistently, kappa ~ 90 eps*sigma stands and the ordering is monotonic. If
N = 300 unrolls where N = 200 did not, the ordering is non-monotonic, the continuum picture fails, and
the +40.7 kT line tension goes with it.

---

## 2026-08-19 tick — threshold CONFIRMED and monotonic; falsification did not fire

**Critical-size test complete** (planted arc0.75, branched, kT = 0.45, 60000 steps, box scaled to N):

| N | R_mid | shell CV | lumen ratio | lumen water | outcome |
|---|---|---|---|---|---|
| 70 | 9.79 | 0.370 | **0.00** | 0 | unrolls, lumen lost |
| 120 | 11.72 | 0.353 | 1.40 | 85 | retained |
| 200 | 17.04 | 0.218 | 1.12 | 45 | retained |
| 300 | 23.26 | **0.194** | 0.93 | 158 | retained |

Shell CV falls MONOTONICALLY with size and only N = 70 loses its lumen. The stated falsification --
all sizes unroll, ordering non-monotonic -- did not fire. The N = 300 render confirms the metric: a
thick annulus with a large water-filled lumen, heads clearly lining the inner boundary, one seam at
the bottom.

So the threshold sits between 70 and 120, the continuum picture holds, and lambda = +40.7 kT per end
survives as the only measurement in this line to have done so twice.

**Reviewer prompt corrected.** `HANDOFF_KAPPA_STUCK.md` asked a reviewer to help measure kappa while
comparing it against dimensionally different values. The correction is now in the document, along with
the threshold result, since question 3 of that prompt has been answered by our own data.

**No new emergent render this tick.** `em_big` (emergence at N = 200, ABOVE the critical size) is
still queued behind the N = 150 arc. Nothing sent, and no planted frame substituted.

**Falsification for `em_big`, stated before it runs.** Every emergence run in this project used
N = 45-70, i.e. BELOW the threshold where even a planted arc unrolls, so none of them could have
closed. If N = 200 dispersed also gives HOLLOW 0 of 41, then being above the critical size is not
sufficient either, and the blocker is nucleation -- reaching a single large aggregate at all -- rather
than the stability of the closed state. If it produces a closed structure, it will be the first
emergent one in this project and must be confirmed by render before any claim: five false HOLLOW
verdicts precede it.

---

## 2026-08-19 tick — first EMERGENT ring-like morphology, above the critical size

**N = 150 arc completes the threshold sweep.** shell CV 0.312, lumen ratio 1.17, 92 waters, retained.
Slots between N = 120 (0.353) and N = 200 (0.218), tightening the monotonic trend. Full series:

| N | 70 | 120 | 150 | 200 | 300 |
|---|---|---|---|---|---|
| shell CV | 0.370 | 0.353 | 0.312 | 0.218 | 0.194 |
| lumen | **lost** | kept | kept | kept | kept |

**Emergence ABOVE the critical size, in progress.** N = 200 branched, L = 52, kT = 0.45, dispersed,
at 45000 of 200000 steps: largest 178/200, verdict `fragmented` (0.89 connectivity, below the assay's
0.9 gate).

The render shows a ring-like closed loop of tails with heads on both faces enclosing a dark region,
plus several separate aggregates elsewhere. **This is the first emergent ring-like morphology in this
project.** It is NOT claimed as closure: the run is a quarter done, the assay says fragmented, and five
false HOLLOW verdicts precede it. Recorded here so that if it does not survive to the endpoint, the
early optimism is on the record alongside the outcome.

What makes it worth noting rather than dismissing: it appeared in the FIRST emergence run ever placed
above the size at which a planted arc stops unrolling. Every previous emergence run used N = 45-70,
below that threshold, where even a hand-built arc flattens.

**Falsification for the endpoint, stated now.** If at 200000 steps the aggregate is a single connected
object (>= 0.9) and `classify` returns HOLLOW with the render showing heads lining an enclosed lumen,
that is an emergent vesicle. If it returns to a slab or the loop dissolves, then being above the
critical size is necessary but not sufficient, and the blocker is nucleation into ONE aggregate rather
than the stability of a closed state -- note the run currently has several separate aggregates, which
is exactly that failure mode.

---

## 2026-08-19 tick — the emergent ring was TRANSIENT; coarsening is arrested

**RETRACTION of last tick's optimism.** The ring-like closed loop at 45000 steps has OPENED by 90000
into a branched network with large voids. It was a transient pore in a percolating network -- the same
structure that produced five false HOLLOW verdicts -- not a closing vesicle. Logged last tick as "NOT
claimed as closure", which was the right call, and the record now carries both the hope and the
outcome.

**Coarsening is arrested.** Largest aggregate has sat at 178/200 from step 40000 to 90000 -- fifty
thousand steps, shell CV flat at ~0.40, no change. The stated falsification fired: being above the
critical size is NECESSARY but NOT SUFFICIENT, and the blocker is reaching ONE aggregate rather than
the stability of a closed state.

That is consistent with the measured `D_M = D_1 / N_beads`: once aggregates are large they barely
diffuse, so the last few merges never happen. 22 lipids remain stranded in separate clusters and
cannot find the main one.

**Next: separate the two steps that emergence conflates.** Nucleation must produce one large
aggregate; closure must then bend it shut. Planting an ARC hands the system its curvature and tests
only the second step. Planting FLAT hands it a single aggregate with NO curvature, so whether it curls
is the closure question asked cleanly for the first time.

Launched: flat two-leaflet ribbon, no curvature planted, N = 200 (L = 52) and N = 120 (L = 44), both
above the critical size, branched, kT = 0.45, 100000 steps.

**Falsification, stated before the run.** If a flat ribbon above the critical size curls and closes,
closure is spontaneous once a single large aggregate exists, and everything now rests on nucleation --
which `D_M = D_1/N` says is the hard part. If it stays flat for 100000 steps, then closure needs a
curvature nucleation event that thermal fluctuation does not supply on these timescales, and the
81 kT of available edge energy is separated from the closed state by a barrier rather than a slope.

---

## 2026-08-19 tick — arrested coarsening now well sampled; flat-ribbon test in flight

**Emergence at N = 200 (above the critical size) ran to 105000 steps.** Largest aggregate 178/200,
UNCHANGED from step 40000 through 105000 -- sixty-five thousand steps without a single merge, shell CV
flat near 0.40 throughout. The render shows a branched bilayer-strand network with two satellite
aggregates that never join.

This upgrades last tick's reading from a snapshot to a well-sampled result: **coarsening is arrested,
not merely slow.** It is precisely what the measured `D_M = D_1 / N_beads` predicts -- a 178-lipid
aggregate of 5-bead lipids has 890 beads and therefore ~1/890 of a monomer's mobility, so the final
merges cannot happen on any affordable timescale.

**Not read as a trend:** `flat200` is at 10000 of 100000 and is a PLANTED structure. Deferred to its
endpoint.

**Where the problem now sits, stated plainly.** Three sub-problems were conflated for most of this
project and are now separated:

1. *Nucleation into one aggregate* -- BLOCKED. Arrested at 178/200 for 65000 steps.
2. *Closure of a curved aggregate* -- WORKS. Planted arcs at N >= 120 retain their lumen, shell CV
   falling monotonically 0.353 / 0.312 / 0.218 / 0.194 for N = 120 / 150 / 200 / 300.
3. *Closure of a FLAT aggregate* -- UNTESTED until now, and the subject of the run in flight.

Only (1) and (3) remain. If (3) works, the whole problem reduces to (1), which is a known and
quantified transport limit rather than a mystery about the force field.

**Falsification for the flat-ribbon runs, restated before their endpoints.** A flat ribbon above the
critical size that curls and closes means closure is spontaneous given one large aggregate. A flat
ribbon that stays flat for 100000 steps means the 81 kT of available edge energy is separated from the
closed state by a BARRIER, and curvature nucleation is a distinct missing step -- a different problem
from anything attacked so far.

---

## 2026-08-19 tick — coarsening arrest now 90000 steps; flat-ribbon still mid-run

**Emergence at N = 200 reached 130000 steps.** Largest aggregate 178/200, unchanged since step 40000:
**ninety thousand consecutive steps with no merge.** The two satellite aggregates on the right have
not moved appreciably in that time.

The strands DO show two-sided head coverage, so local bilayer organisation is real; what never happens
is a change in global topology. That distinction matters -- the force field builds correct membrane
locally and cannot rearrange it globally.

**`flat200` at 30000 of 100000, PLANTED, not read.** Deferred to its endpoint, per the rule that
produced the transient-ring retraction two ticks ago when it was ignored.

**Nothing new concluded this tick.** Recording that plainly rather than manufacturing a finding: the
emergence run is confirming what was already established at 65000 steps, and the one experiment that
could change the picture has not finished.

**Standing falsification, unchanged.** Flat ribbon above the critical size curls and closes -> closure
is spontaneous given one aggregate, and the whole problem reduces to nucleation. Flat ribbon still
flat at 100000 -> the 81 kT of edge energy is behind a BARRIER, and curvature nucleation is a distinct
missing step.

**Stuck-criterion check.** (a) three consecutive ticks with no measurement surviving its error bar: the
threshold sweep and lambda both survived within the last five ticks, so no. (b) same hypothesis
falsified three times with no new mechanism: each failure has produced a new mechanism, so no. (c) two
consecutive attempts at the same measurement failing for instrument reasons: kappa already tripped
this and a reviewer prompt was written. Not stuck, but the margin is thin, and if the flat-ribbon test
comes back null the honest next move is the reviewer rather than a seventh regime.

---

## 2026-08-19 tick — P_fuse launched: does contact suffice, or is there a fusion barrier?

**Runs.** Emergence at N = 200 reached 145000 steps, largest still 178/200 -- arrest now spans 105000
consecutive steps. `flat200` at 45000 of 100000, PLANTED, not read.

**No screenshot sent.** The newest emergent frame is visually indistinguishable from the one sent last
tick, because the system is frozen. A frozen system produces no new picture, and resending a
near-duplicate every half hour is noise rather than progress. Recorded instead.

**The gap this fills.** `D_M = D_1/N_beads` explains why aggregates never MEET. It says nothing about
what happens when they do, and those are different blockers with different cures:

    rarely meet, merge on contact   -> pure transport limit; fix with concentration or seeding
    meet often, bounce apart        -> a FUSION BARRIER; more sampling cannot help and the
                                       interaction form is implicated

**Launched.** Two 60-lipid flat patches placed deliberately IN CONTACT (gap 0.0, 1.0, 2.5 sigma),
branched, kT = 0.45, 5 seeds each, 20000 steps. Diffusion is removed from the question entirely, which
is what makes this cheap and decisive -- and it is the diagnostic the reviewer asked for several ticks
ago that I had not run.

**Falsification, stated before the run.** P_fuse near 1 means transport is the whole story and the
emergence failures are a sampling problem with a known scaling. P_fuse near 0 DESPITE starting in
contact means there is a barrier to merging two bilayer patches, no amount of running or concentration
will produce one aggregate, and the work should redirect at the interaction form rather than at
sampling.

---

## 2026-08-19 tick — P_fuse geometry was broken; caught by arithmetic, not by a result

**BUG, caught before it produced a number.** The first `_pfuse` launch placed two 60-lipid patches in
a box of L = 40. Each patch is `(n_each/2) * 1.05 = 31.5` sigma wide, so two patches plus the gap span
63+ sigma in a 40 sigma box: they wrapped through the periodic boundary and overlapped. P_fuse would
have returned a plausible-looking number from a configuration where the "two" patches were already
merged by construction.

Caught by checking the arithmetic while the run was in flight rather than by looking at the output --
there is no render in this harness, so the geometry had no visual check. An `assert` now enforces
`2 * width + max_gap + margin < L` at startup, so this cannot silently recur.

Relaunched with n_each = 30 (patch width 15.75, two patches plus the largest gap comfortably inside
L = 40). No result yet.

**Other runs.** Emergence at N = 200 reached 155000 steps, largest still 178/200 -- arrest spans
115000 steps. `flat200` at 55000 of 100000, planted, not read.

**No screenshot.** The emergent system is frozen and its newest frame is indistinguishable from the
one already sent.

**Falsification for P_fuse, unchanged.** Near 1 means transport is the whole story. Near 0 despite
starting in contact means a fusion barrier that sampling cannot fix.

**Note on the failure mode.** This is the second time this session that a harness without a render
produced a geometry error -- the first was the undulation spectrum measuring its own sampling noise.
Every harness that plants a configuration should render its initial condition, and the ones that do
not are exactly where the silent errors have been.

---

## 2026-08-19 tick — no new results; made initial-condition rendering the default

**Runs.** P_fuse relaunched with corrected geometry, no rows yet (15 runs). `flat200` at 70000 of
100000, PLANTED, not read. Emergence at N = 200 reached 170000, largest still 178/200 -- arrest spans
130000 steps.

**No screenshot.** The emergent system is frozen; its newest frame is indistinguishable from the one
already sent.

**Nothing new concluded.** Stated plainly rather than dressed up. Both decisive runs are mid-flight and
launching a third would only make them contend.

**Systematic fix instead.** Every harness in this project that plants a configuration WITHOUT
rendering it has produced a silent geometry error, and every harness that renders has been caught by
eye within one cycle:

  * `_pfuse` put two 31.5-sigma patches in a 40-sigma box, wrapping through the periodic boundary so
    the "two" patches were merged before the run began -- it would have returned a plausible P_fuse;
  * `_kappa` binned 120 lipids into 24 bins, so each bin mean carried the scatter of five lipids and
    the "undulation spectrum" was the estimator's own noise.

Both were caught by arithmetic AFTER the fact, not by looking. `render_initial()` now exists in
`_shot.py` and is wired into `_pfuse` and `_linetension`; an image of the starting state costs nothing
and makes that class of error visible at once.

**Falsifications outstanding, both stated earlier and unchanged.**
  * P_fuse near 1 -> transport is the whole story; near 0 despite contact -> a fusion barrier that
    sampling cannot fix.
  * flat ribbon curls and closes -> closure is spontaneous given one aggregate; still flat at 100000
    -> the 81 kT of edge energy sits behind a barrier and curvature nucleation is a distinct step.

---

## 2026-08-19 tick — P_fuse was silently killed; rerun outside bazel

**P_fuse did not run.** The relaunched job printed its header at 04:11 and then died with no traceback
and no rows, and no process remained an hour later. Cause: it was launched with `bazel run` while the
`flat.sh` script was mid-sequence issuing its own `bazel run` invocations, and the two contended for
the bazel server. The run was lost silently -- no error, no output, just an absent process.

That is the same class of loss as the `ring_assay` crash that killed a 150000-step run: a long job
disappearing without an error visible in the place I look. Relaunched directly from
`bazel-bin/projects/vivarium/_pfuse`, which needs no server and cannot contend.

**Note for future ticks:** never issue `bazel run` while another script is doing the same. Use the
built binary with `BUILD_WORKSPACE_DIRECTORY` set, as the render path requires.

**Other runs.** `flat200` at 80000 of 100000, PLANTED, not read -- close to its endpoint, which is the
result this whole line now waits on. `flat120` not started.

**No screenshot.** The emergent system remains frozen at 178/200 and its newest frame is
indistinguishable from the one already sent.

**Nothing concluded this tick.** The only content is the recovery of a lost run and the reason it was
lost.

**Falsifications outstanding, unchanged.** P_fuse near 1 -> transport is the whole story; near 0
despite contact -> a fusion barrier sampling cannot fix. Flat ribbon curls -> closure spontaneous
given one aggregate; still flat at 100000 -> the 81 kT sits behind a barrier.

---

## 2026-08-19 tick — initial-condition render pays off immediately; P_fuse running

**The render_initial fix worked as intended on its first use.** `init_pfuse_gap0.png` shows a proper
two-leaflet slab: heads on both faces, tails between, solvent around, and the two patches seamlessly
joined at gap = 0. Geometry confirmed by eye in seconds, where the previous version's overlap took an
arithmetic check after an hour of wasted run.

It also exposed something about the design: at gap = 0 the two patches are INDISTINGUISHABLE from a
single slab, so that arm is a trivial positive control (it must merge, and if it does not the harness
is broken). The informative arms are gap = 1.0 and 2.5.

**Runs.** P_fuse running from the built binary, no rows yet. `flat200` at 85000 of 100000, PLANTED,
not read. Emergence at N = 200 reached 190000 with largest still 178/200 -- arrest now spans 150000
consecutive steps.

**No screenshot.** The 190000 emergent frame differs from the 130000 one already sent only in noise:
largest identical at 178/200, shell CV 0.407 against 0.418, lumen water 207 against 202. Sending it
would imply change where there is none.

**Nothing concluded.** Both decisive results are still pending.

**Falsifications outstanding, unchanged.** P_fuse: gap 0 must merge or the harness is broken; gaps 1.0
and 2.5 near 1 mean transport is the whole story, near 0 mean a fusion barrier. Flat ribbon: curls
means closure is spontaneous given one aggregate, still flat at 100000 means the 81 kT sits behind a
barrier.

---

## 2026-08-19 tick — the flat-ribbon test was VOID: the ribbon spanned the box

**flat200 finished, and its result is withdrawn before being used.** At N = 200 the plant places
`per = 100` lipids per leaflet at 1.05 spacing, i.e. a ribbon **105 sigma wide in a box of L = 52**.
It wrapped through the periodic boundary and had NO ENDS. The whole point of the flat plant is to
provide two exposed ends whose edge energy closure can recover; with none, there was nothing to gain
and the run faithfully reported that a spanning ribbon stays flat -- which was never in question.

Endpoint numbers, recorded so the void run is on the record: largest 200/200, shell CV 0.537 -> 0.440,
lumen water 84 -> 52, R_mid 13.18 -> 13.83. The render shows a flat spanning slab with one small pore.

**Third geometry error of this kind**, after `_pfuse` (two patches wider than the box) and `_kappa`
(bins too few for the lipid count). All three were in harnesses that plant a configuration. I added
`render_initial()` two ticks ago for precisely this and did not wire it into the flat plant -- the fix
existed and was not applied where it was needed. A width assertion is now in `_plant_flat_ribbon`
itself, so the check travels with the code rather than with my attention.

**Relaunched properly.** N = 120 (width 63) in L = 90, genuinely finite, 100000 steps. Also queued an
emergence run at N = 120, L = 60 to keep a dispersed-start run in flight.

**Falsification, unchanged and now actually testable.** A finite flat ribbon above the critical size
that curls and closes means closure is spontaneous once one aggregate exists. One that stays flat for
100000 steps means the 81 kT of edge energy sits behind a barrier and curvature nucleation is a
distinct missing step.

**Standing question to the user, still open.** The oracle reached its vesicle from a DISPERSED start
with no planting at all (237 clusters -> flat sheet -> vesicle by 625000 steps, largest 20 -> 54). Our
planted diagnostics answer stability, not reachability, and the sharper comparison is the coarsening
curve -- the oracle's cluster count falls 237/146/74/49/43 while ours freezes at 178/200 for 150000
steps. That comparison has not been run and is arguably higher value than any further planting.

---

## 2026-08-19 tick — REFRAMING: the oracle never forms one big aggregate, and neither should we

**From data already in hand**, comparing the oracle's vesicle-producing run against ours:

| | oracle (3-D, N=300) | ours (2-D, N=200) |
|---|---|---|
| clusters at end | **43** | ~3 |
| largest cluster | 54 | 178 |
| largest / N | **0.18** | **0.89** |
| vesicles | 2 | 0 |

The oracle's successful state is MANY SMALL clusters, two of which happen to be closed vesicles of
~40-54 molecules. It never coalesces. Our aggregate is five times larger relative to N than the
oracle's ever gets.

**This inverts the standing diagnosis.** "Coarsening is arrested at 178/200" was read as a failure to
reach one aggregate. But the oracle does not reach one aggregate either -- it succeeds precisely
because its clusters stay small enough to close individually. Our problem is not too little
coarsening; it is **too much**, producing a percolating network that cannot close at any size.

Everything downstream of that reading is affected: the push to larger N, the ring-favourable box, the
critical-size framing as "we were below threshold". The critical-size result stands as a statement
about PLANTED arcs, but the inference "therefore emergence needs N >= 120 in one aggregate" does not
follow from it.

**Falsification, stated before the run.** If a dispersed run at much lower concentration produces many
separate aggregates and at least one closes, the reframing is right and the target is a POPULATION of
small vesicles rather than one large one. If low concentration merely gives small blobs that never
close, then aggregate size is not the discriminator and the oracle's advantage lies elsewhere -- most
likely in being 3-D, where a closed shell is reachable at 40-54 molecules while our 2-D threshold sits
at 120.

**Launched:** emergence at N = 200 in L = 100 (four times the area of the L = 52 run, so aggregates
should stay separate), branched, kT = 0.45, dispersed, 200000 steps.

**Runs.** `flatfin120` at 5000 of 100000, planted, not read. P_fuse still without rows, contending with
the flat script. No new emergent render since the last tick.

**Reporting note.** `E/lipid` is not comparable across runs with different solvent counts: it divides
TOTAL energy, water-water included, by the lipid count. The finite flat run shows -178.74 against -26
elsewhere purely because it carries 5072 waters. Not an anomaly, and not a quantity to compare.

---

## 2026-08-19 tick — THREE RUNS STALLED: 32 threads per process, load 100 on 32 cores

**All three runs showed zero progress across a full tick.** Dilute emergence still at step 0, P_fuse
still without rows, flat ribbon still at 5000. Three simultaneous stalls is an operational fault, not
a coincidence.

**Diagnosis.** Load average **100 on 32 CPUs**, from two compounding causes:

1. **Zombie runs accumulated across ticks.** Still alive were a `_pfuse 20000` believed killed two
   ticks ago, the VOID `flat` run at L = 44 (the spanning-ribbon configuration already superseded),
   and the completed `em_big` whose arrest result was established 150000 steps earlier. I have been
   launching each tick without retiring the previous one.
2. **Each numpy process spawned 32 threads.** Confirmed by counting `/proc/<pid>/task`. The workload
   is O(n) pair arithmetic over a neighbour list, which BLAS threading does not help, so four
   concurrent runs put 128 threads on 32 cores and every run crawled.

**Fixed.** All runs stopped; the two that matter relaunched SEQUENTIALLY with
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`. Load already falling
(100 -> 55). Single-threaded should be FASTER here, not slower.

**Nothing scientific concluded this tick.** The content is that a whole tick of compute was wasted and
why. Recording it because "three runs in flight" was reported as progress in the previous two ticks
when in fact nothing was advancing.

**Standing falsifications unchanged.** P_fuse: gap 0 must merge (positive control); gaps 1.0 and 2.5
near 1 mean transport is the whole story, near 0 mean a fusion barrier. Dilute emergence: many small
separate aggregates with at least one closing confirms the reframing that the oracle succeeds through
a POPULATION of small vesicles rather than one large aggregate.

**Operational rules added:** retire the previous tick's runs before launching new ones; pin thread
counts; run sequentially rather than in parallel; never use `bazel run` while a script is issuing its
own.

---

## 2026-08-19 tick — P_fuse: NOT purely transport, and the positive control failed once

**Thread pinning worked.** With `OMP/OPENBLAS/MKL/NUMEXPR_NUM_THREADS=1` and sequential execution,
P_fuse completed in one tick after two ticks of making no progress at all. Load 100 -> 54.

**Result**, two 30-lipid patches placed in contact, branched, kT = 0.45, 5 seeds, 15000 steps:

| gap | merged | largest frac (mean) |
|---|---|---|
| 0.0 (touching) | 4/5 | 0.900 |
| 1.0 | 2/5 | 0.747 |
| 2.5 | 1/5 | 0.710 |

**Neither branch of the stated falsification is cleanly satisfied.** P_fuse is not near 1 at any finite
separation, so transport is NOT the whole story -- there is real resistance to merging. But it is not
near 0 either: even at 2.5 sigma the largest cluster averages 71% of lipids, so patches do partially
join. The honest reading is an intermediate barrier, monotonic in gap.

**The positive control failed once and that is the most informative part.** At gap 0 the two patches
start geometrically joined -- the initial-condition render confirms a single continuous slab -- yet
1 of 5 seeds ended fragmented. Patches can COME APART. The harness was designed assuming gap 0 must
give 5/5, so this is a property of the physics rather than of the setup: at kT = 0.45 a bilayer patch
is marginally stable against splitting, which also explains the emergence runs ending as several
pieces rather than one.

**Caveat, stated plainly:** 5 seeds gives a binomial standard error near 0.2, so 4/5 against 2/5 is
about a 1-sigma difference. The monotonic trend is suggestive; the individual numbers are not
resolvable. Relaunched at **15 seeds** before anything is concluded from them.

**Geometry verified by render.** `init_pfuse_gap2.5.png` shows two cleanly separated two-leaflet slabs
with heads on both faces -- the guard added after the wrap-around bug is doing its job.

**No emergent screenshot.** The dilute run is at 5000 of 200000 with largest 8/200, i.e. still
dispersing; a frame of near-random lipids is not progress.

**Falsification for the 15-seed rerun.** If gap 0 still fails to reach 15/15, spontaneous splitting of
a joined patch is real and the aggregate-size problem is one of stability, not assembly. If gaps 1.0
and 2.5 stay below ~0.5 with tighter error bars, there is a genuine fusion barrier and more sampling
will not deliver one aggregate.

---

## 2026-08-19 tick — the positive control FAILS: joined patches split at kT = 0.45

**15-seed rerun overturns the 5-seed reading.** Gap 0.0, where the two patches start geometrically
JOINED (confirmed by the initial-condition render as one continuous slab):

| seeds | merged | fraction |
|---|---|---|
| 5 | 4/5 | 0.80 |
| **15** | **7/15** | **0.47** |

The 5-seed value was an over-estimate by a factor of nearly two, which is what a binomial standard
error of 0.2 at n = 5 permits. This is the reason the rerun was stated as mandatory before drawing any
conclusion, and it is the second time this session that a small-n difference has evaporated.

**A joined bilayer patch splits more often than not at kT = 0.45.** That is not a fusion barrier and
not a transport limit -- it is patch INSTABILITY. Two patches placed in contact end up apart because
one aggregate spontaneously becomes two.

**This collides with why kT = 0.45 was chosen.** It was picked as the fluid regime: at kT = 0.17 the
membrane is a gel (neighbours kept 0.80, MSD/a 0.29) that cannot rearrange, and 0.45 was the lowest
temperature measured to be fluid AND intact on a spanning ribbon. But a SPANNING ribbon cannot split --
it is periodic. The stability test that mattered was never run on a FINITE patch, which is the object
emergence actually produces.

**Reinterpretation of the emergence record.** Runs ending as several pieces (178/200 with satellites,
the dilute runs, the 45-lipid slab) were attributed to slow diffusion via `D_M = D_1/N`. At least part
of that is now better explained by patches splitting as fast as they merge, giving a steady state of
several aggregates rather than an arrested approach to one.

**Launched: patch stability against temperature**, gap 0 only, 15 seeds each, kT = 0.25 / 0.30 / 0.35 /
0.45.

**Falsification, stated before the run.** If the merged fraction rises toward 15/15 as kT falls, there
is a window where patches are both mobile and stable and it sits below 0.45. If it stays near 0.5 at
every temperature, patch splitting is not thermal and the interaction form is implicated -- the
aggregate would be unstable at any temperature this model can run.

---

## 2026-08-19 tick — oracle-like cluster distribution reproduced; the aggregates are micelles

**Emergence at N = 120, L = 60, dispersed, 80000 steps.** Largest 36/120 = 0.30, and the render shows
roughly 8-9 SEPARATE small aggregates spread across the box rather than one percolating network.

That is structurally the regime the oracle succeeds in -- 43 clusters, largest 0.18 of N -- and it is
the first time this project has produced a POPULATION of aggregates instead of either one network or
one blob. The reframing two ticks ago (the oracle never coalesces; we over-coarsen) predicted exactly
this would be reachable by diluting, and it was.

**But the aggregates are MICELLES, not vesicles.** Each blob is an orange tail core with blue heads
around its rim -- filled, no lumen. So the cluster-size distribution has been reproduced without the
closure. That separates two things that were previously conflated: getting the right POPULATION is now
solved, and getting any member of it to CLOSE is not.

It is also consistent with the 2-D literature found earlier -- above the CMC, 2-D amphiphiles form
circular micelles and adding more amphiphile "simply results in more micelles, retaining their
characteristic size". Our aggregates sit at 10-36 lipids, well below the planted-arc critical size of
120, so on the arc evidence they are individually too small to hold a lumen even if they curved.

**That is the tension to attack next:** dilution produces many small aggregates (good, oracle-like) but
each is far below the size at which a 2-D ring is stable (bad). The oracle escapes this because in 3-D
a closed shell is reachable at 40-54 molecules, while our 2-D threshold is 120.

**Patch-stability temperature sweep running** (gap 0, 15 seeds, kT = 0.25/0.30/0.35/0.45), no rows yet.

**Falsification unchanged for that sweep.** Merged fraction rising toward 15/15 as kT falls locates a
window where patches are both mobile and stable; staying near 0.5 everywhere means splitting is not
thermal and the interaction form is implicated.

---

## 2026-08-19 tick — temperature falsification FIRES in the opposite direction; I killed my own decisive test

**Patch stability against temperature, gap 0, 15 seeds, 15000 steps:**

| kT | merged | largest frac (mean) |
|---|---|---|
| 0.25 | **0/15** | 0.559 |
| 0.30 | 1/15 | 0.656 |
| 0.45 | 7/15 | 0.761 |

**The stated falsification is met, backwards.** The prediction was that the merged fraction would rise
toward 15/15 as kT fell, locating a window where patches are both mobile and stable. It FALLS TO ZERO.
There is no cooler window: colder is strictly worse.

**Which revises last tick's interpretation.** "A joined bilayer patch splits because kT = 0.45 is too
hot" is wrong. At low kT each patch compacts and rounds up INDIVIDUALLY and cannot rejoin, because
rejoining requires the mobility the gel regime removes. The gap-0 arm therefore measures seam healing
and patch coalescence together, and both are mobility-limited. Splitting is not thermally driven in
the direction assumed.

**Standing tension, now measured on both sides.** Mobility is required to merge (this result) and
mobility is what makes aggregates marginal (the 7/15 at kT = 0.45). Cohesion strong enough to hold a
patch is cohesion strong enough to freeze it. That is the same conflict the (kT, n_tail) plane showed,
now confirmed by a second, independent observable.

**OWN GOAL: `flatfin120` was `Killed`.** The finite flat-ribbon test -- repeatedly described here as
the one experiment the whole line waits on -- was destroyed by my own `pkill -9 -f "_mixture.py 100000"`
during the thread-oversubscription cleanup two ticks ago. The pattern matched the run I wanted to keep
as well as the stale ones I wanted to remove, and I did not check what the kill had hit. Relaunched.

**Falsification for the relaunch, restated.** A finite flat ribbon above the critical size that curls
and closes means closure is spontaneous given one aggregate. One still flat at 100000 steps means the
81 kT of edge energy sits behind a barrier and curvature nucleation is a distinct missing step.

**No emergent screenshot.** Nothing new since the micelle-population frame, which was correctly called
out as not being progress: those aggregates hold 10-36 lipids against a critical size of 120 and have
no bilayer character at all.

---

## 2026-08-19 tick — merging probability is monotonic in temperature and never reliable

**Patch coalescence against temperature, gap 0, 15 seeds each, 15000 steps:**

| kT | merged | largest frac (mean) |
|---|---|---|
| 0.25 | 0/15 | 0.559 |
| 0.30 | 1/15 | 0.656 |
| 0.35 | 3/15 | 0.651 |
| 0.45 | 7/15 | 0.761 |

Monotonic, and it never exceeds 47%. Two patches placed in direct contact fail to become one aggregate
more than half the time at the best temperature tested.

**The core tension is now quantified from both ends.** Merging requires mobility and rises with
temperature; integrity requires cohesion and falls with it -- at kT = 0.55 a planted arc tore in two
(70 -> 38 lipids). So the window where aggregates both merge reliably and hold together may be narrow
or absent, and that is no longer an inference from one observable but a measured trend across four
temperatures plus an independent failure above them.

**Launched: kT = 0.55 and 0.70**, same protocol, to complete the curve.

**Falsification, stated before the run.** If merged reaches ~15/15 at 0.55 or 0.70, a merging window
exists and the question becomes whether integrity survives there -- testable directly against the arc
result. If merged stays below ~10/15 even at 0.70, then two bilayer patches in contact do not reliably
coalesce at ANY temperature this model can run, which would be a statement about the interaction form
rather than about sampling or geometry.

**Flat ribbon relaunched and progressing** (10000 of 100000, largest recovered 75 -> 107 of 120).
PLANTED, not read.

**No emergent screenshot.** Nothing new since the micelle-population frame, which was correctly
identified as not progress: 10-36 lipids per aggregate against a critical size of 120, and no bilayer
character.

---

## 2026-08-19 tick — full 15-seed gap sweep: small-n was systematically optimistic

**Complete gap sweep at kT = 0.45, 15 seeds, against the earlier 5-seed run:**

| gap | 5 seeds | **15 seeds** |
|---|---|---|
| 0.0 (touching) | 0.80 | **0.47** |
| 1.0 | 0.40 | **0.20** |
| 2.5 | 0.20 | **0.13** |

All three dropped by roughly half. Not scatter around a common mean -- every value moved the same
direction, so the 5-seed run was systematically optimistic rather than merely noisy. Worth recording
as a methodological fact: in this harness, small-n over-reports merging, probably because a run that
fragments takes longer to reach its final state and short samples catch it mid-way.

**Settled result.** Two bilayer patches placed in DIRECT CONTACT become one aggregate only 47% of the
time, and 13-20% at 1-2.5 sigma separation. Merging is unreliable at every separation tested, so
neither branch of the original falsification holds: it is not a pure transport limit (contact does not
suffice) and not a hard barrier (it happens sometimes).

**Combined with the temperature curve** (0/15, 1/15, 3/15 at kT = 0.25/0.30/0.35), merging improves
monotonically with mobility and never becomes reliable in any regime where the aggregate also holds
together.

**Flat ribbon progressing properly this time** -- 15000 of 100000, largest recovered 75 -> 107 -> 115
of 120. PLANTED, not read until the endpoint. Verified it is a single run with no duplicates; earlier
`pgrep` matches were my own shell text rather than extra processes.

**No emergent screenshot.** Nothing new since the micelle-population frame.

**Falsification for the runs in flight, unchanged.** kT = 0.55 and 0.70 reaching ~15/15 locates a
merging window; staying below ~10/15 means two patches in contact do not reliably coalesce at any
temperature this model can run.

---

## 2026-08-19 tick — FALSIFICATION FIRED: patches do not reliably merge at ANY temperature

**Complete coalescence curve**, two 30-lipid patches in direct contact, 15 seeds each, 15000 steps:

| kT | 0.25 | 0.30 | 0.35 | **0.45** | 0.55 | 0.70 |
|---|---|---|---|---|---|---|
| merged | 0/15 | 1/15 | 3/15 | **7/15** | 5/15 | 4/15 |
| largest frac | 0.559 | 0.656 | 0.651 | 0.761 | 0.716 | 0.704 |

**The curve has a MAXIMUM at kT = 0.45 and the maximum is 47%.** Below it the gel cannot rearrange;
above it thermal disruption dominates. The stated falsification -- "staying below ~10/15 even at 0.70
means two bilayer patches in contact do not reliably coalesce at any temperature this model can run" --
is met at both 0.55 (5/15) and 0.70 (4/15).

**This is a statement about the INTERACTION FORM, not about sampling, geometry or protocol.** It is
not fixable by longer runs, bigger boxes, different concentrations, or the branched topology, all of
which have been tried. Two patches placed in contact -- with diffusion removed from the question
entirely -- fail to become one aggregate more than half the time at the best temperature available.

**Consequence for the vesicle target.** A 2-D ring needs >= 120 lipids in ONE aggregate (planted-arc
critical size). Dispersed runs produce aggregates of 10-36 lipids. Reaching 120 requires many merge
events, each succeeding at most 47% and typically 13-20% at realistic separations. The 2-D vesicle is
therefore not reachable in this model as it stands, and that now rests on a measured curve rather than
on repeated failures to observe one.

**Stuck criterion (b) has fired** -- the same target has failed across gel, hot, fluid,
stripe-favoured, ring-favourable and dilute regimes, and the mechanism proposed each time has now been
measured and found insufficient. Per the standing instruction, a reviewer prompt is warranted rather
than a seventh regime.

**Flat ribbon at 35000 of 100000**, PLANTED, not read: largest 89/120 with lumen falling 0.56 -> 0.30.
It is the one experiment still capable of changing the picture, so it runs to its endpoint before the
reviewer prompt is finalised.

---

## 2026-08-19 tick — dilute emergence illustrates the coalescence bound directly

**Emergence at N = 200, L = 100 (very dilute), 70000 steps.** Largest 23/200; the render shows roughly
20 small micelles scattered through the solvent, none above ~23 lipids.

This is the same micelle phase, further fragmented by dilution, and it makes the coalescence result
concrete: reaching the 120-lipid critical size from aggregates of ~20 requires many successive merge
events, each succeeding at most 47% in DIRECT CONTACT and 13-20% at realistic separations. The
dispersed route to a 2-D vesicle is closed by arithmetic, not by patience.

**Flat ribbon at 45000 of 100000**, PLANTED, not read. Largest is fluctuating (89 -> 47 -> 73 of 120),
which is itself consistent with the coalescence finding -- the ribbon is repeatedly splitting and
partially rejoining rather than holding as one object.

**Nothing retracted this tick.**

**Standing position.** The falsification that fired last tick is unchanged: patches do not reliably
merge at any temperature (peak 47% at kT = 0.45, falling to 5/15 and 4/15 at 0.55 and 0.70). Stuck
criterion (b) has fired. The reviewer prompt is drafted pending the flat-ribbon endpoint, which is the
only remaining experiment that could alter the conclusion.

**Falsification for the flat-ribbon endpoint, restated.** Curls and closes -> closure is spontaneous
given ONE aggregate, and the whole problem reduces to coalescence, which is now measured and bounded.
Still flat, or split into pieces, at 100000 -> the 81 kT of edge energy sits behind a barrier AND the
aggregate cannot even hold itself together, which would make the interaction-form conclusion firmer
still.

---

## 2026-08-19 tick — holding for the flat-ribbon endpoint; reviewer prompt drafted

**Flat ribbon at 90000 of 100000**, one checkpoint from its endpoint. PLANTED, so still not read as a
trend: largest 68 of 120, shell CV 0.261, lumen ratio 0.21. Deliberately not interpreted -- the whole
point of the endpoint rule is that this project has twice reported a planted structure's mid-run state
as a result and had to retract it.

**Dilute emergence unchanged** at largest 23/200 across 70000, 80000, 95000 and 100000 steps. No
screenshot: four checkpoints at the same value is not progress and resending would imply otherwise.

**Reviewer prompt drafted** at `docs/HANDOFF_COALESCENCE.md`, built around the coalescence curve (peak
47% at kT = 0.45; 0/15 at 0.25; 4/15 at 0.70; 3/15 and 2/15 at gaps 1.0 and 2.5 sigma). Four questions,
the sharpest being whether reliable merging should be expected in a healthy CG membrane model at all --
if real patches also merge stochastically at these sizes, our criterion is wrong rather than the model.

**Nothing concluded or retracted this tick.**

**Falsification for the endpoint, restated one last time before it lands.** A finite flat ribbon above
the critical size that curls and closes means closure is spontaneous given ONE aggregate, and the whole
problem reduces to coalescence -- which is measured and bounded at 47%. One that stays flat or ends
fragmented means the 81 kT of edge energy sits behind a barrier AND the aggregate cannot hold itself
together, which would make the interaction-form conclusion firmer and complete the reviewer prompt.

---

## 2026-08-19 — FLAT RIBBON ENDPOINT: curvature IS spontaneous; closure and integrity are not

**The decisive test, at its endpoint.** Finite flat two-leaflet ribbon, 120 branched lipids, L = 90
(genuinely finite -- width 63 in a 90 box), kT = 0.45, 100000 steps, NO curvature planted:

| | start | end |
|---|---|---|
| largest | 120/120 | **73/120** |
| shell CV | 0.541 | 0.255 |
| lumen ratio | 0.99 | 0.19 |

**The render is more informative than the metrics and disagrees with the obvious reading of them.**
The ribbon has CURLED into a pronounced S/C shape -- it is no longer flat -- and the bilayer structure
is the cleanest this project has produced: crisp heads on both faces, clean tail core, well defined
two-leaflet membrane along its whole length. It split into two pieces, and BOTH pieces curled.

So the binary falsification was too coarse. Three separate answers:

* **curvature: SPONTANEOUS.** A flat ribbon curls on its own, with no curvature planted and no
  orientation term in the energy. This is the first direct demonstration that the measured 81 kT of
  edge energy actually drives bending, rather than merely being available in principle.
* **closure: NO.** The curled ends never meet.
* **integrity: NO.** 120 -> 73, i.e. the ribbon split, consistent with the coalescence curve showing
  patches fail to hold together more than half the time at this temperature.

**Read on the metrics alone** -- lumen 0.99 -> 0.19, verdict "fragmented" -- this would have been
recorded as a flat failure. The render changed the conclusion. That is the reverse of the usual
failure here, where a metric flattered and the render corrected it, and it is the reason both are
required.

**What it changes.** The blocker is now specifically: an aggregate that curls correctly cannot stay
whole long enough to close. Curvature is not the missing ingredient; cohesion at a temperature that
permits rearrangement is. That is exactly the tension the coalescence curve measures, and it moves the
question from "can this model bend a membrane" (answered: yes) to "can it hold one together while it
bends" (answered so far: no).

**Reviewer prompt updated** to carry this result -- it materially changes question 1, since the model
does produce spontaneous curvature and clean bilayer structure, and fails only at holding the
aggregate together.

---

## 2026-08-19 tick — tail length is the one lever that decouples cohesion from mobility

**No new results.** Dilute emergence unchanged at largest 23/200 across 70000-115000 steps, i.e. 45000
steps at the same value. No screenshot: nothing has moved.

**What the flat-ribbon endpoint changed.** Curvature is spontaneous and the bilayer structure is
clean; the failure is that the aggregate splits before it can finish closing. So the target is now
specifically INTEGRITY at a temperature that still permits rearrangement.

**Why every previous attempt could not have worked.** Cohesion and mobility are both governed by
`eps/kT`, and everything tried so far moved that single ratio:

  * temperature 0.17-0.70 -- moves eps/kT directly;
  * well depth and the chi matrix -- moves eps/kT directly;
  * chain stiffness `bend_frac` -- does not change eps/kT and correspondingly changed nothing (freely
    jointed chains are still caged at kT = 0.17);
  * coherent rescaling of the whole interaction vector -- leaves eps/kT unchanged by construction.

**Tail length is different.** Binding per lipid scales with the NUMBER of tail beads while the
per-contact energy is unchanged, so a longer branched lipid can hold an aggregate together without
shifting eps/kT toward the gel. This was tested before only for LINEAR chains, where the packing
parameter `P = v/(a0 l)` is independent of tail length and the test could not have worked. With
branched topology it is a genuine lever for the first time.

**Launched:** gap-0 coalescence and integrity, branched, kT = 0.45, 15 seeds each, at n_tail = 4, 6, 8.

**Falsification, stated before the run.** If merged fraction rises materially above the 7/15 measured
at n_tail = 4, cohesion and mobility ARE separable in this model and the route is longer lipids. If it
stays near 7/15 at n_tail = 8, the two cannot be decoupled by any lever available here, and the
conclusion that the interaction form is at fault becomes firm rather than provisional -- which is
exactly what the reviewer prompt asks about.

---

## 2026-08-19 tick — reproducibility confirmed at n_tail=4; 6 and 8 pending

**n_tail = 4 reproduces 7/15 exactly** against the earlier independent 15-seed run at kT = 0.45. Same
value, same mean largest fraction (0.761). Worth recording: this harness has produced a wrap-around
geometry bug, a silently-killed run and a systematically optimistic small-n estimate, so an exact
reproduction is meaningful evidence that the current configuration is measuring what it claims.

**n_tail = 6 and 8 pending.** No conclusion until both land -- the falsification is stated in terms of
whether the merged fraction rises materially above 7/15, and one arm cannot answer that.

**Dilute emergence unchanged** at largest 23/200 across 70000-125000 steps. No screenshot.

**Fixed while waiting.** The P_fuse initial-condition render tag was `pfuse_gap{gap}` only, so a sweep
over tail length overwrote its own frames. That is the same defect that made the L = 28 and L = 40
emergence renders indistinguishable several ticks ago, and it recurred because the fix then was
applied to one filename rather than to the habit. Tags now carry every swept variable.

**Nothing concluded or retracted this tick.**

**Falsification unchanged.** Merged fraction rising materially above 7/15 at longer tails means
cohesion and mobility are separable and longer lipids are the route; staying near 7/15 at n_tail = 8
means they cannot be decoupled by any lever available in this model.

---

## 2026-08-19 — TAIL LENGTH FAILS TOO: the last lever is exhausted

**Branched tail length at fixed kT = 0.45, gap 0, 15 seeds each:**

| n_tail | merged | largest frac (mean) |
|---|---|---|
| 4 | 7/15 (0.47) | 0.761 |
| 6 | 8/15 (0.53) | 0.832 |
| 8 | 5/15 (0.33) | 0.819 |

**The stated falsification fired.** Merged fraction does not rise materially above 7/15; at n_tail = 8
it is lower. With 15 seeds the binomial standard error is 0.13, so 7, 8 and 5 sit within about
1.5 sigma of each other and the ordering is non-monotonic. The mean largest fraction improves slightly
from 4 to 6 (0.761 -> 0.832) and then stops, which is a weak hint that longer tails hold marginally
more together without ever crossing the threshold.

**This exhausts the levers.** Cohesion and mobility are both set by `eps/kT`:

* temperature, well depth, `chi` -- all move that single ratio, so they trade one against the other
  by construction;
* chain stiffness -- does not move it, and changed nothing;
* coherent rescaling of the interaction vector -- leaves it invariant by definition;
* **tail length** -- the one mechanism that raises binding per lipid at FIXED per-contact energy, and
  the only one with a distinct mechanism. It does not help.

**Standing conclusion, now firm rather than provisional.** In this interaction form, an aggregate
cannot be made to hold together at a temperature where it can still rearrange. Curvature is
spontaneous and the bilayer structure is clean (flat-ribbon endpoint), so the model bends membranes
correctly; it cannot maintain one while it bends. No further parameter search is warranted, and
`docs/HANDOFF_COALESCENCE.md` is finalised with this result in its "what has been tried" section,
including the argument for why that list is exhaustive rather than merely long.

**Dilute emergence unchanged** at largest 23/200 across 70000-155000 steps. No screenshot.

**Falsification for anything further.** Any proposed fix must either (a) raise binding per lipid
without raising per-contact energy by a mechanism other than tail length, or (b) show that reliable
coalescence is not required for vesicle formation in the first place -- which is question 2 of the
reviewer prompt and the one that could invalidate this entire line of reasoning.

---

## 2026-08-19 tick — running the control that can INVALIDATE our own conclusion

**No new results.** Dilute emergence unchanged at largest 23/200 across 70000-170000 steps, i.e.
100000 steps at the same value. No screenshot.

**The conclusion reached last tick rests on an unchecked assumption.** "Patches merge only 47% of the
time and no lever fixes it, therefore the interaction form is at fault" is only valid if reliable
coalescence is REQUIRED -- that is, if a healthy membrane model would merge patches in contact close to
always. Nobody has checked that. It is question 2 of the reviewer prompt, and rather than ask, it can
be measured directly.

**Launched: the identical protocol on the ORACLE.** `bilipid.py` produces vesicles from a dispersed
start (237 clusters -> 43, with 2 vesicles by 875000 steps), so it is a working membrane model by the
only standard that matters here. Two flat two-leaflet patches planted in contact, gaps 0.0/1.0/2.5,
15 seeds each, 30000 steps, largest connected fraction as the readout -- the same measurement, on a
model known to succeed.

**Falsification, stated before the run.** If the oracle merges near 100%, our 47% is a genuine defect
and the interaction-form conclusion stands. If the oracle also lands near 50%, then reliable
coalescence is NOT a property of working membrane models, our criterion was wrong rather than our
model, the whole coalescence argument is void, and `HANDOFF_COALESCENCE.md` must be rewritten around a
different question.

**Why this before anything else.** Every other candidate experiment builds on the coalescence
conclusion. This one tests it. Running the control that can demolish a result before building further
on it is cheaper than discovering the same thing after a reviewer points it out -- and this project has
already withdrawn roughly twenty results, most of them for exactly this reason.

---

## 2026-08-19 — RETRACTION: the coalescence conclusion is void. The oracle scores identically.

**The control fired.** Identical protocol, two flat two-leaflet patches planted in contact, 15 seeds,
gap 0:

| | merged | largest frac (mean) |
|---|---|---|
| our model | **7/15** | 0.761 |
| **oracle (`bilipid.py`)** | **7/15** | 0.910 |

The oracle produces vesicles from a dispersed start (237 clusters -> 43, two vesicles by 875000 steps).
It merges patches in direct contact at EXACTLY the rate ours does. On the binary criterion the entire
coalescence argument was built on, the two models are indistinguishable.

**RETRACTED IN FULL:**

* "Two bilayer patches in contact do not reliably coalesce at ANY temperature this model can run" as
  evidence of a defect -- it is evidence of nothing, since a working model behaves the same;
* "the interaction form is at fault", stated as firm two ticks ago after the tail-length sweep;
* the framing of `docs/HANDOFF_COALESCENCE.md`, whose central question presumed the defect it was
  asking about.

The measured numbers stand -- the coalescence curve, its maximum at kT = 0.45, the tail-length sweep --
but they no longer mean what was claimed. They describe normal behaviour, not pathology.

**What survives, and it is a different signal.** The mean largest fraction differs: **0.910 for the
oracle against 0.761 for ours.** The binary threshold at 0.9 is too coarse to see it -- the oracle sits
right at the threshold so noise pushes it either side, while ours sits well below. So there IS a gap,
it is continuous rather than binary, and the criterion chosen hid it. That is worth pursuing where the
binary claim is not.

**Why this happened.** The criterion "merged means largest fraction > 0.9" was invented here without
any reference to what a working model does. Two ticks were then spent concluding the interaction form
was broken on the strength of it, and a reviewer prompt was written around the conclusion. The control
that would test the assumption was available the whole time and cost one run.

**Gaps 1.0 and 2.5 pending.** No conclusion until they land, but they cannot rescue the retracted
claim -- the positive control alone settles it.

**Falsification for what comes next.** If the oracle's mean largest fraction stays materially above
ours at gaps 1.0 and 2.5 as well, the continuous measure is a real discriminator and the question
becomes what produces that difference. If the two converge, then our aggregates behave like the
oracle's in every respect measured here, and the failure to form vesicles must lie somewhere the
coalescence protocol does not probe at all.

---

## 2026-08-19 — COALESCENCE LINE FULLY VOID, and the real answer falls out

**Full control, identical protocol, 15 seeds:**

| gap | oracle merged | ours merged | oracle frac | ours frac |
|---|---|---|---|---|
| 0.0 | 7/15 | 7/15 | 0.910 | 0.761 |
| 1.0 | 2/15 | **3/15** | 0.613 | **0.667** |
| 2.5 | 0/15 | **2/15** | 0.447 | **0.564** |

**At separation our model is BETTER than the oracle**, on both the count and the continuous measure,
and the oracle still makes vesicles. So the "surviving continuous signal" recorded last tick
(0.910 vs 0.761 at gap 0) is retracted too -- it reverses at 1.0 and 2.5 and was one point of a
three-point comparison read in isolation.

**Coalescence is not the discriminator in any form.** Ten ticks of work on merging, splitting,
temperature curves and tail length describe behaviour our model shares with a working one.

**What the comparison leaves.** Line tension, fluidity, cluster diffusion and now coalescence are all
comparable between the two models. Our flat ribbon curls SPONTANEOUSLY with clean bilayer structure, so
curvature is not missing either. The remaining differences are exactly two: the oracle is 3-D, and the
oracle has `beta = 0.15`.

And the oracle's own beta scan settles which matters: **at beta = 0 it produces 0 vesicles in 1.5M
steps** -- flat sheets and discs, heads outward 0.42 -- against 3-4 sustained vesicles at beta = 0.15.

**So both models fail to close without imposed spontaneous curvature.** Ours behaves like the oracle at
beta = 0: correct bilayers, correct curvature response, no closure. That is not a defect in our
interaction form; it is the same result the reference gives under the same condition. The vesicle
target as specified -- closure with NO imposed C_0 -- may not be achievable in either model.

**This reframes the entire project's negative result.** "Vivarium cannot make a vesicle" was treated
for weeks as a flaw to be found. The measured position is that vivarium reproduces the reference
model's behaviour at beta = 0, and the reference needs beta != 0 to close. The open question is no
longer "what is broken" but "can closure occur without imposed spontaneous curvature at all", which is
a question about membrane physics rather than about this code.

**Dilute emergence finished:** HOLLOW 0 of 41, largest 23-27/200 throughout.

**Falsification for the next step.** The claim above predicts that an EVEN orientation term -- one
supplying rigidity with `C_0 = 0`, which was ruled out earlier on the grounds that it might import
curvature -- should NOT produce closure, while a signed `beta`-like term should. If an even term does
produce closure, the claim is wrong and spontaneous curvature is not required after all.

---

## 2026-08-19 tick — rendering the ORACLE at beta=0 through our own renderer

**No new results.** The dilute emergence run finished (HOLLOW 0 of 41, largest 23-27/200 throughout)
and nothing else completed. No new emergent render, so no screenshot.

**The gap in the synthesis.** Last tick concluded that our model reproduces the reference at beta = 0:
coalescence, line tension, fluidity and cluster diffusion all measured comparable, curvature
spontaneous in both. But the two are described differently in their own logs -- the oracle at beta = 0
is classified "flat sheet/disc", ours as a branched network of strands. Those may be the same object
under two different classifiers, or a genuine remaining difference.

Every oracle result in this project so far has been read from its own shape column. Neither model's
morphology has been viewed through the SAME renderer, which is the one comparison that would settle
it -- and this project's record on trusting classifiers over images is poor.

**Launched:** the oracle at beta = 0, N = 300, L = 25, 400000 steps, rendered with our slab renderer at
the same settings used for our own 3-D frames.

**Falsification, stated before the run.** If the oracle at beta = 0 renders as a branched network of
bilayer strands like ours, the synthesis holds and the two models agree at beta = 0 -- meaning the
vesicle target as specified (closure with no imposed C_0) is unmet by BOTH. If it renders as large
clean flat sheets where ours makes strands and micelles, our model does NOT match the reference even
at beta = 0, and the remaining gap is morphological rather than about spontaneous curvature.

**Note on what this costs.** It is a 400000-step run of the reference model purely to produce pictures.
That is justified only because the entire conclusion of the last two ticks rests on an equivalence
that has been argued from numbers and never checked by eye.

---

## 2026-08-19 tick — oracle render was broken by a coordinate convention; caught by looking

**The beta = 0 render is void.** It showed roughly 20 beads out of 600. Cause: `bilipid` wraps
positions into `[0, L)` while our renderer assumes coordinates centred on zero and cuts a slab about
z = 0. Passing them through unchanged put the slab in a corner of the box, so it sampled a thin sliver
of empty space rather than a cut through the aggregate.

**Caught by looking.** No metric would have flagged it -- the run completed, every checkpoint reported
"rendered", and the images were produced on schedule. Only the picture was obviously wrong. That is the
same lesson as the too-thick slab that turned a hollow shell into a filled ball, and it is the fourth
render-or-geometry convention error this session.

**Fixed properly rather than patched.** The frame is now unwrapped relative to one bead under the
minimum image, then recentred on the aggregate's own centre of mass, and the slab cut through THAT. A
slab through a fixed plane is meaningless for a structure free to sit anywhere in a periodic box --
which is true of every 3-D render in this project, not just this one.

**Relaunched with a positive control.** beta = 0 (400000 steps) AND beta = 0.15 (800000 steps). The
beta = 0.15 arm is the control that makes the comparison interpretable: it is known to produce vesicles
by 625000 steps, so if our renderer shows clean hollow shells there and strands at beta = 0, the
renderer is trustworthy and the beta = 0 morphology can be believed. Without it, a disappointing
beta = 0 image could just be another broken view.

**No new results, nothing concluded.** No emergent render since the dilute run finished, so no
screenshot.

**Falsification, restated.** beta = 0 rendering as branched bilayer strands like ours means the two
models agree at beta = 0 and the vesicle target as specified is unmet by both. Rendering as large clean
flat sheets means our model does not match the reference even at beta = 0, and the gap is
morphological. The beta = 0.15 arm must show vesicles, or neither reading can be trusted.

---

## 2026-08-19 — ORACLE MORPHOLOGY COMPARED BY EYE: beta=0 is flat, beta=0.15 is curved

**Both arms rendered through OUR renderer, recentred on the aggregate's centre of mass.**

* **beta = 0** (400000 steps): an elongated strand -- a slab cut through a flat sheet -- plus one
  compact disc, and scattered fragments. Extended, FLAT structures.
* **beta = 0.15** (700000 steps): curved C-shaped arcs with heads outside and tails inside, i.e. slab
  cuts through small shells, alongside compact clusters.

**The positive control did its job.** The renderer distinguishes the two conditions, and its verdict
matches the oracle's own independent classifier ("flat sheet/disc" against "VESICLE"). So the beta = 0
image can be believed, which was the whole point of running the control arm.

**The synthesis is supported.** beta = 0 produces extended flat structures; that is morphologically
what our model produces -- branched bilayer strands that never curve into shells. The reference model
without spontaneous curvature and our model without it look like the same kind of object.

**Caveat, stated because it limits the strength of this.** The oracle's vesicles are tiny -- R ~ 2.3
sigma, 40-54 molecules -- so a +-2.0 slab captures nearly the whole object and a clean ring is not
expected even for a perfect shell. The beta = 0 structures are much larger, so the two arms are not
sampled equivalently by a fixed slab. The qualitative distinction (flat and elongated versus curved
arcs) is visible and matches the classifier; a quantitative morphological comparison would need the
slab scaled to each object.

**No emergent screenshot.** These are oracle renders, not self-assembly from our model, so they do not
qualify under the standing rule. Nothing new from our own emergence runs.

**Where this leaves the project.** Every measured property now matches between the two models --
coalescence at all three gaps, line tension, fluidity, cluster diffusion, spontaneous curling of a flat
ribbon -- and the one difference that produces vesicles in the reference is `beta`, which we excluded
by design. The remaining question is the one for the reviewer: whether closure without imposed C_0 is
achievable at all, or whether the target as specified is unreachable in principle.

**Falsification for any further work.** A model with an EVEN orientation term (rigidity, C_0 = 0)
should not close if this reading is right. That is the one cheap test left that could overturn it.

---

## 2026-08-19 tick — our force field in 3-D with IMPLICIT solvent, to separate dimensionality from beta

**Two differences remain** between our model and the reference: the oracle is 3-D, and it has
`beta = 0.15`. Every other measured property now matches. This run separates them.

**Why implicit solvent.** Our 3-D explicit water is fragmented droplets at every affordable packing
fraction (0.15-0.35: largest cluster 0.27-0.48, empty cells), which voided every previous 3-D run. The
oracle uses no solvent at all. Setting `phi = 0` removes the defect rather than working around it, and
the hydrophobic ordering survives through `chi`, where tails attract tails (0.70) more than heads
attract heads (0.20) -- the Cooke-Deserno construction.

**Launched:** our field, 3-D, 300 branched lipids, no water, L = 25 (the oracle's box), kT = 0.45,
dispersed start, 400000 steps.

**Falsification, stated before the run.** If vesicles appear, 2-D was the blocker all along, the model
is otherwise complete, and every 2-D negative result was answering a question about dimensionality
rather than about the force field. If flat sheets and strands appear as in 2-D, dimensionality is NOT
the difference and `beta` is the remaining candidate -- which would mean our model reproduces
oracle-at-beta-0 in three dimensions as well as two.

**Two harness bugs fixed to get here**, both of the same family as earlier ones:
* `n_water` was computed from `phi` with no zero case, so implicit solvent raised "L too small";
* `geometry` computed lumen occupancy from an empty water array. It now returns NaN rather than 0 --
  reporting 0 would read as "lumen collapsed" when nothing was measured at all, which is precisely the
  silent-zero this project has been caught by before.

**No emergent screenshot.** Nothing new since the dilute run finished; this 3-D run is at step 0.

---

## 2026-08-19 tick — 3-D implicit solvent under way; shell CV is NOT a shell indicator

**Our field, 3-D, implicit solvent, dispersed, at 40000 of 400000 steps.** Largest 126/300, shell CV
0.187, and the render shows two compact FILLED aggregates -- the +-1.2 slab would show a ring if they
were hollow.

**Metric confusion caught before it became a claim.** Shell CV 0.187 is the lowest any emergent
structure has reached here, and the obvious reading is "most shell-like yet". It is not. Shell CV is
`std(r)/mean(r)` over lipid beads about the centre: a FILLED sphere gives about 0.25 and a thin shell
about 0.05, so a low value means COMPACT, which a filled ball satisfies just as well as a shell.

**Calibration, from the oracle's own vesicles:** shell CV **0.045-0.057** when it is genuinely closed.
That is the reference number this project never had, and it makes 0.187 clearly a blob. Recording it so
"shell CV fell" is never again reported as progress toward closure without checking against 0.05.

**Not over-read.** 40000 of 400000 steps, and the oracle needed 625000 to close, so this is early. It
is a dispersed-start run, so early checkpoints are legitimate to note -- unlike a planted structure,
where they mostly show the plant.

**No conclusion yet. Falsification unchanged:** vesicles here mean 2-D was the blocker and the model is
otherwise complete; flat sheets and compact blobs mean dimensionality is not the difference and `beta`
is the only remaining candidate.

---

## 2026-08-19 tick — 3-D with implicit solvent gives the SAME phenotype as 2-D

**At 200000 of 400000 steps:** largest 126/300, unchanged since step 20000 -- **180000 steps frozen**.
Shell CV oscillating 0.182-0.217 against the oracle's 0.045-0.057 for genuine vesicles. The render
shows filled blobs with heads and tails intermixed, no hollow interior at a slab that would reveal one.

**Dimensionality is not the difference.** Moving to 3-D and removing the solvent defect entirely --
the two changes that were supposed to matter -- reproduces the 2-D phenotype exactly: rapid
condensation into a few aggregates, then arrest, with filled interiors rather than shells. Same
arrested coarsening, same filled aggregates, same shell CV far from the oracle's.

**Which leaves `beta` as the only remaining candidate**, and the oracle's own scan already establishes
what it does: 0 vesicles at beta = 0 over 1.5M steps, 3-4 sustained at beta = 0.15. Our model now
matches the reference at beta = 0 in BOTH dimensions, on every property measured -- coalescence at all
three gaps, line tension, fluidity, cluster diffusion, spontaneous curling of a flat ribbon, and now
3-D morphology.

**Not final until the run ends.** 200000 of 400000, and the oracle needed 625000 steps to close, so
this arm is still short of the reference's own timescale. But the largest cluster has not moved in
180000 steps, which is what arrest looks like rather than slow progress.

**Falsification for the endpoint.** If shell CV falls toward 0.05 and a lumen appears by 400000, 3-D
does help and this reading is wrong. If it stays near 0.19 with largest frozen, dimensionality is
excluded and the project's negative result is: our force field reproduces the reference at beta = 0,
and closure requires the spontaneous-curvature term that was excluded by design.

---

## 2026-08-19 — QUANTITATIVE EQUIVALENCE: our model at 3-D matches the oracle at beta = 0

**Direct comparison, both 300 molecules, 3-D, no solvent, dispersed start:**

| | largest / N | shell CV | closed? |
|---|---|---|---|
| **oracle, beta = 0** (1.5M steps) | 103/300 = **0.34** | **0.367** | 0 vesicles |
| **ours** (300k steps, still running) | 126/300 = **0.42** | **0.270** | none |
| oracle, beta = 0.15 | 54/300 = 0.18 | **0.045-0.057** | 3-4 vesicles |

Our aggregate fraction and shell CV sit in the same range as the reference at beta = 0, and both are far
from the beta = 0.15 signature. The oracle at beta = 0 is classified "flat sheet/disc" and "tube/
elongated" over its last checkpoints; ours is filled blobs and strands. Same regime, by the numbers and
by the renders.

**Shell CV is rising in our run** (0.182 -> 0.270 between 180000 and 300000 steps), i.e. moving AWAY
from the 0.05 that marks a closed shell, while largest has been frozen at 126 since step 20000.

**The equivalence is now supported on seven independent measurements:** coalescence at three gaps, line
tension, fluidity, cluster diffusion, spontaneous curling of a flat ribbon, 3-D morphology by render,
and now aggregate fraction and shell CV against the reference's own beta = 0 endpoint.

**The project's negative result, stated precisely.** Our force field reproduces the reference model at
beta = 0 in both dimensions and on every property measured. The reference produces vesicles only at
beta != 0, where beta IS the spontaneous curvature. Closure with no imposed C_0 is therefore not
demonstrated by either model, and the vesicle target as originally specified -- emergent closure with
curvature arising rather than imposed -- has not been achieved by us and is not achieved by the
reference either under the same constraint.

**What would overturn this.** Adding a signed beta-like term to OUR field and obtaining vesicles would
confirm the force field is otherwise complete; failing to obtain them would show some further
difference. That is the natural final experiment and it is a real implementation -- an orientation term
with correct gradients through bead positions -- not a parameter change. It is scoped, not started.

**Falsification for the run still in flight.** Shell CV falling toward 0.05 by 400000 with a lumen
appearing would overturn the equivalence. Staying near 0.27 with largest frozen confirms it.

---

## 2026-08-19 tick — shell CV rising monotonically; queued a run at the oracle's own timescale

**3-D implicit at 360000 of 400000.** Largest still 126/300, frozen since step 20000. Shell CV rising
monotonically across the whole run:

    step      180k    200k    240k    260k    280k    300k    320k    340k    360k
    shell CV  0.182   0.198   0.227   0.265   0.253   0.270   0.276   0.285   0.293

That is the aggregate becoming LESS compact over time, moving steadily away from the 0.045-0.057 that
marks a closed shell in the reference. Not a system approaching closure slowly.

**No screenshot:** structure unchanged from the frame already sent, largest frozen and morphology the
same filled blobs.

**One objection to the equivalence remains open**, and it is fair: our run is 400000 steps while the
oracle needed 625000 to its first vesicle. A negative at 400000 does not exclude closure at 700000.

**Queued: 1.2M steps**, the same configuration, which is nearly twice the oracle's time to first
closure. That removes the objection rather than arguing against it.

**Falsification, stated before the long run.** If a lumen appears and shell CV falls toward 0.05 before
1.2M steps, the equivalence claim is wrong and our model simply needed the reference's own timescale.
If largest stays frozen and shell CV keeps rising, the "not long enough" objection is closed and the
negative result stands as stated: our force field reproduces the reference at beta = 0, and closure
requires the spontaneous-curvature term excluded by design.

---

## 2026-08-19 — 3-D IMPLICIT RUN COMPLETE: dimensionality excluded

**Endpoint, 400000 steps, 300 branched lipids, 3-D, implicit solvent, dispersed:**

| | start | end |
|---|---|---|
| largest | 13/300 | **126/300**, frozen since step 20000 |
| shell CV | 0.264 | **0.319** |

Shell CV rose monotonically 0.182 -> 0.319 over the second half, against 0.045-0.057 for the
reference's genuine vesicles. **The stated falsification is met**: shell CV did not fall toward 0.05
and no lumen appeared, so 3-D does not help and dimensionality is excluded as the difference.

**That leaves `beta` alone.** Our force field now matches the reference at beta = 0 on eight
independent measurements: coalescence at three gaps, line tension, fluidity, cluster diffusion,
spontaneous curling of a flat ribbon, 3-D morphology by render, aggregate fraction, and shell CV.

**Limitation of the 1.2M continuation, stated plainly.** `_mixture` fixes both the build seed and the
integrator seed, so the long run reproduces the 400000-step trajectory exactly -- it has already hit
largest = 126 at step 60000, the same value. It therefore tests DURATION only, not seed variability.
The conclusion rests on one trajectory per condition in 3-D, which is thinner than the 15-seed
coalescence work and should be described that way. Multiple seeds at 1.2M steps each is not affordable
here; if the duration test comes back negative, the honest statement is "one trajectory, run to twice
the reference's time to closure", not "3-D cannot close".

**No screenshot.** Structure unchanged from the frame already sent: largest frozen, same filled blobs.

**Falsification for the 1.2M run, unchanged.** A lumen with shell CV falling toward 0.05 before 1.2M
steps overturns the equivalence. Largest frozen with shell CV rising closes the duration objection for
this trajectory.

---

## 2026-08-19 tick — seed control added; 3-D replicates launched to fix the one-trajectory weakness

**The weakness identified last tick, now addressed.** `_mixture` hardcoded both the builder seed and
the integrator seed, so every 3-D result in this project is ONE trajectory, and the 1.2M "long run" is
a deterministic replay of the 400k one -- it reproduces largest = 126 at step 60000 exactly. Duration
and seed variability are different questions and only the first was being asked.

**Launched:** three independent seeds at 400000 steps each, same configuration (300 branched lipids,
3-D, implicit solvent, dispersed, L = 25, kT = 0.45). The 1.2M duration arm continues in parallel.

**Why replicates before more duration.** The coalescence work taught that small samples in this harness
are systematically optimistic -- the 5-seed gap sweep over-reported by roughly 2x against 15 seeds. A
conclusion resting on n = 1 in 3-D, while the 2-D coalescence numbers rest on n = 15, is the weakest
leg of the equivalence argument and the cheapest to strengthen.

**Falsification, stated before the replicates land.** If all three seeds arrest with largest well below
300 and shell CV rising away from 0.05, the 3-D negative is a property of the model rather than of one
trajectory. If any seed closes, the single-trajectory conclusion was wrong and n = 1 was exactly the
error the coalescence work warned about.

**No screenshot:** the replicates are at step 0 and the completed run's structure is unchanged from the
frame already sent.

**Also fixed:** render tags now carry the seed (`mix3d_random_N300_sd{seed}_s{step}`), so replicate
frames cannot overwrite one another -- the same defect as the missing `L` and missing `n_tail` in
earlier tags, applied as a rule this time rather than patched per filename.

---

## 2026-08-19 tick — seed variability is real: 67 vs 126 at the same step

**First replicate reporting.** Seed 1 at step 60000 has largest **67/300** where seed 0 had **126/300**
at the same point -- roughly a factor of two. Shell CV 0.297, still far from the 0.05 that marks a
closed shell.

**So the n = 1 concern was substantive, not pedantic.** Aggregate size in 3-D varies about twofold
between trajectories, which means the single-trajectory result reported two ticks ago ("largest 126,
frozen") described one draw rather than the model's behaviour. The equivalence argument's 3-D leg was
genuinely thinner than its 2-D legs, and the replicates are the right fix.

**Neither trajectory is closing**, which is the part that matters for the conclusion: seed 0 arrested
with shell CV rising to 0.319, seed 1 is at 0.297 and also not falling. Variability is in HOW MUCH
aggregates, not in WHETHER they close.

**Duration arm at 300000** of 1.2M, reproducing seed 0 exactly as expected of a deterministic replay
(largest 126, shell CV 0.270). It tests duration only; the replicates test variability. Both are needed
and neither substitutes for the other.

**No screenshot:** seed 1 is early and seed 0's structure is unchanged from the frame already sent.

**Falsification unchanged.** All three seeds arresting with shell CV rising means the 3-D negative is a
property of the model. Any seed closing means the single-trajectory conclusion was wrong.

---

## 2026-08-19 — 3-D RENDERS WERE CUT AT A FIXED PLANE; "filled blob" readings are suspect

**Caught by an empty frame.** Seed 1 at step 220000 rendered as a completely blank image. Cause:
`_mixture.shot` cuts its slab about z = 0 while the aggregate is free to sit anywhere in a periodic
box, so it caught nothing.

**The serious consequence is not the blank frame.** An OFF-CENTRE slab through a hollow shell looks
like a FILLED DISC. Every "filled blobs, not shells" reading taken from a 3-D render in this project
was made through a fixed-plane cut of unknown offset, so those readings are suspect until re-rendered.
That includes the frames sent for the 3-D implicit-solvent runs.

**This is the same defect fixed in the ORACLE renderer two ticks ago and not propagated here.** The
oracle version was patched to unwrap and recentre on the aggregate's centre of mass; `_mixture.shot`
was left alone. Third instance in this session of fixing a defect in one place and leaving its sibling
untouched -- the others being the render-tag omissions (L, then n_tail, then seed).

**Fixed properly:** `shot` now unwraps relative to one bead under the minimum image and recentres on
the aggregate's centre of mass before slabbing.

**What is NOT affected.** All 2-D renders -- every emergence frame sent to the user, the flat-ribbon
curl, the planted rings and arcs -- have no slab at all and are unaffected. The metrics are also
unaffected: shell CV, largest cluster and lumen occupancy are computed from coordinates, not from the
render.

**Re-render launched** on seed 0 to 240000 steps with the corrected slab, so the "filled versus hollow"
question can be re-answered on the same trajectory that produced the original claim.

**Falsification, stated before the re-render.** If the recentred slab shows filled discs, the original
reading stands and 3-D aggregates really are solid. If it shows rings, the aggregates were hollow all
along and the 3-D negative result is wrong -- which would also undo the conclusion that dimensionality
is excluded.

---

## 2026-08-19b — the shell-CV metric was wrong in the direction that flatters us; implicit solvent was different physics

Chasing the blank frame from the previous entry turned up two more defects, both load-bearing.

### The shell-CV metric had two defects (`_cvcontrol.py`, gated in `tests/test_geometry_metric.py`)

Planted control: a shell at real membrane density (area/lipid 1.2 sigma^2, Fibonacci-sampled), three
bead layers at radii 6/7/8, so its CV is known analytically as 0.117. Scored three ways:

| configuration | legacy | fixed | legacy error |
|---|---|---|---|
| centred shell alone | 0.117 | 0.117 | 0% |
| SAME shell straddling a corner | **0.035** | 0.117 | **70% LOW** |
| centred shell + 180 loose lipids | **0.595** | 0.117 | **411% HIGH** |

* **The centre was a plain mean of WRAPPED coordinates.** For a straddling cluster that lands in empty
  space; radii become about L/2*sqrt(3) and the spread is divided by that inflated mean. Minimum-image
  wrapping of the displacement HIDES it, because every radius still comes out below L/2. The bias is
  toward LOW CV, which is the direction that reads as a tight vesicle.
* **It averaged over every lipid, not the largest cluster.** In the 3-D runs the largest cluster held
  119-126 of 300, so two thirds of the beads scored sat in other aggregates.

**Withdrawn:** every shell CV from a multi-cluster emergent run. That includes the 3-D implicit-solvent
series "rising 0.182 -> 0.319" and last tick's "seed 1 at 0.154, the lowest yet." Seed 1's number is
confounded twice over and is exactly what a straddling aggregate produces.

**Not withdrawn:** single-aggregate planted runs at the box centre, where the legacy path is exact
(0% error above). That covers the planted-ring stability series and the critical-size sweep.

**My stated expectation was also wrong** and is recorded as such: the control first predicted ~0.05 for
the planted shell. 0.05 is the ORACLE's vesicle value; this construction is three beads thick and its
true CV is 0.117. The measurement was right and the prediction was wrong.

### The corrected render answers the filled-versus-hollow question, and raises a worse one

With the slab recentred, the aggregate is a **filled disc** -- so the original reading stands and the
falsification stated last entry resolves in favour of "solid, not hollow." But the heads (blue) are
scattered THROUGH the tail mass rather than sitting on the surface, which is not merely "not a
vesicle": it is not even an amphiphile aggregate.

**Cause: deleting the water deleted the hydrophobic drive.** Amphiphilicity here lives entirely in
`chi`, and a head is driven to the surface because it gains `chi_HW = 0.75` from water. At `phi = 0`
there is no water, while head-head (0.20) and head-tail (0.20) both remain ATTRACTIVE, so nothing
makes a buried head costly. The implicit-solvent runs were not a cheaper version of the same physics.

**Fix by derivation, not by tuning.** Integrate the solvent out instead of dropping it. In the
mean-field limit the potential of mean force is the exchange energy,

    chi_eff_ij = chi_ij + chi_WW - chi_iW - chi_jW

which on `default_chi` gives **tail-tail +1.70, head-tail +0.45, head-head -0.30**. That ordering --
cohesive tails, mutually repulsive heads -- is what implicit-solvent membrane models (Cooke-Deserno)
are built on, and it arrives from the explicit table with no new free parameter. The negative entry is
representable because `qk_factors` already carries eigenvalue signs, so a repulsive affinity is still
a query-key inner product and the transformer-only constraint holds.

**Consequence: every 3-D implicit-solvent result is void**, including the claim that 3-D reproduces
the 2-D phenotype and therefore that dimensionality is excluded. That claim rested on runs whose
lipids were not amphiphiles.

**Falsification, stated before the run.** Two seeds, 400k steps, identical but for the derived chi.
If heads segregate to the aggregate surface and shell CV (now measured correctly, on the largest
cluster) falls toward 0.117 or below, the implicit-solvent physics was the blocker and the 3-D
negative was an artefact of the wrong chi. If heads stay buried, the derived chi is not sufficient and
the defect is elsewhere in the model.

Suite: 178 passed, including 3 new metric gates.

---

## 2026-08-19c — shell CV has no discriminating power at our system size; the 0.05 target was unreachable

The planted 3-D vesicle reads shell CV **0.246 at step 0** -- before a single step of dynamics, on a
structure that is hollow by construction. That is the same value the emergent runs were producing, and
it was being read as "filled blob."

**Why.** shell CV = std(r)/mean(r) is a ratio, so it separates hollow from solid only while the
membrane is thin compared with the radius:

    thin shell of thickness t at radius R    CV = t / (sqrt(12) R)
    solid ball of radius R                   CV = 0.258, at ANY radius

Our 4-tail lipid is 5 beads, about 5 sigma, planted at R_mid 5.71. Thickness and radius are the same
size, so the shell's CV collapses onto the ball's. Measured on planted structures (`_cvdegenerate.py`,
box scaled to the structure):

| geometry | hollow-shell CV | gap vs solid ball | hollowness gap |
|---|---|---|---|
| **our 4-tail lipid, R_mid 5.71** | 0.248 | **0.016** | 1.035 |
| same lipid, R_mid 12 | 0.118 | 0.144 | 1.066 |
| thin shell, R_mid 12 | 0.068 | 0.185 | 0.850 |
| oracle-like, R_mid 20 | **0.041** | 0.220 | 1.047 |

**Two conclusions, both withdrawing earlier work.**

1. **The instrument was blind in the regime it was used.** 0.016 of separation between a perfect
   vesicle and a solid ball. Every 3-D reading of the form "shell CV says filled, not hollow" is void
   -- not because the numbers were miscomputed, but because the metric could not have said otherwise.
2. **The 0.05 target was geometrically unreachable.** The oracle's 0.045 is reproduced here by
   GEOMETRY ALONE at R_mid 20, so it is a signature of vesicle SIZE, not of vesicle quality. Reaching
   it needs R_mid ~20, i.e. about 4200 lipids, against our 300. The standing falsification criterion
   "shell CV falling toward 0.05" could never have been met at N = 300 in L = 25 regardless of the
   physics, and every negative verdict that leaned on it is withdrawn.

**Replacement: `hollow`** -- bead density in the inner third over density in the shell region. 0 = empty
centre, ~1 = filled. It separates by about 1.0 at every radius tested, including ours, and it asks the
question directly instead of inferring it from a spread. On the real planted vesicle it reads **0.000**
where CV reads 0.246. Now reported every checkpoint and gated by three tests, including one that pins
CV's blindness so the regression is visible if it ever changes.

**Relaunched** all three arms (planted control, seeds 0 and 1) under the derived chi with `hollow`
reported. The earlier arms were killed: they carried the legacy metric, and two duplicate seed-0 runs
had been writing the same filenames.

**Falsification, unchanged in substance but now measurable.** If the emergent aggregates reach
`hollow` near 0 with heads at the surface, they are vesicles and every "filled blob" verdict was an
instrument artefact. If `hollow` stays near 1, they are genuinely solid and the negative stands -- this
time on an instrument with power to say so.

---

## 2026-08-19d tick — critical-size test launched; derived chi restores head segregation

**Running:** 23 processes. Three 3-D arms under the solvent-averaged chi (planted vesicle control,
emergent seeds 0 and 1) plus the 20-run critical-size arc series below. Nothing is read as a trend yet;
the 3-D arms had run 90 seconds at tick time and the planted arm is at step 0.

### The derived chi works, visibly

Emergent 3-D seed 1 at step 20000, first frame under the solvent-averaged chi: heads sit on the RIM of
each tail core instead of scattered through it, which is what the earlier corrected render showed and
what the derived chi was introduced to fix. Largest 48/300 (from 11), E/lipid -86.9, `hollow` 2.92.

`hollow` above 1 means the core is DENSER than the shell region, i.e. a solid micelle -- correct for an
aggregate this small. **Caveat recorded now rather than after it misleads:** at R_mid 1.54 the inner
third spans about 1 sigma and holds very few beads, so `hollow` is noisy below a few hundred beads. It
is a large-aggregate instrument, and small-cluster values should not be read as structure.

### Today's blindness finding is bounded to 3-D

In 2-D the same ratio argument gives a ring of thickness 5 at R_mid 8.90 a CV of 0.162 against a filled
disc's 0.354 -- a gap of **0.192**, against 0.016 in 3-D. So shell CV retains discriminating power in
2-D, and the 2-D ring-stability and critical-size conclusions do NOT fall with the 3-D ones.

### The critical-size test, launched

The standing plan: edge saved is 2*lambda and constant; bending paid is pi*kappa/R and falls with size;
so a threshold ribbon length exists, and all three earlier failed closure attempts used ~70 lipids and
may have sat below it.

Sizes N = 70, 120, 200, 300 at kT = 0.45, arc0.75, explicit solvent phi = 0.55 (matching the conditions
lambda = 18.31 eps was measured in, so no new baseline is needed), **5 seeds each, 20 runs**, 150 000
steps.

**Box sized from the UNROLLED contour, not the arc.** Measured R_mid per size, then L = max(5R, 1.3 x
contour):

| N | R_mid | contour if straightened | L used | water |
|---|---|---|---|---|
| 70 | 6.74 | 31.8 | 42 | ~1200 |
| 120 | 9.88 | 46.6 | 61 | ~2600 |
| 200 | 15.33 | 72.2 | 94 | ~6200 |
| 300 | 22.49 | 106.0 | 138 | ~7800 |

A first attempt used L = 115 for N = 300, where the straightened ribbon of 106 sigma nearly spans the
box. That would have confined the OPEN state and biased the test toward closure -- the same failure as
the flat ribbon that spanned L = 52. Caught before launch by computing the contour rather than the
diameter.

The N = 300 plant was rendered and checked: a clean C, heads on both faces, tails in the core, two
exposed ends, box comfortably larger than the arc.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If closure fraction rises with N -- arcs staying
open at 70 and closing at 200 or 300 -- a critical size exists, kappa follows from the threshold as
kappa = 2*lambda*R*/pi, and the three earlier failures were undersized rather than physically blocked.
If ALL four sizes unroll at 5 seeds each, the continuum picture behind every interpretation in this
project is wrong, including the line-tension argument for closure. If all four CLOSE, the earlier
70-lipid failures were caused by something other than size and the threshold framing is also wrong.

---

## 2026-08-19e tick — the arc test was not too expensive; the machine was oversubscribed

### The measurement that changed the plan

The explicit-solvent arc series looked unaffordable: after ~37 minutes the N = 120/200/300 arms were
still at step 0, and a timing probe gave about 7 steps/s, implying 14-24 hours per run. I killed those
arms on that basis.

Then I profiled the same configuration **with nothing else running**:

    N = 300 arc, implicit solvent, 1500 beads, L = 138    100.5 steps/s

A **14x** discrepancy, entirely CPU contention: 23 concurrent numpy processes on 32 cores. The design
was affordable all along, and I nearly abandoned a valid experiment because of a number produced by my
own scheduling. Lesson recorded as a standing rule: **cap concurrency at 8 and never time anything
while a batch is running.** This is the second scheduling self-injury in this project, after the
32-threads-per-process oversubscription that stalled three runs for a full tick.

**What is NOT established:** the explicit-solvent cost. Both probes ran under contention, so the honest
statement is that explicit N = 300 carries 14 800 beads against implicit's 1500 and is roughly an order
of magnitude dearer, with no clean measurement of the constant.

### Profile, for the record

At 100 steps of N = 300 implicit: `_rebuild` 0.249 s, `numpy.ufunc.at` 0.225 s, `content` 0.146 s,
`_well` 0.088 s, `_pairs` 0.082 s. **`np.add.at` is 22% of runtime** and is the known-slow scatter-add;
`np.bincount` per axis is the standard replacement and is the next performance item. Not done this tick
because 26 runs now depend on the hot path and it must not change under them.

The rebuild rate (50 rebuilds per 100 steps) was measured 20 steps after a planted start, i.e. during
the overlap transient, so it says nothing about steady state and no conclusion is drawn from it.

### 3-D emergence, both seeds

| seed | step | largest | E/lipid | hollow |
|---|---|---|---|---|
| 0 | 20000 | 60/300 | -119.0 | 2.61 |
| 1 | 20000 | 48/300 | -86.9 | 2.92 |

Heads on the rim of each tail core in both, so the derived chi's restoration of head segregation
**replicates across seeds**. `hollow` above 1 means solid cores: these are micelles. Coarsening to a
single aggregate is untouched. The planted 3-D control is still at step 0 and is not read.

### Relaunched: the critical-size test in implicit solvent

N = 70/120/200/300, arc0.75, kT = 0.45, **5 seeds each**, 150 000 steps, implicit solvent with the
solvent-averaged chi, concurrency capped at 8.

**Plus six planted-RING controls** (N = 70 and 300, 3 seeds each). Implicit solvent with the derived chi
is a NEW condition, and "arcs do not close" is uninterpretable if the closed state is not even stable
there. This is the control the earlier explicit-solvent series did not need and this one does.

**Caveat stated now, not after the fact:** lambda = 18.31 eps was measured in EXPLICIT solvent. A
threshold radius from this series converts to kappa only with lambda measured in the same condition,
which has not been done. The falsification below does not depend on lambda -- it asks only whether
closure fraction varies with size -- but any kappa quoted from it would be unearned until lambda is
re-measured at phi = 0.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If closure fraction rises with N across 5 seeds, a
critical size exists and the three earlier ~70-lipid failures were undersized. If all four sizes unroll,
the continuum picture behind every interpretation in this project is wrong. If all four close, size was
never the variable. And if the planted RING controls fail to hold at either size, the whole series is
void and the result is about implicit solvent rather than about size.

---

## 2026-08-19f tick — the implicit-solvent arc series is VOID: the aggregates are not bilayers

### The critical-size test completed, and its control killed it

All 20 arcs and 6 planted-ring controls finished. The ring controls -- included last tick precisely
because implicit solvent with the derived chi is a new condition -- did their job:

| planted RING (closed-state control) | hollow | verdict |
|---|---|---|
| N = 70, 3 seeds | 1.13 - 1.16 | **collapsed to a filled disc** |
| N = 300, 3 seeds | **0.000** | holds, cleanly hollow |

So the closed state is not stable at N = 70 in this condition, and the N = 70 arm was void before the
arcs were read. The arcs showed a real size trend in `hollow` (means: N=70 1.39, N=120 1.45, N=200 1.16,
N=300 0.58).

**Then the render killed the whole series.** The N = 300 arc at 150 000 steps is still an open C, and
both it and the stable N = 300 ring are **scrambled**: heads and tails intermixed throughout, not heads
on the faces with tails in the core. Geometry survived; bilayer order did not. A trend in `hollow`
across sizes is a statement about droplet shape, not about membrane mechanics, so **the critical-size
test does not measure kappa in this condition and the series is withdrawn.**

This is the fourth time in this project a metric and a render have disagreed, and the fourth time the
render was right.

### Made it a measurement instead of an impression

"It looks scrambled" is not a result. Added `mix`: for every head bead in the aggregate, the fraction
of its close non-bonded neighbours that are TAIL beads, divided by the aggregate's tail fraction.
**1.0 = randomly mixed; a freshly planted perfect bilayer reads 0.536.**

Planted N = 300 ring, L = 138, kT = 0.45, 5 seeds per condition:

| step | 0 | 3000 | 6000 | 12000 |
|---|---|---|---|---|
| implicit sd0 | 0.625 | 0.934 | 0.936 | 0.929 |
| implicit sd1 | 0.625 | 0.942 | 0.925 | 0.921 |
| implicit sd2 | 0.625 | 0.950 | 0.936 | 0.953 |
| implicit sd3 | 0.625 | 0.934 | 0.935 | 0.934 |

**Implicit solvent scrambles the bilayer to near-random mixing within 3000 steps**, in every seed, while
the ring keeps its shape (hollow 0.000, shell CV 0.12). The explicit arm is still running and is the
comparison that decides whether this is a solvent effect or simply kT = 0.45 being too hot.

**Likely cause, stated as a hypothesis not a conclusion.** The exchange-averaged chi gives head-tail
**+0.45**, i.e. ATTRACTIVE: by that mean-field accounting an H-T contact frees water to make a W-W bond
and is favourable. Nothing then keeps heads out of the tail core except head-head repulsion. Cooke and
Deserno make head-tail purely repulsive instead. So the derivation may be too crude for a dense phase,
even though it fixed the gross defect it was introduced for (heads buried at no cost).

### Two instrument fixes

* **A cluster wider than half the box has no unambiguous centroid** under periodic boundaries. A planted,
  obviously hollow N = 300 ring in L = 70 (diameter 50.7) returned `hollow` = **1.556**, i.e. filled.
  `geometry` now returns NaN for every shape observable in that regime instead of a plausible number.
  The guard immediately proved itself: two straggler runs queued behind `xargs` started under the old
  L = 70 script after the relaunch, and came back NaN instead of quietly contributing wrong data.
* **Final state is now saved** to `docs/states/*.npz`. Post-hoc analysis has had to re-run the
  simulation three times in this project because only images and printed metrics survived, so a new
  observable could never be applied to a finished experiment.

### 3-D emergence, still in flight and progressing

Seed 1 has coarsened from ~7 micelles at step 20 000 to ~4 at 100 000, largest **48 -> 69/300**; seed 0
is at 61/300 with E/lipid -136.7. `hollow` 2.5-3.1 throughout: solid micelles, nothing hollowing out.

**FALSIFICATION, STATED BEFORE THE EXPLICIT ARM IS READ.** If explicit solvent holds `mix` near 0.54
while implicit sits at 0.93, the solvent-averaged chi is disqualified for dense phases and all membrane
work must stay explicit -- with the arc series re-run there. If explicit ALSO rises to ~0.93, the
bilayer is simply unstable at kT = 0.45 and the fault is temperature, not solvent, which would also
call into question every 2-D result measured at this temperature. If explicit rises only partway, the
effect is real but shared, and the ranking of causes needs a temperature sweep.

---

## 2026-08-19g tick — the force field was O(n^2) per step: 9.4x speedup, explicit solvent now affordable

### The blocker was never the physics

The explicit-solvent arm sat at step 0 for ~50 minutes, under 1 step/s, against 100 steps/s for a
1500-bead implicit run -- **superlinear**, so not simply "more beads." Profiled alone:

    explicit, 13 336 beads:  1.01 steps/s
    of which `content`    :  18.1 s of 19.7 s  = 92% of runtime

`Field.content()` builds the **full (n, n) attention matrix every step** and then indexes only the
neighbour pairs out of it. At 13 336 beads that is 178 million entries, about 1.4 GB, to obtain roughly
150 000 pair values.

`content_pairs(pi, pj)` evaluates the same query-key inner product only on pairs that can contribute:

| | before | after |
|---|---|---|
| explicit N = 300 ring, 13 336 beads | 1.01 steps/s | **9.54 steps/s** |

**9.4x**, values identical to **2.8e-17**, full suite PASSED (186 tests, 558 s). The attention view is
unchanged -- `content()` still exists and the tests still compare against it; it is simply not computed
where the distance cutoff already guarantees zero. This is the single largest speedup this project has
had, and it makes explicit-solvent membrane work affordable: 60 000 steps drops from ~16 hours to ~1.

**Why the existing performance test missed it.** `test_performance_field.py` pins throughput at ONE
system size, and a quadratic term is invisible until the system is large. Added
`tests/test_field_scaling.py`: 4x the beads at fixed density must cost far less than 16x. Comparing two
sizes is the only way a scaling defect can show up at all.

### The implicit-solvent result is now complete, all 5 seeds

Planted N = 300 ring, L = 138, kT = 0.45, 60 000 steps, `mix` (1.0 = randomly mixed, planted perfect
bilayer = 0.536):

| seed | step 0 | 3000 | end (60000) |
|---|---|---|---|
| 0 | 0.625 | 0.934 | 0.928 |
| 1 | 0.625 | 0.942 | 0.909 |
| 2 | 0.625 | 0.950 | 0.938 |
| 3 | 0.625 | 0.934 | 0.921 |
| 4 | 0.625 | 0.933 | 0.909 |

Scrambles within 3000 steps in **every** seed and stays there for the remaining 57 000, while the ring
holds its shape (hollow 0.000, shell CV 0.12). Mean end value **0.921 +- 0.012**.

The explicit arm produced nothing except step 0 before the fix, so **the comparison that decides
solvent-versus-temperature is still open** and is relaunched on the fast binary. No conclusion is drawn
about the derived chi until it lands.

### 3-D emergence: coarsening has stalled

Seed 1: largest 69/300 at step 120 000 and still 69/300 at 140 000, E/lipid -129.3, hollow 2.92.
Seed 0: 61/300 at 100 000, hollow 2.90. Solid micelles, arrested.

**Render limitation recorded:** `shot` centres the slab on the whole system's centre of mass, which is
meaningless when several separate aggregates exist -- the step-140 000 frame therefore catches one
aggregate and looks emptier than the step-100 000 frame. Not a collapse, an artefact of where the plane
falls. Centring on the largest cluster is the fix and is not done yet.

**FALSIFICATION, STATED BEFORE THE RELAUNCHED EXPLICIT ARM IS READ.** If explicit holds `mix` near 0.54
while implicit sits at 0.921 +- 0.012, the solvent-averaged chi is disqualified for dense phases and all
membrane work stays explicit -- now affordable. If explicit also rises to ~0.92, the bilayer is unstable
at kT = 0.45 regardless of solvent, and every 2-D result measured at this temperature is in question. If
it rises partway, both contribute and a temperature sweep is required to rank them.

---

## 2026-08-19h tick — temperature is NOT the cause; the solvent itself is not a liquid

### The temperature hypothesis is falsified

Planted N = 300 ring, explicit solvent, L = 138, 20 000 steps, 5 seeds per temperature. `mix` at the
end (1.0 = randomly mixed; planted perfect bilayer = 0.536):

| kT | seeds | mean |
|---|---|---|
| 0.15 | 0.908 0.914 0.910 0.901 0.905 | **0.908** |
| 0.25 | 0.895 0.892 0.898 0.911 0.911 | **0.901** |
| 0.35 | 0.897 0.901 0.888 0.893 0.902 | **0.896** |
| 0.45 | 0.900 (1 seed so far) | 0.900 |

**Flat across a 3x temperature range.** Cooling from 0.45 to 0.15 changes `mix` by 0.008, well inside
the seed spread. So the branch of last tick's falsification that said "explicit also rises to ~0.92, so
kT = 0.45 is too hot" is itself **wrong in its diagnosis**: explicit does rise (0.90 against implicit's
0.921), but temperature is not why. Both solvent conditions and every temperature give a scrambled
bilayer.

### What the render shows, and it is not what I was looking for

The explicit ring at the end is intact and hollow -- a clear lumen with water inside -- but the lipids
are intermixed, and **the water has phase-separated into a percolating network with large vacuum
voids.** At packing fraction 0.55 it should be a homogeneous liquid.

That is the 2-D counterpart of this project's own known-void finding, that 3-D explicit solvent at
phi 0.15-0.35 is fragmented droplets rather than a liquid. The solvent is evidently below its
liquid-vapour critical point over the range tested, so the "explicit solvent" arms have not been
simulating a membrane in water; they have been simulating a membrane in a two-phase fluid.

**This is a better candidate cause than either solvent-averaging or temperature**, and it was invisible
in every metric because no observable in this project measures whether the SOLVENT is a liquid.

### Retracted this tick

* **The guard I added last tick was wrong** and rejected valid data. It tested `2 * max(radius)`, which
  one lipid poking out of an otherwise intact ring is enough to trip: it NaN'd 3 of 5 explicit seeds
  whose rings were whole at largest = 300, R_mid 25.98. It now tests the cluster's per-axis SPAN, which
  is what unwrapping ambiguity actually depends on.
* **Every 3-D shape metric at L = 25 is void.** With the corrected guard, the planted 300-lipid vesicle
  fails the span test **at step 0**: the aggregate is wider than half the box. Re-run at L = 44 it is
  measurable, and collapses -- hollow 0.000 -> 0.018 -> **1.163** and `mix` 0.837 -> 0.963 -> 0.992
  within 200 steps. So a planted 3-D vesicle is not stable under the derived chi, and separately, the
  emergent 3-D numbers reported in the last four ticks (R_mid, shellCV, hollow at L = 25) are
  unverified. R_mid read a constant 1.57 for clusters of 61, 69 and 92 lipids, which cannot be right.
  Cluster COUNTS remain sound, being connectivity rather than geometry.
* **Fourth filename collision.** The render tag carried L, then n_tail, then seed, and still not kT, so
  all four temperature arms overwrote the same frames and the phase-separated-water image above cannot
  be attributed to a temperature. Metrics were unaffected (separate log files). kT is now in the tag
  and in the saved-state filename.

### Emergence

The L = 25 runs ended: seed 1 frozen at 69/300 from step 120 000 to 180 000; seed 0 reached 92/300.
No emergence run was left in flight, so three were relaunched at **L = 36**, chosen so a 300-lipid
aggregate still spans less than half the box and the metrics stay valid if coarsening ever succeeds.

**FALSIFICATION, STATED BEFORE THE WATER RUNS ARE READ.** Three short runs at kT = 0.15, 0.45 and 0.90,
identical but for temperature, with kT now in the render tag. If the water is a homogeneous liquid at
0.90 and voided at 0.15, the solvent has a liquid-vapour transition inside our working range and every
explicit-solvent result to date was measured in a two-phase fluid -- which would make solvent state, not
chi and not temperature, the reason bilayers do not hold. If the water is voided at ALL three, the
solvent model is wrong at this density irrespective of temperature. If it is homogeneous at all three,
then what I saw was a rendering or density artefact and this whole line is dropped.

---

## 2026-08-19i tick — ROOT CAUSE: the planted lipids were mechanically forced straight, and chi never made head-tail contact unfavourable

Three explanations for the scrambled bilayer are now falsified with 5 seeds each, and the real cause is
found. This entry supersedes the solvent and temperature lines of enquiry.

### Falsified: solvent phase state

Short runs at kT = 0.15, 0.45, 0.90 with kT now in the render tag. The water IS two-phase at 0.15 -- a
percolating network with large vacuum voids at packing fraction 0.55 -- and nearly homogeneous at 0.90,
so the solvent does have a liquid-vapour transition inside the working range. **But `mix` is 0.917,
0.894 and 0.910 across that range**, so solvent phase state does not explain the scrambling either.
Together with the previous tick, that is solvent type, temperature (6x range) and solvent phase state
all excluded.

### The planted structures were never valid configurations

| plant | E/lipid | min non-bonded r | pairs < 0.8 sigma |
|---|---|---|---|
| ring | 800.6 | **0.000** | 225 |
| arc0.75 | 811.4 | **0.000** | 1441 |
| sphere | 795.7 | 0.057 | 622 |

Equilibrium is about **-20** E/lipid. Decomposing the ring's +790 showed it was **not** steric at all:

    non-bonded core   +0.81      non-bonded well  -10.41
    1-2 springs     +400.00      (mean bond 1.500 against rest 1.0, max deviation 2.000)
    1-3 springs     +400.00      (mean 2.667 against rest 2.0)

**The plant laid a BRANCHED lipid out colinearly.** With `n_tail = 4` the second branch starts at
`idx[3]`, which the plant placed 3 sigma from the head against a rest length of 1. Every planted lipid
carried ~800 eps of spring strain, so every planted run began by snapping back rather than by doing
dynamics -- and that is enough on its own to scramble leaflets. **Every planted-structure result in this
project carried that confound.**

### The deeper defect: the branch angle was pinned at 180 degrees

`_infer_13` adds a 1-3 spring at rest length 2*r_bond for every angle in the bond graph. Centred on the
HEAD of a branched lipid, the two neighbours are the first beads of the **two different tails**, so
pinning them 2 sigma apart with both bonds at 1 sigma **forces the branch angle to 180 degrees**. The
two-tailed lipid was mechanically a linear five-bead chain **with the head in the middle of the tails**.
A head pinned between two outward-pointing tails cannot reach a surface, which is precisely `mix` ~0.9.

Fixed: triples centred on a HEAD are dropped, since a branch angle is set by sterics rather than by a
spring. For a LINEAR lipid the head is an end and never a centre, so nothing changes there.

Fixed too: the ring/arc plant now places the two tails **side by side** (radial offset 0.866, lateral
+-0.5, so both first tail beads sit exactly 1 sigma from the head), and the leaflet radii use the BEAD
count rather than the tail count with a 0.5 sigma gap, which also removed the 25 exactly-coincident bead
pairs that no relaxation could separate (the push direction d/r is 0/0). A steric push-off now runs
before dynamics for all planted starts.

| | before | after |
|---|---|---|
| planted ring E/lipid | 790.4 | **53.0** |
| 1-2 spring energy | 400.00 | **0.00** (max deviation 0.000) |
| 1-3 spring energy | 400.00 | 0.93 |
| min non-bonded r | 0.000 | 0.860 |

### The result that survives all of it

From a **strain-free, correctly planted** bilayer at **kT = 0** -- pure downhill descent, no thermal
noise -- `mix` still goes **0.624 -> 0.899 within 150 steps** while the energy falls monotonically from
158 to -20. **The ordered bilayer is not a local energy minimum of this force field.**

The reason is in chi and is not subtle. Explicit: HEAD-HEAD 0.20 and HEAD-TAIL **0.20**, so a head is
exactly indifferent between a head neighbour and a tail neighbour. Solvent-averaged: HEAD-HEAD -0.30 and
HEAD-TAIL **+0.45**, so a head positively PREFERS a tail neighbour. In neither table is head-tail contact
unfavourable relative to head-head -- and that is what amphiphilicity means. Emergent aggregates confirm
it: `mix` 1.014 and 1.020, indistinguishable from random.

**FALSIFICATION, STATED BEFORE THE SWEEP IS READ.** `chi_HT` scanned over 0.20 (current), 0.10, 0.00 and
-0.20, explicit solvent, planted ring, kT = 0.35, 5 seeds each, 6000 steps. If `mix` falls toward the
planted 0.54 as `chi_HT` drops, the missing head-tail penalty is the root cause and the force field has
been non-amphiphilic in the one term that defines an amphiphile. If `mix` stays near 0.90 at every value
including -0.20, the cause is elsewhere and the chi table is exonerated. A partial fall means chi_HT
contributes but does not account for it.

Emergence in flight at L = 36: largest 28/300 at step 80 000, much slower than L = 25 as expected from
the lower concentration, `mix` 1.014.

---

## 2026-08-19j tick — `mix` was not a valid order metric; with a calibrated one, IMPLICIT solvent keeps the bilayer

### chi_HT is exonerated: my own hypothesis from last tick is falsified

Planted N = 300 ring, explicit, kT = 0.35, 6000 steps, 5 seeds per value:

| chi_HT | mix at end | mean |
|---|---|---|
| 0.20 (default) | 0.879 0.859 0.868 0.881 0.873 | 0.872 |
| 0.10 | 0.877 0.859 0.888 0.893 0.872 | 0.878 |
| 0.00 | 0.874 0.872 0.865 0.893 0.908 | 0.882 |
| -0.20 | 0.867 | 0.867 |

Flat. Making head-tail contact **repulsive** changes nothing, so the missing head-tail penalty is NOT
the root cause and the chi table is cleared.

### Why nothing moved it: `mix` cannot measure order

Control: take the planted bilayer, keep leaflet assignment **perfectly intact**, add only Gaussian
positional jitter.

| jitter | 0.0 | 0.2 | 0.5 | 1.0 |
|---|---|---|---|---|
| mix | 0.615 | 0.702 | 0.765 | **0.840** |

Jitter alone reproduces almost the entire "scrambled" signal. **`mix` conflates thermal roughness with
leaflet disorder**, so every conclusion drawn from it -- across the last four ticks -- was drawn from an
instrument that could not distinguish the two.

### The replacement, and the first version of it was circular

`seg`: the signed radial offset of each head from its own tails, in sigma, with the leaflet assigned
from the **molecule centre**. Calibrated against two controls:

| configuration | seg |
|---|---|
| planted bilayer | **1.534** |
| + 1.0 sigma jitter | 1.518 |
| every lipid rigidly rotated about its own centre | **0.028** |

A first version assigned the leaflet by the HEAD's own radius and then measured the head's offset, which
is circular: its scrambled control scored **2.950** against an ordered 1.534, i.e. the negative control
beat the positive one. Caught by running the control rather than trusting the construction.

### Two bugs I introduced last tick, both caught here

* The plant fix used `nb - 1` for how far a lipid reaches inward, but a BRANCHED lipid has `nt//2` beads
  per branch and reaches `0.866 + (half - 1)` -- 1.866, not 4. The leaflets ended up **5.26 sigma apart**,
  the ring was two disconnected annuli, `largest` read 178/300 and `seg` collapsed to 0.137 because it
  was measuring half a ring about an off-centre centroid. Fixed; `largest` is 300/300 and seg 1.589.

### The result, and it REVERSES the last three ticks

Correctly planted ring, kT = 0.35, 8000 steps, **5 seeds each**:

| solvent | seg at end | mean +- sd |
|---|---|---|
| explicit | 0.158 0.194 0.178 0.171 0.271 | **0.194 +- 0.040** |
| implicit (solvent-averaged chi) | 0.758 0.770 0.828 0.756 0.706 | **0.764 +- 0.041** |

Against 1.53 ordered and 0.028 disordered, that is a **10 sigma** separation between conditions.
**Implicit solvent RETAINS half the leaflet order; explicit destroys it.** Under `mix` the two read 0.92
and 0.90 and I concluded implicit was slightly worse -- exactly backwards.

This is consistent with the previous tick's finding that our explicit water is a two-phase fluid with
vacuum voids at these densities: the membrane is being disrupted by a solvent that is not a liquid.

### Retracted

* **"The ordered bilayer is not a local energy minimum of this force field"** (last tick) rested on `mix`
  at kT = 0 and is withdrawn pending re-measurement with `seg`.
* Every ordering claim from `mix`, in either direction, across four ticks.

**FALSIFICATION, STATED BEFORE THE RUN.** kT = 0.0 and 0.15, implicit solvent, correct plant, 5 seeds,
4000 steps. If `seg` holds near its planted value at kT = 0, the ordered bilayer IS a local energy
minimum and last tick's claim was an artefact of the broken metric plus the strained plant. If `seg`
still falls to ~0.03 at kT = 0, the claim stands on better evidence than it originally had. An
intermediate plateau, like the 0.76 seen at kT = 0.35, means the model has a partially ordered ground
state and the question becomes why order is lost rather than whether.

Emergence in flight at L = 36: largest 43/300 at step 140 000, still solid micelles.

---

## 2026-08-19k tick — the bilayer is stable in implicit solvent; the branch-angle bug was the blocker

### The kT = 0 test resolves, and the render confirms it

Correct plant, implicit solvent, `seg` (planted 1.53, disorder control 0.028):

| condition | seg |
|---|---|
| kT = 0.0 (deterministic) | **0.879** |
| kT = 0.15, 5 seeds | 0.778 +- 0.046 |
| kT = 0.35, 5 seeds | 0.764 +- 0.041 |

**Caveat on the kT = 0 row:** all five seeds returned 0.879 to three decimals, which is not agreement
between independent samples -- with no thermal noise the trajectory is deterministic and the seed only
sets initial velocities, which are zero. That row is n = 1 and is reported as such.

**The render settles what the number means.** At kT = 0 the ring is a clean closed annulus with a real
lumen and visible leaflet structure: heads on the outer rim, heads on the inner rim, tails in the middle
band. So `seg` ~0.88 IS a bilayer, and the planted 1.53 is simply a more perfectly aligned configuration
than any relaxed membrane can hold. The falsification resolves to its third branch: a partially ordered
ground state, where "partially" reflects the idealization of the reference rather than a defect.

### What this overturns

* **"The ordered bilayer is not a local energy minimum"** -- withdrawn as stated. The planted
  configuration does relax away at kT = 0, but it relaxes to a BILAYER at 0.879, not to the disordered
  0.028 that `mix` implied. The claim was measuring the idealization of the plant, not a failure of the
  physics.
* **"Implicit solvent does not preserve bilayer order in 2-D"** (four ticks ago) -- withdrawn. That
  verdict came from a render of a run started from the BROKEN plant carrying ~800 eps/lipid of spring
  strain, whose first hundred steps were a snap-back rather than dynamics. With the branch-angle and
  planting bugs fixed, the same configuration holds a bilayer.

**So the blocker was the 180-degree branch-angle pin, not chi, not the solvent model, not temperature,
not dimensionality.** Every one of those was investigated and cleared in turn; the defect was a 1-3
spring applied where a branch angle belongs.

### The standing picture, on validated instruments

| condition | seg | verdict |
|---|---|---|
| planted, idealized | 1.53 | reference only |
| implicit, kT 0.0-0.35 | 0.76-0.88 | **bilayer, lumen holds** |
| explicit, kT 0.35 | 0.194 +- 0.040 | destroyed |
| disorder control | 0.028 | floor |

Explicit solvent remains the outlier, consistent with the earlier finding that our explicit water is a
two-phase fluid with vacuum voids at these densities. Membrane work should stay implicit until the
solvent's own phase behaviour is fixed.

### Launched: emergence on the corrected force field

Every emergence run to date used the force field WITH the branch-angle pin, i.e. lipids mechanically
forced straight with the head between the two tails. Those runs produced solid micelles and nothing
else, which is what such a molecule should produce. Relaunched from a dispersed start on the corrected
field: 2-D at L = 60 with 5 seeds and 3-D at L = 36 with 3 seeds, implicit solvent, kT = 0.30, 400 000
steps.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If emergent aggregates now reach `seg` in the
0.7-0.9 band that planted bilayers hold, self-assembly produces bilayers and the milestone is within
reach. If `seg` stays near the 0.17 of the dispersed start while clusters grow, the corrected molecule
still does not self-assemble into a bilayer and the defect is in aggregation rather than in molecular
geometry. If clusters do not grow at all at kT = 0.30, the run is under-sampled and says nothing either
way.

**Amendment, same tick — `seg` has a validity domain and small micelles are outside it.** The 3-D
emergent runs report `seg` of **-0.24, -0.45, -0.26** at largest 13-20 lipids. Negative means heads
pointing inward, which is not credible; the cause is that `seg` assigns leaflets by comparing each
molecule's centre with the aggregate's median radius, and a small SOLID micelle has no mid-surface for
that comparison to mean anything. The metric is defined for shell and ring geometries. Like shell CV
before it, it needs a size floor, and values from aggregates below roughly 50 lipids should be discarded
rather than interpreted. The 2-D arm additionally hit the span guard (`seg` NaN at largest 107/300 in
L = 60): a condensed 1500-bead 2-D aggregate is about 44 sigma across, above the L/2 = 30 limit, and the
target ring is 48 across, so 2-D emergence was relaunched at L = 120 with 5 seeds.

---

## 2026-08-19l tick — emergent BILAYER RIBBONS on the corrected field; planting infrastructure fixed end to end

### Bilayer order is temperature-robust in implicit solvent

Planted ring, implicit, `seg` (planted 1.53, disorder 0.028), 5 seeds except where noted:

| kT | 0.0 (n=1) | 0.15 | 0.35 | 0.45 | 0.60 |
|---|---|---|---|---|---|
| seg | 0.879 | 0.778 +- 0.046 | 0.764 +- 0.041 | **0.722 +- 0.036** | **0.723 +- 0.038** |

Flat from 0 to 0.60, so emergence can be run hot -- faster diffusion -- without losing the bilayer.
Suite PASSED (253 s) with the branch-angle and `content_pairs` changes in.

### The headline: emergent bilayer strips

2-D emergence relaunched at N = 120, L = 56, kT = 0.60, 5 seeds. The earlier arms were crawling because
I had both cooled them to kT = 0.30 and been forced into dilute boxes by the span guard (2-D packing
0.10, 3-D 0.032); largest reached only 12-20 lipids in 20 000 steps.

**The render shows elongated slabs with heads lining both long edges and tails filling the interior --
bilayer strips.** Every previous emergence run in this project produced solid micelles with no leaflet
structure. The difference is the corrected molecule: the 1-3 spring centred on the head had been pinning
the two tails at 180 degrees, making every lipid a straight chain with its head in the middle.

### A third metric, because the first two do not apply to ribbons

`seg` assumes a radial mid-surface, so it is undefined for a flat ribbon and meaningless for small solid
micelles. Added `burial`: local neighbour count within 2 sigma, tails minus heads. No centre, no radius,
no mid-surface. Calibrated: planted bilayer **7.178**, still 5.220 under 1 sigma jitter, **0.673** with
every lipid rigidly rotated about its own centre.

| | burial |
|---|---|
| dispersed start | 1.000 |
| orientations randomized | 0.673 |
| **emergent, steps 20-60k** | **3.5 - 4.0** |
| planted flat bilayer, N = 20/30/40 | 2.475 / 2.483 / 2.500 |

**What this does NOT establish.** Emergent burial (3.5-4.0) exceeds a size-matched planted flat bilayer
(2.48), and that is not evidence of superior order: burial rises with COMPACTNESS, and a compact
aggregate buries more tails than a thin ribbon whatever its organization. The control that would settle
it is randomizing orientations of the EMERGENT structure in place -- shape matched, order destroyed --
and it has not been run. No quantitative order claim is made for the emergent structures in this entry;
the ribbon morphology rests on the render alone, and is stated as such.

### Planting infrastructure fixed end to end

`_plant_flat_ribbon` was missed when the ring plant was fixed, so the "planted bilayer" reference used
for the size-matched control was itself an exploding configuration at +778 eps/lipid. Fixing it exposed
a second defect in all three plants: a branched lipid puts its two tails side by side at +-0.5, giving a
lateral footprint near 2 sigma, but the leaflets were spaced for a single-file chain. Neighbouring
lipids' tails sat 0.03-0.05 sigma apart -- 600 pairs inside 0.8 sigma on the ring -- and the push-off
then fought the attractive well, driving the flat plant from E/lipid 21 to **1548**.

| plant | before | after |
|---|---|---|
| ring | E/lip 800, springs 800, min r 0.000 | **E/lip -7.77**, springs 0.93, min r 0.931, 0 overlaps |
| flat | E/lip 778, springs 800, min r 0.050 | **E/lip -7.25**, springs 0.93, min r 1.000, 0 overlaps |
| arc0.75 | E/lip 811, springs 800, min r 0.000 | **E/lip -7.75**, springs 0.93, min r 0.938, 0 overlaps |

Energies are now NEGATIVE, i.e. bound rather than strained. This is the first valid planted bilayer this
project has had, and every planted result before it was measured on a configuration that exploded.

**FALSIFICATION, STATED BEFORE THE CONTROL IS RUN.** Randomize lipid orientations in place on the
emergent aggregates and re-measure burial. If emergent burial stays near 3.5-4.0 while the randomized
control drops toward 0.7, the ribbons carry genuine amphiphilic order and the morphology in the render is
real. If the randomized control also reads 3-4, burial is measuring compactness alone at these sizes, the
metric is void in this regime, and the ribbon claim rests on the render only until a better observable
exists.

---

## 2026-08-19m tick — the emergent order is REAL (5.9 sigma); but the aggregates thicken, so they are droplets not membranes

### The pre-committed control passes

All five 2-D emergence runs finished 400 000 steps. The control stated last tick -- randomize lipid
orientations IN PLACE, so shape is matched and only order is destroyed -- was run on the saved end
states, scored on the largest cluster:

| seed | largest | burial (emergent) | burial (rotated) |
|---|---|---|---|
| 0 | 43 | 2.738 | 0.250 |
| 1 | 61 | 2.766 | 0.303 |
| 2 | 56 | 2.897 | 0.384 |
| 3 | 85 | 2.150 | 0.203 |
| 4 | 52 | 3.490 | 0.269 |

**2.808 +- 0.427 against 0.282 +- 0.060, a 5.9 sigma separation.** The falsification resolves to its
first branch: the heads-out/tails-in organization is genuine and is not an artefact of compactness. This
is the first emergent amphiphilic order in this project that survives a shape-matched null.

### But the morphology is wrong, and the render caught it

At 400 000 steps the largest aggregate is a **thick slab** with heads on the rim AND scattered through
the interior, not the thin strips visible at 60 000. Measured as the minor-axis extent of the largest
cluster:

| largest | thickness (sigma) |
|---|---|
| 43 | 9.55 |
| 52 | 10.51 |
| 56 | 13.04 |
| 61 | 12.04 |
| 85 | 13.12 |

A bilayer is two leaflets thick, about **5.8 sigma** for this lipid, and crucially that is
**size-independent**: a membrane grows laterally, not thicker. Ours are 1.6-2.3x too thick and thicken
monotonically with aggregate size. The burial numbers agree from the other direction -- the largest
aggregate (85) has the LOWEST burial (2.150) and the smallest (52) the highest (3.490), because a
thickening slab buries heads.

**So what emerges is a condensed droplet with an ordered surface, not a membrane.** The ribbon
morphology reported last tick from the step-60 000 render was real at that size and does not survive
coarsening; that reading is corrected here rather than retracted, since the strips did exist -- they
just are not the final state.

### The live hypothesis: the packing parameter is too large

The lipid is **one head bead against four tail beads**. Tail volume dominates head area, which pushes
the packing parameter `P = v/(a0*l)` above the bilayer band and favours bulk condensed phases over
membranes. That is consistent with everything above: strong surface order (the amphiphile works) but no
thickness control (the geometry does not).

**FALSIFICATION, STATED BEFORE THE RUN.** 2-D emergence, N = 120, L = 56, kT = 0.60, 200 000 steps,
5 seeds each, at `frac_short` 0.0 (all 4-tail, the current lipid) and 1.0 (all 2-tail, half the tail
volume per head). If thickness falls toward ~5.8 sigma and stops growing with aggregate size at
`frac_short` 1.0, thickening is a packing-parameter problem and the lipid geometry is the thing to fix.
If thickness is unchanged, packing is not the cause and the defect is in the interactions rather than the
shape. If the 2-tail lipid instead disperses or forms micelles without growing, its packing parameter has
overshot into the detergent band and the answer lies between the two.

---

## 2026-08-19n tick — fifth filename collision contaminated the packing test; preliminary answer is "packing is not the cause"

### The collision

Both packing arms wrote to the same state and render filenames, because the tag carried `kT` but not
`frac_short`. The tag has now been missing, in turn: **L, then n_tail, then seed, then kT, and now
frac_short** -- five times, the same failure each time. Of the five saved states, three are 4-tail and
two are 2-tail, whichever seed index finished last.

It was caught because the `.npz` stores `chains`, so each surviving state could be attributed to its arm
after the fact. That is luck, not method: the state file was added two ticks ago for a different reason.
Fixed by putting `frac_short` in both the render tag and the state filename, and the whole test is
**re-running with 5 seeds per arm**.

### What the surviving states show, stated as preliminary

Attributed by `chains`, so n = 3 for 4-tail and n = 2 for 2-tail -- below the 5-seed bar this project
requires for a reported difference, hence preliminary:

| lipid | largest | thickness (sigma) | burial |
|---|---|---|---|
| 4-tail | 42 | 8.98 | 2.780 |
| 4-tail | 60 | 13.60 | 3.992 |
| 4-tail | 31 | 9.64 | 3.250 |
| 2-tail | 43 | 8.84 | 1.605 |
| 2-tail | 49 | 10.29 | 1.571 |

At comparable aggregate size (42 against 43, 49) the thickness is **essentially unchanged** -- 8.98
against 8.84 and 10.29 -- while burial falls sharply, 2.78-3.99 down to 1.57-1.61, and cohesion with it,
E/lipid -21.0 against -9.6.

**Preliminary reading: the second branch of the falsification.** Halving the tail volume per head does
not thin the aggregate, so thickening is not simply a packing-parameter problem in the tail-count knob,
and the short lipid additionally loses the amphiphilic order the long one had. The render agrees: the
2-tail arm makes many small compact clusters with heads scattered through them rather than lining the
edges.

**No conclusion is recorded until the 5-seed rerun lands.** The falsification stated last tick stands
unchanged for it: thickness falling toward 5.8 sigma and ceasing to grow with size means packing is the
cause; unchanged thickness means the defect is in the interactions rather than the shape; dispersal or
micelles means the 2-tail lipid overshot into the detergent band.

### What is not in doubt

The 5.9 sigma order result from last tick is unaffected -- it was measured on the 4-tail states with a
shape-matched null, before this sweep existed.

---

## 2026-08-19o tick — packing-parameter hypothesis FALSIFIED; head-tail attraction is the new candidate

### The clean rerun

The re-run with `frac_short` in the tag reproduced the contaminated run's numbers **exactly** -- same
seeds, deterministic integrator -- so the physics was never in question, only the file attribution. Five
seeds per arm, 200 000 steps, N = 120, L = 56, kT = 0.60, implicit solvent:

| lipid | largest | thickness (sigma) | a bilayer would be | overshoot | burial |
|---|---|---|---|---|---|
| 4-tail | 42 60 31 85 52 | **11.27 +- 1.96** | 5.8 | **1.94x** | 3.333 +- 0.437 (n=4) |
| 2-tail | 36 38 39 43 49 | **9.04 +- 0.66** | 3.8 | **2.38x** | 1.643 +- 0.083 |

**The falsification resolves to its second branch.** Halving the tail volume per head makes the
aggregate thinner in absolute terms but **relatively worse** -- 2.38x the bilayer thickness against
1.94x -- and costs most of the amphiphilic order (burial 1.64 against 3.33) and most of the cohesion
(E/lipid -9.6 against -21.0). So thickening is **not** a packing-parameter problem reachable through the
tail-count knob, and the 4-tail lipid is the better molecule on every measure taken.

One 4-tail seed (largest 85) returns NaN for burial: its aggregate spans more than half of L = 56, so
the guard fires. Burial for that arm is n = 4, and is reported as such.

### The render adds something the mean hides

Within a single run, a thin bilayer strip with heads lining both long edges **coexists** with a thick
slab whose heads are buried. The 11.27 +- 1.96 is an average over genuinely different objects, not a
uniform morphology. Whatever prevents thickening evidently works sometimes.

### New candidate, and the reason it is plausible

In the solvent-averaged chi the head-tail term is **+0.45, attractive**. Nothing makes an internal
head/tail interface costly, so stacking extra layers is free and a bilayer has no reason to stop at two
leaflets. That fits every observation: strong surface order (the amphiphile works), no thickness control
(nothing forbids buried interfaces), and thickening that grows with aggregate size.

A chi_HT sweep was run three ticks ago and showed nothing, but it is not evidence here: it used the
EXPLICIT solvent, the broken plant carrying ~800 eps/lipid of strain, and `mix`, which was later shown
unable to distinguish roughness from disorder. All three defects are now fixed.

**FALSIFICATION, STATED BEFORE THE RUN.** `VIVARIUM_CHI_HT` at 0.20, -0.25 and -0.75 -- implicit
head-tail of +0.45, 0.00 and -0.50 -- implicit solvent, 5 seeds each, 200 000 steps, scored on thickness
against the 5.8 sigma target and on burial. If thickness falls toward 5.8 and stops growing with
aggregate size as the term goes negative, head-tail attraction is what permits layer stacking and the
fix is to make internal interfaces costly. If thickness is flat across the sweep, this candidate joins
packing in the falsified column and the cause is neither the molecule's shape nor its cross-term. If the
aggregates instead fragment at -0.75, the term has overshot and the usable window lies between.

---

## 2026-08-19p tick — REPULSIVE head-tail gives clean bilayer ribbons; the thickness metric was wrong, not the physics

### The result

Making the head-tail term repulsive produces the cleanest membrane morphology this project has had. At
implicit head-tail **-0.50** the emergent aggregates are thin ribbons, uniformly about two leaflets
thick, heads lining both long edges, tails inside -- and several are CURVED. At +0.45 the same
configuration gives thick blobs with heads buried.

Metrics moved together with the render:

| implicit HT | burial | hollow | core depth (bilayer ref 1.467) |
|---|---|---|---|
| +0.45 | 3.33 | 2.0 - 2.5 | 1.208 - 1.275 |
| 0.00 | ~4.8 | - | 1.381 - 1.413 |
| -0.50 | 5.1 - 5.6 | **0.50 - 0.62** | 1.421 - 1.433 |

Core depth is at step 30 000 with the runs continuing; burial and hollow are end-of-run.

### The thickness metric was measuring the wrong thing

The PCA minor-axis thickness reported **16.8 sigma at -0.50 against 11.3 at +0.45**, i.e. it called the
visibly cleaner structures worse. It takes the narrow extent of the WHOLE aggregate, and for a CURVED
ribbon that spans the entire arc -- a closed or bent sheet has both principal axes spanning its diameter.
The metric assumed an elongated straight slab, which is the one shape the good structures are not.

Replaced by **core depth**: mean distance from each tail bead to the nearest head bead. Local, so
curvature cannot affect it, and it is **size-independent** on the reference -- a planted flat bilayer
reads 1.466 at N = 20 and 1.467 at N = 40.

**What core depth actually measures, stated so it is not over-read:** head PENETRATION, not thickness.
Low means heads are mixed into the interior, which is the +0.45 defect. It cannot distinguish a clean
bilayer from an over-thick slab whose heads sit only on the outside, since both keep interior tails far
from any head. So it is necessary but not sufficient, and the thin-ribbon claim rests on the render plus
burial plus hollow together.

### Retracted

* **Last tick's thickness numbers** (11.27 +- 1.96 for 4-tail, 9.04 +- 0.66 for 2-tail) are withdrawn as
  a measure of bilayer quality. They are still a correct minor-axis extent, but that quantity conflates
  thickness with curvature, so the 1.94x and 2.38x "overshoot" figures should not be used.
* The **packing-parameter falsification stands** -- it compared two lipids under the same metric, and
  the burial and cohesion differences (1.643 +- 0.083 against 3.333 +- 0.437; E/lipid -9.6 against
  -21.0) do not depend on the thickness measure at all.

### Sixth and seventh filename collisions

`chi_HT` was not in the state or render tag, so the three sweep arms overwrote each other; the surviving
states were attributable only because their burial values matched one arm's log exactly. That is the
sixth time a swept variable has been missing from the tag -- after L, n_tail, seed, kT and frac_short --
and the seventh fix now adds `chi_HT`. The sweep is re-running with all parameters in the filename.

**FALSIFICATION, STATED BEFORE THE COMPLETED RUNS ARE READ.** Five seeds per arm to 200 000 steps. If
core depth at -0.50 holds near the 1.467 reference while +0.45 stays near 1.25, and burial stays
separated, repulsive head-tail is established as the fix for head penetration. If core depth at -0.50
drifts ABOVE 1.6 as aggregates grow, the structures are thickening with clean surfaces -- which core
depth cannot see -- and a genuine thickness measure is still required before any bilayer claim. If the
arms converge by 200 000 steps, the step-30 000 separation was a transient of the aggregation stage.

**Sweep completed, 200 000 steps, 5 seeds per arm.** Core depth against the planted-bilayer reference of
1.467:

| implicit HT | core depth | n | burial |
|---|---|---|---|
| +0.45 | **1.216 +- 0.028** | 4 | 3.33 |
| 0.00 | 1.379 | 2 | 4.81 |
| -0.50 | **1.460 +- 0.009** | 3 | 5.41 |

**The falsification resolves to its first branch.** At -0.50 core depth is statistically
indistinguishable from a planted bilayer (1.460 against 1.467), separated from +0.45 by **8.4 sigma**,
with burial separated in the same direction. Core depth did NOT drift above 1.6, so the second branch --
aggregates thickening behind clean surfaces, which core depth cannot see -- is excluded by this data.
Repulsive head-tail is established as the fix for head penetration.

**A bias in those means, stated rather than averaged over.** Every NaN is a LARGE aggregate: 85 and 89,
and 58, 62, 95. The span guard fires when a cluster exceeds half the box, so at L = 56 the metric
systematically discards the biggest structures and the means above describe only the smaller ones. Since
thickening is a phenomenon that grows with size, that is a bias toward the favourable case, and the arms
have n = 4, 2 and 3 rather than 5.

**Rerun launched at L = 120**, where a 120-lipid aggregate cannot reach half the box, at +0.45 and -0.50,
5 seeds, 300 000 steps.

**FALSIFICATION, STATED BEFORE IT IS READ.** If the separation survives with every seed reporting -- core
near 1.46 at -0.50 and near 1.22 at +0.45 -- the result stands on unbiased data. If the large aggregates
that were previously discarded show core depth well above 1.467 at -0.50, they are thickening behind
clean surfaces, the effect was hidden by the guard, and a direct thickness measure is still needed. If
the separation vanishes when the big clusters are included, it was an artefact of scoring only small
aggregates.

---

## 2026-08-19q tick — the unbiased rerun answered a different question than the one asked

### What it gave

L = 120, 300 000 steps, 5 seeds per arm, **every seed reporting** (no NaN, so the guard bias is gone):

| implicit HT | core depth (ref 1.467) | burial |
|---|---|---|
| +0.45 | 1.291 +- 0.047 | 4.167 +- 0.79 |
| -0.50 | **1.453 +- 0.012** | 5.544 +- 0.28 |

Core depth at -0.50 is indistinguishable from a planted bilayer, and the render shows a textbook bilayer
ribbon: two leaflets, heads lining both long edges, uniform along its length.

### What it failed to give, which is what it was launched for

`largest` is **13-23 lipids in every seed**, against 42-95 at L = 56. Enlarging the box to escape the
span guard made the system so dilute that coarsening never happened. **The question -- do LARGE aggregates
thicken? -- is still unanswered**, and this run cannot answer it. I traded a metric bias for a sampling
failure.

The burial separation also weakens on this data: 5.544 +- 0.28 against 4.167 +- 0.79 is 1.6 sigma, where
the L = 56 data gave a much cleaner split. Small aggregates are simply less distinguishable.

### The actual fix, which is not a bigger box

`core` and `burial` are computed from **pairwise distances only** -- no centroid, no radius, no
mid-surface. The span guard exists for centroid ambiguity, so it should never have voided them. Voiding
them discarded exactly the largest aggregates (85, 89, 62, 58, 95 lipids) and biased every mean toward
the small ones, which matters precisely because thickening is size-dependent.

Both are now computed **before** the guard and returned through it; only the centroid-dependent
quantities (`R_mid`, `shell_cv`, `hollow`, `seg`) still go NaN. That removes the bias without changing
the box, so aggregates can grow AND be measured.

**Rerun launched at L = 56** -- the box that permits growth -- at +0.45 and -0.50, 5 seeds, 200 000 steps.

**FALSIFICATION, STATED BEFORE IT IS READ.** With the large aggregates now scored: if core depth at -0.50
stays near 1.46 across all seeds including the 85-95 lipid clusters, repulsive head-tail holds at every
size reached and the bilayer result is unbiased. If core depth at -0.50 falls with aggregate size, large
aggregates admit heads into the interior after all and the fix only works while structures are small. If
core depth rises well above 1.467 for the big clusters, they are thickening behind clean surfaces --
which core depth cannot detect -- and a direct local thickness measure is still owed.

---

## 2026-08-19r tick — repulsive head-tail confirmed on unbiased data at every size reached; critical-size test launched

### The result, with the largest aggregates now included

L = 56 (the box that permits growth), 200 000 steps, 5 seeds per arm, `core` and `burial` computed
before the span guard so nothing is discarded:

| implicit HT | core depth (ref 1.467) | burial | largest |
|---|---|---|---|
| +0.45 | 1.219 +- 0.026 | 3.348 +- 0.389 | 31 - 85 |
| **-0.50** | **1.448 +- 0.017** | **5.349 +- 0.157** | 38 - 95 |

**7.4 sigma** on core depth, **4.8 sigma** on burial, with every seed reporting.

**The size question is answered.** Core depth at -0.50 by aggregate size: 38 -> 1.472, 47 -> 1.451,
50 -> 1.457, 58 -> 1.424, 95 -> 1.437. No decline with size beyond about two standard deviations, and no
rise above the 1.467 reference, so the third branch -- large aggregates thickening behind clean surfaces,
which core depth cannot detect -- is excluded at every size reached. The +0.45 arm shows the opposite,
drifting slightly UP with size (31 -> 1.192, 85 -> 1.231) while remaining far below the reference.

The renders match: long, thin, curved bilayer ribbons with heads lining both edges along their whole
length. **The thickening problem is solved**, and the fix is a single sign change in one chi entry.

### What this cost, recorded because the pattern repeats

Reaching this took three attempts, and the first two failed for opposite reasons. The L = 56 sweep gave a
clean separation but the span guard silently discarded exactly the largest aggregates. The L = 120 rerun
included every seed but was so dilute that nothing coarsened, so it tested only 13-23 lipid clusters. The
fix was neither box: `core` and `burial` never needed the centroid, so the guard should not have applied
to them at all. **Two runs were spent adjusting the experiment when the instrument was at fault** -- the
same failure mode as `mix`, shell CV, and the PCA thickness measure before it.

### Launched: the critical-size test

The standing plan, runnable for the first time on a sound basis -- valid plants (E/lipid -7.8, zero
overlaps, verified core 1.462 at plant), a bilayer-forming field, and calibrated metrics. Arcs of
**N = 40, 70, 120, 200** at kT = 0.45, implicit solvent, head-tail -0.50, **5 seeds each**, 150 000
steps. Boxes 60/90/145/230, sized from each arc's own radius `R = 2N/(4*pi*0.75)` plus lipid reach and
multiplied by 2.5, so the OPEN state is never confined -- the error that invalidated the first attempt at
this test. Three emergence runs continue alongside so there is always a dispersed-start structure to show.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If closure fraction rises with N -- arcs staying
open at 40 and closing at 120 or 200 -- a critical size exists, kappa follows as
`kappa = 2*lambda*R*/pi`, and the three historical failures at ~70 lipids were undersized. If ALL four
sizes unroll across 5 seeds, the continuum picture behind every interpretation in this project is wrong,
and that conclusion now rests on a force field that demonstrably makes bilayers rather than on one that
did not. If all four close, size was never the variable and the historical failures had another cause.

---

## 2026-08-19s tick — the critical-size test resolves NEGATIVE: arcs open further at every size

### The result

Arcs of N = 40, 70, 120, 200 at kT = 0.45, implicit solvent, head-tail -0.50, 5 seeds each, 150 000
steps, on valid plants (E/lipid -17.78, core 1.462 at plant, fully connected). Distance between the
arc's two exposed ends:

| N | planted gap | final gap (mean of 5) |
|---|---|---|
| 40 | 12.0 | **16.56** |
| 70 | 21.1 | **25.72** |
| 120 | 36.1 | **44.84** |
| 200 | 60.0 | **74.30** |

**The gap grew in all 20 runs.** Not one arc at any size moved toward closure; they opened by 24-38%.
The falsification resolves to its second branch, and it does so on a force field that demonstrably makes
bilayers (core depth 1.448 +- 0.017 against a planted reference of 1.467, 7.4 sigma above the attractive
setting) rather than on the broken one that produced the three historical failures.

### A reading I nearly published, caught by the render

`R_mid` contracted in exactly the way closure predicts. An arc spanning 0.75 of a circle that closes at
fixed lipid count must shrink to 0.75x its planted radius:

| N | planted R | predicted if closed | observed |
|---|---|---|---|
| 70 | 14.9 | 11.2 | 10.0 - 12.3 |
| 120 | 25.5 | 19.1 | 19.4 - 21.6 |
| 200 | 42.4 | 31.8 | 31.5 - 35.7 |

Three sizes matching a quantitative prediction to within a few percent. `hollow` agreed -- 0.000 in most
seeds at N = 120 and 200. **The render shows a wide-open C.** The arcs contract while staying open, and
`hollow` cannot tell a closed ring from an open C because both have empty middles. Fourth time in this
project a plausible metric reading has been overturned by looking, and the first where the metric had a
quantitative prediction behind it.

### What this does and does not establish

It does NOT yet falsify the continuum picture, because the number that picture rests on is suspect.
**lambda = +18.31 +- 7.07 eps was measured on the OLD force field** -- before the branch-angle fix that
was pinning every lipid straight with its head in the middle, and before the head-tail sign change. The
claim "closure has ~81 kT to gain" therefore comes from a model that did not make bilayers. If the edge
is cheap on the corrected field -- plausible, since a repulsive head-tail term lets heads cap an exposed
edge comfortably -- then there is little to gain by closing and the arcs opening is the correct physics
rather than a contradiction.

**Launched: lambda on the corrected field.** Finite flat ribbons of N = 20, 30, 40, 60, 80, 5 seeds each,
40 000 steps, L = 200 so no ribbon spans the box. For a ribbon with two ends
`E(N) = N*e_bulk + 2*lambda`, so a straight-line fit of total energy against lipid count gives 2*lambda
as the intercept.

**FALSIFICATION, STATED BEFORE THE FIT IS READ.** If lambda comes out near the historical +18.31 eps per
end, the edge really is expensive, closure really is favoured by ~81 kT, and arcs opening at every size
means the barrier is kinetic or the continuum picture is wrong -- a genuine negative. If lambda is near
zero or negative on the corrected field, the historical value was an artefact of the broken lipid, there
was never a driving force for closure, and every closure experiment in this project has been chasing a
number that does not exist. If lambda is positive but small -- under about 5 eps -- closure is weakly
favoured and the 150 000-step window is simply too short to see it.

**lambda re-measured on the corrected field.** Finite flat ribbons N = 20/30/40/60/80, 5 seeds, 40 000
steps, L = 200. Total energy against lipid count, fitted per seed so the five fits are independent:

    bulk energy per lipid   -20.929 eps
    2*lambda (intercept)    +20.24 eps
    lambda per end          **+10.12 +- 5.08 eps**  = +22.5 kT at kT = 0.45  (2.0 sigma from zero)
    per-seed lambda          6.24, 10.77, 8.61, 6.39, 18.57
    closure gain 2*lambda    **45 +- 23 kT**

Against the historical **+18.31 +- 7.07 eps** the difference is 8.19 with a combined sd of 8.71, i.e.
**0.94 sigma** -- statistically consistent. The N = 80 ribbon was rendered and is intact, flat and
two-ended, so the fit is not contaminated by curling or fragmentation.

**The falsification resolves to its FIRST branch, and the negative result stands.** lambda is positive,
the edge is expensive, closure is favoured by about 45 kT -- and arcs still open at every size in all 20
runs. The historical lambda was NOT an artefact of the broken lipid, so that escape is closed. What
remains is a kinetic barrier, or a continuum picture that does not apply here.

**FALSIFICATION, STATED BEFORE THE NEXT RUN.** N = 70 arcs planted at span 0.75, 0.85, 0.92 and 0.97 --
end gaps of about 21, 13, 7 and 3 sigma -- kT = 0.45, 5 seeds each, 100 000 steps. If closure occurs only
at the narrowest gaps, the barrier sits at contact, the failure is nucleation-limited, and the continuum
argument survives with a kinetic caveat. If the ends spring apart even from span 0.97, where they start
about 3 sigma apart, then the closed state is not preferred despite a positive lambda and the continuum
picture is falsified for this model. If closure is stochastic across seeds at intermediate spans, the
barrier height can be read off the span at which the closure fraction crosses one half.

---

## 2026-08-19t tick — closure falsified directly: arc ends spring apart even from 2.2 sigma

### The span sweep

N = 70 arcs planted at four spans, kT = 0.45, implicit, head-tail -0.50, 5 seeds each, 100 000 steps.
Gap between the two exposed ends:

| span | planted gap | final gap (5 seeds) | mean |
|---|---|---|---|
| 0.75 | 21.0 | 28.0 27.2 28.8 22.8 24.7 | **26.3** |
| 0.85 | 11.9 | 25.1 22.5 17.5 17.1 22.7 | **21.0** |
| 0.92 | 6.0 | 19.0 19.8 11.0 12.8 10.7 | **14.7** |
| 0.97 | **2.2** | 18.5 17.3 10.6 10.9 11.9 | **13.9** |

**Every one of the 20 runs opened.** At span 0.97 the two ends start 2.2 sigma apart -- in contact for
this model -- and still spring to 13.9. The falsification resolves to its **second branch**: the closed
state is not preferred despite a positive lambda, so **the continuum picture is falsified for this
model**. It is not a nucleation barrier; there is nothing to nucleate past.

Note `hollow` reads 0.000 for most of these, and would have been read as "closed" by the metric that
misled the previous tick. The end gap is the observable that decides, and it says the opposite.

### The mechanism, and it is a genuine tension in the model

The arc's ends are capped by **heads**, and the solvent-averaged head-head term is
`0.20 + 1.00 - 0.75 - 0.75 = -0.30`, i.e. **repulsive**. That repulsion is precisely what drives heads
onto the two surfaces and builds the bilayer -- and it is also what makes two head-capped edges push
apart. **The term that creates the membrane forbids closing it.**

That is a sharper statement than "closure does not happen here": it identifies a specific opposition
between two requirements in one parameter, and it is testable.

### Retracted

* Nothing measured is retracted this tick. The **standing plan** is: the critical-size test was
  predicated on closure being driven by edge energy once the ribbon is long enough, and both the size
  sweep (all four sizes, 20 runs) and this span sweep (all four spans, 20 runs) contradict it. kappa
  cannot be extracted from a threshold that does not exist, so `kappa = 2*lambda*R*/pi` is unavailable
  by this route.

### Seventh filename collision, averted and then fixed structurally

The head-head sweep would have overwritten its own three arms, since `chi_HH` was not in the tag. Rather
than adding a seventh variable by hand -- after L, n_tail, seed, kT, frac_short and chi_HT -- the tag now
**enumerates every `VIVARIUM_*` override automatically**, so a new knob cannot be forgotten. The runs
were killed and relaunched before they produced data.

**FALSIFICATION, STATED BEFORE THE SWEEP IS READ.** `chi_HH` at 0.20, 0.50 and 0.90 -- implicit head-head
of -0.30, 0.00 and +0.40 -- with head-tail held at -0.50. Two observables per arm: `core` on emergent
runs, which must stay near 1.467 for the bilayer to survive, and the end gap on N = 70 arc0.92 plants,
which must fall below about 3 sigma for closure. If some value gives both, the model can make a closed
vesicle and the opposition is only apparent. If every value that closes the arc destroys the bilayer
(core falling toward the 1.22 of the attractive setting), the opposition is real and this force field
cannot produce a vesicle without a further term. If nothing closes at any head-head value, the
obstruction is not head-head repulsion and the mechanism above is wrong.

---

## 2026-08-19u tick — kappa MEASURED at last; last tick's falsification is RETRACTED

### My proposed mechanism was wrong

The head-head sweep, N = 70 arc0.92, 5 seeds per arm, end gap (planted 6.0, closed means < 3):

| chi_HH | implicit HH | end gaps | mean | core (emergent) |
|---|---|---|---|---|
| 0.20 | -0.30 | 19.0 19.8 11.0 12.8 10.7 | 14.7 | 1.457 1.472 1.451 |
| 0.50 | +0.00 | 11.9 19.6 11.1 10.7 15.9 | 13.8 | 1.415 1.450 1.445 |
| 0.90 | **+0.40** | 21.1 21.2 10.3 10.7 11.7 | **15.0** | 1.449 1.443 1.425 |

**Flat.** Making heads ATTRACT each other does not help closure at all, and the bilayer survives
throughout (core 1.42-1.47 against a reference of 1.467). The third branch of the falsification: head-head
repulsion is not the obstruction, and last tick's mechanism -- "the term that creates the membrane forbids
closing it" -- is **wrong and withdrawn**.

### What the render showed instead

The relaxed arc is a **polygon**: straight facets joined by sharp kinks, not a smooth curve. A ribbon that
localizes bending into defects rather than curving uniformly is a STIFF ribbon.

### kappa, measured

At fixed lipid count the arc's contour length is exactly N for every span --
`R * 2*pi*span = [N/(2*pi*span)] * 2*pi*span = N` -- so varying span sweeps curvature at constant length
and `E_bend = kappa*N/(2R^2)` can be fitted directly against `1/R^2`, at the planted geometry, with no
dynamics and no spectrum:

| span | 0.50 | 0.60 | 0.75 | 0.85 | 0.92 | 0.97 |
|---|---|---|---|---|---|---|
| R | 22.28 | 18.57 | 14.85 | 13.11 | 12.11 | 11.49 |
| E_total | -1279.6 | -1288.0 | -1244.6 | -1256.5 | -1231.3 | -1236.2 |

    kappa = 269.5 +- 69.0 eps*sigma  (R^2 = 0.79, 3.9 sigma from zero) = 599 kT*sigma

**This is the first kappa this project has measured.** The undulation spectrum was abandoned as
unusable -- per-mode spread 16.7x at 60 lipids and 1712x at 120, a flat-in-q spectrum meaning the
estimator was reading its own sampling noise. The energetic route works because it compares planted
geometries rather than fluctuations.

### RETRACTION: the continuum picture was not falsified

Last tick I concluded from the span sweep that "the closed state is not preferred despite a positive
lambda, so the continuum picture is falsified for this model." **That is withdrawn.** With kappa now
measured, the criterion `kappa < 2*lambda*R/pi` gives

    R* = pi*kappa/(2*lambda) = pi*269.5/(2*10.12) = **41.8 sigma**,  critical contour = 263 lipids

and every closure test run so far sat below or barely at that threshold: the span sweep was at
**R = 11.5**, a quarter of R*, and the size sweep reached R = 42.4 only at N = 200, and there with a
60-sigma gap for the ends to cross. **The arcs opening was the theory's own prediction.** I tested the
regime where the theory says nothing closes, and read the result as though it said something closes.

### Launched: the first test actually above threshold

N = 300 (R = 49.2) and N = 400 (R = 65.6) at span 0.97, so the radius is above R* AND the gap is only
9-12 sigma. 5 seeds each, 150 000 steps, boxes 150 and 200. Two emergence runs continue alongside.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If these close -- end gap falling below about 3
sigma -- the continuum picture holds, kappa and lambda are quantitatively right, and closure was only ever
a question of size. If they open like every smaller arc, the picture fails where it makes its clearest
prediction, and that is a real falsification rather than the mis-scoped one withdrawn above. If they
close in some seeds and not others, R* is right but the barrier is stochastic, and the closure fraction
against N gives its height.

---

## 2026-08-19v tick — closure fails ABOVE the critical radius too; the drive is now measured directly

### The properly-scoped test

N = 300 (R = 49.2) and N = 400 (R = 65.6) at span 0.97, both above the measured R* = 41.8 sigma and both
planted with small gaps. 5 seeds each, 150 000 steps:

| N | R planted | gap planted | final end gaps | mean |
|---|---|---|---|---|
| 300 | 49.2 | 9.3 | 44.4 33.3 36.0 37.5 36.4 | **37.5** |
| 400 | 65.6 | 12.4 | 49.2 39.1 44.1 44.8 44.4 | **44.3** |

**All 10 opened**, by roughly fourfold, and the arcs STRAIGHTENED (R_mid 49.2 -> 54.7 and 65.6 -> 72.8).
The bilayer itself is perfect throughout (core 1.470-1.479 against a reference of 1.467), so this is not
a structural failure. N = 400 additionally fragmented in 3 of 5 seeds (largest 355, 221, 246); N = 300
stayed whole in all five.

### How far this falsifies the continuum picture

Honestly: **less than it looks, because the inputs are loose.** At R = 49.2 the criterion
`kappa < 2*lambda*R/pi` gives 269.5 against 317, favoured by a margin of 0.85; at R = 65.6, 269.5 against
423, margin 0.64. But kappa carries +-69 and lambda carries +-5.08 on a value of 10.12 -- a **50%** error
-- so one standard deviation on lambda alone flips R = 65.6 from favoured to not. The prediction at these
sizes is marginal, and a marginal prediction cannot be strongly falsified.

What IS established without theory: **closure has never occurred, at any size from R = 11.5 to 65.6, at
any gap from 2.2 to 60 sigma, at any head-head value, across roughly 60 runs.** No trend toward closure
appears as R crosses R*.

### The direct test, which needs no theory

Rather than refine kappa and lambda further, compare the two states directly: a planted closed **ring**
and a planted **arc0.97** at the same N = 300, both relaxed identically, 5 seeds each, 60 000 steps. If
closure is favoured the ring must sit lower by about `2*lambda` = 20 eps in total energy. This replaces
an inference through two uncertain constants with a single measured energy difference.

An equivalent comparison was made before the rewrite -- ring -28.91 against arc -28.54 eps/lipid, "ring
lower by ~74 kT" -- but that was on the force field with the 180-degree branch-angle pin, which did not
make bilayers, so it carries no weight now.

### The contrast worth recording

Emergent ribbons adopt strong curvature freely -- the step-300 000 frame shows a deep horseshoe -- while
planted arcs unbend. Curvature per se is not what the membrane resists. That points away from bending
rigidity as the obstruction and toward the edge term being weaker than measured.

**FALSIFICATION, STATED BEFORE THE RESULT IS READ.** If the ring is lower than the arc by close to
20 eps, the closure drive is real and the failure is kinetic -- the ends never find each other -- which
would make the next question how to nucleate contact rather than whether closure is favoured. If the two
are equal within error, there is **no drive at all**, lambda's positive value does not survive into the
closed state, and every closure experiment in this project has been chasing a force that is not there. If
the ring is HIGHER, the open ribbon is the preferred state and closure is thermodynamically forbidden
here, which would settle the milestone as unreachable without a new term in the model.

---

## 2026-08-19w tick — THERE IS NO CLOSURE DRIVE: ring and arc are isoenergetic

### The direct measurement

Planted closed ring against planted arc0.97, same N = 300, relaxed identically, 5 seeds each, 60 000
steps. Energies **time-averaged over the equilibrated half** of each trajectory:

| | endpoint only | time-averaged |
|---|---|---|
| ring | -6267.6 +- 6.2 | **-6230.7 +- 3.2** |
| arc0.97 | -6259.8 +- 11.4 | **-6231.2 +- 5.1** |

    ring - arc = +0.5 +- 6.0 eps   (0.1 sigma)
    predicted if closure favoured: -20.2 eps   -> EXCLUDED at more than 3 sigma

**The closed and open states are isoenergetic.** The falsification resolves to its second branch: there
is no thermodynamic drive to close. This explains roughly 60 failed runs across every size (R = 11.5 to
65.6), every gap (2.2 to 60 sigma), and every head-head value tried.

The endpoint-only comparison would have been reported as `-7.8 +- 13.2`, which is consistent with both
-20.2 and 0 and settles nothing. Time-averaging the SAME data cut the error by a factor of two and made
the answer unambiguous -- worth recording as a method note, since three of this project's inconclusive
results were single-snapshot comparisons.

### What this does to lambda

`lambda = +10.12 +- 5.08 eps` was measured from the intercept of `E(N) = N*e_bulk + 2*lambda` on finite
ribbons, and it is a real feature of that fit. But **it does not survive into a closure gain.** Whatever
the intercept represents, removing the two ends by closing the ribbon does not lower the energy. Any
argument in this project of the form "closure has 2*lambda to gain" is therefore withdrawn -- including
the "~81 kT" and the revised "~45 kT" figures, and the critical-radius arithmetic
`R* = pi*kappa/(2*lambda)` that depends on it. kappa itself (269.5 +- 69.0 eps*sigma) is unaffected,
being measured independently from bending energy against 1/R^2.

### The physical reason, and what it implies

**In implicit solvent an exposed edge costs almost nothing.** A tail at the rim simply has fewer
neighbours. Real vesicles close because the edge places tails in contact with WATER -- in this model's
own table, tail-water is 0.00 against tail-tail 0.70 -- and the water was deleted when the solvent was
integrated out. The solvent-averaged chi correctly reproduces bulk cohesion but cannot reproduce the
cost of an INTERFACE with a solvent that is no longer represented.

That makes the earlier rejection of explicit solvent worth revisiting: it was rejected at `seg = 0.194`,
but that was measured with the 800-eps/lipid plant, before the branch-angle fix and before the head-tail
sign change. All three defects are now repaired.

**FALSIFICATION, STATED BEFORE THE RUN.** Explicit solvent (phi = 0.55) on the corrected field, head-tail
at 0.20 and -0.25, planted ring against planted arc0.97 at N = 300, 5 seeds each, scored on `core` for
the bilayer and on the ring-minus-arc energy for the drive. If explicit solvent now holds a bilayer
(core near 1.467) AND makes the ring lower by something near 20 eps, the missing ingredient is the
solvent interface and closure should follow. If it holds a bilayer but the ring is still isoenergetic,
the absent drive is not about water and the model lacks the ingredient entirely. If the bilayer still
fails in explicit solvent, the earlier rejection stands on repaired foundations and implicit solvent is
the only regime this force field supports -- in which case a vesicle needs a term this model does not have.

---

## 2026-08-19x tick — explicit solvent cannot supply the drive either; and my measurement there was unusable

### Explicit solvent on the fully repaired field

N = 300, phi = 0.55, kT = 0.45, chi_HT = 0.20, ring against arc0.97, 5 seeds:

| | value |
|---|---|
| core, ring | **0.462** |
| core, arc | **0.377** |
| core at plant | 1.417 |
| bilayer reference | 1.467 |

**The bilayer collapses.** Core depth falls from a correct 1.417 at planting to 0.38-0.46, meaning heads
end up distributed through the tail region. The earlier rejection of explicit solvent (seg 0.194) was
made with the 800-eps/lipid plant, before the branch-angle fix and before the head-tail sign change; all
three are now repaired and **the rejection stands on repaired foundations**. This is the third branch of
the falsification stated last tick.

### The measurement was also unusable, which is my fault and is now fixed

    ring - arc = -15.0 +- 79.8 eps

The error is four times the signal. Total energy in explicit solvent is about **-61 000** because it
counts ~10 000 water beads, and the water-water term's fluctuation is +-80 eps -- far larger than the
~20 eps difference the comparison exists to detect. Comparing two lipid configurations by TOTAL energy in
a solvent bath is simply the wrong estimator.

Added `Field.energy_solute`: total energy **excluding water-water pairs**. Lipid-lipid and lipid-water
terms are both kept, so the solvent's effect on the lipids is fully counted, while the term that is the
same ensemble in both arms -- and carries all the noise -- is dropped. This is the same class of error as
the endpoint-versus-time-average problem caught last tick: the physics was fine, the estimator was not.

### The remaining possibility, and it is specific

Our explicit water is **not a liquid at kT = 0.45**: it was measured several ticks ago as a percolating
two-phase network with vacuum voids at packing 0.55, and was homogeneous only at kT = 0.90. A membrane
immersed in a two-phase fluid is not a test of explicit-solvent membrane physics. That defect was logged
and never acted on, and it is the obvious reason the bilayer fails in explicit mode.

**FALSIFICATION, STATED BEFORE THE RUN.** Ring against arc0.97, N = 300, phi = 0.55, **kT = 0.90** where
the water is homogeneous, 5 seeds each. If the bilayer survives (core near 1.467) AND ring minus arc is
near -20 eps on the solvent-excluded energy, then explicit solvent supplies the missing edge cost, the
whole failure was a broken solvent, and closure should follow. If the bilayer survives but ring and arc
remain isoenergetic, water is not the missing ingredient and the model lacks the closure drive
intrinsically. If the bilayer fails at kT = 0.90 as well, explicit solvent is unusable in this force
field at any temperature, implicit is the only regime available, and -- since implicit has no edge cost --
a vesicle is unreachable without adding a term the model does not currently have.

### Note on the standing brief

The tick brief still carries `lambda = 18.31 eps` and "closure has ~81 kT to gain". Both were withdrawn
last tick: the direct ring-versus-arc measurement gave **+0.5 +- 6.0 eps** where a drive would have shown
about -16 to -20, excluding it at roughly 3 sigma. The critical-size plan that the brief describes rests
on that drive and is therefore no longer the live question; what replaces it is whether ANY configuration
of this model has a closure drive at all.

---

## 2026-08-19y tick — explicit solvent fails at kT = 0.90 too; testing whether a usable window exists at all

### The result

Ring and arc0.97 at N = 300, phi = 0.55, **kT = 0.90** -- the one temperature at which our water was
measured to be a homogeneous liquid rather than a two-phase network with vacuum voids -- 5 seeds each:

| | core (ref 1.467) |
|---|---|
| ring | **0.386 +- 0.217** |
| arc0.97 | **0.265 +- 0.128** |

**The bilayer collapses here as well.** With kT = 0.45 already failing, explicit solvent is unusable at
both temperatures tested, and the falsification resolves to its third branch: implicit is the only regime
this force field supports, and implicit has no edge cost.

**A checkpoint I refused to read, correctly.** At step 12 000 these same runs showed core 1.31-1.37, and
I noted them as promising but explicitly declined to treat early checkpoints of a PLANTED structure as a
result. They were mid-collapse. Had I reported them, this tick would have claimed explicit solvent works.

### Two of my own measurement faults, one fixed

* The energy comparison here still read `ring - arc = -161.8 +- 104.5 eps`, because **`energy_solute` was
  added to `Field` last tick but never wired into the driver** -- the run was still printing TOTAL
  energy, water-water noise included. Now wired: the driver reports solvent-excluded energy. An
  observable that exists but is not called changes nothing, and I recorded it as fixed when it was only
  written.
* The comparison is void regardless, since both structures had collapsed. No closure conclusion is drawn
  from it.

### The specific hypothesis this leaves

Two requirements pull the temperature in opposite directions. The water must be **hot enough** to sit
above its liquid-vapour coexistence -- it was two-phase at 0.45 and homogeneous only by 0.90. The
membrane must be **cold enough** that ordering energies of order 1 eps beat kT -- and at kT = 0.90,
kT/eps ~ 0.9, so the membrane melts. **If those windows do not overlap, explicit solvent is unusable in
this model by construction rather than by accident**, and the vesicle milestone needs a term the model
does not have.

**FALSIFICATION, STATED BEFORE THE SWEEP IS READ.** Planted ring, explicit solvent, phi = 0.55,
kT = 0.45, 0.60, 0.75, 0.90, 1.10, 3 seeds each, 30 000 steps, scored on `core` against the 1.467
reference. If some intermediate temperature holds core near 1.467, a window exists, explicit solvent is
usable there, and the closure question reopens at that temperature. If core is low at every temperature,
there is no window: the membrane cannot survive in this solvent at any temperature where the solvent is
worth having, which closes explicit solvent for good and makes the negative structural rather than
circumstantial.

### No emergent screenshot this tick

The newest emergent renders are step-15 000 frames of deterministic replicates of trajectories already
shown at step 300 000, so there is no new emergent result to show. Per the standing rule, no planted
structure is sent in their place.

---

## 2026-08-19z tick — RETRACTION: explicit solvent does NOT destroy the bilayer. I read the wrong column, twice.

### The error

For two ticks I reported that explicit solvent collapses the membrane, quoting core depths of 0.462,
0.377, 0.386 and 0.265 against a reference of 1.467. Those numbers are **the `lumen` column**, not
`core`. The analysis scripts indexed `r[10]` in Python, which is 0-based, while `core` is at index **9**;
index 10 is `lumen`. The `awk` one-liners used `$10`, which IS core because awk is 1-based, so the same
quantity was printed correctly in the terminal and incorrectly in the Python summaries -- and I trusted
the Python.

Recomputed with the correct column, all five seeds, time-averaged over the equilibrated half:

| condition | CORE (correct) | what I reported (lumen) |
|---|---|---|
| explicit kT = 0.45, ring | **1.352 +- 0.013** | 0.462 |
| explicit kT = 0.45, arc | **1.365 +- 0.020** | 0.377 |
| explicit kT = 0.90, ring | **1.328 +- 0.014** | 0.386 |
| explicit kT = 0.90, arc | **1.333 +- 0.008** | 0.265 |

Bilayer reference 1.467; implicit solvent gives about 1.45. **Explicit solvent holds the bilayer.**

### What this retracts

* **"Explicit solvent destroys the bilayer"** -- withdrawn, both instances.
* **"Implicit is the only regime this force field supports"** -- withdrawn.
* **The no-overlapping-window hypothesis** -- withdrawn before it was tested. The window sweep
  (kT = 0.45 to 1.10) was launched to find a temperature where water is liquid AND the membrane holds;
  its premise was an artefact. Its partial data shows core 1.31-1.42 at every temperature, consistent
  with the corrected numbers above.
* Last tick's claim that a step-12 000 checkpoint was "mid-collapse" -- there was no collapse. The
  caution was right in principle and the diagnosis was wrong.

### How it was caught

Two supposedly identical runs disagreed: last tick's kT = 0.90 ring reported core 0.386, while this
tick's sweep showed 1.33 at the same temperature. Printing both full series showed them agreeing exactly
at every shared step -- deterministic, identical runs -- which meant the disagreement had to be in the
analysis, not the physics. **The check that found it was comparing two runs that should have matched.**

### What it reopens

Explicit solvent is where the edge cost should live: an exposed edge puts tails against water, and in
this model's own table tail-water is 0.00 against tail-tail 0.70. Implicit solvent was shown to have no
closure drive (ring minus arc = +0.5 +- 6.0 eps). **The explicit case has never been measured with a
usable estimator** -- the earlier attempts used TOTAL energy and carried +-80 to +-105 eps of
water-water noise, and `energy_solute` was written but not wired into the driver until this tick.

**FALSIFICATION, STATED BEFORE THE RUN.** Planted ring against planted arc0.97, N = 300, explicit
phi = 0.55, kT = 0.45, 5 seeds each, 60 000 steps, energies **excluding water-water pairs** and
time-averaged over the equilibrated half. If the ring sits about 20 eps below the arc, explicit solvent
supplies the closure drive that implicit lacks, and the vesicle milestone becomes a question of running
emergence in explicit solvent. If ring and arc are isoenergetic here too, the absence of a drive is a
property of the force field rather than of the solvent treatment, and closure needs a term the model does
not have. If the ring is HIGHER, the open ribbon is genuinely preferred and closure is forbidden.

### Emergence

The last three emergence relaunches used seeds 0-4 with identical parameters and therefore reproduced
the same deterministic trajectories, producing no new structures -- which is why there was no new
emergent render to show last tick. Relaunched on **seeds 5-9**.

---

## 2026-08-19aa tick — the explicit-solvent runs were destroying their own plant; fixed before reading them

### The bug

Every explicit-solvent planted run began by wrecking the structure it was supposed to measure. Water was
placed **uniformly at random**, so it landed on top of the planted membrane -- minimum separation
**0.007 sigma** -- and the steric push-off then resolved those overlaps by deforming the membrane:

| | before | after |
|---|---|---|
| planted ring, largest at step 0 | 290/300 | **300/300** |
| core at step 0 | 1.417 | **1.467** (= the bilayer reference) |
| E/lipid at step 0 | +182.2 | **-9.29** |
| largest by step 3000 | **50/300 (fragmented)** | run in progress |
| R_mid at step 0 | 58.3 against a planted 47.7 | -- |

Water is now placed on a jittered lattice with the membrane's sites excluded. **The earlier explicit
runs were measuring the destruction of the plant, not the physics**, which retroactively explains the
fragmentation I was about to interpret.

Caught by reading step-0 values rather than waiting: `largest = 290/300` before a single step of dynamics
is not something a correct plant can produce.

### Why the previous explicit conclusions are now doubly void

Last tick I retracted "explicit solvent destroys the bilayer" because I had read the `lumen` column as
`core`. The corrected numbers (core 1.33-1.37) came from runs that ALSO had the overlapping-water defect.
They happened to show an intact bilayer anyway, so the retraction stands, but the values themselves are
superseded by the runs now in flight.

### Emergence, on genuinely new trajectories

Seeds 5-9, 300 000 steps, implicit, head-tail -0.50:

| seed | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|
| largest | 74 | 39 | 50 | 48 | 64 |
| core | 1.458 | 1.463 | 1.459 | 1.462 | 1.451 |
| burial | 5.588 | 5.564 | 5.460 | 5.297 | 5.449 |

**Every one an intact bilayer** (reference 1.467). The render shows a sharp kink where two ribbons meet,
consistent with the measured stiffness: this membrane bends by forming defects rather than curving
smoothly.

### The decisive measurement, relaunched

Ring against arc0.97, N = 300, explicit phi = 0.55, kT = 0.45, 5 seeds, 60 000 steps, solvent-excluded
energy, time-averaged over the equilibrated half -- now starting from an intact plant.

**FALSIFICATION, UNCHANGED FROM LAST TICK AND RESTATED BEFORE READING.** If the ring sits about 20 eps
below the arc, explicit solvent supplies the closure drive that implicit lacks (implicit gave
+0.5 +- 6.0 eps) and the milestone becomes a question of running emergence in explicit solvent. If ring
and arc are isoenergetic here too, the absent drive belongs to the force field rather than to the solvent
treatment. If the ring is higher, the open ribbon is genuinely preferred and closure is forbidden in this
model.

---

## 2026-08-19ab tick — the drive test cannot resolve its own signal; switching to a lower-variance estimator

### Explicit solvent, ring against arc, from an intact plant

At step 27 000 of 60 000, 5 seeds, solvent-excluded energy, time-averaged:

| | core (ref 1.467) | E |
|---|---|---|
| ring | 1.334 +- 0.006 | -1983.6 +- 18.5 |
| arc0.97 | 1.337 +- 0.013 | -1995.1 +- 10.5 |

    ring - arc = +11.5 +- 21.3 eps   (0.5 sigma)

Two things follow, and only one of them is a result.

**The bilayer holds in explicit solvent** -- core 1.334 and 1.337, stable and equal between the two
geometries, on runs that finally start from an intact plant. Last tick's retraction is confirmed on clean
data.

**The drive measurement cannot resolve its own signal.** Excluding water-water pairs cut the noise from
+-80 to +-18.5, which is a real improvement, but a 20 eps effect still sits inside a +-21.3 error. The
seed-to-seed standard deviation is about 41 eps, so reaching +-5 by adding seeds alone would take roughly
**69 seeds**. Reporting "no drive in explicit solvent" from this would be reading noise; reporting a
drive would be too.

### The switch

`lambda` is the physical quantity that decides whether an edge is expensive, and it has a much better
estimator: the intercept of `E(N) = N*e_bulk + 2*lambda` across several ribbon sizes, fitted per seed.
That protocol gave `lambda_implicit = +10.12 +- 5.08 eps` -- an error four times smaller than the
ring-versus-arc difference, from the same number of seeds, because a slope-and-intercept fit over four
sizes uses far more information than one paired difference.

Launched: finite flat ribbons N = 20, 40, 60, 80 in **explicit** solvent, phi = 0.55, kT = 0.45, L = 120,
5 seeds each, 40 000 steps, solvent-excluded energy. The plant is verified intact -- N = 40 starts at
E/lipid -8.78, largest 40/40, core **1.467**, exactly the reference.

### Emergence

Seeds 5-9 completed (largest 39-74, core 1.451-1.463, every one an intact bilayer). Seeds 10-11 launched
so a dispersed-start run is always in flight.

**FALSIFICATION, STATED BEFORE THE FIT IS READ.** If `lambda_explicit` is substantially larger than
`lambda_implicit` = 10.12 -- say above 25 eps -- then water does make an exposed edge expensive, the
closure drive exists in explicit solvent, and the failure to close in implicit was a direct consequence
of deleting the solvent. If `lambda_explicit` matches the implicit value within error, water contributes
nothing to the edge cost, and the absent closure drive is a property of the force field that no solvent
treatment will repair. If `lambda_explicit` is near zero or negative, the edge is actually cheap in
water, and the entire edge-tension route to closure is dead for this model.

---

## 2026-08-20 tick — a direct edge-cost estimator, validated against the known implicit value

### The ring-versus-arc test is confirmed unusable

At step 42 000 of 60 000, explicit solvent, 5 seeds: `ring - arc = +20.8 +- 23.9 eps`. The error has not
shrunk with more sampling, exactly as predicted last tick. The sign has wandered from +11.5 to +20.8
between checkpoints, which is what a 0.9-sigma quantity does. **No closure conclusion is drawn from this
comparison in either solvent**, and the runs were killed to free CPU rather than left to accumulate more
of the same.

Confirmed on clean data alongside it: the bilayer holds in explicit solvent, core 1.326 +- 0.011 (ring)
and 1.331 +- 0.011 (arc).

### A better estimator, and it reproduces the known answer

Added a **spanning** ribbon plant: a bilayer that wraps the box seamlessly and therefore has NO ends. At
matched lipid count and matched spacing, `E(finite) - E(spanning)` is `2*lambda` as a **direct paired
difference** -- the bulk term cancels exactly, with no extrapolation and no intercept to fit.

Positive control, implicit solvent, N = 60, spacing 2.05 in both:

    spanning  E/lipid  -19.45     finite  E/lipid  -19.12     difference x 60 = 19.8 eps

against `2*lambda = 20.24 eps` from the independent `E(N)` fit. **The new estimator reproduces the known
value at the planted geometry**, which is the check that makes it worth trusting on the unknown one. Both
plants verified intact at core 1.467.

Running: finite against spanning at N = 60, 5 seeds, in **both** solvents, 40 000 steps -- implicit as the
control, explicit as the question. The `lambda_explicit` multi-size fit (N = 20/40/60/80) continues in
parallel, so the explicit answer will arrive from two independent estimators.

### Process failure caught

**No emergence run was alive at the start of this tick.** Seeds 10-11 were queued as the tail of an
`xargs -P 10` batch and were killed along with the drive runs before they started, so the standing
requirement to keep a dispersed-start run in flight was silently broken. Emergence relaunched on seeds
10-13 as its own batch, not appended to another. No new emergent render exists this tick as a result, and
no planted structure is sent in its place.

**FALSIFICATION, STATED BEFORE THE RESULT IS READ.** `2*lambda` from the finite-minus-spanning difference,
in both solvents. If explicit gives substantially more than implicit's ~20 eps, water makes an exposed
edge expensive and the closure drive exists there. If the two agree, water contributes nothing to the
edge cost and the missing drive belongs to the force field rather than to the solvent treatment. If
explicit gives less, edges are cheaper in water than in vacuum and the edge-tension route to closure is
dead for this model. The implicit arm must reproduce ~20 eps after relaxation or the estimator itself is
in question and neither number counts.

---

## 2026-08-20b tick — the new estimator failed its own control; both its numbers discarded

### The control did its job

Direct `2*lambda = E(finite) - E(spanning)` at N = 60, matched spacing, 5 seeds, 40 000 steps:

| solvent | 2*lambda |
|---|---|
| implicit (CONTROL) | **-60.1 +- 3.4** -- the independent `E(N)` fit says **+20.24** |
| explicit | -7.2 +- 9.5 |

Opposite sign, three times the magnitude. Last tick I pre-committed that "the implicit arm must reproduce
~20 eps after relaxation or the estimator itself is in question and neither number counts." It does not,
so **neither counts** and both are discarded.

**Why it fails, which is visible in the data.** The finite ribbon reads LOWER than the end-free one,
which is backwards. At step 0 the difference was +19.8, correct to within 2%. After 40 000 steps it is
-60.1. The spanning ribbon **wraps the box and is topologically pinned**, so it cannot compact; the
finite ribbon is free to. The comparison therefore measures relaxation freedom, not edge cost. Their
`core` values confirm they are no longer matched states -- 1.415 against 1.385.

The estimator is sound only at fixed matched geometry, which is exactly where it was validated and
exactly where it is useless, since the quantity of interest is the relaxed one.

### The other estimator is also in trouble

`lambda_explicit` from the multi-size fit has N = 20 and N = 40 finished, and N = 40 shows
**largest = 35.2/40**: the ribbon is shedding lipids in explicit solvent. If fragmentation grows with N,
`E(N)` is no longer the energy of one ribbon with two ends and the intercept means nothing. That check
has to be made before the fit is read, and it will be made on all four sizes.

### Stepping back: test the milestone, not a proxy

Three separate estimators have now failed to resolve a ~20 eps edge energy inside systems whose total
energy is in the thousands and which relax and fragment. Rather than build a fourth, the direct question
is available and has **never been asked**: every emergence run in this project has been in IMPLICIT
solvent, the regime now known to have no edge cost. Explicit solvent holds the bilayer (core 1.33) and is
where an exposed edge puts tails against water.

**Launched: self-assembly from a dispersed start in EXPLICIT solvent**, N = 120, L = 56, phi = 0.55,
kT = 0.45, 5 seeds, 400 000 steps. Cheap -- only ~2200 water beads at this box size.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If aggregates in explicit solvent close into rings
-- `hollow` near 0 with a small end gap, confirmed by render -- the milestone is reached and the whole
failure was running emergence in the solvent-free regime. If they form the same open ribbons as implicit,
closure fails in both solvents and the missing drive is a property of the force field, which is a clean
negative on the model rather than on the solvent treatment. If they fail to aggregate at all, the
explicit run is under-sampled and says nothing either way.

Implicit emergence continues in parallel (seeds 10-13; seed 11 at step 225 000 has largest 45/120,
core 1.448, burial 5.589).

---

## 2026-08-20c tick — first emergence in EXPLICIT solvent: strong curvature, one closed loop, and a confound

### What the run shows

Self-assembly from a dispersed start in explicit solvent, N = 120, L = 56, phi = 0.55, kT = 0.45,
5 seeds, at step 180 000 of 400 000. **This had never been run** -- every emergence run in this project
was implicit.

| seed | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| largest | 66 | 94 | 46 | 65 | **103** |
| core | 1.300 | 1.277 | 1.359 | 1.291 | 1.323 |

**Aggregation is markedly stronger than implicit**, which reached 38-74 over comparable runs, and here
reaches 46-103 of 120. The morphology is different too: the large aggregate in seed 4 is a long ribbon
swept round into a near-closed horseshoe, and **seed 3 contains an actually closed loop** -- more
curvature than implicit solvent ever produced.

### The confound, stated before any claim

Our explicit water is a **two-phase fluid at kT = 0.45** -- measured several ticks ago as a percolating
network with vacuum voids. Vapour voids therefore exist, and an amphiphile will line a void because that
is what a surfactant does at a liquid-vapour interface. **A membrane coating a bubble is visually
indistinguishable from a vesicle**, and would produce exactly the curvature and closure seen here without
any of the physics the milestone is about.

The two instruments disagree, so neither settles it: the `lumen` metric reports 1.43x bulk density for
seed 3's loop, meaning water-filled, while the render shows few water beads inside it. That disagreement
is itself the reason not to claim anything yet.

**No closure claim is made this tick.**

### The control, launched

The same emergence run at **kT = 0.90**, where the water was measured to be homogeneous and there are no
bubbles to coat. The bilayer is known to survive there (core 1.33), so the condition is viable. 5 seeds,
400 000 steps.

**FALSIFICATION, STATED BEFORE THE CONTROL IS READ.** If curved and closed structures appear at kT = 0.90
as well, they are not bubble artefacts and explicit solvent genuinely drives closure -- the milestone
would then rest on running long enough and confirming a water-filled lumen. If the structures revert to
the straight open ribbons that implicit solvent gives, the kT = 0.45 curvature was the solvent's phase
separation and not membrane physics, and the apparent progress is withdrawn. If aggregation itself
collapses at kT = 0.90, the temperature is too hot for a fair comparison and the control is
uninformative rather than negative.

### Note on the two failed estimators

Last tick's finite-minus-spanning estimator remains discarded. The multi-size `lambda_explicit` fit is
also now suspect: N = 40 showed largest 35.2/40, so ribbons shed lipids in explicit solvent, and an
`E(N)` intercept is only meaningful if every ribbon stays whole. Both are superseded by testing the
milestone directly, which is what the emergence runs above do.

---

## 2026-08-20d tick — the bubble control is UNINFORMATIVE, not negative; and the closed loop reopened

### The control failed to be a control

Emergence at kT = 0.90, where the water is homogeneous and there are no vapour voids to coat, 5 seeds,
against the kT = 0.45 arm:

| | largest | core | burial |
|---|---|---|---|
| kT = 0.90 (homogeneous water) | 62 - 118 | 1.286 - 1.321 | **0.145 - 0.532** |
| kT = 0.45 (bubbles present) | 64 - 104 | 1.252 - 1.289 | **1.303 - 2.351** |

Aggregation is fine at kT = 0.90 -- seed 3 reaches 118 of 120 -- so the third branch's "fails to
aggregate" did not happen. But **burial collapses to 0.145-0.532**, below even the dispersed start's
1.000, and the render shows a loose ramified network with heads scattered through it rather than lining
edges. **The membrane is melted at that temperature.** Its failure to produce closed structures therefore
says nothing about whether the kT = 0.45 curvature was bubble-driven, and the control is recorded as
**uninformative rather than negative**.

Note that `core` reads 1.286-1.321 at kT = 0.90, close to its kT = 0.45 values, while `burial` and the
render both say the structure is disordered. `core` measures head penetration depth and can stay
respectable in a loose network; this is a case where two calibrated metrics disagree and the render
breaks the tie against `core`.

### The closed loop reopened

Seed 3 at kT = 0.45 contained a closed loop at step 180 000. By step 380 000 that loop is a C again.
**The apparent closure was transient**, which is consistent with every other closure attempt in this
project and is recorded here so the earlier frame is not remembered as more than it was.

### The direct test, running now

Rather than another temperature control, the question is settled by asking what the enclosed region
CONTAINS. Added a flood-fill analysis: rasterize the box, mark cells near lipid beads as membrane,
flood-fill from the boundary to identify outside, and treat unreached non-membrane cells as enclosed.
Then compare water density inside those cells against outside.

* enclosed water at about bulk density -> a vesicle
* enclosed region empty -> a surfactant film on a vapour void

This distinguishes exactly the two cases that a render cannot, and that `lumen` and the render disagreed
about last tick (1.43x bulk against a visually empty interior). First completed state (seed 2) has **no
enclosed region at all**; the remaining four are still writing.

**FALSIFICATION, STATED BEFORE THE REMAINING STATES ARE READ.** If any enclosed region holds water near
bulk density, the model has produced a water-filled vesicle from a dispersed start, transient or not, and
the milestone is within reach in explicit solvent. If every enclosed region is empty, the curvature seen
in explicit solvent is surfactant adsorption onto vapour bubbles created by our two-phase water, the
apparent progress is withdrawn, and explicit solvent offers nothing the implicit case did not. If no
enclosed regions exist at the end of any run, nothing closed at all and the transient loop at 180 000 was
a fluctuation.

---

## 2026-08-20e tick — the enclosure detector failed its positive control; fixed, and the answer is a clean negative

### Last tick's result was void

Last tick I reported "no enclosed region" for all five explicit-solvent emergence seeds. Before accepting
it I ran the control that result required: a **freshly planted, intact N = 300 ring**, which is enclosed
by construction. The detector reported **no enclosed region** for it too. The instrument was broken and
the five-seed result meant nothing.

**The bug, and my first fix for it was also wrong.** The rasterizer wrapped coordinates with `% L`. The
plant centres the ring on the origin, so `% L` splits it across the box edge and the membrane never forms
a closed curve on the grid -- measured extent after wrapping was x 0.0-150.0, y 0.0-150.0 for a ring only
96 sigma across. My first fix unwrapped relative to a reference bead under the minimum image, which
**cannot** rescue a cluster wider than L/2, and this ring is 96 against L/2 = 75; the control still
failed. The working fix shifts the aggregate to the box centre using its RAW centroid before wrapping.

Positive control after the fix:

    enclosed area 5904 sigma^2   (a ring of R_mid ~48 encloses about 6362)
    n_water_in 4111              rho_in/rho_out 1.02

Water at bulk density inside a planted ring, and the area within 7% of geometry. The detector now works,
and is committed as `_lumen.py` rather than left in /tmp.

### The answer, with a working instrument

Explicit-solvent emergence, N = 120, 5 seeds, 400 000 steps, at the end of each run:

| seed | enclosed area | water inside | rho_in/rho_out |
|---|---|---|---|
| 0 | 1 sigma^2 | 0 | 0.00 |
| 1 | none | -- | -- |
| 2 | none | -- | -- |
| 3 | **21 sigma^2** | 26 | 1.92 |
| 4 | none | -- | -- |

Against the planted ring's 5904 sigma^2, the largest emergent enclosure is **21 sigma^2 -- 0.4%** -- a
pocket of radius about 2.6 sigma. **Nothing closed.** The falsification resolves to its third branch: no
persistent enclosed region, and the loop seen at step 180 000 in seed 3 was a fluctuation, as the
step-380 000 render already showed by reopening into a C.

The one non-empty pocket contains water at 1.92x bulk density rather than vacuum, so it is not a vapour
bubble either -- it is a compressed water pocket in a fold of the membrane.

### Where the bubble question stands

Undecided, and now less important. The bubble-coating hypothesis mattered only if explicit solvent had
produced closure; it produced none, so there is nothing to attribute to bubbles. What explicit solvent
did produce that implicit did not is **stronger aggregation** (largest 46-104 of 120 against 38-74) and
**more curvature**, both real and both short of closure.

**FALSIFICATION FOR THE NEXT RUN.** Emergence in explicit solvent is the most promising regime found, but
120 lipids may simply be too few: the measured critical radius before lambda was withdrawn was tens of
sigma, and a 120-lipid ribbon is about 120 sigma of contour. Running N = 300 and N = 500 in explicit
solvent, 3 seeds each, L scaled to keep packing constant. If enclosed area grows sharply with N and a
lumen at bulk density appears, closure is size-limited and the milestone needs bigger systems. If
enclosure stays near zero at 500 lipids, size is not the limitation and closure does not occur in this
model in either solvent at any size tested.

---

## 2026-08-20f tick — size scaling launched; the explicit-solvent negative is now final at N = 120

### The N = 120 explicit result, complete

All five seeds reached 400 000 steps. Final state, with the enclosure detector that now passes its
positive control (planted ring: 5904 sigma^2 enclosed, water at 1.02x bulk):

| seed | largest | core | burial | enclosed area | rho_in/rho_out |
|---|---|---|---|---|---|
| 0 | 66 | 1.252 | 1.303 | 1 sigma^2 | 0.00 |
| 1 | 98 | 1.270 | 1.651 | none | -- |
| 2 | 64 | 1.278 | 2.156 | none | -- |
| 3 | 101 | 1.264 | 2.351 | 21 sigma^2 | 1.92 |
| 4 | **104** | 1.289 | 2.163 | none | -- |

**Explicit solvent beats implicit on aggregation and curvature and still does not close.** Largest
reaches 104 of 120 against implicit's 38-74; the seed-4 render shows a ribbon sweeping most of the way
round a large region with a wide mouth left open, unchanged since step 180 000. The largest enclosed
region anywhere is 0.4% of a planted ring's.

### Two stale arms killed

The kT = 0.90 emergence arm was declared uninformative last tick -- the membrane melts there (burial
0.145-0.532) -- so it was consuming CPU without being able to answer anything, and was stopped. A 3-D
sphere run at L = 25 was also still alive from many ticks ago, in the configuration whose shape metrics
are known-void because the aggregate spans more than half the box; also stopped.

### The size question, launched

Every closure attempt in explicit solvent has used 120 lipids, which is only about 120 sigma of contour.
Whether that is simply too small is a separate question from whether the model can close at all, and it
has never been separated.

N = 300 and N = 500, explicit solvent, kT = 0.45, **L scaled as sqrt(N/120) x 56** -- 88.0 and 114.0 --
so the lipid packing fraction is held at 0.15 and only system size changes. 3 seeds each, 400 000 steps.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If enclosed area grows sharply with N and a lumen at
about bulk density appears at 300 or 500, closure is size-limited: the model can do it and every previous
attempt was simply too small. If enclosed area stays at the few-sigma-squared noise level at 500 lipids,
size is not the limitation, and closure does not occur in this model in either solvent at any size tested
-- which would be the strongest negative this project has, resting on a validated detector rather than on
a render or an energy difference no estimator could resolve. If the larger systems fail to aggregate into
single large ribbons at all, the runs are under-sampled at that size and say nothing either way.

---

## 2026-08-20g tick — I destroyed a validated instrument, restored it, and it finds a real (transient) lumen

### I overwrote an existing detector with a worse one

Last tick I ran `cp /tmp/lumen.py _lumen.py`, not knowing `_lumen.py` already existed in the project with
its own bazel target. Its docstring is a direct warning against what I replaced it with:

> The current `enclosed` flood-fill fires on everything: 29 on a field of compact micelles, 19 on a
> branched worm network. Both are false positives -- it counts grid gaps BETWEEN aggregates, and pockets
> at branch points, as if they were interiors.

My replacement summed **all** enclosed cells, which is precisely that failure. Its "21 sigma^2 in seed 3"
was therefore unreliable. Restored from git (`2756bc0`), and its validated logic -- **largest contiguous
pocket**, not the sum, with a **minimum area** -- ported to `field.py` states as `_lumen_field.py`.

Two further errors surfaced while restoring it. The duplicate bazel target broke the build until the
appended block was deleted. And the original's one-cell-per-bead occupancy, which works at DPD's density
of 4, leaves our membrane a dotted line at cell = 0.5 that the flood-fill leaks through -- the planted
ring scored **0** on its own positive control until each bead was stamped as a disc of its own radius.

### The recalibrated detector, passing every control

| control | requirement | score |
|---|---|---|
| planted ring | high | **25626 cells** |
| planted flat ribbon x3 | 0 | 0, 0, 0 |
| implicit emergent ribbons x4 | 0 | 0, 0, 0, 0 |

### The result

Explicit-solvent emergence, N = 120, 5 seeds, 400 000 steps:

| seed | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| lumen (cells) | 0 | 0 | 0 | **253** | 0 |

Seed 3's enclosure is **63 sigma^2, radius about 4.5 sigma, holding 68 water beads at 1.73x bulk
density** -- water-filled, so not a vapour bubble, which settles the confound raised three ticks ago for
this structure. The render confirms a closed loop at step 400 000.

**What this is NOT.** It is one seed in five. It is **1% of a planted ring's lumen area** (63 against
6407 sigma^2). The enclosed water is compressed rather than at bulk density. And the same loop was OPEN
at step 380 000 and closed again by 400 000, so it **fluctuates** rather than persisting. The honest
description is a transient water-filled enclosure, not a stable vesicle.

It is nonetheless the first enclosure in this project to survive a detector that passes a positive
control and three classes of negative control.

### Also this tick

Periodic state saving added -- state is now written at every checkpoint, overwriting, instead of only at
the end. Several ticks have been spent waiting for runs to finish before a new observable could be
applied to them. Two stale arms were killed: the kT = 0.90 emergence runs (membrane melts there, declared
uninformative) and a 3-D sphere run at the known-void L = 25.

**FALSIFICATION, STATED BEFORE THE SIZE RUNS ARE READ.** N = 300 and N = 500 in explicit solvent at fixed
packing are at step 80 000-140 000 of 400 000, with largest 51-79, so they are still coarsening and are
NOT read this tick. If lumen area at N = 300 or 500 reaches a substantial fraction of a planted ring's
and persists across checkpoints rather than flickering, closure is size-limited and real. If lumen stays
at zero or at the same transient 1% seen at N = 120, size is not the limitation and the model produces
only fluctuating pockets, never a vesicle.

---

## 2026-08-20h tick — lumen wired into the simulation; measuring rate and persistence instead of anecdotes

### What was NOT read

The N = 300 and N = 500 size arms are at steps 220 000 and 120 000 of 400 000, with largest 64-97 and
66-95 -- a smaller FRACTION of their systems than N = 120 reached, so they are still coarsening. **Not
read as a size result this tick.**

They also cannot be measured mid-run: periodic state saving was added last tick, but these runs started
before it and still write state only at completion. The infrastructure improvement helps only runs
launched after it, which I should have anticipated when I added it.

### Lumen is now measured inside the simulation

The validated detector is wired into the driver and prints at every checkpoint. Verified against its
positive control through the new path: a planted N = 300 ring reads **25621 cells**, matching the 25626
measured standalone.

This matters because the only positive result this project has is a single anecdote: seed 3's
**63 sigma^2** water-filled enclosure, which was OPEN at step 380 000 and closed again at 400 000. One
seed in five, fluctuating, is not a measurement.

### The experiment that turns it into one

10 fresh seeds at N = 120 in explicit solvent, 400 000 steps, with `lumen_c` printed every checkpoint.
That yields two numbers the anecdote lacks:

* **rate** -- what fraction of seeds ever form an enclosure above the detector's threshold
* **persistence** -- how many consecutive checkpoints an enclosure survives once formed

A structure that appears in one checkpoint and vanishes in the next is a fold; one that persists over
many is a vesicle, however small.

**FALSIFICATION, STATED BEFORE THE RUN.** If several of the 10 seeds form enclosures that persist over
many consecutive checkpoints, the model does produce vesicles at the small end and the milestone is a
question of stabilising and growing them. If enclosures appear in a few seeds but never survive more than
a checkpoint or two, the model produces transient folds and not vesicles, and seed 3 was a fluctuation
caught at the right moment -- which would make the enclosure result an artefact of when the snapshot was
taken rather than a property of the system. If no seed ever encloses, seed 3 was a rare outlier and the
rate is below 1 in 10.

### Observation recorded for later

In the N = 300 render the amphiphile ribbons **preferentially line the vapour voids** created by our
two-phase water. That is surfactant adsorption at a liquid-vapour interface, and it is a real effect in
these runs rather than a hypothesis -- it was raised as the bubble-coating confound three ticks ago and
is now visible directly. It does not invalidate seed 3's enclosure, which was measured to contain water
at 1.73x bulk density rather than vacuum, but it does mean curvature in explicit solvent has two possible
sources and the water-content check is required for every future closure claim.

---

## 2026-08-20i tick — restart-from-state added; the enclosure holds so far under 5 independent thermal seeds

### Rate: no enclosure in 10 fresh seeds yet, but not yet at the right step

Ten seeds at N = 120 explicit, `lumen_c` printed every checkpoint. Through step ~160 000 of 400 000, **all
ten read 0**. That is not yet evidence of a low rate: seed 3's enclosure appeared at step **400 000**, and
these runs have not reached it. Recorded as incomplete rather than as a negative.

### Persistence, attacked from the other end

Waiting for a fresh enclosure costs 400 000 steps per attempt and may not sample one at all. So I added a
**restart-from-saved-state** capability (`plant="state:<path>"`) and restarted from the one configuration
that HAS the 63 sigma^2 water-filled enclosure, with five different thermal seeds.

Verified through its own control first: the restart reproduces the source state's enclosure at
**255 cells** against 253 measured standalone.

`lumen_c` after restart, five independent thermal seeds, checkpoints every 5000 steps:

| seed | t=0 | 5k | 10k |
|---|---|---|---|
| 0 | 262 | 243 | 263 |
| 1 | 252 | 272 | 246 |
| 2 | 265 | 262 | 273 |
| 3 | 269 | 254 | 252 |
| 4 | 254 | 254 | -- |

**The enclosure holds in all five, with no decay trend**, fluctuating between 243 and 273 cells. That is
the first evidence that it is a stable object rather than a snapshot artefact.

**Why this is not yet the answer.** The source enclosure was OPEN at step 380 000 and closed at 400 000,
so it changes on a scale of ~20 000 steps; surviving 10 000 steps is inside that window and proves little.
The run continues to 100 000 steps, five times the timescale on which the original changed.

### Two bugs of mine, both caught by their own output

* The restart's `plant` string is a filesystem path, and the state-save code embeds `plant` in the output
  filename, producing a nested nonsense path. Fixed by tagging restarts by their origin seed.
* The launch script set `ST=<path>` and exported only the shell FUNCTION, so `$ST` was empty inside the
  `xargs` subshell and every run failed with `FileNotFoundError: ''`. Caught because the logs contained a
  traceback rather than data.

**FALSIFICATION, STATED BEFORE THE REST OF THE RUN IS READ.** If `lumen_c` stays in the 240-280 band
through 100 000 steps in all five seeds, the enclosure is a stable structure -- a small vesicle -- and the
milestone becomes growing it and raising its formation rate. If it decays to 0 in most seeds within
20 000-40 000 steps, it is a long-lived fold and the enclosure result is downgraded accordingly. If it
decays in some seeds and not others, the enclosure is metastable and the seed spread gives its lifetime.

**Persistence resolved, and the structure is NOT a vesicle.**

Five thermal seeds restarted from the enclosure state, checkpoints every 5000 steps, linear fit of
`lumen_c` against step:

| seed | n | steps | mean | slope per 1e5 steps |
|---|---|---|---|---|
| 0 | 9 | 40000 | 252.8 | -23.3 |
| 1 | 10 | 45000 | 256.4 | +6.5 |
| 2 | 11 | 50000 | 261.8 | -6.9 |
| 3 | 10 | 45000 | 262.1 | +22.2 |
| 4 | 10 | 45000 | 256.4 | +32.2 |

    mean slope +6.1 +- 9.9 cells per 100000 steps   (0.6 sigma from zero)

A fold decaying on the source structure's own ~20 000-step timescale would show about **-1275**. Decay is
excluded by roughly two orders of magnitude. **The enclosure is stable**, and the falsification's first
branch is met on that point.

**But the render answers the question I had not checked, and it answers against the vesicle reading.**
The boundary is a **thick disordered amphiphile mass with a hole in it** -- heads scattered through the
interior rather than lining two faces -- and `core` reads **1.278** against the bilayer reference of
1.467. A vesicle requires a bilayer boundary. This has a stable water-filled lumen and a boundary that is
not a bilayer.

**Recorded as: a stable, water-filled, enclosed pocket in a thick aggregate.** Not a vesicle. The
milestone is not reached. Both facts are real and neither is allowed to stand in for the other -- the
lumen is measured by a detector that passes one positive and three negative control classes, and the
boundary is disqualified by a metric calibrated on planted bilayers plus the render.

**FALSIFICATION FOR THE NEXT STEP.** The gap is now specific: the model makes bilayers (core 1.45-1.47 in
implicit) and separately makes stable enclosures (in explicit, core 1.28), but not both at once. Explicit
solvent supplies the enclosure and degrades the bilayer; implicit preserves the bilayer and supplies no
enclosure. If a solvent condition exists where core stays above about 1.40 AND a lumen persists, the
milestone is reachable by tuning between the two regimes. If core and lumen remain anti-correlated across
that scan, the two requirements are in direct conflict in this force field and a vesicle needs a term the
model does not have.

---

## 2026-08-20j tick — the untried combination: explicit solvent WITH repulsive head-tail

### The gap, stated precisely

Two capabilities exist in this model and have never coexisted:

| regime | chi_HT | core (bilayer ref 1.467) | lumen |
|---|---|---|---|
| implicit | **-0.50** (repulsive) | **1.45 - 1.47** | never |
| explicit | +0.20 (attractive, default) | 1.28 - 1.34 | stable 63 sigma^2 in 1 of 5 |

The repulsive head-tail term is what produced good bilayers, and it was only ever applied in IMPLICIT
solvent. Explicit solvent is what produced the enclosure, and it has only ever run with the DEFAULT
attractive term. **The combination has never been run**, which is an omission rather than a result --
`VIVARIUM_CHI_HT` sets the raw `chi[HEAD, TAIL]` in both solvent modes, so nothing prevented it.

Launched: N = 120, explicit phi = 0.55, kT = 0.45, `chi_HT` at 0.20, -0.25 and -0.50, **5 seeds each**,
400 000 steps, scored on `core` and `lumen_c` together.

### Rate, still incomplete

The ten-seed rate run is at step 300 000-320 000 of 400 000 and all ten read `lumen_c = 0`. Seed 3's
enclosure appeared at 400 000, so these have not reached the step where it showed up. **Still recorded as
incomplete, not as a low rate** -- this is the third tick these have been in flight and the temptation to
call 0/10 a result grows each time; it is not one until they finish.

### Size arms

N = 300 is at step 340 000 with largest 137/300; N = 500 at 180 000 with largest 67/500. Neither has
reached a fraction comparable to N = 120's, so neither is read.

**FALSIFICATION, STATED BEFORE THE SCAN IS READ.** If any `chi_HT` gives `core` above about 1.40 AND a
persistent lumen, the two requirements are compatible and the milestone is reachable by tuning between
the regimes. If `core` rises with repulsive head-tail while `lumen_c` falls to zero -- the anti-correlation
already visible between the two regimes -- the requirements are in direct conflict in this force field,
and a vesicle needs a term the model does not have. If `core` does not rise in explicit solvent at all,
then whatever degrades the bilayer there is the solvent itself rather than the head-tail term, and the
repulsive term is not the missing ingredient.

---

## 2026-08-20k tick — formation rate measured (rare); repulsive head-tail fixes the bilayer in explicit solvent

### The rate run finished, and the answer is clean

Ten seeds, N = 120, explicit solvent, 400 000 steps, `lumen_c` at all 20 checkpoints each:

| seed | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|
| largest | 87 | 78 | 108 | 117 | 61 | 120 | 93 | 66 | 79 | 54 |
| max lumen_c over the run | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Zero enclosures in 200 checkpoint samples.** Not one seed enclosed at any point. Checking the whole
series rather than the final state matters here: seed 3's enclosure fluctuated, so "zero at the end"
would not have settled it. "Never, in 200 samples" does.

Combined with the single enclosure among the original five seeds, **formation is a rare nucleation event
of roughly 1 in 15 runs**. Once formed it is stable -- the restart experiment excluded decay at about
130x. So the picture is coherent: rare to nucleate, durable once nucleated.

### The untried combination works, on the bilayer at least

Explicit solvent with the repulsive head-tail term, at step ~190 000 of 400 000:

| chi_HT | core (bilayer ref 1.467) | lumen |
|---|---|---|
| +0.20 (default) | 1.277 - 1.323 | 252 in seed 3 |
| **-0.25** | **1.386 - 1.435** | 0 in 3 seeds so far |

**Core rises from ~1.29 to ~1.40 in explicit solvent.** The render agrees: thinner ribbons with heads
more consistently on the faces. This settles one sub-question outright -- **the head-tail term, not the
solvent, was degrading the bilayer in explicit solvent**, so the third branch of last tick's
falsification is excluded.

The lumen question is not settled: 3 of 5 seeds reporting, at half the run length, all zero. Given the
measured formation rate of about 1 in 15, seeing zero in 3 seeds is exactly what a rate that unchanged
would predict, so this is **not** yet evidence of anti-correlation. The arm must finish, and even then
5 seeds cannot distinguish 1-in-15 from 0.

### Deterministic reproduction, noted

Seed 3 at `chi_HT = 0.20` reproduces its enclosure at 252 cells, matching the 253 measured from the
original run's saved state. Same seed, same parameters, same trajectory -- a useful check that the
enclosure is a property of the trajectory rather than of a particular analysis.

**FALSIFICATION, STATED BEFORE THE ARM FINISHES.** If `chi_HT = -0.25` or -0.50 produces an enclosure in
any seed while holding core above 1.40, the two requirements are compatible and the milestone is within
reach. If both repulsive arms finish with zero enclosures, that is consistent with the 1-in-15 base rate
and settles nothing about compatibility -- the honest next step would then be many more seeds at the best
core setting, not a new hypothesis. Only a rate measured at comparable seed count in both arms can
establish anti-correlation, and that needs of order 30 seeds per arm to distinguish 1-in-15 from zero.

---

## 2026-08-20l tick — the trade is visible: good bilayer with a marginal lumen, or a stable lumen with a poor bilayer

### The combination scan, at step ~300 000 of 400 000

| chi_HT | core (ref 1.467) | max lumen over the run |
|---|---|---|
| +0.20 (default), 5 seeds | 1.236 - 1.342 | **274** in seed 3, 0 elsewhere |
| **-0.25**, 3 seeds so far | **1.403 - 1.424** | **69** in seed 1, 0 elsewhere |

**Repulsive head-tail raises core from ~1.29 to ~1.41 in explicit solvent** and one seed produced an
enclosure, so the two are not obviously exclusive.

### But the enclosures are not equivalent, and the raw numbers show it

The reported `lumen_c` has a hard threshold at 40 cells, which turns a fluctuating quantity into a
binary one. Measured RAW (threshold removed), restarting five thermal seeds from each source enclosure:

| source | source size | restart raw sizes |
|---|---|---|
| chi_HT = +0.20, seed 3 | 255 | 242 - 280 over 10 checkpoints, slope +6.1 +- 9.9 per 1e5 steps |
| chi_HT = -0.25, seed 1 | 69 | **78, 20, 59, 37, 15** |

The default-chi enclosure is **large and stable**; the repulsive-chi one **fluctuates fivefold around
the detection threshold** and does not hold. Reading only the thresholded value would have shown
"59, 0, 78, 0, 0" and hidden that the object is marginal rather than absent.

**So the trade is: a good bilayer with a marginal lumen, or a stable lumen with a poor bilayer.** That is
one seed on each side, so it is suggestive and not established.

### What was verified rather than assumed

The restart state was checked independently before its results were read: the file on disk really did
contain the 69-cell enclosure, so the restarts began from the intended configuration and seed 1's early
loss is a real decay rather than a mis-copied state.

### Running

* 15 more fresh seeds at `chi_HT = -0.25`, for 20 total. The base rate is ~1 in 15, so 3 seeds could never
  distinguish "as often as default" from "never"; 20 can.
* 5 persistence restarts from the -0.25 enclosure, continuing.

**FALSIFICATION, STATED BEFORE THE 20-SEED ARM IS READ.** If enclosures appear in the -0.25 arm at a rate
comparable to default (roughly 1-2 in 20) AND any of them reaches the 240-280 size band that the default
enclosure occupies, the requirements are compatible and the milestone is reachable. If enclosures appear
but all stay in the marginal 15-80 raw band, size and bilayer quality are anti-correlated and this force
field trades one for the other. If no enclosure appears in 20 seeds while default gives 1 in 15, the
repulsive term suppresses enclosure outright, which is the strongest form of the conflict.

---

## 2026-08-20m tick — separating "cannot form" from "cannot exist"

### The repulsive-head-tail arm, still accumulating

Nine of fifteen new seeds reporting, at steps 120 000-240 000 of 400 000:

    core 1.401, 1.419, 1.421, 1.421, 1.422, 1.427, 1.427, 1.448, 1.452     max lumen: all 0

**Core in explicit solvent now matches implicit-solvent quality** (1.45-1.47) and reaches within 0.015 of
the 1.467 reference in the best seeds. That is the best membrane any explicit run has produced, and the
render shows thin ribbons with heads cleanly on both faces.

No enclosures yet. With the base rate at roughly 1 in 15, zero in nine partial runs is what an unchanged
rate predicts, so **this is not evidence of suppression** and is not read as one.

### The experiment that does not depend on a rare event

Every closure measurement so far has waited for spontaneous nucleation, which happens about once in
fifteen 400 000-step runs. That samples NUCLEATION, not stability, and the two questions have been
conflated throughout this project.

A **planted ring** separates them: it is a perfect bilayer with a large lumen by construction. Verified at
step 0 in explicit solvent: **largest 120/120, core 1.465, lumen 3436 cells** -- thirteen times the
largest emergent enclosure ever seen here (255 cells).

Running it at `chi_HT = -0.25` (the setting that gives core 1.40-1.45) and at +0.20 (the setting whose
emergent enclosure was stable), 5 seeds each, 150 000 steps, explicit solvent, same box and packing as
the emergence runs.

* If it holds at -0.25, a good-bilayer vesicle **is a stable state** in this force field and the only
  obstacle is nucleation -- which is a tractable problem (seeding, larger systems, longer runs).
* If it collapses at -0.25 but holds at +0.20, bilayer quality and lumen stability are **genuinely
  incompatible** here, which is the strongest form of the trade seen last tick.
* If it collapses at both, explicit solvent cannot hold a vesicle at all and the emergent enclosure at
  +0.20 was a small structure stabilised by something other than membrane mechanics.

**FALSIFICATION, STATED BEFORE THE RESULT IS READ.** The criterion is the lumen at the end relative to its
planted 3436 cells, with `core` reported alongside so a lumen preserved by a degraded membrane is not
mistaken for success. Holding above about 2000 cells with core above 1.40 is survival; falling below ~400
is collapse; anything between is partial and needs the seed spread to interpret.

---

## 2026-08-20n tick — planted vesicle at half-run: fragmenting at the good-bilayer setting

### Not read as a result

The planted-vesicle runs are at step 75 000-82 500 of 150 000. Per the standing rule, a planted structure
is read at the END, not mid-run, so **no conclusion is drawn this tick**.

One item is recorded because it is a structural state rather than a trend: at `chi_HT = -0.25` the ring's
largest connected component has fallen from **120/120 to 41-73** across all five seeds. A ring that has
broken into pieces is not going to re-form into one; but whether the final state is fragmentation or
partial recovery is left to the end of the run.

Current values, for the record only:

| chi_HT | largest | core | lumen (planted 3436) |
|---|---|---|---|
| -0.25 | 41, 55, 62, 67, 73 | 1.401 - 1.444 | 0, 0, 0, 0, 0 |
| +0.20 | 80, 84, 96, 111, 120 | 1.292 - 1.342 | 0, 0, 0, 0, **1839** |

### The 20-seed emergence arm

Seeds through sd13 report `core` 1.401-1.452 with max lumen 0. The renders show thin, well-resolved
ribbons -- but broken into several pieces rather than one aggregate, which is the same fragmentation the
planted ring is showing at this setting. That the two independent lines of evidence point the same way is
worth noting now so it is not treated as a fresh discovery later.

### What the shape of the answer will be

If the planted result holds to the end, the finding is uncomfortable and specific: **the head-tail setting
that produces the best bilayers is also the one that cannot keep a vesicle intact**, while the setting
that holds a vesicle produces a mediocre bilayer. That is a property of the force field, not of sampling,
because a planted structure removes the nucleation question entirely.

**FALSIFICATION, RESTATED BEFORE READING THE FINAL STEP.** Judged on the final lumen against its planted
3436 cells, with `core` alongside so a lumen preserved by a degraded membrane is not counted as success.
Above ~2000 cells with core above 1.40 is survival; below ~400 is collapse; between is partial. The
-0.25 arm is additionally judged on `largest`: a final value near 120 would mean the mid-run fragmentation
was transient and this entry's caution was warranted.

---

## 2026-08-20o tick — a PLANTED vesicle fails in explicit solvent at BOTH head-tail settings

### The result, read at the end of the run

Planted ring, N = 120, explicit solvent, 150 000 steps, 5 seeds per setting. Planted values: largest
**120/120**, core **1.465**, lumen **3436 cells**.

| chi_HT | largest | core | lumen |
|---|---|---|---|
| **-0.25** (good bilayer) | 55, 62, 67, 73, 74 | 1.431 - 1.449 | **0, 0, 0, 0, 0** |
| **+0.20** (default) | 80, 96, 111, 120, 120 | 1.289 - 1.321 | 0, 0, 0, 0, **1828** |

**The vesicle fails at both settings, in different ways.** At -0.25 the ring **fragments** -- largest
falls from 120 to 55-74 in every seed -- and the lumen is gone in 5 of 5. At +0.20 the ring stays
connected but **deflates**: the lumen is gone in 4 of 5, with one seed retaining 1828 of 3436 cells.

This matches the third branch of the falsification, not the second I expected from the mid-run reading.
The mid-run entry drew no conclusion, which was the right call for a different reason than anticipated:
the -0.25 fragmentation held, but +0.20 turned out to be failing too, at 4 of 5 rather than holding.

**Why this is stronger than the earlier negatives.** A planted structure removes nucleation from the
question entirely. Every previous closure result could be blamed on a rare nucleation event not being
sampled; this one cannot. Explicit solvent does not hold a vesicle that it is handed.

### The picture across the 2x2, with one cell missing

| | planted vesicle | emergent enclosure |
|---|---|---|
| implicit | reported stable, but only with older metrics | **never**, 0 in many runs |
| explicit | **fails at both chi_HT** (this tick) | rare, ~1 in 15, small |

The implicit/planted cell was measured long ago with `hollow` and `seg`, before the validated lumen
detector existed, so it is not on the same footing as the rest. **Launched: the same planted ring in
implicit solvent**, identical N, box, packing, duration and metric, at `chi_HT` -0.75 and +0.20. Verified
at step 0: largest 120/120, core 1.465, lumen 3436, matching the explicit arm exactly.

### The 20-seed emergence arm

Nine seeds running (the other six were queued behind the planted runs and have not started), at steps
280 000-360 000, core 1.415-1.425, max lumen 0. Renders show thin well-resolved ribbons that are
persistently **broken into separate pieces** -- the same fragmentation the planted ring shows at this
setting, now visible from both directions.

**FALSIFICATION, STATED BEFORE THE IMPLICIT ARM IS READ.** If the planted ring holds its lumen in implicit
solvent while failing in explicit, then the solvent is what destroys vesicles here, and the milestone
needs implicit solvent plus a nucleation mechanism -- since implicit has never nucleated one. If it fails
in implicit too, no configuration of this force field holds a vesicle, planted or otherwise, and the
model needs a term it does not have. If it holds only at `chi_HT = 0.20`, the repulsive term is
incompatible with closure regardless of solvent.

---

## 2026-08-20p tick — IMPLICIT holds a good-bilayer vesicle; the "trade" hypothesis is REFUTED

### The control, read at the end of the run

Planted ring, N = 120, **implicit** solvent, 150 000 steps, 5 seeds per setting, identical box, packing,
duration and metric to the explicit arms. Planted: largest 120/120, core 1.465, lumen 3436.

| solvent | chi_HT | largest | core | lumen |
|---|---|---|---|---|
| **implicit** | **-0.75** | **120/120 in 5 of 5** | **1.442 - 1.462** | **1828 - 1996** |
| implicit | +0.20 | 120/120 in 5 of 5 | 1.384 - 1.403 | 1542 - 1596 |
| explicit | -0.25 | 55 - 74 | 1.431 - 1.449 | 0 in 5 of 5 |
| explicit | +0.20 | 80 - 120 | 1.289 - 1.321 | 0 in 4 of 5 |

**First branch of the falsification.** The vesicle survives in implicit solvent and fails in explicit, so
**the solvent is what destroys vesicles here**, not the membrane physics.

### RETRACTION: the trade hypothesis

Three ticks ago I proposed that bilayer quality and lumen stability are anti-correlated in this force
field -- "a good bilayer with a marginal lumen, or a stable lumen with a poor bilayer." **That is
refuted.** In implicit solvent the BETTER bilayer setting gives the LARGER lumen:

    chi_HT = -0.75:  lumen 1924 +- 68     core 1.442 - 1.462
    chi_HT = +0.20:  lumen 1569 +- 21     core 1.384 - 1.403
    difference 355 +- 71, i.e. 5 sigma, in the POSITIVE direction

The two requirements are compatible and mutually reinforcing. The apparent trade was an artefact of
explicit solvent, where the membrane is being degraded by the fluid rather than by the head-tail term.

### The diagnosis is now coherent with everything measured

* Ring and arc are **isoenergetic** in implicit (+0.5 +- 6.0 eps, measured directly) -- so there is no
  thermodynamic drive to close.
* The ring is nonetheless **metastable**: planted, it holds at 120/120 with a 1900-cell lumen.
* Two states of equal energy with a barrier between them: **the vesicle survives if handed to the model
  and never forms on its own.** That is exactly what ~60 failed closure runs showed.
* Explicit solvent HAS the water that supplies edge tension in reality, but our water is two-phase at
  kT = 0.45 and destroys the membrane before it can drive anything.

**The missing ingredient is an edge penalty without a destructive solvent.**

### The next experiment, and why not a fudge term

Adding an explicit edge-energy term would import the answer, the same objection that ruled out porting
the oracle's `beta`. The principled route is to fix the solvent instead. `chi_WW` sets both the
hydrophobic effect and water's own critical point; at 1.00 the fluid is two-phase at our temperature.
Lowering it moves water toward supercritical but weakens the hydrophobic drive, so the two effects pull
opposite ways and the usable window must be measured.

Launched: planted vesicle in explicit solvent at `chi_WW` = 1.00, 0.70, 0.50, 5 seeds each. The planted
vesicle is the fast decisive readout because it already fails at chi_WW = 1.00.

**FALSIFICATION, STATED BEFORE THE SCAN IS READ.** If some `chi_WW` lets the planted vesicle survive in
explicit solvent with core above 1.40 and lumen above ~1500, that condition has both a real solvent and a
stable vesicle, and the milestone reduces to nucleation in a regime that now has an edge cost. If the
vesicle fails at every `chi_WW`, explicit solvent cannot host a vesicle in this force field at any water
cohesion, and the only remaining routes are a different solvent model or accepting implicit solvent plus
an externally imposed nucleation event. If lowering `chi_WW` saves the vesicle but flattens head/tail
segregation, the hydrophobic drive has been traded away and the fix is illusory -- `core` will show it.

---

## 2026-08-20q tick — lowering water cohesion repairs the solvent; emergence relaunched in it

### The solvent was the problem, and it is fixable

Planted vesicle in explicit solvent, scanning water self-attraction. Planted: 120/120, core 1.465,
lumen 3436.

| chi_WW | largest | core | lumen | status |
|---|---|---|---|---|
| 1.00 | 80 - 120 | 1.288 - 1.334 | 0, 0, 0, 0, 1837 | complete |
| 0.70 | **120/120 in all** | 1.304 - 1.345 | 2242, 0, 0, 0 | 4 of 5 complete |
| 0.50 | 120/120 | **1.355 - 1.371** | -- | **only 30 000-52 500 of 150 000, NOT read** |

Two things are already established from the complete arms:

* **The ring stops fragmenting.** At chi_WW = 1.00 largest falls to 80-120; at 0.70 and 0.50 it stays at
  **120/120 in every seed**.
* **Core rises rather than falls** -- 1.29-1.33 at 1.00, 1.36-1.37 at 0.50. I had flagged the opposite as
  the risk of this change ("saving the vesicle while flattening segregation... core will show it"), and
  core shows the reverse. The hydrophobic drive was not traded away.

**The render confirms the mechanism.** At chi_WW = 0.50 the water is a single homogeneous phase filling
the box evenly, including the lumen -- not the percolating network with vacuum voids present in every
explicit run to date. This is the first time this project has had a solvent that behaves like a fluid.

The chi_WW = 0.50 lumen is **not read**: those runs are a third of the way through and a planted lumen
starts at 3436, so any early value is its initial condition, not a result.

### Emergence in a working solvent, launched

Every emergence run in explicit solvent so far has been in the two-phase fluid. Explicit solvent is also
the only regime that has ever nucleated an enclosure (~1 in 15). Running emergence at chi_WW = 0.50 for
the first time, at both `chi_HT` settings, 5 seeds each, 400 000 steps.

The completed repulsive-head-tail emergence arm gives core 1.437-1.442 with max lumen 0 and renders
showing branched webs rather than closed shapes -- the baseline this new arm must beat.

**FALSIFICATION, STATED BEFORE ANY RESULT IS READ.** If enclosures appear at a rate above the ~1-in-15
baseline, or at sizes above the 255-cell best, the repaired solvent is what emergence was missing and the
milestone is close. If the rate and sizes are unchanged, fixing the solvent's phase behaviour does not
help nucleation, and the barrier is in the membrane mechanics rather than the fluid. If aggregation
itself weakens -- largest falling well below the 87-120 this regime reaches -- then lowering water
cohesion has weakened the hydrophobic drive after all, in a way the planted test could not reveal because
a planted structure does not need to assemble.

---

## 2026-08-20r tick — a planted vesicle SURVIVES in explicit solvent once the water is repaired

### The result, read at the end of the run

Planted vesicle, explicit solvent, 150 000 steps, 5 seeds per water setting. Planted: 120/120, core
1.465, lumen 3436.

| chi_WW | largest | core | lumen | seeds retaining a lumen |
|---|---|---|---|---|
| 1.00 | 80 - 120 | 1.288 - 1.334 | 0, 0, 0, 0, 1837 | 1 of 5 |
| 0.70 | 120/120 | 1.304 - 1.345 | 2242, 0, 0, 0 | 1 of 4 |
| **0.50** | **120/120 in 5 of 5** | 1.327 - 1.356 | **2781, 2794, 2802, 2763, 0** | **4 of 5** |

At chi_WW = 0.50 the vesicle is fully intact and holds **81% of its planted lumen**, with the four
surviving seeds agreeing to within 1.4% (2763-2802). At chi_WW = 1.00 the same structure fragmented and
deflated to zero. **Repairing the solvent's phase behaviour is what saves the vesicle.**

### Scored honestly against the stated criterion: PARTIAL

The criterion set before the run was "core above 1.40 AND lumen above ~1500". Lumen passes at 2780;
**core does not**, at 1.327-1.356 against the 1.467 reference and implicit solvent's 1.44-1.46. So this
is a partial pass, not a success: **the vesicle survives, but on a mediocre bilayer.**

### The combination that has not been tried

Repulsive `chi_HT` is what raises core, and the emergence runs at chi_WW = 0.50 with chi_HT = -0.25
already reach **core 1.375-1.447**. That combination has never been run on a planted vesicle, which is
the fast readout for whether a good bilayer and a stable lumen can hold at once in explicit solvent.
Launched at chi_HT = -0.25 and -0.50, 5 seeds each; verified at step 0 as 120/120, core 1.465, lumen 3436.

### Emergence in the repaired solvent, NOT read

At step 180 000 of 400 000: largest **22 - 81**, core 1.267 - 1.447, max lumen 0. The renders show
excellent thin bilayers but small, numerous aggregates.

Largest 22-81 is below the 87-120 the old solvent reached, which is the **third branch** of the
falsification written before that launch: weaker aggregation would mean lowering water cohesion has cost
part of the hydrophobic drive, invisible to the planted test because a planted structure never has to
assemble. At 45% of the run and against a baseline measured at 400 000 steps, that comparison is not yet
fair, so it is recorded as a watch item rather than a result.

**FALSIFICATION, STATED BEFORE THE COMBINATION IS READ.** If chi_HT = -0.25 or -0.50 at chi_WW = 0.50
holds the planted vesicle with core above 1.40 AND lumen above ~1500, then explicit solvent supports a
good-bilayer vesicle and every remaining obstacle is nucleation. If core rises but the lumen collapses,
the trade I retracted two ticks ago is real in explicit solvent specifically, and only implicit gives
both. If the vesicle fragments as it did at chi_WW = 1.00 with repulsive chi_HT, the repulsive term is
incompatible with an intact vesicle whenever water is present.

---

## 2026-08-20s tick — a stable bilayer VESICLE exists in explicit solvent; emergence there aggregates poorly

### The combination passes its criterion

Planted vesicle, explicit solvent, `chi_WW = 0.50` with repulsive `chi_HT`, 150 000 steps, 5 seeds.
Planted: 120/120, core 1.465, lumen 3436.

| chi_HT | largest | core | lumen |
|---|---|---|---|
| -0.25 | **120/120 in 5 of 5** | **1.419 - 1.459** | 2766, 0, 2791, **3746**, 3345 |
| -0.50 | 120/120 | **1.455 - 1.470** | 0, **4014**, 3186 (3 complete) |

The criterion set before the run -- **core above 1.40 AND lumen above ~1500** -- is met in 4 of 5 seeds
at -0.25 and 2 of 3 at -0.50. Several lumens **exceed** the planted 3436, meaning the vesicle relaxed
outward to a preferred radius rather than merely surviving.

**The render confirms the structure**: a closed, roughly circular vesicle with a water-filled lumen,
water outside, and heads on BOTH the outer and inner faces with tails between -- a genuine bilayer, not a
thick aggregate with a hole. This is the first stable bilayer vesicle this project has had in a solvent
that behaves like a fluid.

### And the cost, which the planted test could not have shown

Emergence at `chi_WW = 0.50`, near completion (340 000-380 000 of 400 000):

| chi_HT | largest | core | max lumen |
|---|---|---|---|
| 0.20 | 22 - 81 | 1.264 - 1.317 | 0 |
| -0.25 | 56 - 66 | 1.420 - 1.446 | 0 |

Largest **22-81 against the old solvent's 87-120**. This is the **third branch** of the falsification
written before that launch: weaker aggregation means lowering water cohesion cost part of the hydrophobic
drive, invisible to a planted test because a planted structure never has to assemble. **It is now
confirmed at comparable run length.**

### Where this leaves the milestone

The two requirements are now separated onto one axis, with complementary failures at its ends:

| chi_WW | aggregation (largest) | planted vesicle |
|---|---|---|
| 1.00 | **87 - 120** | destroyed, lumen 0 in 4 of 5 |
| 0.50 | 22 - 81 | **stable, core 1.42-1.47, lumen 2766-4014** |

Neither end gives both. The target state is stable; the solvent that nucleates is the one that destroys
it. That is a far sharper statement than "no closure", and it is a one-parameter question.

### Launched

`chi_WW` = 0.70 and 0.85, at `chi_HT = -0.25`, running **emergence and the planted vesicle at the same
settings**, 5 seeds each, so both requirements are scored on the same axis rather than in separate
experiments.

**FALSIFICATION, STATED BEFORE THE SCAN IS READ.** If an intermediate water cohesion gives aggregation
near the 87-120 band AND holds the planted vesicle with core above 1.40 and lumen above 1500, the
milestone is reachable at that setting and the remaining work is sampling. If aggregation and vesicle
stability remain anti-correlated across the whole axis, they are in direct conflict through the water
term, and a vesicle needs something this force field does not have. If both degrade at intermediate
values, the two ends are separate optima and the axis is the wrong knob.

---

## 2026-08-20t tick — my aggregation comparison was unfair; redone properly, chi_WW = 0.85 is the interesting point

### Correcting last tick's comparison

Last tick I reported that repairing the water weakens aggregation, comparing largest **22-81 at step
380 000** against a baseline of **87-120 at step 400 000**. Different run lengths against different
baselines is not a fair test, and I should not have stated it as a confirmed branch.

Redone at the **same step** (120 000), chi_HT = -0.25 throughout:

| chi_WW | n | largest at 120k | core |
|---|---|---|---|
| 1.00 | 15 | 57.3 +- 16.7 | 1.412 +- 0.023 |
| **0.85** | 5 | **64.0 +- 19.0** | 1.417 +- 0.021 |
| 0.70 | 5 | 44.6 +- 12.5 | 1.421 +- 0.024 |
| 0.50 | 5 | 32.0 +- 11.9 | 1.411 +- 0.017 |

At this step chi_WW = 0.85 aggregates **as well as the original water** (0.7 sigma apart), and the
0.50 deficit is only **1.2 sigma** -- not significant.

Redone at the **end** of each run, properly powered:

    chi_WW = 1.00   n=15   largest 94.8 +- 5.5
    chi_WW = 0.50   n=5    largest 54.2 +- 5.7
    difference +40.6 +- 7.9   (5.1 sigma)

**So the claim survives but with a correction**: the aggregation penalty at chi_WW = 0.50 is real and
large, but it **develops late in the run** rather than being present throughout. Last tick's statement was
right in direction and wrong in evidence.

### The water axis so far

| chi_WW | aggregation (end) | planted vesicle survival |
|---|---|---|
| 1.00 | **94.8 +- 5.5** | 1 of 5 |
| 0.85 | **as good as 1.00 at 120k** | **running -- the decisive point** |
| 0.70 | 44.6 at 120k | 1 of 5 (lumen 2305, 0, 0, 0, 0) |
| 0.50 | 54.2 +- 5.7 | **4 of 5** (lumen 2766-3746) |

0.70 is the worst of both -- weaker aggregation AND poor vesicle survival -- so the axis is not simply
monotone, and an intermediate optimum is possible rather than excluded.

### Priority error, corrected

The chi_WW = 0.85 planted arm -- the measurement the whole axis turns on -- had been queued behind five
400 000-step emergence runs in the same `xargs` batch and had not started at all. Relaunched as its own
batch. Verified at step 0: 120/120, core 1.465, lumen 3436.

**FALSIFICATION, STATED BEFORE THE 0.85 PLANTED ARM IS READ.** If the vesicle survives at chi_WW = 0.85
in a majority of seeds with core above 1.40 and lumen above 1500, that setting has full aggregation
strength AND a stable vesicle, and the milestone reduces to nucleation sampling at a single known
condition. If it fails there as it did at 0.70 and 1.00, then vesicle survival requires water cohesion at
or below 0.50, which costs 40 lipids of final aggregate size, and the two requirements are genuinely
opposed along this axis. If it survives but aggregation at 0.85 falls at long times the way 0.50 did, the
120 000-step comparison was too early to judge and the axis needs end-of-run data at every setting.

---

## 2026-08-20u tick — the water axis is closed; aggregation and vesicle survival are opposed along it

### The decisive point, read at the end

Planted vesicle at `chi_WW = 0.85`, the setting that aggregates as well as the original water, 150 000
steps, 5 seeds. Planted: 120/120, core 1.465, lumen 3436.

    largest 50, 68, 72, 73, 84      core 1.414 - 1.438      lumen 0, 0, 0, 0, 0

**It fragments and loses the lumen in 5 of 5.** Second branch of the falsification.

### The completed axis

| chi_WW | aggregation (largest, end) | planted vesicle survives | emergent enclosure |
|---|---|---|---|
| 1.00 | **94.8 +- 5.5** (n=15) | 1 of 5 | ~1 in 15, up to 255 cells |
| 0.85 | 80 - 120 | **0 of 5** | 41 cells in 1 of 5 (marginal) |
| 0.70 | 44.6 at 120k | 1 of 5 | 0 of 5 |
| 0.50 | 54.2 +- 5.7 | **4 of 5** (lumen 2766-3746) | 0 of 5 |

**Vesicle survival requires water cohesion at or below 0.50, and that costs 40 lipids of final aggregate
size (5.1 sigma).** The conditions that drive lipids together hard enough to build large closed
structures are the same conditions that destroy a vesicle once it exists. The axis is closed as a route
to holding both at fixed conditions.

Confirmed at full run length: emergence at 0.85 reaches largest 80-120, matching the original water, which
is what the step-120000 comparison predicted. That prediction is now validated rather than assumed.

### The consequence, launched

The two requirements are opposed **at fixed conditions** -- but they need not be applied at the same
**time**. Real vesicle preparation is a two-stage protocol: detergent removal, temperature quench,
dialysis. So: assemble at `chi_WW = 1.00`, where aggregation is strongest, then continue **the same
configuration** at `chi_WW = 0.50`, where a closed structure is stable.

Restarted 8 completed strong-cohesion emergence states (largest 60-120) into the weak-cohesion solvent,
200 000 steps each. Verified at step 0: the configuration carries over intact at largest 120, core 1.407.

**Nothing is imported by this.** Both stages use the model's own physics; only the solvent condition
changes, and it changes to a value the model already runs at. This is not the `beta` objection -- no term
is added that encodes the answer.

**FALSIFICATION, STATED BEFORE THE QUENCH IS READ.** If enclosures appear after the quench at a rate above
the ~1-in-15 baseline, or grow from the marginal sizes seen at fixed conditions, then assembly and
stability simply needed to be separated in time and the milestone is reachable by protocol. If the
quenched structures behave exactly as fixed-condition ones -- no enclosures, or the same rare marginal
ones -- then separating the two stages does not help, and the obstacle is not the ordering of conditions
but something in the membrane mechanics. If the structures fall apart on quenching, the weak-cohesion
solvent cannot hold what the strong one built, and the two regimes are incompatible even sequentially.

---

## 2026-08-20v tick — the quench raises FLICKERS, not vesicles; a persistence criterion applied to every arm

### First reading, and why it was wrong

The quench (assemble at chi_WW = 1.00, continue at 0.50) gave enclosures in **3 of 8** seeds against a
~1-in-15 fixed-condition baseline. Read as a rate, that is the protocol working.

The time series say otherwise:

    sd1: 0 0 0 0 0 0 0 0 0 49 70 0 50 0 0
    sd2: 0 0 0 0 0 0 0 0 0 0 0 40 0 0 0
    sd4: 0 0 0 0 0 0 0 0 0 0 42 0 0

These are **single-checkpoint flickers just above the 40-cell detection threshold**, not structures. The
one genuinely persistent enclosure this project has found held **252-274 for eight consecutive
checkpoints**. Counting "ever exceeded threshold" conflates the two.

### One criterion, applied to every arm

Longest run of consecutive checkpoints with a lumen:

| arm | seeds | ever >0 | >=2 consecutive | >=4 consecutive | max lumen |
|---|---|---|---|---|---|
| fixed chi_WW = 1.00 | 15 | 2 | 1 | **1** | 158 |
| fixed chi_WW = 0.85 | 5 | 1 | 0 | 0 | 41 |
| fixed chi_WW = 0.50 | 5 | 0 | 0 | 0 | 0 |
| **quench 1.00 -> 0.50** | 8 | **4** | 1 | **0** | 70 |

**The quench doubles transient detections and produces no persistent structures.** By the criterion that
matters -- four consecutive checkpoints -- it is 0 of 8 where fixed conditions managed 1 of 15. That is
the **second branch** of the falsification written before the run: separating assembly and stability in
time does not help, so the obstacle is not the ordering of conditions.

### What the quench did establish

The third branch is excluded: the structures **did not fall apart** when the solvent was weakened.
Largest stayed at 119-120 in 7 of 8, with core 1.410-1.451. The weak-cohesion solvent holds what the
strong one built -- it simply does not cause it to close.

### Status and caution

The quench arm is at 60-75% of its 200 000 steps and 12 more seeds are now running, so these numbers are
provisional. The correction above is not: the flicker-versus-structure distinction is a property of the
data already collected, not of how long it runs.

**FALSIFICATION, STATED BEFORE THE FULL QUENCH ARM IS READ.** Scored on seeds reaching four consecutive
checkpoints with a lumen, the same criterion applied to every arm above. If the full 20-seed quench gives
a rate above the fixed-condition 1 in 15, the protocol helps and the earlier flicker reading was merely
underpowered. If it stays at zero, the quench is excluded as a route and the remaining candidates are
larger systems, longer runs, or an ingredient the model does not have. If persistent enclosures appear
only in seeds whose pre-quench aggregate was largest, the limitation is aggregate size rather than the
protocol, which is testable directly.

---

## 2026-08-20w tick — the two stages do different jobs: strong cohesion nucleates, weak cohesion sustains

### The full quench arm, on the persistence criterion

| arm | seeds | ever >0 | >=2 consec | >=4 consec | max lumen |
|---|---|---|---|---|---|
| fixed chi_WW = 1.00 | 15 | 2 | 1 | **1** | 158 |
| fixed chi_WW = 0.85 | 5 | 1 | 0 | 0 | 41 |
| fixed chi_WW = 0.50 | 5 | 0 | 0 | 0 | 0 |
| quench 1.00 -> 0.50 | 20 | 8 | 3 | **1** | **208** |

At four consecutive checkpoints the quench gives **1 of 20** against **1 of 15** fixed. **The quench does
not increase nucleation**, confirming the second branch on the full arm.

### An attribution failure, and its recovery

The one persistent quench result held **158-208 cells for eighteen consecutive checkpoints**, and I could
not initially say whether it was created or inherited: the source-to-seed mapping had been left to glob
ordering and never recorded, and the state file I checked showed lumen 0 -- because bash glob and Python
`sorted()` order `sd1, sd10, sd18, sd19...` differently, so I was reading the wrong source.

**The render filename carried the mapping**: the frames are tagged `restart19`, which identifies the
source exactly. The tag was added many ticks ago for a different reason and happened to preserve what the
launch script discarded.

### The recovered history, and what it means

Source `sd19` at fixed chi_WW = 1.00:

    0 0 0 0 0 0 0 0 0 0 0 154 137 130 112 144 133 158 124 125

An enclosure **nucleated spontaneously** at about step 220 000 and held nine checkpoints. Quenched to
chi_WW = 0.50, the same structure persisted **eighteen more** checkpoints and **grew from 125 to
158-208**, before dissolving in the final two.

**So the two stages do different jobs.** Strong cohesion is what nucleates; weak cohesion is what
sustains and enlarges. That is consistent with every other measurement: the planted vesicle survives only
at chi_WW <= 0.50, and enclosures only ever nucleate at chi_WW >= 0.85.

### What it is not

An enclosed pocket in an irregular aggregate, **208 cells = 52 sigma^2, about 6% of a planted vesicle's
859 sigma^2**, and it dissolved by the end. The render shows a hole in a lumpy aggregate, not a bilayer
shell. **No vesicle. The milestone is not reached.**

**FALSIFICATION, STATED BEFORE THE RE-RUN IS READ.** The quench is repeating with the source-to-seed
mapping written to `/tmp/qmap.txt` at launch, plus four fresh dispersed-start runs at chi_WW = 0.85 so
nucleation continues to be sampled. Scored on four consecutive checkpoints AND on whether the source had
a lumen at read time. If quenched seeds whose sources had NO lumen produce persistent enclosures, the
quench nucleates after all and the 1-of-20 was underpowered. If every persistent quench enclosure traces
to a source that already had one, the quench is purely a stabiliser, and raising the yield means raising
the nucleation rate at strong cohesion -- a different experiment from anything run so far.

---

## 2026-08-20x tick — the quench is a STABILISER, not a nucleator; nucleation is the rate-limiting step

### With the mapping recorded, the answer is clean

Quench re-run with the source-to-seed mapping written at launch, 20 seeds:

| source lumen at its own end | seeds | quench longest run | quench max lumen |
|---|---|---|---|
| **0** | **19** | 0 - 2 (flickers) | 0 - 70 |
| **125** (source sd19) | 1 | **13 consecutive** | **195** |

**Every persistent quench enclosure traces to a source that already had one.** Nineteen lumen-free
sources produced nothing but single- or double-checkpoint flickers near the 40-cell threshold. This is the
second branch of the falsification stated before the run.

**So the quench cannot create an enclosure -- only sustain and enlarge one.** Combined with the earlier
arms, the division of labour is now measured rather than inferred:

* strong cohesion (chi_WW >= 0.85) **nucleates**, at roughly 1-2 in 15-20 runs
* weak cohesion (chi_WW <= 0.50) **sustains and grows**, but nucleates nothing in 25 runs
* the planted vesicle survives only at chi_WW <= 0.50

**Nucleation is the rate-limiting step**, and it is the one thing no condition tested so far improves.

### Launched: what controls nucleation

Concentration is the direct knob -- a smaller box raises the encounter rate at fixed lipid count. Box
L = 45, 50, 56 at N = 120, chi_WW = 1.00 where nucleation actually happens, 5 seeds each, 400 000 steps.
That spans 1.55x in area.

### A collision caught before it corrupted the sweep

The render and state tags carried N, kT, frac_short and every `VIVARIUM_*` override -- but **not L**,
because `_env_tag()` enumerates environment variables and L is a positional argument. Sweeping box size
with identical seeds would have had all three sizes overwriting each other's renders and states. This is
the same missing-variable failure as the very first collision in this project, and the automatic helper
built to end that class of bug did not cover it. Fixed: `L` is now in both tags, and the sweep was
relaunched from scratch.

**FALSIFICATION, STATED BEFORE THE SWEEP IS READ.** Scored on nucleation events per run -- an enclosure
persisting four or more consecutive checkpoints -- across the three box sizes, 5 seeds each. If the rate
rises as the box shrinks, nucleation is encounter-limited and the milestone is a matter of concentration
and run length, both cheap. If the rate is flat across a 1.55x range in area, nucleation is not
encounter-limited and something else gates it -- most likely a barrier in the closure step itself, which
would point back at the isoenergetic ring-versus-arc result. If the smallest box suppresses nucleation,
crowding interferes with closure and the optimum is at lower concentration than tested.

---

## 2026-08-20y tick — nucleation looks ENCOUNTER-LIMITED; best emergent enclosure yet, and it holds water

### The concentration sweep, compared at a matched step

Nucleation rate against box size, N = 120, chi_WW = 1.00, all compared at **step 160 000** because L = 45
had run further and raw counts would have flattered it:

| L | area | seeds | any lumen | >=2 consec | >=4 consec | max |
|---|---|---|---|---|---|---|
| **45** | 2025 | 5 | **2** | **1** | **1** | **187** |
| 50 | 2500 | 5 | 0 | 0 | 0 | 0 |

The L = 45 series are structures, not flickers:

    sd31:  0 x8  then 44 53 54 55 57          (persistent, growing)
    sd32:  0 0   then 187 177 170 180 172 182 175 164 191 192

**sd32 nucleated de novo at about step 60 000 and has held ~180 cells for ten consecutive checkpoints.**
For comparison, at L = 56 the rate was 1-2 in 15 with nucleation only at step ~220 000.

This is the **first branch** of the falsification: the rate rises as the box shrinks, so nucleation is
encounter-limited -- which makes it improvable by concentration and run length, both cheap.

### A visual misread of my own, corrected by measurement

Looking at the render I judged the enclosed region to be a **vapour void lined by surfactant** -- the
bubble-coating confound I had recorded as mandatory to check in this solvent, since chi_WW = 1.00 water is
two-phase and does contain voids.

The measurement says otherwise:

    204 cells = 51 sigma^2
    44 water beads inside, density 0.216/cell
    773 outside, density 0.144/cell
    rho_in / rho_out = 1.50

**It is water-filled at 1.5x bulk density, not a void.** The interior water simply looks sparser than the
surroundings at render scale. Had I trusted the image, I would have discarded the best emergent result
this project has produced.

### What it is and is not

**Is:** a persistent, water-filled, de novo enclosure from a dispersed start -- 51 sigma^2, ten-plus
consecutive checkpoints, at raised concentration.

**Is not:** a vesicle. 51 sigma^2 is **6%** of a planted vesicle's 859 sigma^2 lumen, and the boundary is
a lumpy aggregate rather than a clean bilayer shell. The milestone is not reached.

### Launched

Two cheap extensions: **L = 38 and 42** to see whether the rate keeps rising with concentration, and
**five more seeds at L = 45** so the rate carries an error bar instead of being 2 of 5.

**FALSIFICATION, STATED BEFORE THE EXTENSION IS READ.** Scored on enclosures persisting four or more
consecutive checkpoints, at matched step. If the rate keeps rising from L = 45 to 42 to 38, nucleation is
encounter-limited across the range and the milestone is a sampling problem. If it peaks and falls, there
is an optimum concentration and crowding interferes below it -- the third branch stated last tick. If
L = 45's 2-of-5 does not reproduce in the added seeds, the apparent rise was a small-sample artefact and
the encounter-limited reading is withdrawn.

---

## 2026-08-20z tick — the concentration trend is real, but I cannot yet tell a LUMEN from a PACKING GAP

### The trend, at matched step

| L | area | seeds | any lumen | >=4 consec | max |
|---|---|---|---|---|---|
| 38 | 1444 | 1 | 1 | 1 | 633 |
| 42 | 1764 | 5 | 3 | 1 | 334 |
| 45 | 2025 | 10 | 4 | 2 | 250 |
| 50 | 2500 | 5 | 0 | 0 | 0 |
| 56 | 3136 | 5 | 0 | 0 | 0 |

Monotone in both rate and size. The L = 38 seed nucleated by step **20 000** against L = 45's ~60 000 and
L = 56's ~220 000.

### Two false alarms of mine, both checked rather than assumed

* I read sd34's series as showing a 633-cell enclosure **at step 0**, which would have meant the detector
  fires on random configurations. It does not: `awk 'NR>4'` had skipped the step-0 row, and the 633 is at
  step 20 000. A direct control confirms **lumen = 0 at step 0 for every box size**.
* I judged from the render that the L = 45 enclosure was a **vapour void**. Measurement said water-filled
  at 1.50x bulk. Recorded last tick.

### The failure that matters, and it qualifies the last two ticks

The L = 38 render shows a **dense percolating jumble** filling the box, heads and tails intermixed, whose
dark regions look like **packing gaps in a crowded network** rather than lumens inside a membrane. That is
the exact false positive the original `_lumen.py` was written to avoid.

**I tried twice to build a discriminator and both failed their positive control:**

| attempt | planted vesicle | L = 38 jumble | verdict |
|---|---|---|---|
| randomize lipid orientations in place | 4014 -> **4049** | 194 -> 163 | useless: the metric is positional, so rotation cannot move it |
| fraction of lining lipids with head inward | **0.54** | **0.70** | backwards -- the jumble scores higher |
| same, restricted to the inner leaflet | **0.54** | **0.70** | unchanged; the shell still catches outer-leaflet lipids |

**So `lumen_cells` measures a geometric enclosure and nothing more.** The concentration trend stands as a
count of geometric enclosures. It does **not** currently stand as evidence of vesicles, and the last two
ticks' framing is qualified accordingly. The one enclosure independently shown to hold water at 1.50x
bulk (L = 45) remains the strongest single case, because that check does not depend on the failed
discriminator.

### Also fixed

Four of five L = 38 runs had **crashed**: `only 394 free water sites for 411 waters`. The water lattice
oversampled by a fixed 1.6x, which is insufficient when lipids cover ~42% of the box. It now scales with
the lipid fraction. The densest point of the concentration sweep therefore rested on the single seed that
survived, which is now being remeasured with 5 fresh seeds at L = 38 and 5 matched controls at L = 45.

**FALSIFICATION, STATED BEFORE THE RERUN IS READ.** Two things are being tested. If the L = 38 rerun
reproduces enclosures in a majority of its 5 seeds, the concentration trend is real at the densest point
rather than resting on one survivor. And separately, any claim that these are vesicles requires a
discriminator that scores a planted vesicle ABOVE a jumble -- both of mine did the reverse, so until one
passes that control, every enclosure here is reported as a geometric pocket of stated area and water
content, never as a vesicle.

---

## 2026-08-21 tick — concentration trend reproduces at 5 of 5; third discriminator fails, but informatively

### The rerun, with the water-placement bug fixed

L = 38 with five fresh seeds, against matched L = 45 controls, at step 120 000:

| L | seeds | any lumen | >=4 consec | max | core |
|---|---|---|---|---|---|
| **38** | 5 | **5 of 5** | 2 | 206 | 1.394 |
| 45 | 5 | 2 of 5 | 1 | 394 | 1.406 |

**Every seed at the densest concentration forms an enclosure.** The trend no longer rests on the single
seed that survived the crash, and with L = 50 and L = 56 at 0 of 5 the ordering is
38 > 45 > 50 = 56. **Nucleation is encounter-limited**, confirmed.

### Third discriminator attempt, third failure

Per-bead head enrichment in the layer lining the enclosure -- built specifically because the two previous
attempts assigned lipids to leaflets and a bilayer's outer leaflet defeats that by construction:

| | planted vesicle | L = 38 jumble |
|---|---|---|
| head enrichment | **1.19 - 1.31** | **1.63** |

Backwards again. Small pockets have high surface-to-volume, so heads line them strongly; the measure is
confounded by pocket size, not by membrane order.

**But this failure carries information the others did not.** The jumble's pockets score 1.63, well above
1.0 -- so they are **head-lined, amphiphile-bounded water pockets**, not raw gaps between random surfaces.
The distinction I was chasing is therefore softer than assumed: what separates these from a vesicle is not
whether a membrane bounds them, but how ORDERED that membrane is -- and `core` already measures exactly
that. The enclosures sit at core 1.39-1.41 against a planted vesicle's 1.465.

**Standing rule, unchanged:** no enclosure is called a vesicle. Each is reported as a geometric pocket
with its area, water content and boundary order.

### The combination not yet tried

Every knob so far fixes one half and breaks the other -- except that **concentration and water cohesion
act on different things**:

* high concentration (L = 38) supplies nucleation, 5 of 5 seeds
* weak water cohesion (chi_WW = 0.50) supplies membrane order (core 1.42-1.47) and vesicle stability, its
  only cost being weak aggregation -- which concentration supplies independently

Launched: L = 38 at `chi_WW` = 0.50 and 0.70, 5 seeds each, 400 000 steps.

**FALSIFICATION, STATED BEFORE THE RUN.** If L = 38 with chi_WW = 0.50 gives enclosures at the L = 38 rate
AND core at the chi_WW = 0.50 level (>= 1.42), the two knobs are independent and the result is a
persistent, water-filled, well-ordered enclosure formed from a dispersed start -- the closest this project
can come to the milestone without a discriminator that passes its control. If core stays at 1.39, water
cohesion does not control membrane order at high concentration and the two knobs interact. If enclosures
disappear at chi_WW = 0.50 even at L = 38, weak cohesion suppresses nucleation independently of
concentration, and the opposition is fundamental rather than a matter of finding the right corner.

---

## 2026-08-21b tick — best-scoring condition found, and the detector's false-positive rate measured

### The combination: highest persistence yet

L = 38 (nucleation) crossed with `chi_WW` (membrane order), 5 seeds each, matched step 120 000:

| chi_WW | any lumen | **>=4 consec** | max | core |
|---|---|---|---|---|
| 1.00 | 5 of 5 | 2 | 206 | 1.394 |
| 0.70 | 4 of 5 | 1 | 925 | 1.412 |
| **0.50** | **5 of 5** | **4 of 5** | 686 | 1.407 |

`chi_WW = 0.50` **doubles the persistence rate** to 4 of 5. Seed 54 held ~370 cells for all twenty
checkpoints, water-filled at **1.58x bulk density**; seed 51 reached 686.

Scored against the criterion set before the run -- enclosures at the L = 38 rate AND core >= 1.42 --
this is the **second branch**: the rate target is exceeded, but core reaches only 1.407. The two knobs
partially interact; weak water cohesion does not deliver at high concentration the membrane order it
gives at L = 56.

### The render undercuts the metric, again

The structure is a **crowded amphiphile network with irregular water-filled gaps**, not a vesicle. The
365-cell enclosure is one of those gaps.

**That exposes a confound in the concentration trend itself.** Crowding makes gaps trivially more likely,
which is why 5 of 5 seeds "enclose" at L = 38 -- and it explains why three separate discriminators all
failed. The trend may be measuring gap frequency rather than nucleation.

### The detector's false-positive rate, measured rather than assumed

Step 0 is a random configuration where no enclosure can exist, so any score there is spurious:

| configuration | random configurations scoring an enclosure |
|---|---|
| N = 120, L = 38 and 56 | **0 of 3** |
| N = 300, L = 60 and 90 | 0 of 3 |
| **N = 300, L = 60, 12 seeds** | **3 of 12**, all ~50 cells (51, 50, 51) |

The rate is **seed-dependent and only visible with enough samples** -- the first three seeds I tried gave
zero. So `min_cells = 40` is too low at N = 300, where the noise sits at ~50 cells.

**Consequence, applied going forward:** the N = 120 results stand, sitting far above their own zero noise
floor (206-686 against 0 of 3 spurious). At N = 300 nothing below **~100 cells** counts.

### Launched

N = 300 at L = 60 -- the same 0.42 lipid area fraction as L = 38, but 2.5x more lipids, so a single
aggregate can be large relative to the box while empty space remains and a closed structure would be
unambiguous rather than a gap between crowded arms.

**FALSIFICATION, STATED BEFORE THE RUN.** Scored on enclosures above **100 cells** (the measured N = 300
noise floor) persisting four or more consecutive checkpoints, with core and water content reported
alongside. If such enclosures appear and the render shows an isolated closed object rather than a gap in
a network, that is the strongest emergent result this project can produce and the milestone is in reach.
If enclosures appear only in the 50-100 cell band, they are indistinguishable from the measured noise and
the concentration trend is confirmed as a crowding artefact. If aggregates remain space-filling even at
this size, the model cannot make an isolated closed object at any concentration that nucleates one.

---

## 2026-08-21c tick — a discriminator that PASSES its control: every emergent enclosure is a PERCOLATING network compartment

### The larger system, read at the end

N = 300, L = 60 (same 0.42 lipid area fraction as L = 38), chi_WW = 0.50, 5 seeds, 400 000 steps. Noise
floor at this size measured last tick as ~100 cells.

    sd63:  97 117 120 625 661 532 529 605 565 546 576 529 567 510 579 568 507 514 510 509
    sd64:  ... 611 117 110 1344 1516 1635 1564 1725 1731
    sd62:  ... 2832 408 363 3373 3554 ... 636 542

All five seeds hold enclosures far above the noise floor, sd63 stable at ~550 for seventeen consecutive
checkpoints and sd64 growing to **1731** -- half a planted vesicle's 3436. `largest` is 300/300 and core
1.397-1.422.

### The fifth discriminator attempt, and this one works

Four previous attempts failed their positive control (a planted vesicle had to score above a jumble, and
each time scored below). A fifth, **span/L**, failed too: the planted vesicle spans 0.87 of its box simply
by being large, so a span threshold called it percolating.

The correct test is **topological, not geometric**: does the enclosing cluster connect to its own
**periodic image**? Unwrap by BFS and check whether any bead is reached with two inconsistent unwrapped
positions.

| | largest | lumen | percolates |
|---|---|---|---|
| **planted vesicle (control)** | 120 | 4014 | **False** |
| N = 300, L = 60, all 5 seeds | 300 | 273 - 1731 | **True** |
| N = 120, L = 38 | 120 | 365 | **True** |

**It passes its control and separates every case.**

### What this settles

**Every emergent enclosure this project has produced is a compartment in a percolating network** -- a
sponge phase -- and the planted vesicle is the only finite closed object it has ever had. The render
agrees: a bilayer network spanning the box with water-filled compartments between its arms.

This retroactively explains the four failed discriminators. Those pockets genuinely are amphiphile-lined
and water-filled -- head enrichment 1.63, water at 1.5-1.6x bulk -- so no measure of *lining* or *content*
could separate them from a vesicle. The difference was never chemistry or water; it is **topology**.

**Every enclosure count reported in the last five ticks is therefore a count of network compartments.**
The concentration trend, the quench results and the chi_WW combination all stand as measurements of
compartment formation, not of vesicle formation.

### Launched

A vesicle needs an aggregate large enough to close but a box large enough that it cannot span. 300 lipids
closed into a ring gives R = 300/(2*pi) = 48, diameter 96, so **L = 120** leaves room for a finite closed
object. 5 seeds, 800 000 steps -- double length, since dilution slows coarsening.

**FALSIFICATION, STATED BEFORE THE RUN.** Scored on a **non-percolating** cluster with a lumen above the
noise floor, confirmed by render. If one appears, it is a vesicle by every test this project has, and the
milestone is reached. If aggregates grow until they percolate and only then enclose, closure in this model
is intrinsically a network phenomenon and an isolated vesicle needs something the force field lacks. If
aggregates stay small and never close, the dilution needed to prevent percolation also prevents the
aggregate reaching closure size, and the two requirements are geometrically incompatible at this lipid
count -- which would make the next move more lipids, not different chemistry.

---

## 2026-08-21d tick — percolation test wired into the simulation; the emergent phase is a bilayer SPONGE

### Nothing read from the decisive run

N = 300 at L = 120 is at step **40 000 of 800 000** -- largest 8-21 lipids, core 1.39-1.47, lumen 0
everywhere. Nothing has coarsened. **Not read.** Dilution was the price of making a finite closed object
geometrically possible, and it is being paid in coarsening time as expected.

### The discriminator is now part of the instrument

`percolates` -- does the enclosing cluster connect to its own periodic image -- is wired into the driver
and printed at every checkpoint as a `perc` column. Verified **through the new code path**, not just
standalone: a planted vesicle reads `perc = n` with `lumen_c = 3436`.

This matters because the quantity is cheap to compute and impossible to reconstruct later: five earlier
analyses had to be redone post-hoc, and one enclosure could not be attributed at all because the launch
script discarded information the render filename happened to preserve.

### What the emergent phase actually is

The N = 300, L = 60 renders and the topological test agree: a **bilayer sponge phase** -- a network of
two-leaflet ribbons spanning the box, with water-filled compartments between the arms. Seed 63 held
~550 cells for seventeen consecutive checkpoints at core 1.409.

The ribbons are good membrane, heads on both edges. **That is precisely why five chemistry- and
geometry-based discriminators failed**: the compartments are genuinely amphiphile-lined (head enrichment
1.63) and genuinely water-filled (1.5-1.6x bulk). Nothing about their local structure differs from a
vesicle's. Only their topology does.

A sponge phase is a real lyotropic phase, not an artefact -- it is what this force field makes at these
concentrations. The milestone asks for a different one.

### The state of the question

| structure | exists in this model? | evidence |
|---|---|---|
| bilayer membrane | **yes** | core 1.44-1.47, emergent, many seeds |
| water-filled compartment | **yes** | 1.5-1.6x bulk water, persistent 17+ checkpoints |
| sponge phase | **yes** | percolates = True, all seeds at L <= 60 |
| **isolated closed vesicle** | **only when planted** | percolates = False, lumen 3436, stable 150 000 steps |

**FALSIFICATION, UNCHANGED AND RESTATED.** The dilute run is scored on a **non-percolating** cluster with
a lumen above the noise floor, confirmed by render. A non-percolating closed object would be a vesicle by
every test this project has. Aggregates that percolate before they enclose would mean closure here is
intrinsically a network phenomenon. Aggregates that stay small and never close would mean the dilution
preventing percolation also prevents reaching closure size -- pointing to more lipids rather than
different chemistry as the next move.

---

## 2026-08-21e tick — dilution buys geometric room at an unaffordable coarsening cost; building dense then diluting instead

### The dilute run is too slow, quantified

N = 300 at L = 120, step 120 000 of 800 000: largest **14-25 lipids**, core 1.407-1.472, lumen 0 in all
five seeds.

Largest grew from ~10 at step 40 000 to ~20 at 120 000 -- a factor of 2 over 3x the time, so
`largest ~ t^0.63`. Reaching the ~200 lipids a closed ring needs would take
`(200/20)^(1/0.63) = 39x` longer, about **4.7 million steps**. The 800 000-step budget cannot get there,
and this is a projection from measured growth rather than an impression.

**Dilution buys the geometric room for a finite closed object and charges for it in coarsening time.**

### Build dense, then dilute

The sponge phase at L = 60 already has all 300 lipids in one connected structure; its only defect is that
it percolates. Re-solvating the same lipids in a box twice as wide removes the periodic self-contact.

Verified at step 0 after the fixes below: **largest 297/300, core 1.422, lumen 579, `perc = n`** and
E/lipid **-6.15**. That is exactly the configuration the dilute run would need 4.7M steps to reach.

### Three bugs in the transplant, each caught by its own number

Building this exposed a chain of errors, none of which would have been visible from the trajectory alone:

| symptom | cause | fix |
|---|---|---|
| `state has 2521 beads, this configuration has 10084` | water count scales with box area, so a state saved at L = 60 cannot be loaded at L = 120 | transplant the LIPIDS, re-solvate |
| E/lipid **37634** | water was placed avoiding the ORIGINAL random lipids, then the transplant put lipids on top of it | re-place water after the transplant |
| E/lipid **37578 -> 29631** | saved coordinates are wrapped into the old box, so molecules whose bonds crossed the old boundary are torn by ~L_old in the new one | unwrap per molecule using the state's own L |
| still **29631** | my own recentring shifted per BEAD about the centroid, re-tearing the molecules just unwrapped | recentre rigidly, no further wrapping |

Final: **-6.15**. A physically sensible bound state, four fixes deep.

### Caveat recorded before reading anything

`perc = n` is **necessary but not sufficient**. A finite BRANCHED network is also non-percolating, and
would pass the topological test while being no more a vesicle than the sponge is. The render must show an
isolated closed shell, not a finite tangle.

**FALSIFICATION, STATED BEFORE THE QUENCH IS READ.** 5 seeds, 300 000 steps, scored on `perc`, `lumen_c`
and the render together. If the aggregate retracts into an isolated closed shell -- non-percolating, lumen
above the noise floor, render showing a single ring rather than a tangle -- that is a vesicle by every
test this project has. If it stays a finite branched tangle, non-percolation was achieved trivially by
enlarging the box and the topology test needs a shape criterion added. If it fragments into small flakes,
the sponge was held together only by the crowding of its original box and dilution destroys it.

---

## Tick: the topology test needed a shape criterion, and now has one

### What ran

The dilution quench (L=60 percolating sponge, 300 lipids transplanted and re-solvated into L=120,
chi_WW=0.50, chi_HT=-0.25, 5 seeds, 300 000 steps) reached step 75 000-90 000. **Provisional numbers,
read mid-run, not concluded:**

| seed | largest | core | lumen_c | perc |
|---|---|---|---|---|
| 0 | 300 | 1.413 | 714 | n |
| 1 | 299 | 1.402 | 166 | n |
| 2 | 300 | 1.405 | 407 | n |
| 3 | 240 | 1.421 | 380 | n |
| 4 | 289 | 1.413 | 1677 | n |

Every seed non-percolating, aggregate intact, core in the bilayer range. That excludes the third branch
of the pre-committed falsification: the sponge was not held together only by the crowding of its box.

### The render decided what the metric could not

`perc = n` in 5/5 is exactly the outcome I flagged before launch as **necessary but not sufficient**:
"a finite BRANCHED network is also non-percolating, and would pass the topological test while being no
more a vesicle than the sponge is." Looking at seed 4 (the largest lumen, 1677 cells) settles it. The
frame shows a **finite branched tangle** floating in water, not a closed shell. Non-percolation was won
trivially by enlarging the box.

### The shape criterion, and its positive control

A vesicle encloses exactly ONE region; a branched tangle encloses several. The flood-fill in
`lumen_cells()` already found every interior component and threw all but the largest away, so the new
`n_enclosed()` costs nothing extra. Both now come from one pass over `_interior_mask()`.

| structure | perc | **n_enclosed** | component sizes |
|---|---|---|---|
| planted vesicle (POSITIVE CONTROL) | n | **1** | [4014] |
| dilution quench sd0 | n | **4** | [714, 205, 151, 148] |
| dilution quench sd1 | n | **3** | [166, 67, 52] |
| dilution quench sd2 | n | **3** | [407, 96, 78] |
| sponge at L=60 | Y | **6** | [509, 247, 244, 96] |

The control passes at 1 and every tangle scores 3 or more. `lumen_cells` returns byte-identical values
after the refactor (planted vesicle: 4014 before, 4014 after); the suite passes in 265 s.

**Had I reported the 1677-cell lumen as a vesicle, it would have been one compartment out of four.**

### The energetics say the competitor is the sponge, not the open ribbon

With R(N) = N/2pi and the measured kappa = 269.5 +- 69.0 eps*sigma, lambda = +18.31 +- 7.07 eps:

    R* = pi*kappa/(2*lambda) = 23.1 sigma      N=300 gives R = 47.7 sigma

N = 300 is **twice** the closure threshold. A vesicle beats an open ribbon here by
2*lambda - pi*kappa/R = 36.6 - 17.7 = +18.9 eps. And yet the system builds a branched network. The
reason is a competitor neither number covers: **a junction network eliminates every free edge too, and
pays no long-range curvature to do it.** The contest is vesicle vs sponge, and the sponge has been
winning it in every emergent run.

### FALSIFICATION, STATED BEFORE THE RESULT IS READ

Launched: planted vesicle, N = 300, L = 120, chi_HT = -0.25, chi_WW = 0.50, kT = 0.45, 5 seeds,
100 000 steps. The solvent matched the quench arm exactly without being tuned to (8584 waters in both),
so `E_solute`/lipid is directly comparable against the 5 quench seeds at the same lipid count and box.

* **E_vesicle < E_sponge beyond the seed spread** -> the sponge is a KINETIC TRAP. Closure is
  thermodynamically preferred and the search moves to annealing and nucleation barriers.
* **E_sponge < E_vesicle beyond the seed spread** -> the sponge is the GROUND STATE at these
  parameters. No amount of sampling produces a vesicle, and the lever must be kappa or the junction
  cost, not the protocol. `bend_frac` is the knob that moves kappa.
* **The two overlap within spread** -> degenerate. Both metastable, the model has no preference, and
  the premise that a vesicle is this model's target state is itself falsified at these chi.

Reading at step 100 000, at the END, both arms. Not mid-run, and not from the planted arm's early
checkpoints, which start relaxed by construction (step 0 already reads E/lip -8.78, core 1.467,
n_enclosed 1) and would flatter the vesicle if read as a trend.

### Still in flight

* N = 300, L = 120 dispersed-start emergence runs to 800 000 steps (an EMERGENCE arm is always running).
* Dilution quench to 300 000 steps.

---

## Tick: both arms of the vesicle/sponge fork are equilibrated, and neither is read yet

### What ran

Three arms in flight. **The fork arm is deliberately NOT concluded this tick** -- the planted vesicle is
at step 20 000 of 100 000, and reading a planted structure's early checkpoints as a trend is the
specific error this log exists to prevent.

**Equilibration check (this is a methodological check on WHEN to read, not a result):**

| step | vesicle sd0 E/lip | | step | sponge sd0 E/lip |
|---|---|---|---|---|
| 0 | -8.78 | | 0 | -6.15 |
| 5 000 | -7.75 | | 15 000 | -6.62 |
| 10 000 | -7.68 | | 60 000 | -6.73 |
| 15 000 | -7.41 | | 105 000 | -6.71 |
| 20 000 | -7.49 | | 135 000 | -6.86 |

The vesicle's -8.78 at step 0 was an unthermalized plant; it relaxes UPWARD and is flat at about -7.45
from step 5 000. The sponge relaxes DOWNWARD and is flat at about -6.70 from step 15 000. Both arms sit
on their plateaus, so the step-100 000 comparison will be between two equilibrated states rather than
between a plant and a plateau. **The apparent 0.75 eps/lipid gap is recorded here as provisional and is
not being interpreted.**

### Emergence arm: coarsening is the binding constraint, not closure

The N = 300, L = 120 dispersed-start runs at step 280 000 have **largest cluster = 20-27 lipids** out of
300. The closure threshold is a contour of 2*pi*R* = 145 lipids. These aggregates are a fifth of the
size at which closure becomes energetically possible, so they are not failing to close -- they have not
yet assembled anything that COULD close.

Their energies are the surprise:

| seed | largest | E/lip | core |
|---|---|---|---|
| 70 | 27 | -6.82 | 1.422 |
| 71 | 25 | -6.58 | 1.441 |
| 72 | 24 | -6.96 | 1.434 |
| 73 | 20 | -6.63 | 1.433 |
| 74 | 25 | -6.69 | 1.448 |

A 25-lipid blob sits at -6.7 eps/lipid, indistinguishable from the 300-lipid sponge's -6.70. **There is
almost no energetic gradient driving small clusters to merge**, which explains the measured
`largest ~ t^0.63` coarsening directly: the drive is interfacial, not per-lipid, so it weakens as
clusters grow.

### Render, at 135 000

Seed 2 of the quench, the seed with the largest compartment (2431 cells). Sixty thousand steps on from
the last tick and the topology is unchanged: a branched tangle, not a shell retracting. The large dark
pocket is one compartment among several. `perc = n` in every seed, as before, and as before that fact
alone means nothing.

### FALSIFICATION, STATED BEFORE THE RESULT IS READ

If the vesicle arm does come in below the sponge at step 100 000, the sponge is a kinetic trap held
shut by junction-removal barriers. A barrier is escapable by temperature; a ground state is not. So the
anneal tests the trap hypothesis from the opposite side, and it is informative under BOTH branches of
the fork, which is why it is launched before the fork is read.

Launched: the 5 quench sponges restarted at **kT = 0.60 and kT = 0.75** (their own kT was 0.45),
100 000 steps, 5 seeds per temperature, 10 runs. Seed-to-source mapping was written to
`/tmp/anneal_mapping.txt` AT LAUNCH rather than reconstructed afterwards from render tags.

* **n_enclosed falls toward 1 at either temperature while `core` stays above 1.35** -> the sponge is an
  escapable kinetic trap, the membrane survived the anneal, and the route to an emergent vesicle is
  annealing rather than any change to chi.
* **n_enclosed stays >= 3 at both temperatures with `core` above 1.35** -> the membrane was intact and
  still would not resolve its junctions. The trap is not thermal, and a 225 eps gap that survives
  450 kT of nothing happening needs re-examination, starting with whether a perfectly planted ring is
  a fair stand-in for any reachable state.
* **`core` drops below 1.35 at both temperatures** -> the bilayer melted before the junctions moved, the
  anneal window is empty, and this test says nothing either way. Report that, do not read the
  n_enclosed values from a melted membrane.

### Still in flight

* Planted vesicle N = 300, 5 seeds, to 100 000 (the fork; read at the end).
* Dilution quench, 5 seeds, to 300 000.
* Dispersed-start emergence, 5 seeds, to 800 000 (an EMERGENCE arm is always running).
* Anneal ladder, 10 runs, to 100 000.

---

## Tick: two measurements of lambda disagree, and lambda is load-bearing for everything here

### What ran (nothing concluded from these; all mid-run)

* Planted vesicle N = 300: step 35 000-40 000 of 100 000. E/lip -7.37 to -7.63, largest 300/300,
  n_enclosed 1 in all five. Planted, mid-run, **not read as a trend**.
* Anneal ladder, step 10 000 of 100 000:

| kT | E/lip | largest | core | n_enclosed |
|---|---|---|---|---|
| 0.60 | -5.22 to -5.60 | 240-300 | 1.383-1.409 | 2, 5, 5, 5, 7 |
| 0.75 | -4.04 to -4.52 | 184-290 | 1.356-1.381 | 4, 5, 6, 6, 7 |

Early, so provisional. Two things are already visible and both are warnings rather than results: the
anneal is **roughening the membrane, not resolving its junctions** (n_enclosed unchanged from the
sponge's 3-6), and at kT = 0.75 `core` has drifted to 1.356-1.381, against the 1.35 melt floor set
before launch. The kT = 0.75 rung may fail its own control, in which case its n_enclosed values must be
discarded rather than reported.

### The contradiction

The standing plan rests on lambda = +18.31 +- 7.07 eps, from the intercept of E(N). But the direct
ring-versus-arc comparison at N = 300 measured the same quantity as **+0.5 +- 6.0 eps**:

| route | 2*lambda | implied lambda |
|---|---|---|
| E(N) intercept | 36.6 | **+18.31 +- 7.07** |
| direct ring - arc | +0.5 +- 6.0 | **+0.25 +- 3.0** |

These differ by 18 eps against a combined error of about 7.7 -- roughly **2.3 sigma apart**, and they
are measurements of the same constant. The direct route compares two states; the intercept route
extrapolates a fit. When they disagree the direct one is the one to believe, and the direct one is
**consistent with zero**.

If lambda is really about zero then R* = pi*kappa/(2*lambda) is undefined rather than 23 sigma, closure
has no edge drive at all, and the "closure has ~81 kT to gain" premise that has motivated a long run of
experiments is wrong. That would also retire the critical-size framing: there would be no threshold
ribbon length because the term that falls off with R has nothing to beat.

It would NOT contradict the vesicle-versus-sponge gap. Neither a vesicle nor a sponge has free edges, so
that comparison never depended on lambda; whatever separates them is junction cost.

### Why the old number cannot simply be adopted

The +0.5 +- 6.0 measurement was made in implicit solvent on the pre-rewrite force field. Every current
result is explicit-solvent at chi_HT = -0.25, chi_WW = 0.50. Neither existing lambda was measured under
the conditions the project now runs in, which is exactly how a load-bearing constant goes stale
unnoticed.

### FALSIFICATION, STATED BEFORE THE RESULT IS READ

Launched: planted **arc0.97**, N = 300, L = 120, kT = 0.45, chi_HT = -0.25, chi_WW = 0.50, 5 seeds,
100 000 steps -- matched in every parameter to the running ring arm, so `E_ring - E_arc = -2*lambda`
comes out as one measured difference with no fit and no extrapolation.

The matching is verified, not assumed: both arms built **8584 waters**, and both start at **exactly
-8.78 eps/lipid at step 0**. Identical step-0 energy means the two plants carry the same internal
strain, so a difference at step 100 000 is the closure term rather than a planting artifact.

* **E_ring - E_arc close to -36.6 eps** -> the intercept lambda stands, edges are expensive, closure
  has a real drive and its failure is kinetic.
* **E_ring - E_arc consistent with 0 across 5 seeds** -> **lambda is retracted to ~0 for the current
  model.** R* becomes undefined, the critical-size plan is withdrawn, and the only remaining candidate
  drive is junction cost, measured by the vesicle/sponge arm.
* **E_ring > E_arc** -> negative line tension: open edges are FAVOURED, which would make ribbons the
  preferred state and would explain the arcs' fourfold opening directly. Report it rather than
  explaining it away.

Reading both arms at step 100 000, at the end.

### Still in flight

* Ring arm and arc arm, N = 300, 5 seeds each (the lambda measurement).
* Anneal ladder, 10 runs.
* Dilution quench, 5 seeds, to 300 000.
* Dispersed-start emergence, 5 seeds, to 800 000 (an EMERGENCE arm is always running).

---

## Tick: a false alarm about the detector, and a real limit on what it can report

### The alarm

Planted ring sd0 showed `lumen_c` flickering 25036 -> 0 -> 24769 -> 0 -> 0 -> 0 over 25 000 steps while
`largest` stayed 300 and `core` stayed 1.44-1.45. An intact ring cannot lose and regain a 25 000-cell
lumen in 5 000 steps, so this looked like the detector leaking.

### RETRACTED: my diagnosis of it

I attributed the leak to in-leaflet bead spacing of 1.8 sigma, computed as circumference/lipids-per-
leaflet = 270/150. **That arithmetic conflated lipids with beads and is wrong.** The measured median
nearest-neighbour distance in these states is **0.95 sigma**. Four of the five ring seeds read
n_enclosed = 1 at the ORIGINAL dilation; only sd0 does not, and sd0 needs bead = 4.0 to close, which is
past the point where a genuine 4-sigma opening gets sealed into a false lumen.

So sd0 most likely has a **real transient pore**, and the flicker is physics. The detector was not at
fault, and the default is left at 1.0 -- raising it would have changed every historical `lumen_c` to fix
a problem that does not exist at this density.

### What the sweep DID establish, which is a real limit

The dilation knob was swept on the actual states:

| state | nenc @ bead 1.0 / 1.5 / 2.0 / 3.0 | call |
|---|---|---|
| planted ring sd1-sd4 | [1, 1, 1, 1] | VESICLE |
| planted ring sd0 | [0, 0, 0, 0] | genuinely open |
| quench sd0 | [5, 4, 4, 3] | TANGLE |
| quench sd1 | [4, 2, 2, 2] | TANGLE |
| quench sd2 | [5, 5, 5, 3] | TANGLE |
| quench sd3 | [8, 6, 6, 4] | TANGLE |
| quench sd4 | [5, 3, 3, 3] | TANGLE |

**The COUNT is not a measurement.** It moves by a factor of two with the dilation knob as thin necks
seal and unseal. The 1-versus-many CALL never flips anywhere in that range. From here only the call is
reportable, and the count is an ordinal. The gate was rewritten to assert the call across
bead 1.0-3.0 rather than to assert a number, and the over-seal control (a 4-sigma opening must read 0)
is kept.

Synthetic calibration, for the record -- ring must read 1, a real gap must read 0:

    bead   1.0s 1.4s 1.8s 2.2s | 4s gap  6s gap
    1.0      1    0    0    0  |   0       0
    2.0      1    1    1    0  |   0       0
    3.0      1    1    1    1  |   0       0
    3.5      1    1    1    1  |   1       0   <- invents lumens

### The anneal is failing its own control

At step 45 000-50 000 of 100 000, provisional:

| kT | largest | core | n_enclosed |
|---|---|---|---|
| 0.60 | 228-300 | 1.382-1.395 | 5, 1, 4, 7, 3 |
| 0.75 | 109-252 | 1.354-1.391 | 1, 4, 4, 7, 1 |

The seeds reading n_enclosed = 1 are the ones that FRAGMENTED (kT 0.75 sd0 at largest 156, sd4 at 114).
That is not annealing to a vesicle, it is falling apart into a piece that happens to enclose something,
and it is exactly why a `largest` guard has to accompany any n_enclosed = 1 claim. Nothing here is a
vesicle. `core` at kT = 0.75 has reached 1.354 against the 1.35 floor set before launch, so that rung is
on the edge of failing its melt control outright.

### FALSIFICATION, STATED BEFORE THE RUN

Coarsening, not closure, is the binding constraint on emergence: dispersed runs stall at 20-27 lipids
against a ~145-lipid closure threshold. Every previous emergence attempt was either dense enough to
coarsen but too small to hold a vesicle (L = 60), or roomy enough for one but too dilute to coarsen
(L = 120).

Launched: **N = 160, L = 65, dispersed start, kT = 0.45, 5 seeds, 800 000 steps.** The size is chosen so
both constraints are satisfiable at once -- a vesicle of R = 160/2pi = 25.5 sigma has diameter 51 sigma
and fits inside 65, while the lipid area fraction 160/65^2 = 0.038 is 1.8x denser than the L = 120 runs
that stalled. N = 160 also sits just above the ~145-lipid threshold, so one loop consumes nearly all the
material and little is left over to branch with.

* **Largest reaches >= 145 lipids AND n_enclosed = 1 across bead 1.0-3.0** -> an emergent vesicle, the
  first in this project, and the material-excess explanation for the sponge is confirmed.
* **Largest reaches >= 145 but the call is TANGLE** -> branching is not driven by surplus material, and
  the sponge is what this force field builds at any size.
* **Largest stays < 145 after 800 000 steps** -> coarsening is the binding constraint at every density
  where a vesicle can fit, and emergent closure is out of reach for this model without a nucleation aid.

### Still in flight

Ring and arc arms (the lambda measurement, read at 100 000), anneal ladder, dilution quench,
the N = 300 dispersed emergence at 320 000, and the new N = 160 emergence.

### Verification, reported honestly

The full bazel suite **TIMED OUT at 900.2 s** and is recorded as a failure by bazel. It is not a real
failure: the suite normally runs in 265-414 s, and the machine is currently carrying 44 simulation
processes on 32 cores. It is also not a pass, and is not reported as one. The six `n_enclosed` gates
were run directly instead and pass in under a second: `6 passed`.

One of them failed first, and the failure was mine, not the metric's -- the synthetic theta's crossbar
was built at 2.1 sigma spacing, which leaks at bead 1.0 and made a theta read as a plain ring. Rebuilt
at the measured 0.95 sigma membrane density it passes at every dilation. The test caught exactly the
sparse-structure sensitivity documented above, in a shape I had built carelessly.

The full suite must be re-run under lower load before this is treated as green.

---

## Tick: lambda is drifting upward because the arc has not finished opening

### The measurement, at matched steps

Ring and arc arms compared seed-for-seed at the SAME step, 5 seeds each, both past equilibration:

| step | ring mean | arc mean | E_ring - E_arc | sem | implied 2*lambda |
|---|---|---|---|---|---|
| 35 000 | -7.506 | -7.512 | +0.006 | 0.062 | -1.8 eps |
| 40 000 | -7.488 | -7.506 | +0.018 | 0.053 | -5.4 eps |
| 45 000 | -7.542 | -7.480 | -0.062 | 0.054 | +18.6 eps |
| 50 000 | -7.556 | -7.474 | -0.082 | 0.043 | +24.6 eps |

At step 50 000 this reads **lambda = +12.3 +- 6.4 eps, 1.9 sigma from zero**.

**It is not converged, and the direction of the drift explains a great deal.** The ring's energy is flat;
the ARC's is climbing steadily (-7.512 -> -7.474) and its R_mid is climbing with it
(44.30 -> 44.70 -> 45.07 -> 45.43 -> 45.46). The arc is still opening. `E_ring - E_arc` equals -2*lambda
only once the ends are fully separated, so **an arc read too early reports lambda too low** -- and at
step 35 000 this very measurement would have reported lambda = -0.9, i.e. "isoenergetic".

That is almost certainly what the earlier **+0.5 +- 6.0 eps** ring-versus-arc result was: an
under-converged arc, not evidence that lambda is zero. The 2.3 sigma contradiction flagged last tick is
therefore probably not a contradiction at all, but the same measurement stopped at different times. The
intercept value +18.31 +- 7.07 and the still-rising +12.3 +- 6.4 are consistent with each other.

**This is not yet a retraction of the retraction.** The arc must be shown to stop opening before any
number is final.

### A dead end, recorded

An independent lambda route was attempted and abandoned: a flat ribbon with two ends versus a periodic
end-free ribbon, which has zero curvature in both arms and so no opening transient at all. It does not
work here. The `flat` plant refused outright, with a guard already written for this mistake -- "flat
ribbon of 120 lipids is 123.0 wide and would span a box of L=60.0: it would have no ends... Need
L > 154" -- and `span` ran but wrapped the 123-wide ribbon twice through the 60 box and self-overlapped,
`min non-bonded r 0.000`, E/lip **+55.49**. Matching N to L for the spanning arm forces a DIFFERENT box
for the ended arm, which destroys the matched comparison that made the idea attractive. Ring-versus-arc
at fixed N and L remains the better measurement; its only defect is that it needs time.

### RETRACTED: my worry that the new box was cavitating

The N = 160, L = 65 render shows large black patches in the solvent and I suspected the water had
fragmented, which the known-void makes a live risk. Measured instead of eyeballed:

| run | rho_water | max void | p99 void |
|---|---|---|---|
| N = 160, L = 65 (new) | 0.511 | 5.0 sigma | 3.0 sigma |
| N = 300, L = 120 (quench) | 0.596 | 7.0 sigma | 4.0 sigma |
| N = 300, L = 120 (ring) | 0.596 | 6.0 sigma | 4.0 sigma |

The new box has SMALLER voids than the runs already accepted. The patches are a dot-size artifact of
rendering a smaller box at the same pixel scale. **The solvent is fine and the concern is withdrawn.**

### Emergence, N = 160 L = 65, step 40 000-80 000

largest 20-31 of 160, core 1.374-1.456, roughly twenty micellar blobs, no bilayer ribbon, nothing near
the ~145-lipid threshold. Too early to judge against its 800 000-step falsification.

### FALSIFICATION, STATED BEFORE THE RUN

Launched: **arc0.97, N = 300, L = 120, 5 fresh seeds, 300 000 steps** -- three times the current arm, so
the opening saturates instead of being cut off mid-flight. The ring's energy is flat from step 5 000 and
needs no extension.

* **R_mid plateaus and `E_ring - E_arc` settles near -36.6 eps** -> lambda = +18.31 stands, the earlier
  +0.5 was an under-converged arc, and the contradiction is resolved in favour of the intercept.
* **R_mid plateaus and the difference settles near 0** -> lambda really is ~0, the drift seen here was
  transient, and the critical-size plan is withdrawn.
* **R_mid never plateaus within 300 000 steps** -> the arc does not have a converged open state at this
  size, `E_ring - E_arc` is not a measurement of lambda at all, and BOTH existing values must be
  discarded rather than averaged.

### Still in flight

Ring (95 000/100 000), short arc (50 000/100 000), long arc (fresh), anneal ladder (70 000/100 000),
dilution quench (210 000/300 000), N = 300 dispersed emergence (360 000/800 000), N = 160 dispersed
emergence (80 000/800 000).

---

## Tick: the fork is resolved. The vesicle is the ground state by 583 kT and heat cannot reach it.

### THE FORK, both arms equilibrated and read at the end

N = 300, L = 120, 8584 waters, chi_HT = -0.25, chi_WW = 0.50, kT = 0.45, 5 seeds each:

| arm | E_solute/lipid | seeds |
|---|---|---|
| VESICLE (planted, step 100 000) | **-7.572 +- 0.046** | -7.59 -7.48 -7.55 -7.50 -7.74 |
| SPONGE (emergent, step 240 000) | **-6.698 +- 0.034** | -6.77 -6.71 -6.77 -6.60 -6.64 |

    sponge - vesicle = +0.874 +- 0.058 eps/lipid = +262 +- 17 eps total = +583 kT   (15.2 sigma)

The vesicle arm held 300/300 lipids with core 1.440-1.448 in every seed. **The sponge is not the ground
state; it is a kinetic trap, and a deep one.** This is the first branch of the fork stated three ticks
ago, and it is not marginal.

### The anneal, concluded: the trap is NOT thermal

Pre-registered criterion: n_enclosed falling toward 1 while core stays above 1.35 means an escapable
trap. At step 100 000:

| kT | E/lip | largest | core | n_enclosed | seeds at 1 | melt control |
|---|---|---|---|---|---|---|
| 0.60 | -5.54 | 193-285 | 1.382-1.398 | 2, 2, 3, 3, 9 | **0/5** | passed 5/5 |
| 0.75 | -4.49 | 95-233 | 1.355-1.389 | 0, 2, 2, 4, 5 | **0/5** | passed 5/5 |

**The membrane survived and the junctions still did not resolve.** The melt control passed at both
temperatures, so this is not a case of the test window being empty. Instead the aggregate FRAGMENTED --
1/5 intact at kT = 0.60, 0/5 at kT = 0.75, against 300/300 before heating.

The physical statement: **the barrier to resolving a junction is higher than the barrier to tearing the
aggregate apart.** Heat destroys the sponge before it anneals it. Raising temperature is therefore
excluded as a route, and this closes the second branch of the anneal falsification exactly as written.

### Emergence, N = 160 L = 65, step 200 000

largest 38-66 of 160 (against 20-27 at step 280 000 in the L = 120 box), core 1.417-1.446. The render
shows the round micelles of step 40 000 have coarsened into **elongated bilayer ribbons**, one curved
into a horseshoe. Ribbons are the object that can close, and the dilute box never produced them. Still
short of the ~145-lipid threshold, and `largest ~ t^0.63` projects only about 120 by the 800 000-step
end, so this run is likely to fall just short of its own criterion.

### FALSIFICATION, STATED BEFORE THE RUN

With the vesicle established as the ground state and heat excluded as a way to reach it, the barrier has
to be LOWERED rather than climbed. The remaining lever is kappa: the sponge survives because a junction
network eliminates free edges without paying long-range curvature, so making curvature cheap should
remove its advantage. Predicted threshold radius R* = pi*kappa/(2*lambda) falls from 23 sigma at
kappa = 269.5 to about 5.7 sigma at a quarter of that, far below these aggregates' R_mid of ~22.

`VIVARIUM_BEND` was added to scale the 1-3 spring that sets chain stiffness. `_env_tag()` enumerates
every `VIVARIUM_*` variable, so the arms tag themselves apart automatically -- verified on disk as
`..._bend0.25_...` and `..._bend0.50_...` rather than assumed.

Launched: the 5 quench sponges restarted at **bend_frac 0.25 and 0.50** against the default 1.0,
kT = 0.45, 150 000 steps, 5 seeds per rung, 10 runs. Seed-to-source mapping written at launch to
`/tmp/bend_mapping.txt`. All ten start from n_enclosed = 6, largest 300, core 1.420.

* **The call becomes VESICLE (n_enclosed = 1 across bead 1.0-3.0) with largest >= 285 and core > 1.35 in
  >= 3/5 seeds at either rung** -> kappa is the controlling variable, the sponge is a stiffness artifact,
  and the route to an emergent vesicle is a softer chain.
* **The call stays TANGLE at both rungs with the membrane intact** -> kappa is not the lever either.
  Neither temperature nor bending cost dissolves the junction network, and what needs measuring next is
  the junction energy itself rather than another global parameter.
* **`core` collapses below 1.35 or `largest` falls below 285** -> softening destroyed the bilayer instead
  of unbending it, the rung says nothing about closure, and its n_enclosed values must be discarded --
  the same trap the anneal fell into, where the seeds reading 1 were the fragmented ones.

### Still in flight

Short arc (85 000/100 000), long arc (30 000/300 000, for the lambda convergence question),
dilution quench (240 000/300 000), N = 300 dispersed emergence, N = 160 dispersed emergence
(200 000/800 000), and the two bend rungs.

---

## Tick: lambda is ~0, and the reason is one hardcoded number

### RETRACTED: lambda = +18.31 +- 7.07 eps, and the "81 kT to gain" premise

The ring and arc arms both reached step 100 000. At the pre-registered read:

| analysis | ring | arc | diff | lambda |
|---|---|---|---|---|
| all 5 seeds, final checkpoint | -7.572 | -7.578 | +0.006 +- 0.067 | **-0.9 +- 10.0 eps** (0.1 sigma) |
| intact arcs only (4/5) | -7.572 | -7.560 | -0.012 +- 0.074 | +1.8 +- 11.1 eps (0.2 sigma) |
| **time-averaged over plateau (step >= 20 000, 17 checkpoints/seed)** | -7.5018 +- 0.0063 | -7.4831 +- 0.0177 | | **+2.8 +- 2.8 eps** (1.0 sigma) |

Time-averaging cost nothing and cut the error bar 3.5x, from +-10.0 to +-2.8. The result is
**lambda = +2.8 +- 2.8 eps: consistent with zero, and 2.0 sigma from the intercept's +18.31 +- 7.07.**

Closure therefore gains 2*lambda = 5.6 eps = **12 kT, not 81 kT.** The standing figure was too large by
about 6.5x. The arcs fragmented in several seeds (min largest 126-249) and fragmentation ADDS ends,
which biases lambda upward, so +2.8 is if anything generous.

### RETRACTED: last tick's explanation of the drift

Last tick I read `E_ring - E_arc` moving +0.006, +0.018, -0.062, -0.082 across steps 35 000-50 000 as the
arc still opening, and said the two lambda routes were "the same measurement stopped at different
times." **That was a four-point drift read as a trend.** R_mid does not rise monotonically -- per seed it
runs 45.08, 44.99, 44.88, 38.30 and 43.89, 42.83, 54.14, 43.75 -- it fluctuates. The swing was noise
against a +-0.04-0.07 error bar. The reconciliation I offered was wrong; the disagreement is real, and it
resolves against the intercept, not in its favour.

### The mechanism, found in the source

    chi[TAIL, WATER] = chi[WATER, TAIL] = 0.00   # tails gain nothing from water

This is the term that prices a bilayer edge, and it was the only chi with no override. At 0.00 a tail is
**indifferent** to water: it neither gains nor loses by sitting on an exposed rim. With no cost to an
exposed edge there is no drive to close one -- which is why every arc in this project has unrolled, at
every size from R = 11.5 to 65.6, across roughly 60 runs.

### Everything measured now fits one picture, with no contradiction

| observation | explanation |
|---|---|
| arcs always unroll, at every size | lambda ~ 0: closing gains nothing |
| vesicle sits 262 +- 17 eps below the sponge | junction cost -- neither state has edges, so lambda is irrelevant to it |
| heat fragments before it anneals | junction barrier exceeds cohesion barrier |
| emergent aggregates are sponges | ribbons fuse into junctions kinetically and cannot undo it |

lambda ~ 0 does NOT contradict the fork result. The vesicle's advantage was never edge elimination.

### Emergence, N = 160 L = 65: coarsening has plateaued

largest by step: 23, 26, 40, 56 at 160 000, then **56, 56, 56** through 280 000. Not frozen -- it grew,
then stopped. Ribbons have ceased merging at about a third of the ~145-lipid threshold. Provisional
against its 800 000-step criterion, but the third branch looks likely to fire.

### PRE-REGISTERED PREDICTION for the bend rungs, before they are read

With lambda = +2.8, closure needs `kappa < 2*lambda*R/pi` = 2(2.8)(22)/pi = **39 eps*sigma**. If kappa
scales with the 1-3 spring, bend_frac 0.25 gives kappa ~ 67 and 0.50 gives ~135, both still above 39.
**Both rungs are therefore predicted to FAIL to close**, and closing would need bend_frac <~ 0.15. At
step 15 000 of 150 000 they sit at n_enclosed 4-7, largest 240-300, core 1.400-1.420 -- membrane intact,
no retraction. If either rung DOES close, the kappa-scaling assumption behind this prediction is wrong
and should be measured rather than assumed.

### FALSIFICATION, STATED BEFORE THE RUN

`VIVARIUM_CHI_TW` added. Launched: ring and arc0.97, N = 300, L = 120, 5 seeds each, 100 000 steps, at
**chi_TW = -0.50** (negative is repulsive here), everything else matched to the arms just read. lambda is
extracted by the same time-averaged ring-minus-arc assay, now good to +-2.8 eps. Arms tag apart on disk
as `..._tw-0.50_...`, verified rather than assumed.

* **lambda rises above the old value by more than the combined error** -> tail-water contact is what
  prices an edge, the model's edges were free by construction, and raising this term is the route to a
  closure drive.
* **lambda stays consistent with zero** -> edge cost is not set by tail-water contact and the reason
  edges are free lies elsewhere; the assay is precise enough now that this would be a real null.
* **core falls below 1.35 or largest below 285** -> -0.50 is too strong to test at, the bilayer is
  damaged rather than re-priced, and the rung must be discarded rather than read.

### Still in flight

Long arc (45 000/300 000), bend rungs 0.25 and 0.50 (15 000/150 000), chi_TW ring and arc arms,
dilution quench (270 000/300 000), N = 300 and N = 160 dispersed emergence.

---

## Tick: a free shortcut that turned out to be underpowered, and a careless kill

### The static assay: validated, then found too blunt

Existing equilibrated ring and arc states were re-priced under two chi matrices with no dynamics at all.
The method validates cleanly against the runs it is meant to predict:

| | ring | arc | lambda |
|---|---|---|---|
| static, chi_TW = 0.00 | -7.5717 +- 0.0465 | -7.5786 +- 0.0480 | **-1.0 +- 10.0 eps** |
| dynamic, same states, final checkpoint | -7.572 | -7.578 | -0.9 +- 10.0 eps |

Agreement to 0.1 eps. The static route is sound.

Then the paired test -- same configurations priced under both matrices, so bulk noise should cancel:

| seed | 2*lambda @ tw=0 | 2*lambda @ tw=-0.50 | change |
|---|---|---|---|
| 0 | -16.8 | -25.6 | -8.8 |
| 1 | -49.4 | -29.2 | +20.3 |
| 2 | +7.1 | -25.1 | -32.2 |
| 3 | +24.8 | -5.6 | -30.4 |
| 4 | +23.9 | +90.3 | +66.4 |

    change in 2*lambda = +3.07 +- 18.46 eps

**Pairing did not help; it made the error bar worse.** Ring and arc are different configurations, so
nothing cancels, and the per-seed 2*lambda values scatter over 140 eps. The quantity being measured is
two lipid-ends' worth of energy buried in a 300-lipid aggregate.

**This is an UNDERPOWERED test, not a null.** Detecting the effect sought needs about +31 eps in
2*lambda and the error bar is +-18. Reading "0.2 sigma, therefore chi_TW does nothing" off this table
would be wrong, and it is not being read that way. What supplies power is time-averaging over the
plateau, which cut the dynamic error bar from +-10.0 to +-2.8; the running chi_TW arms will have that
and this static shortcut cannot.

### Launched: measure lambda where the edge is a larger fraction

The N = 300 assay is noise-limited by construction -- 2*lambda is about 1.6% of the total energy, so
configuration scatter swamps it. Halving N does not change lambda but scales the bulk noise with N.

Launched: ring and arc0.97 at **N = 80, L = 60**, 5 seeds each, 100 000 steps, everything else matched.
At N = 80 the same 2*lambda is roughly 6% of the total, a 3.75x better signal-to-noise before any
time-averaging.

* **lambda at N = 80 comes out tight and near zero** -> confirms the N = 300 result at much better
  precision and the +18.31 intercept is retired for good.
* **lambda at N = 80 comes out near +18** -> the N = 300 measurement was biased rather than merely
  noisy, most likely by the arc fragmentation seen there (min largest 126-249), and the retraction of
  the intercept value must itself be retracted.
* **The N = 80 ring fails to hold (largest < 76 or core < 1.35)** -> a ring this small is not metastable
  and the assay says nothing; report that rather than the number.

### Emergence: a correction, and a hypothesis weakened

Last tick I wrote that N = 160 coarsening had "plateaued", from seed 2 sitting at 56 for 120 000 steps.
**That generalized one seed.** Seed 3 has since grown 66 -> 78. Coarsening here is slow and
non-monotonic (seed 4 went 47 -> 40), not stalled.

More important, seed 3's 78-lipid aggregate reads n_enclosed = 2 and the render shows a Y-shaped
BRANCHED assembly. **Branching is present at 78 lipids, roughly half the closure threshold.** The
hypothesis that the sponge topology comes from surplus material -- that N = 160 would leave nothing
spare to branch with -- is weakened by its own run. Junctions appear as soon as ribbons meet.

### A careless kill, reported

Retiring the arclong arm, whose question was already answered, I matched on
`_mixture.py 300000 2 300` -- a prefix the **dilution quench shares**, differing only in the plant
argument. Fifteen processes matched where five were intended, and all five quench runs died at
270 000-285 000 of 300 000.

The loss is real but bounded: that arm's structural result was concluded several ticks ago (branched
tangle, perc = n, n_enclosed 2-5) and its contribution to the fork was the step-240 000 sponge energy
-6.698 +- 0.034, which is unaffected. States are on disk at 270 000, so it is restartable if ever
needed. A kill pattern has to be anchored on the DISTINGUISHING argument, not a shared prefix.

### Still in flight

chi_TW ring and arc (10 000/100 000), bend rungs 0.25 and 0.50 (22 500-30 000/150 000), N = 80 lambda
assay (fresh), N = 160 and N = 300 dispersed emergence.

---

## Tick: the first closure this project has produced, from an assay that failed

### The N = 80 assay is VOID, and why

It was launched to measure lambda where the edge is a larger fraction of the total. It cannot, because
**the arc closed.**

| step | n_enclosed | lumen | R_mid |
|---|---|---|---|
| 0 | 0 | 0 | 13.47 |
| 5 000 | 1 | 1637 | 13.99 |
| 50 000 | 1 | ~1410 | 13.4 |
| 100 000 | 1 | ~1400 | 13.2 |

`n_enclosed = 0` at step 0 confirms the 2.4 sigma gap WAS resolvable, so this is a real transition and
not the detector failing to see a gap it never could. The render at step 100 000 shows a closed ring
with a water-filled lumen. **5/5 seeds closed by step 5 000 and held for the remaining 95 000 steps.**

The time-averaged numbers are ring -7.3467 +- 0.0628 against arc -7.3880 +- 0.0205, giving an apparent
lambda = -1.7 +- 2.6 eps. **That number is void**: both arms are rings, so it measures ring minus ring.
The pre-registered branch about the ring failing to hold did not fire; an outcome I had not anticipated
did.

### What the failure found instead

| N | R | planted end-gap | outcome |
|---|---|---|---|
| 80 | 12.7 | **2.4 sigma** | **closed 5/5, stable 95 000 steps** |
| 300 | 47.7 | 8.4 sigma | never closed, ~60 runs |

Closure looks **ENCOUNTER-LIMITED, not energy-limited.** Once the ends are within contact range they
fuse, and the fused state is stable for as long as it has been watched. Beyond contact range nothing
brings them together -- which is exactly what lambda ~ 0 means: no long-range drive across a gap.

This also reframes every previous closure failure. They were not the membrane refusing to bend. Every
one of them started with ends far apart, and nothing in this force field pulls distant ends together.

**It cuts against the standing plan.** That plan predicts closure gets EASIER with size, because
bending paid, pi*kappa/R, falls while edge saved, 2*lambda, is constant. The observation is the
reverse: the SMALL arc closed and the large ones did not. But size and gap are confounded here -- the
same span plants a smaller gap at smaller R -- so this is not yet a clean falsification, which is what
the next run is for.

### FALSIFICATION, STATED BEFORE THE RUN

Launched: **arc0.99 and arc0.98 at fixed N = 300**, 5 seeds each, 100 000 steps, everything else matched
to the arc0.97 arm already run. Holding N fixed removes the size confound and varies only the gap:

    span 0.99 -> 3.0 sigma      span 0.98 -> 6.0 sigma      span 0.97 -> 9.0 sigma (never closed)

Both new arms confirmed `n_enclosed = 0` at step 0, so both gaps are resolvable.

* **arc0.99 closes and arc0.98 does not** -> a capture radius of a few sigma, closure is encounter-
  limited, and the size effect seen at N = 80 was the gap all along.
* **Both close** -> the capture radius is at least 6 sigma and the N = 300 arc0.97 failure sits just
  beyond it; the picture holds with a wider radius.
* **Neither closes** -> gap is NOT the controlling variable at N = 300 and size genuinely matters, which
  supports the continuum picture and means the N = 80 closure has some other cause. The encounter-
  limited reading would then be withdrawn.

### Emergence: the largest aggregate yet

N = 160, L = 65, seed 0 reached **largest = 118** at step 400 000, up from 52 at 320 000 -- 81% of the
~145-lipid threshold and by far the biggest this project has assembled from a dispersed start. It is an
open BRANCHED ribbon, n_enclosed = 0, with its ends far apart, which is precisely what the encounter-
limited picture says will not close.

### The bend rungs, still consistent with the prediction

At 45 000-52 500 of 150 000: n_enclosed 4-9, largest 217-300, core 1.406-1.419. No retraction toward a
single compartment, as predicted before they were read.

### Still in flight

chi_TW ring and arc (35 000-40 000/100 000), bend rungs, gap scan, N = 160 and N = 300 emergence.

---

## Tick: closure happens at every gap; "never closed" was wrong

### RETRACTED: "N = 300 arc0.97 never closed, ~60 runs"

Written last tick, and wrong. Two of the five N = 300 arc0.97 seeds closed, at steps 60 000 and 90 000,
with lumens of 27 596 and 27 642 -- essentially the whole interior of an R = 44 ring. **The data was in
the output I was reading when I wrote the claim.** I had the nenc column in front of me showing sd2 = 1
and sd3 = 1 and described the arm as never closing.

### The gap scan, at fixed N = 300

Closure time per seed, first step at which n_enclosed = 1:

| arm | gap | closed by 10 000 | closed by 100 000 | closure steps |
|---|---|---|---|---|
| N = 80 arc0.97 | 2.4 sigma | **5/5** | 5/5 | all at 5 000 |
| N = 300 arc0.99 | 3.0 sigma | 3/5 | still running | 5 000, 5 000, 5 000 |
| N = 300 arc0.98 | 6.0 sigma | 1/5 | still running | 10 000 |
| N = 300 arc0.97 | 9.0 sigma | 0/5 | **2/5** | 60 000, 90 000 |

The rate falls monotonically with gap, and **there is no hard capture radius**: even a 9 sigma gap
closes given enough time. The pre-registered second branch fires -- "both close, the capture radius is
at least 6 sigma" -- not the first.

Corrected reading: closure is a **thermally activated encounter process**. Its rate falls steeply with
initial gap, but it is never forbidden. Last tick's phrasing, "beyond contact range nothing brings them
together", is withdrawn; they do come together, slowly.

This is more encouraging than the version it replaces. Closure at N = 300 is achievable, not blocked.

### A false positive, caught by its own gate

em160 seed 3 reached n_enclosed = 1 at largest = 78 -- a single-compartment EMERGENT enclosure, which
would be the first candidate vesicle this project has produced from a dispersed start. **It is not one.**

    bead 1.0: n_enclosed = 1, sizes [69]
    bead 1.5: n_enclosed = 0
    bead 2.0: n_enclosed = 0
    bead 3.0: n_enclosed = 0

The call is UNSTABLE across the dilation knob, which by the rule set several ticks ago disqualifies it.
The pocket is 69 cells against 4014 for a real planted vesicle, and the render shows it is the gap
between the branches of a Y-shaped assembly. It vanishes as soon as beads are dilated, because a pocket
that small is filled in by the dilation itself.

**Reporting the driver's raw nenc column would have announced an emergent vesicle.** This is exactly
what the robustness rule was written for, and it is the first time it has actually caught something.

### FALSIFICATION, STATED BEFORE THE RUN

Every arc in this project was HANDED its curvature. Emergent ribbons are flat. So the question the arc
results cannot answer is whether this model curls a flat bilayer at all -- and `_plant_flat_ribbon`
exists for precisely that, per its own comment: "planting FLAT hands it a single aggregate with no
curvature at all, so whether it curls is the closure question asked cleanly."

Launched: **flat ribbon, N = 80, L = 110**, 5 seeds, 200 000 steps. N = 80 is the size where a handed arc
closed 5/5, so a failure here isolates curling from encounter. L = 110 satisfies the plant's own guard
(a ribbon of 80 lipids is ~82 wide and needs L > ~103, or it spans the box and has no ends at all).
Confirmed at step 0: n_enclosed = 0, largest 80, core 1.467, 8073 waters.

* **The ribbon curls and closes in >= 1/5 seeds** -> curling is spontaneous, and emergent closure is a
  matter of time and of avoiding branches, not of a missing force.
* **It stays open in 5/5 while the same N closed 5/5 from an arc** -> the arc results depend entirely on
  being handed curvature. A flat emergent ribbon will never close, and the blocker is curling rather
  than encounter.
* **It fragments (largest < 76) or core < 1.35** -> the plant is unstable at this box size and the run
  says nothing either way.

### Still in flight

chi_TW ring and arc, bend rungs 0.25/0.50, gap scan 0.99 and 0.98 to 100 000, flat-ribbon curling test,
N = 160 emergence (480 000-520 000/800 000, largest 118 in seed 0).

---

## Tick: a branching metric built and discarded on its own control

### The gap scan, sharpening

At step 20 000 (still running to 100 000):

| arm | gap | closed |
|---|---|---|
| N = 300 arc0.99 | 3.0 sigma | **4/5** |
| N = 300 arc0.98 | 6.0 sigma | 1/5 |
| N = 300 arc0.97 | 9.0 sigma | 2/5 by step 100 000 |

The monotonic dependence of closure rate on gap holds and is strengthening.

### DISCARDED: a tip-counting metric for branching

With closure now known to be achievable at N = 300, the obvious blocker for emergence is that emergent
aggregates are BRANCHED -- a branched network has many ends rather than two, so there is no single pair
to bring together. I built a tip counter to quantify that on saved states, for free.

It looked convincing:

| state | nlip | tips |
|---|---|---|
| em160 sd0 | 129 | 56 |
| em160 sd1 | 52 | 26 |
| em160 sd3 | 78 | 38 |

correlation(size, tips) = **+0.99**.

**Then the positive control killed it.** A closed ring must read ~0 tips:

    N=80 arc, CLOSED        nlip= 80  tips= 25
    N=300 planted ring      nlip=300  tips=134

Tips/lipid is 0.31-0.45 for closed rings against 0.43-0.50 for the branched emergent aggregates -- the
same ratio. **The detector measures boundary roughness, not branch points**, and the +0.99 correlation
is perimeter scaling, nothing more. Discarded before it was reported as a finding. Branching remains
unquantified; the claim that it is the blocker is so far only visual.

### A design cost error, recorded

The flat-ribbon curling test is running far slower than intended. The flat plant needs L > ~103 at
N = 80 purely so the ribbon has ends rather than spanning the box -- but that box then holds **8073
waters for 80 lipids**, roughly 4x the per-step cost of the N = 80 arc runs at L = 60, where 1921 waters
sufficed. Four of five seeds had not reached their first checkpoint after twelve minutes. CPU time
confirms they are running, not wedged (7-8.5 minutes each), and 200 000 steps projects to about five
hours.

Retired to make room: the N = 300, L = 120 dispersed arm, which had answered its question -- it stalls at
27-36 lipids of 300 and is superseded by the N = 160 box. The kill pattern was **counted before it was
used** (5 matches, 0 of them em160), after last tick's pattern destroyed the dilution quench.

### FALSIFICATION, STATED BEFORE THE RUN

Launched a second curling arm in **implicit solvent**: flat ribbon, N = 80, L = 110, phi = 0.0, 5 seeds,
200 000 steps. With no water the pair cost collapses, so this answers the curling question far sooner
than the explicit arm. Implicit solvent is a known-good regime here -- it holds a planted vesicle at
120/120 with a ~1900-cell lumen where explicit solvent originally destroyed one.

* **The flat ribbon curls and closes in >= 1/5 seeds, in either arm** -> curling is spontaneous, and the
  emergence blocker is branching and time, not a missing force.
* **It stays open in 5/5 in BOTH arms, while an N = 80 arc closed 5/5** -> closure in this model requires
  being handed curvature, and a flat emergent ribbon will never close.
* **The two arms disagree** -> curling depends on the solvent treatment, which would be a result in its
  own right and would mean no implicit-solvent closure claim transfers to the explicit runs.

### Emergence: a new high

N = 160 seed 0 reached **largest = 129** at step 520 000, up from 118 last tick and 52 at step 320 000 --
89% of the ~145-lipid threshold, and the largest aggregate this project has assembled from a dispersed
start. Open, branched, n_enclosed = 0, perc = n.

### Still in flight

chi_TW arms (55 000-60 000/100 000), bend rungs (67 500-75 000/150 000), gap scan to 100 000, explicit
and implicit flat-ribbon curling tests, N = 160 emergence.

---

## Tick: the model does not curl a flat bilayer, and the metric said otherwise

### The implicit flat-ribbon test, complete at 200 000

| seed | largest | core | R_mid (step 0 -> 200 000) | n_enclosed |
|---|---|---|---|---|
| 0 | 80 | 1.464 | 27.52 -> 18.65 | 0 |
| 1 | 80 | 1.473 | 27.53 -> 17.96 | 0 |
| 2 | 80 | 1.474 | 27.52 -> 18.17 | 0 |
| 3 | 80 | 1.483 | 27.53 -> 17.96 | 0 |
| 4 | 80 | 1.481 | 27.52 -> 18.20 | 0 |

**5/5 stayed open. The membrane is perfect throughout** (core 1.464-1.483 against a 1.467 reference), so
this is not a structural failure. The trajectory settles fast: R_mid reaches 18.75 by step 20 000 and
then sits at ~18.5 with flat energy (-12.4) for the remaining 180 000 steps.

### CAUGHT BY THE RENDER: R_mid falling is NOT curling

I read R_mid 27.52 -> 18.2 as the ribbon curling substantially without closing, and wrote that down.
**The render shows a straight ribbon** -- a gently undulating flat bilayer, heads on both faces, tails
in the core, no curvature at all. The R_mid drop is the ribbon CONTRACTING laterally as it relaxes from
the planted spacing, not bending.

Reporting the metric alone would have produced a claim -- "the ribbon curls but cannot close" -- that the
picture flatly contradicts. This is the third time in this project a structural claim has needed the
render to survive, and the first time the render has overturned a claim I had already formed.

### What it means

**This model does not curl a flat bilayer.** Curvature has to be handed to it. That is consistent with
every result so far: the arcs that closed were all planted with curvature (N = 80 at 2.4 sigma closed
5/5; N = 300 closes at every gap tested at rates falling with gap), while nothing that started flat has
ever closed.

It also fits the emergent renders directly -- the ribbons in the N = 160 box are long and STRAIGHT.

### The matched control this needs, launched

The flat arm is implicit solvent; the N = 80 arc that closed 5/5 was explicit. Comparing them would
confound curvature with solvent. Launched: **arc0.97, N = 80, L = 110, phi = 0.0**, 5 seeds, 200 000
steps -- identical to the flat arm in size, box and solvent, differing only in being handed curvature.
Step 0 verified: n_enclosed = 0, largest 80, core 1.463.

* **Implicit arc closes while implicit flat did not** -> handed curvature is the whole difference, in a
  matched solvent, and the no-curling conclusion stands.
* **Implicit arc also fails to close** -> closure in implicit solvent does not work at this size at all,
  the flat result says nothing about curling, and the comparison must be redone in explicit solvent
  (where the slow flat arm is still running).
* **Both close** -> the flat arm's 5/5 failure was a fluke of the first 200 000 steps and needs longer.

### Gap scan, still sharpening

At step 45 000: arc0.99 (3.0 sigma) **4/5**, arc0.98 (6.0 sigma) **3/5** -- up from 1/5 at step 20 000.
The gap dependence is a rate difference, not a threshold, exactly as revised two ticks ago.

### RETRACTED: "new high, 129 lipids, 89% of threshold"

Reported last tick as progress. Seed 0 has since fallen from 129 back to **83**. Aggregates merge and
split; growth is not monotonic and 129 was a fluctuation, not a trend. Current largest across seeds:
83, 81, 70, 104, 56. I framed a single high-water mark as progress and should not have.

### Still in flight

chi_TW arms (75 000-85 000/100 000), bend rungs (97 500/150 000), gap scan to 100 000, explicit flat
ribbon (30 000/200 000), implicit arc control, N = 160 emergence (640 000/800 000).

---

## Tick: the matched control lands, and chi_TW is a real null

### THE MATCHED CONTROL: curvature must be handed to this model

Identical implicit solvent, identical N = 80, identical L = 110. The only difference is the plant:

| arm | closed | when | final state |
|---|---|---|---|
| **flat ribbon** | **0/5** | never | straight, largest 80, core 1.464-1.483 |
| **arc0.97** | **5/5** | all at step 10 000 | closed, held to 200 000, core 1.452-1.466 |

Both arms kept a perfect membrane, so neither result is a structural failure. This fires the first
pre-registered branch: **handed curvature is the whole difference, in a matched solvent.**

The no-curling conclusion stands. This model closes curvature it is given and never generates its own.
It explains the entire history: every closure in this project came from a planted arc, and nothing that
started flat has ever closed. It also explains the emergent renders directly -- the N = 160 aggregates
are long STRAIGHT segments meeting at junctions, which is what a membrane that cannot curl will build.

### chi_TW: a real null, not an underpowered one

The arms completed at step 100 000. Time-averaged over the plateau, 5 seeds:

| chi_TW | ring | arc | lambda |
|---|---|---|---|
| 0.00 | -7.5018 +- 0.0063 | -7.4831 +- 0.0177 | **+2.8 +- 2.8 eps** |
| -0.50 | -6.2308 +- 0.0222 | -6.2653 +- 0.0175 | **-5.2 +- 4.2 eps** |

    change = -8.0 +- 5.1 eps  (1.6 sigma)

Making tails hydrophobic did NOT raise the edge cost. At +-4.2 eps this assay would detect the ~+15 eps
needed to reach the old +18.31 at 3.6 sigma, so this is a **real null with adequate power**, unlike the
static paired test discarded two ticks ago. The second pre-registered branch fires.

**Why, most likely:** a bilayer edge heals by heads reorienting to cover the exposed tails, so tail-water
contact never actually occurs at the rim and no tail-water term can price it. That would make lambda ~ 0
a structural property of this lipid, not a tunable one.

Caveat recorded: 1/5 chi_TW arcs closed, at step 90 000, which pulls that seed toward zero. Four of five
stayed open.

### A column error, caught

The closure check first reported "0/5 chi_TW arcs closed" because it read `f[12]`, which is `perc`
(Y/n), where `nenc` is `f[11]`. Corrected before use: the true count is 1/5. The awk one-liners use
1-indexed `$12` for nenc and the Python uses 0-indexed `f[11]`; mixing the two conventions has now
caused this twice.

### FALSIFICATION, STATED BEFORE THE RUN

If curvature cannot come from tail-water contact and does not arise spontaneously, the remaining source
is headgroup packing: a leaflet whose heads repel more strongly wants a larger head area per lipid,
which is exactly a spontaneous curvature. chi_HH already has an override and its default is +0.20
(attractive); negative is repulsive here.

Launched: **flat ribbon, N = 80, L = 110, implicit, chi_HH = -0.30 and -0.60**, 5 seeds each, 200 000
steps -- the identical protocol that just produced 0/5 closure at the default chi_HH, so the flat arm is
its own control. Arms tag apart on disk as `..._hh-0.30_...` and `..._hh-0.60_...`, verified.

* **The flat ribbon curls and closes in >= 1/5 at either value, with core > 1.35** -> head-head repulsion
  generates spontaneous curvature, and it is the missing ingredient for emergent closure.
* **It stays flat 0/5 at both values with the membrane intact** -> head repulsion does not generate
  curvature either, and the source must be leaflet ASYMMETRY rather than any symmetric pair term.
* **core < 1.35 or largest < 76** -> the value is too strong, the bilayer is damaged rather than curved,
  and that rung says nothing.

### Emergence

N = 160 at step 680 000-720 000: largest by seed 91, 81, 70, 104, **123**. Still fluctuating rather than
growing steadily, consistent with last tick's retraction. All n_enclosed = 0 except seed 3 at 2.

### Still in flight

Gap scan (4/5 and 3/5 at step 60 000), bend rungs (112 500/150 000), explicit flat ribbon
(50 000/200 000), chi_HH scan, N = 160 emergence.
