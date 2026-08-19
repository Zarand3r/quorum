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
