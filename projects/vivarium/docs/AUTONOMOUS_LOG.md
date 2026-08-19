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
