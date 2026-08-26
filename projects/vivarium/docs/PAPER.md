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

The transformer path also produces the result end to end: six seeds run to 1.6 x 10^6 steps give a
debounced formation rate of 1/6 against 1/6 for a matched integrator control, so the equivalence is not
limited to the short horizons the bit-for-bit test covers.

Neither of the other two vesicle operations occurs. **Fusion has never been observed**, and osmotic
deflation drives a taut ring through the reduced-volume sequence to a **dumbbell whose neck never
pinches: zero fission in 50 runs**. We name the leading suspect, a Langevin thermostat that screens the
hydrodynamics driving Rayleigh-Plateau pinch-off, and state it as untested.

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

### 1.1 Scoreboard against the three operations

The project targets three vesicle operations and nothing else. No proteins, no biology.

| operation | status | best evidence |
|---|---|---|
| **emerge** | **works, rarely** | 2/18 fresh dispersed-start seeds; ~10/48 across all arms; **1/6 through the transformer path**, matching its integrator control |
| **come together** | **never observed** | 8/8 losses of a two-vesicle state were detector flicker with `largest` unchanged at 52, not fusion |
| **split** | **never observed** | **0 fission in 50 deflation runs**; 15/15 earlier two-compartment episodes ended by `nenc` 2 -> 1, never by dividing |

**Each blocked operation now has a named mechanism rather than a mystery**, which is what Sections 13
and 14.1 are for.

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

### 4.4 The pocket state is an arrested trap, not a precursor

Three seeds hold a durable enclosed pocket that the gate rejects. To test whether such a pocket is a
vesicle in progress, we took sd45004's 900,000-step state and ran **five replicas varying only the
thermal noise**, 200,000 steps each.

**0/5 reached a vesicle call, and the pocket persisted in 54 of 55 checkpoints**, while the cluster
coarsened from 123 to 149 lipids. The branched network with a pocket is a **dead end**, not a precursor.

This also **retracts** a within-seed lumen growth trend of +16.7 +- 3.7 cells per 100,000 steps
(t = 4.54) measured on sd45004, since none of five noise replicas started from its own state grew a
vesicle. Two other seeds had already given -6.8 +- 4.3 and -8.3 +- 13.5 on the same measurement.

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

**Doubling the material makes this worse, not better.** Five seeds at N = 320 lipids in L = 92, density
0.0378 matched to the standard arm's 0.0379, run to 1.6 x 10^6 steps:

| seed | largest reached | at end | `nves >= 2` |
|---|---|---|---|
| 91001 | 243 | 210 | 0 |
| 91002 | 174 | 174 | 0 |
| 91003 | 131 | 94 | 0 |
| 91004 | **309** | 309 | 0 |
| 91005 | 274 | 153 | 0 |

**0/5, and every seed coarsened past the 120-lipid cliff of Section 9**, one of them putting 309 of 320
lipids into a single cluster. The extra material went into a bigger branched network rather than into a
second vesicle. **Waiting for two to nucleate is closed as a strategy**, which leaves separate
nucleation as the only untested route.

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

### 12.4 The transformer path now produces the result, and the equivalence holds at full length

**Superseded on 2026-08-25.** This section previously read "no result yet comes from the transformer
path," which was true when written and is now false.

Six seeds ran the full 1.6 x 10^6 steps with `VIVARIUM_ENGINE=transformer`, against the same six seeds
on the integrator as a matched control. `emerge3T` seed 65001 carries a **debounced formation**:

| step | largest | lumen_c | nenc | perc | nves |
|---|---|---|---|---|---|
| 700,000 | 35 | 154 | 1 | n | 1 |
| 720,000 | 34 | 161 | 1 | n | 1 |
| 760,000 | 35 | 158 | 1 | n | 1 |
| 780,000 | 35 | 145 | 1 | n | 1 |

Two consecutive pairs, with `perc = n` so the lumen is not a periodic-wrap artifact.

| arm | seeds with any vesicle call | **debounced** |
|---|---|---|
| **transformer** | 1/6 | **1/6** |
| integrator control | 2/6 | **1/6** |

**The pre-registered clause fires.** A formation rate consistent with the integrator means the
transformer formulation does the physics rather than merely reproducing a step, and the equivalence is
**not** limited to the short horizons Section 3 proves it on.

**How the error was found, since it matters more than the result.** A launch script omitted
`VIVARIUM_ENGINE=transformer`, and the arm committed two days earlier as the transformer emergence arm
had been running the integrator for two days. We caught it by reading `/proc/<pid>/environ` for all 108
live simulations rather than trusting the commit message. **Every result in this paper predating
2026-08-25 came from the integrator.**

## 13. Fission: deflation produces a dumbbell, and the neck never pinches

A closed 2-D membrane has a circumference fixed by its lipid count and an enclosed area fixed by how
much water is inside. Every ring planted before 2026-08-25 was filled to bulk, which is the taut circle,
and a taut circle has no excess membrane to buckle with. `VIVARIUM_LUMEN_FILL` under-fills the lumen,
leaving the same circumference around a smaller area. That is the **reduced-volume axis** of the
standard vesicle shape sequence, and it is how protein-free vesicles divide.

Natural systems make the same distinction. Cells divide membranes with dedicated machinery that spends
GTP or ATP, dynamin for endocytic necks and ESCRT-III for reversed-topology scission, and none of that
is in scope here. **Protein-free vesicles still divide, but only under an imposed drive**: osmotic
deflation, shear, or lipid fed in faster than volume grows. **The lever below supplies that drive
directly**, which is why a null result from it constrains the model rather than the setup.

### 13.1 The lever, and a first implementation that did nothing

Patching the fill target alone produced **byte-identical trajectories at fill 1.0, 0.6 and 0.35.** The
grid water placement already leaves the lumen near bulk, because the lumen interior sits far from any
lipid and the lattice rejects only sites within 0.9 sigma of one. A function that only **adds** water
cannot deflate anything. Removing the surplus is the half that does the work.

Removal is gated at `fill < 1.0`, so `fill = 1.0` reproduces the pre-lever baseline exactly, verified at
lumen water 1.035 of bulk at step 0. Measured at plant: **1.071 / 0.621 / 0.467 / 0.354** for fill
1.0 / 0.70 / 0.50 / 0.35.

### 13.2 The dumbbell is real, and it is not a plant artifact

Planted 80-lipid ring, L = 44, kT = 0.45, 300,000 steps. Seed 4 at fill 0.50:

| step | R_mid | lumen | nenc |
|---|---|---|---|
| 0 (plant) | 17.46 | 1289 | 1, a taut circle |
| 60,000 | 15.01 | 1139 | 1 |
| 120,000 | 15.80 | 629 | 1 |
| **125,000** | 16.24 | **505** | **2** |
| 300,000 | 14.36 | 413 | 2 |

**The plant is one circular ring. The two-compartment state develops over 125,000 steps as the lumen
deflates, then holds for the remaining 175,000.** The render shows two lobes, each enclosing its own
void, joined by a visible neck, with heads lining both lobes inside and out.

### 13.3 No fission, in 50 runs

**`nves >= 2` never occurred, and `largest` never left 79-80.** The cluster did not divide in any run at
any fill.

### 13.4 The deflation effect shrank by 6x on replication

| arm | first 5 seeds | next 15 seeds | pooled |
|---|---|---|---|
| taut, fill 1.0 | 0/5 | 0/15 | **0/20** |
| deflated, fill 0.50 | **2/5** | **1/15** | **3/20** |

**Fisher one-sided p = 0.1154, not significant.** The pre-registered establishing clause required
>= 7/20 against <= 2/20 and observed 3/20 against 0/20, so it does not fire.

What survives is that a two-compartment state has appeared **only ever under deflation**, 3/20 against
0/20 across 40 runs. That is the correct sign and it is under-powered. **The original 2/5 was a
favourable fluctuation, and this is the third time in this project an n = 5 effect has shrunk on
replication.**

### 13.5 The leading hypothesis for the arrested neck

**The thermostat screens hydrodynamics.** A Langevin thermostat applies friction to every particle
independently in the lab frame, which destroys momentum conservation and suppresses long-range
hydrodynamic coupling. Neck pinch-off is a hydrodynamic instability of Rayleigh-Plateau type, so the
thermostat damps precisely the collective modes that would drive it. The dumbbell held 175,000 steps
without pinching, which reads as an arrested shape rather than a slow transition.

The testable fix is a **momentum-conserving thermostat**: DPD pairwise noise, or Lowe-Andersen. A
pairwise DPD thermostat is itself a masked attention head, so it costs the transformer framing nothing.

**NOT TESTED. Stated as the next experiment, not as a finding.**

## 14. Two negative results on the energetics

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

## 15. The packing parameter behaves as theory predicts

Largest cluster at a matched step, identical box, N, kT and chi, varying only tail length:

| arm | seeds | mean | sd | sem |
|---|---|---|---|---|
| frac_short = 1.0 (2 tails) | 6 | **13.0** | 5.3 | 2.2 |
| frac_short = 0.5 | 6 | **29.2** | 5.9 | 2.4 |
| frac_short = 0.0 (4 tails) | 14 | **43.6** | 12.5 | 3.3 |

Monotone, and every adjacent pair separates: **t = 7.7, 3.5 and 5.0**. Halving tail volume at fixed head
area collapses a 44-lipid ribbon to a 13-lipid micelle, which is the Israelachvili packing parameter
behaving as stated.

## 16. Method errors, and the guards installed

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

## 17. Why seeds matter is not yet answered

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

## 18. Limitations

The system is **two-dimensional**. A 2-D vesicle is a ring, and the packing arguments transfer only
loosely.

**Three-dimensional explicit solvent does not work** at packing fraction 0.15 to 0.35, where the solvent
forms fragmented droplets rather than a liquid. Every 3-D result is void.

**The MLP is inert** at `W1 = W2 = 0`, and nothing is trained.

**The thermostat is not momentum-conserving.** Langevin friction acts per particle in the lab frame,
which screens the long-range hydrodynamics that governs undulation relaxation and neck pinch-off. This
is the leading suspect for the arrested dumbbell of Section 13.5.

**Active noise is absent.** The thermal noise is a correct equilibrium Ornstein-Uhlenbeck process
obeying fluctuation-dissipation at kT = 0.45, and `check_same_ensemble` verifies the overdamped and
inertial integrators sample the same ensemble. Real membranes in cells are driven far from equilibrium,
with stronger and colored fluctuations. Equilibrium noise is the right baseline and not the whole story.

**An open detector bug: `nves` can exceed `nenc`, which should be impossible.** Seen on `emerge3T`
sd65001 at 1,560,000 and 1,600,000, reading `nves = 1` with `nenc = 0` and `lumen_c = 0`, and previously
on sd9312 and sd9326. It does not touch any formation reported here, all of which carry `nenc >= 1`
throughout, but it is unfixed and any future count should be checked against it.

**Formation is rare and slow.** Two of 18 fresh seeds within 10^6 steps, with lags spanning 26x and no
observable that predicts them.

## 19. What would change the conclusion

**Supplying a hydrophobic drive** by setting `chi_TW < 0` addresses the missing energetics. Measured
alone it makes closure worse (lambda = -5.15 +- 1.49), so it needs pairing with a compensating change.

**Engineering the end gap** follows directly from Section 5, which is the only lever shown to move
closure by an order of magnitude. Nothing tested so far reduces the gap in an emergent run.

**A momentum-conserving thermostat** (DPD pairwise noise, or Lowe-Andersen) restores the hydrodynamics
that neck pinch-off needs, and a pairwise DPD thermostat is itself a masked attention head. This is the
cheapest untested lever and the one we would run first.

**Fixing the 3-D solvent** is the largest single blocker to physical realism.

**Training the MLP** would make the architecture claim substantive rather than structural.

## 20. Reproduction

```
bazel test //projects/vivarium:test_suite          # 1 of 1 PASSED (157.6 s; 236.2 s after the deflation lever)

# one emergent run, dispersed start
VIVARIUM_CHI_HT=-0.25 VIVARIUM_CHI_WW=0.50 VIVARIUM_CHECKPOINT_EVERY=20000 \
  ./bazel-bin/projects/vivarium/_mixture 1600000 2 160 0.0 65 0.45 0.55 random 45007

# the same run with the dynamics as a transformer forward pass
VIVARIUM_ENGINE=transformer ...same arguments...

# isolate and unwrap the largest cluster
python3 projects/vivarium/cluster_shot.py <state.npz> out.png
```

```
# a deflated ring: same circumference, smaller enclosed area (Section 13)
VIVARIUM_LUMEN_FILL=0.50 VIVARIUM_CHI_HT=-0.25 VIVARIUM_CHI_WW=0.50 VIVARIUM_CHECKPOINT_EVERY=5000 \
  ./bazel-bin/projects/vivarium/_mixture 300000 2 80 0.0 44 0.45 0.55 ring 4
```

`VIVARIUM_NOISE_SEED` overrides the thermal noise independently of placement.
`VIVARIUM_LUMEN_FILL` sets lumen water as a fraction of bulk; below 1.0 it removes the surplus.
`VIVARIUM_SAVE_ALL` writes step-tagged states that never collide.

**Log column map:** 1 step, 2 E/lip, 3 largest, 4 R_mid, 11 lumen_c, 12 nenc, 13 perc, 19 nves.
