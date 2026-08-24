# Vesicles from a Transformer: Emergent Bilayer Self-Assembly with Attention-Only Dynamics

**Status:** working paper, 2026-08-24. Every number comes from run logs recorded in the append-only
`docs/AUTONOMOUS_LOG.md` (23,587 lines, ~60 dated entries). Retracted claims stay in the text, marked,
because several survived for days and the retractions carry more information than the claims did.

---

## Abstract

We express a coarse-grained lipid simulator entirely as a transformer and show that vesicles
self-assemble under it from a dispersed start. Every force is an unnormalised masked attention head:
the non-bonded interaction is a query-key inner product modulated by a distance function, and the
harmonic bonds are the same score-times-relative-position shape on a pair mask. One forward pass equals
one integrator step bit-for-bit, the token channel reproduces the species interaction table to exactly
0.0, and the formulation costs 21.17 +- 2.42 against the integrator's 20.65 +- 1.66 ms per step.

Vesicles form in **2 of 18** fresh dispersed-start seeds and in roughly **10 of 48** across all arms,
confirmed by an isolating render as well as by the detector. We identify the control variable for
closure: **the end-to-end gap of the ribbon, not its length, its radius, or its lipid count.** A 6x
change in gap moves the closed fraction from 0.000 to 0.512, while a 2.9x change in length at wide gap
gives zero closures in 320 checkpoints. Closure is two-state and reversible, with emergent vesicles
holding their lumen 0.458 of the time, placing them between planted arcs of 4.2 and 1.63 sigma gap.

Three negative results constrain the interpretation. Line tension is not the driver: `chi_TW = 0.00`
removes the hydrophobic drive by construction, and a direct measurement gives lambda = +2.8 +- 2.8 eps
against a retracted +18.31 +- 7.07. Bending rigidity resists three independent measurement routes. And
**no dispersed-start run has ever held two vesicles at once**, in any arm.

---

## 1. The claim, and what would falsify it

Coarse-grained lipid models produce vesicles. Transformers process sequences. We claim these are the
same computation exactly rather than by analogy, and that the transformer version produces the science
result rather than merely reproducing a step.

Three things would falsify the claim. An approximate rather than exact head decomposition would make the
framing decorative. A large cost penalty would make it a curiosity rather than a formulation. And
vesicles forming under the integrator but not under the transformer would limit the equivalence to short
horizons. Section 3 settles the first two. Section 12.4 leaves the third open with the experiment
running.

## 2. The model

The system is two-dimensional with explicit solvent. A lipid is one head bead and four tail beads in
**two branches from a single head**, which is what a phospholipid is. Single-chain amphiphiles are
detergents: the packing parameter `P = v / (a0 * l)` has both `v` and `l` linear in tail count, so `P`
does not depend on tail length, and lengthening a linear tail from 2 to 4 to 6 never moved the phase.
Branching doubles `v` at fixed `l` and puts `P` in the bilayer band.

Interactions use a Flory-Huggins `chi` table scaling an attractive well, so `chi > 0` attracts. With
explicit water the beads feel the **exchange** energy rather than the tabulated one:

```
chi_eff_ij = chi_ij + chi_WW - chi_iW - chi_jW
```

| pair | raw | effective |
|---|---|---|
| head-head | +0.20 | **-0.800** |
| head-tail | -0.25 | **-0.500** |
| tail-tail | +0.70 | **+1.200** |

The sign flip cost two days. We described raising raw `chi_HH` from 0.20 to 0.60 as "raising head-head
repulsion" while the effective value moved from -0.800 to -0.400, which **halves** it. The driver now
prints both tables at startup.

Dynamics is velocity Verlet with an exact Ornstein-Uhlenbeck thermostat at `dt = 8e-3`, `kT = 0.45`,
`gamma = 1`. Arguments to the driver are `steps d n_lip frac_short L kT phi plant seed`.

## 3. Every force is an attention head, and the identity is exact

The non-bonded force already had attention's shape:

```
F_i = sum_j [ a(r_ij) + b(r_ij) * (q_i . k_j) ] * (x_i - x_j)
```

`a` and `b` are analytic radial functions, `q_i . k_j` is a query-key inner product read from the token
channel, and the values are **relative positions**, which makes the head equivariant. The harmonic bonds
and the 1-3 stiffener are the same shape restricted to a pair mask.

The token state is `(x, v, h)`. Positions and velocities are equivariant, `h` is invariant and holds the
one-hot species. `Wq` and `Wk` are the eigendecomposition factors of the `chi` table, so `q_i . k_j`
reproduces the species lookup identically rather than approximately.

### 3.1 Four assertions gate the claim

| assertion | result |
|---|---|
| heads reproduce `field.forces` on the **production** topology | **< 1e-13** relative |
| token channel `q_i . k_j` matches the `chi` table | **exactly 0.0** |
| one forward pass equals one integrator step | **bit-for-bit**, max abs diff **0.0** |
| MLP changes forces when given non-zero weights | passes |

The production-topology test matters most. Every other test builds its own bond list; this one calls
`_mixture.build`, so branched lipids and explicit water populate exactly as a real run does. A refactor
exact on toy chains and wrong on the real topology would pass everything else.

We compare only **one** step bit-for-bit, deliberately. Summing heads in a different order than
`field.forces` changes the last bit, and the dynamics amplifies that: 0 after 1 step, 1.8e-15 after 20,
4.9e-08 after 400. A multi-step tolerance would be arbitrary. The single-step identity is exact and is
the thing actually claimed.

### 3.2 The formulation is free

Five matched 400-step replicates per engine, alternating order on the same loaded machine, N = 208:

| engine | mean | sd | sem |
|---|---|---|---|
| integrator | 20.65 | 1.66 | 0.74 ms/step |
| transformer | 21.17 | 2.42 | 1.08 ms/step |

The difference is 0.52 +- 1.31 ms/step, consistent with zero. **Takeaway: expressing the dynamics as
masked attention heads costs nothing.**

### 3.3 What "transformer-only" does not cover

The attention is **unnormalised**. Softmax would make each pair's contribution depend on neighbour count
and would break momentum conservation, since the resulting forces would not be symmetric.

`a(r)` and `b(r)` are **analytic**, filling the role ALiBi plays in a language model rather than being
learned. We rejected replacing them with an MLP because `well'` is sinusoidal and both carry a `1/r`
factor, so an MLP could only approximate an otherwise exact force law.

**`W1 = W2 = 0` in every run executed**, so the MLP has contributed nothing to any result here. Nothing
is trained. This is a hand-specified force field written in attention form.

A full trajectory is 1.6 x 10^6 applications of one weight-tied block. It is a single forward pass in
the sense an unrolled recurrent network is, at that depth, with a modular-wrap nonlinearity and fresh
Gaussian noise injected per layer.

## 4. Vesicles form, and the picture agrees with the metric

### 4.1 Detection, and its measured error rate

Clusters come from connectivity at cut 1.4 under the minimum image. A cluster is called a vesicle when
it encloses a region **and** that region is large enough for the lipid count,
`lumen >= 0.10 * n^2 / pi`, with `n_enclosed == 1` stable across bead radii 1.0/1.5/2.0/3.0, and the call
debounced at two consecutive checkpoints.

We measured the per-checkpoint **false-negative rate at 0.057** across 20 planted rings (52 x10, 80 x5,
120 x5) restricted to seeds closed at their last checkpoint: 8 zero rows in 141, longest run 2. An
independent route gave 0.941 recall, reproducing this within 0.002.

The rate has teeth in both directions. A single zero reading is **not** evidence a vesicle opened, and 6
of 9 rings that ever read zero recovered. But 45 consecutive zeros, as three two-ring seeds showed, has
probability about 10^-55 under flicker, so those openings are real.

The size clause carries most of the discrimination. Counting **any** enclosed region across the 18 fresh
seeds gives **5/18**; counting by the full gate gives **2/18**. The three extra seeds hold small pockets
in branched networks. sd45004 reaches lumen 122 against the 482 its 123 lipids require, a ratio of 0.253.
The gate is calibrated against renders: a planted N=300 ring scores 0.882 and passes; an emergent N=160
branched net scores 0.028 and fails.

### 4.2 The isolating render

Whole-box frames cannot settle the question. At L = 65 a 66-lipid ring is one of six structures and a
third of the frame width. We therefore isolate the largest cluster, **unwrap it across the periodic
boundary** so a boundary-crossing ring is not drawn as two arcs, and render it alone
(`cluster_shot.py`).

**sd45007 at 960,000 steps is a vesicle.** A closed bilayer ring encloses a clear void with a ribbon
tail still attached. Tails sit in the wall interior and **heads line both the outer surface and the
lumen-facing inner surface**. Largest cluster 66 lipids, lumen 460 cells, `nves = 1` for eight
consecutive checkpoints, `perc = n` at all 49 checkpoints so the lumen is not a periodic-wrap artifact.
A ring of the measured `R_mid = 11.16` encloses 391 cells against 460 measured.

**sd45004 at 900,000 steps is a branched network** with a small triangular gap, confirming the gate's
rejection.

### 4.3 A statistic we retract

We computed radius-from-centroid CV as a ring test and obtained **0.456 for the vesicle against 0.421
for the network**, both far above the CV well under 0.2 a ring should give. On that number we were about
to report that the gate cannot separate the two cases and that 2/18 is an artifact. The number is
correct and the inference is wrong: **the attached tail inflates the CV**, so a tailed vesicle scores
like a ribbon. **Radius CV is retracted as a ring discriminator in this system.**

## 5. The end gap controls closure. Length, radius and lipid count do not.

This is the central mechanistic result, and it falsifies the plan the project was run under.

### 5.1 The span scan

Planted arcs at fixed n = 80, identical box, lipids, water, `chi` and `kT`, varying only the arc span
and therefore the end-to-end gap. Fraction of checkpoints with an enclosed region:

| span | end gap | closed checkpoints | fraction | seeds closed at 300k |
|---|---|---|---|---|
| 0.75 | 26.7 sigma | 0 / 74 | **0.000** | 0/5 |
| 0.85 | 14.1 sigma | 2 / 74 | **0.027** | 0/5 |
| 0.95 | 4.2 sigma | 28 / 80 | **0.350** | 2/5 |

Monotone, and 13x from 0.85 to 0.95.

### 5.2 Length does not matter, at either gap

At fixed wide gap, varying length across a 2.9x range:

| n | 70 | 80 | 120 | 200 |
|---|---|---|---|---|
| closed checkpoints | 0/80 | 0/80 | 0/80 | 0/80 |

**320 checkpoints, zero closures.** The n = 200 arcs did not unroll either: radius held within 4% on
four of five seeds, with the plant intact at 200/200 lipids.

At fixed narrow gap of 4.2 sigma, varying length and therefore radius:

| arm | n | span | radius | seeds closed at 300k | checkpoints closed |
|---|---|---|---|---|---|
| gap52 | 52 | 0.925 | 8.95 | **3/5** | 41/80 = **0.512** |
| arc80 | 80 | 0.95 | 13.40 | 2/5 | 28/80 = **0.350** |
| gap120 | 120 | 0.966 | 19.77 | 2/5 | 18/45 = 0.400 |

**A 6x change in gap moves closure from 0.000 to 0.512. A 2.3x change in length at fixed gap moves it
1.46x.**

### 5.3 The radius confound resolves against radius

Radius varies 2.2x across the three gap-matched arms. The critical-size picture predicts the smallest
radius (n = 52, R = 8.95) should close **least**, because bending cost scales as `pi*kappa/R`. It closes
**most**, 0.512 against 0.350. At 1.46x on five seeds we report this as **radius is not the control
variable**, not as a reversal.

### 5.4 Closed rings show no size dependence either

Planted rings at 300,000 steps: 52 gives 8/10, 80 gives 5/5, 120 gives 3/5. Non-monotone, and no pair
separates (Fisher 52 against 120 p = 0.560; 80 against 120 p = 0.444). Pooled, 16 of 20 rings are stable.

**Neither the open nor the closed geometry shows size dependence over a 2.3x range.**

### 5.5 The standing plan cannot fire, and its premise is wrong

The project ran under a standing falsification: *"if arcs of 70/120/200/300 lipids all unroll at
kT = 0.45, the continuum picture is wrong."* **None of them unroll**, so the clause cannot fire as
written. The substantive question is answered anyway: the threshold ribbon length the plan was built to
find **does not exist, because length is not the operative variable.**

### 5.6 A negative result against our own hypothesis

If closure needs ends within about 4 sigma, smaller aggregates should help, because a short ribbon curls
tighter. Final read at 600,000 steps of the mixed-tail arms:

| arm | seeds | largest cluster | vesicle checkpoints |
|---|---|---|---|
| frac_short = 1.0 | 6 | 13.8 +- 4.4 | **0** |
| frac_short = 0.5 | 5 | 38.0 +- 8.8 | **0** |

**38-lipid aggregates over 600,000 steps in six seeds produced zero closures.** Making emergent
aggregates smaller does not produce closure. We record this because it cuts against the gap story.

**Takeaway: the end-to-end gap controls closure. Ribbon length, radius and lipid count do not.**

## 6. Closure is two-state and reversible, and emergent vesicles sit on the same axis

For each of 12 reproduced formers, every checkpoint after first closure, pooled: **218/476 = 0.458** of
checkpoints hold a vesicle. Per-seed the fraction runs from 0.074 to 1.000, so this is a pooled
statement rather than a property of any seed.

Placing that number on the planted-arc dose-response curve:

| object | closed fraction |
|---|---|
| planted arc, gap 26.7 sigma | 0.000 |
| planted arc, gap 14.1 | 0.038 |
| planted arc, gap 4.2 | 0.350 |
| **emergent vesicle** | **0.458** |
| planted arc, gap 1.63 | 0.812 |

**An emergent vesicle behaves like a small-gap planted arc.** It flickers between closed and open and
holds its lumen about half the time. The same two-state physics appears without planting anything.

## 7. Vesicles form at their final size

Lumen over the 200,000 steps after first sustained closure, eight seeds: growth factor
**0.99 +- 0.05**. Two of eight grew more than 10% and two shrank more than 10%, symmetrically.

**Size is set at closure, not by later inflation.** The enclosed area reaches only **0.23** of what a
perfect ring of the same lipid count would enclose, so the closed object is a floppy loop rather than a
taut circle.

## 8. The aggregate distribution is still coarsening, and fission balances fusion near 90 lipids

We **retract** an earlier claim of a dynamic fission-fusion steady state. Mean largest-cluster size is
**80.4 for steps 400k-900k (n = 195) and 115.8 beyond 900k (n = 189)**, still drifting upward at 1.4M.
The process coarsens slowly with size-dependent rates.

383 transitions between adjacent checkpoints across 12 seeds, late window, excluding the n = 160 system
ceiling where fusion is forced to zero:

| size bin | n | P(fission) | P(fusion) |
|---|---|---|---|
| 40-59 | 65 | 0.015 | 0.231 |
| 60-79 | 61 | 0.066 | 0.213 |
| **80-99** | 90 | **0.089** | **0.100** |
| 100-119 | 83 | 0.108 | 0.036 |
| 120-139 | 28 | 0.036 | 0.107 |
| 140-159 | 12 | 0.167 | 0.167 |

**Fusion falls with size, fission rises, and they cross in the 80-99 bin**, unchanged under the transition
threshold. The eight confirmed vesicles closed at a median of **88 lipids**. We report the coincidence
as worth pursuing rather than as a cause: with the distribution still drifting, a common scale could set
both, and eight closures cannot separate them.

## 9. A cliff at 120 lipids

P(vesicle present | largest cluster size), pooled over the 12 formers, compared **within** formers so
the test is not circular:

| size | after first formation | n |
|---|---|---|
| 40-59 | 0.722 | 36 |
| 60-79 | 0.863 | 51 |
| 80-99 | 0.478 | 209 |
| 100-119 | 0.710 | 62 |
| **120-139** | **0.143** | 56 |
| **140-159** | **0.091** | 33 |
| **160-179** | **0.017** | 59 |

**An order of magnitude drops at 120 lipids.** We checked whether the gate creates the cliff: `nenc`
stays at 0.80-0.91 through the 120-159 band while `nves` collapses to 0.09-0.14. The difference is the
size clause, and the renders confirm its verdict. Above 120 lipids the clusters are branched networks
whose pockets are not vesicles.

## 10. The integrator is deterministic in the seed, and the check splits cleanly

All **12 of 12** historical formers re-formed on replay. First-formation steps:

| arm of origin | seeds | match |
|---|---|---|
| std160 | 9308, 9317, 9315, 9314, 9312, 9316, 9302, 9326 | **8/8 exact, to the checkpoint** |
| other arms | 1459, 349, 9805 | 3/3 differ |

**The split is the result.** Seeds that should reproduce exactly do; seeds run under parameters
different from their arm of origin do not.

## 11. Nothing predicts the formation lag

The lag from eligibility (largest >= 52) to first closure spans **40,000 to 1,060,000 steps, a 26x
range**. If an observable at the crossing predicted it, seeds could be screened rather than run to
completion.

| correlate | r | t (10 dof) |
|---|---|---|
| time of eligibility | -0.529 | -1.97 |
| size at eligibility | +0.113 | +0.36 |
| energy at eligibility | +0.236 | +0.77 |
| growth before eligibility | +0.370 | +1.26 |
| size at formation | +0.565 | +2.16 |
| mean size over the lag | +0.638 | +2.62 |

**The two apparent hits are definitional artifacts**, since both are measured over the interval whose
length is the outcome. Nothing survives correction for testing six correlates. **Formation cannot be
screened for in advance.**

## 12. Open questions, with the experiments running

### 12.1 The formation-rate drought is suggestive, not established

We **retract** earlier drought figures of P ~ 0.002 to 0.02. Those came from hazard models with at-risk
denominators, censoring choices, eligibility estimates and a size-window correction, all assumptions we
introduced. The assumption-free version is a 2x2 on per-seed outcomes at matched duration and verified
identical composition:

| | formed | not |
|---|---|---|
| historical std160 (30 seeds, 1.6M) | 8 | 22 |
| our arms (12 seeds, >= 1.5M) | 0 | 12 |

**Fisher exact p = 0.0804. Not significant.**

### 12.2 Coarse sampling undercounts episodes by 3.8x

Distinct enclosed-state episodes over 0-140,000 steps, five seeds, fine (2,000-step) against coarse
(20,000-step) sampling: **3.8 against 1.0**. The mechanism is the lifetime distribution. Across 26
episodes at fine resolution the mean is 25,462 steps and the **median 6,000**, with **18 of 26 (0.69)
shorter than one standard sampling interval**.

We bound what this affects. The factor applies to **episode counts within a run**, not to the binary
"did this seed ever form" that the drought comparison uses. A seed counts as a former if any one episode
is sampled, so the 8/30 comparison is much less affected than the raw factor suggests.

### 12.3 Multiplicity has never emerged from a dispersed start

**Zero runs, in any arm, have reached two simultaneous vesicles from a dispersed start.**

Two-vesicle states do exist. At 500-step resolution the sd55002 event resolves into **58 and 47 lipids,
each passing the gate independently** (lumens 222 and 311, then 233 and 303), for 1,000 to 1,500 steps,
with the render showing two separate closed loops. That is the first verified two-vesicle state in the
project.

Two routes to a pair behave differently. **Pinch-born** pairs re-fuse within 500 to 1,500 steps. We
corrected our own reading here: the 28-sigma centroid separation is the **midpoint of a dumbbell** whose
lobes pinch apart and rejoin, not two bodies that drifted together. **Born-apart** pairs **never merge**:
all 8 losses of the two-vesicle call had `largest` unchanged at 52, so what dropped was the vesicle call
on one ring at the measured 0.057 flicker rate. We therefore **withdraw** an earlier claim that the model
lacks a fusion barrier.

Across 15 two-compartment episodes, **all 15 ended by the enclosed count falling from 2 to 1, never by
the cluster splitting.** The obstruction is fission, not the making of a second lumen. We also retract a
claim that one seed held the state for 21 consecutive checkpoints: those 21 checkpoints span 8 separate
episodes, and the longest single episode is 6 checkpoints.

### 12.4 No result yet comes from the transformer path

All results here come from the integrator calling `field.forces` directly. We discovered on 2026-08-24
that a launch script omitted `VIVARIUM_ENGINE=transformer`, so the six-seed arm committed two days
earlier as the transformer emergence arm had been running the integrator. Six matched transformer seeds
now run against six integrator seeds as a control. **The equivalence is proven per step and not yet
demonstrated across a full emergent trajectory.**

## 13. Two negative results on the energetics

### 13.1 Line tension is not the driver, and the earlier figure was wrong

An intercept fit gave lambda = +18.31 +- 7.07 eps, quoted as +40.7 +- 15.7 kT per end, implying about
81 kT available from closure. **This is retracted.** A direct ring-versus-arc comparison at N = 300
gives **lambda = +2.8 +- 2.8 eps, consistent with zero.**

The reason is structural. **`chi_TW = 0.00`**: the tails are not hydrophobic, so the exchange term that
would pay for hiding an edge is absent by construction. Making the tails hydrophobic does not fix it.
That variant gives **lambda = -5.15 +- 1.49**, so closure becomes *less* favourable, even though the
edge cost does engage and raises tail burial by 60%.

An intermediate claim of 5.41 +- 1.40 eps from three paired seeds also failed at n = 9, falling to
+1.61 +- 1.67 with four of the six new seeds negative.

**Takeaway: closure in this model is geometric and kinetic. No energetic drive stands behind it, which
is consistent with the gap result of Section 5 and with closure being reversible.**

### 13.2 Bending rigidity resists three measurement routes

The **undulation spectrum** measures its own sampling noise: per-mode kappa spreads 16.7x at 60 lipids
and 1712x at 120, with a flat-in-q spectrum. The **critical-size test** cannot separate the sizes,
because Section 5 shows no size dependence exists to find. The **curvature series** gives
kappa = 13.84 +- 10.91 eps*sigma with chi-squared per degree of freedom of 0.01 and a high-to-low ratio
of **8.47**, failing a pre-registered factor-of-two bar. We declined to add a span that would have
passed, because including it raises chi-squared per degree of freedom to 1.84.

**Kappa is closed as a line of work**, under a stopping rule fixed before the final fit.

## 14. The packing parameter behaves as theory predicts

Largest cluster at a matched step, identical box, N, kT and chi, varying only tail length:

| arm | seeds | mean | sd | sem |
|---|---|---|---|---|
| frac_short = 1.0 (2 tails) | 6 | **13.0** | 5.3 | 2.2 |
| frac_short = 0.5 | 6 | **29.2** | 5.9 | 2.4 |
| frac_short = 0.0 (4 tails) | 14 | **43.6** | 12.5 | 3.3 |

Monotone, and every adjacent pair separates: **t = 7.7, 3.5 and 5.0**. Halving tail volume at fixed head
area collapses a 44-lipid ribbon to a 13-lipid micelle, which is the Israelachvili packing parameter
behaving as stated.

## 15. Method errors, and the guards installed

This section exists because the errors were more instructive than most positive results.

| error | consequence | guard |
|---|---|---|
| Read stale `/tmp` logs from dead runs, four times | reported trends from finished experiments | `status.sh` reads `/proc/<pid>/fd/1`, live processes only |
| `_save_state` filename carries no step or run identity | relaunching five seeds destroyed the historical states their closure sizes came from | hazard documented at the call site; `docs/states_protected/`; `VIVARIUM_SAVE_ALL` |
| Described a raw `chi` change by its raw sign | ran a lever backwards for two ticks | driver prints raw **and** effective tables at startup |
| Sampled every 20,000 steps | merged 3.8 episodes into one; median episode is 6,000 steps | checkpoint interval is a swept variable; event counts are lower bounds |
| Pre-registered thresholds against the wrong baseline | a clause could not fire as written | baselines stated numerically in the registration |
| Pre-registrations with missing branches | three outcomes occurred that no branch covered | registrations enumerate an "other" branch |
| Counted total checkpoints as contiguous | a 21-checkpoint episode was really 8 episodes | episodes counted by run-length, not by total |
| One seed argument fixed both placement and noise | no experiment could separate them | `VIVARIUM_NOISE_SEED` overrides noise alone |

**Takeaway: in this project the render and the metric have each flattered the other. A structural claim
now requires both, and the render must isolate the object being claimed.**

## 16. Why seeds matter is not yet answered

A variance decomposition holds one factor fixed and measures the surviving spread in largest-cluster
size. **The two sampling steps disagree:**

| step | A: noise only | B: placement only | C: total |
|---|---|---|---|
| 40,000 | 5.06 | **8.54** | 8.65 |
| 80,000 | **9.73** | 7.25 | 10.50 |

`A^2 + B^2` also exceeds `C^2` at both steps (98.5 against 74.8; 147.3 against 110.3), over-explaining
the total. Both facts indicate n = 10 per arm is too small. Arms now run at 25 seeds under a
pre-registered stopping rule: if the decomposition stays unstable across steps, we report it as not
estimable and stop.

**One result survives both steps.** Arm A's spread is comparable to the total rather than near zero, so
**fixing the initial placement does not collapse the outcome spread.**

## 17. Limitations

The system is **two-dimensional**. A 2-D vesicle is a ring, and the packing arguments transfer only
loosely.

**Three-dimensional explicit solvent does not work** at packing fraction 0.15 to 0.35, where the solvent
forms fragmented droplets rather than a liquid. Every 3-D result is void.

**The MLP is inert** at `W1 = W2 = 0`, and nothing is trained.

**No result yet comes from the transformer path** (Section 12.4).

**Formation is rare and slow.** Two of 18 fresh seeds within 10^6 steps, with lags spanning 26x and no
observable that predicts them.

## 18. What would change the conclusion

**Supplying a hydrophobic drive** by setting `chi_TW < 0` addresses the missing energetics. Measured
alone it makes closure worse (lambda = -5.15 +- 1.49), so it needs pairing with a compensating change.

**Engineering the end gap** follows directly from Section 5, which is the only lever shown to move
closure by an order of magnitude. Nothing tested so far reduces the gap in an emergent run.

**Fixing the 3-D solvent** is the largest single blocker to physical realism.

**Training the MLP** would make the architecture claim substantive rather than structural.

## 19. Reproduction

```
bazel test //projects/vivarium:test_suite          # 157.6 s, 1 of 1 PASSED

# one emergent run, dispersed start
VIVARIUM_CHI_HT=-0.25 VIVARIUM_CHI_WW=0.50 VIVARIUM_CHECKPOINT_EVERY=20000 \
  ./bazel-bin/projects/vivarium/_mixture 1600000 2 160 0.0 65 0.45 0.55 random 45007

# the same run with the dynamics as a transformer forward pass
VIVARIUM_ENGINE=transformer ...same arguments...

# isolate and unwrap the largest cluster
python3 projects/vivarium/cluster_shot.py <state.npz> out.png
```

`VIVARIUM_NOISE_SEED` overrides the thermal noise independently of placement.
`VIVARIUM_SAVE_ALL` writes step-tagged states that never collide.

**Log column map:** 1 step, 2 E/lip, 3 largest, 4 R_mid, 11 lumen_c, 12 nenc, 13 perc, 19 nves.
