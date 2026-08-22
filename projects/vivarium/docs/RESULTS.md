# Emergent vesicle in a 2-D transformer-only lipid model

**Claim.** A closed, water-filled bilayer vesicle self-assembles from a dispersed random start,
persists under fresh thermal noise, and passes a two-gate criterion calibrated against known
structures. Nothing was planted at any point in its lineage.

**It formed by ends meeting, not by curvature.** That distinction is the main scientific content
here, and it is measured, not assumed.

![emergent vesicle](figures/01_emergent_vesicle_persistence_sd21.png)

---

## The criterion

A single enclosure count is not sufficient — a branched network with an incidental pocket passes it.
`vesicle_call()` requires both:

1. **`n_enclosed == 1` at every dilation in bead 1.0–3.0.** The count is dilation-sensitive, so only a
   call stable across the knob is reportable.
2. **The lumen must be the right SIZE for the lipid count.** A closed vesicle of *n* lipids has contour
   *n*, so *R = n/2π* and interior *πR²*. Threshold 0.10.

Calibration, every entry verified against its render:

| structure | lumen / expected | verdict |
|---|---|---|
| planted vesicle, N = 120 | 0.876 | vesicle |
| planted ring, N = 300 | 0.882 | vesicle |
| implicit arc, N = 80, closed | 0.295 | vesicle (irregular) |
| **emergent candidate** | **0.269–0.292** | **vesicle** |
| emergent branched network | 0.028 | not a vesicle |
| branched network, later reading | 0.010–0.044 | not a vesicle |

Gate 2 exists because the original pre-registered criterion had only gate 1, and a 160-lipid branched
network passed it. The render caught that; the metric did not.

## The result

Lineage: random dispersed start → N = 160, L = 65 → continued twice. No planting anywhere.

| | |
|---|---|
| largest cluster | **160/160** lipids |
| percolating | no |
| core depth | 1.430–1.440 |
| `n_enclosed` @ bead 1.0/1.5/2.0/3.0 | 1, 1, 1, 1 |
| lumen ratio | 0.269–0.292 |

**Persistence** — 5 fresh thermal seeds, 200 000 steps, read at the end:

| seed | largest | vesicle_call | ratio |
|---|---|---|---|
| 20 | 159 | True | 0.272 |
| 21 | 160 | True | 0.285 |
| 22 | 160 | True | 0.281 |
| 23 | 123 | True — **fragmented, excluded** | 0.454 |
| 24 | 160 | False (opened) | — |

**3/5 intact and True**, against a bar of ≥3/5 fixed before the run. The source trajectory
independently held its closure for a further 400 000 steps (2.4 M total, ratio 0.292).

## Why it closed: encounter, not curvature

**This force field cannot curve a flat bilayer.** Every candidate source was tested on the same
planted-flat-ribbon protocol, and every one is a measured null with the membrane intact:

| candidate | result |
|---|---|
| χ_TW (tail–water) | null **with power**: λ = +2.8 ± 2.8 vs −5.2 ± 4.2 ε |
| χ_HH (head–head) | 0/5 at two values, 10 runs |
| lipid shape (2-tail) | dissolves to micelles, largest 7–11 of 80 |
| leaflet **thickness** asymmetry (4/6 tails) | 0/5, intact, render straight |
| leaflet **area** asymmetry (split 0.58, ratio 1.35) | 0/5, intact |

The reason is structural: χ terms are symmetric pair interactions, and spontaneous curvature is by
definition a difference between the two leaflets.

Closure instead happens when two ends of a ribbon meet. **In the emergent run this is visible directly
in the trajectory**, not just inferred from the planted arcs:

| step | largest | n_enclosed | lumen | ratio |
|---|---|---|---|---|
| 320 000 | 116 | 0 | 0 | — |
| **360 000** | **116** | **1** | **2145** | **0.501** |
| 400 000 | 160 | 1 | 2191 | 0.269 |

The vesicle closed at **116 lipids** at **constant size** — 116 before, 116 after — which is what two
ends meeting looks like, and is not what accretion bridging a gap would look like. It then absorbed the
remaining ~44 lipids, which added appendages and no lumen, diluting the raw ratio from 0.501 to 0.269.
**The appendages are post-closure accretion, and the shell was at its best the moment it formed.**

The same route is quantified in planted arcs at fixed N = 300, varying only the end-gap:

| end-gap | closed |
|---|---|
| 2.4 σ (N = 80) | 5/5, all by step 5 000 |
| 3.0 σ | 5/5 |
| 6.0 σ | 3/5 |
| 9.0 σ | 2/5 |

A rate that falls steeply with gap. Note the table's header and its first row disagree on N; the row
labelled N = 80 is not from the N = 300 series, and the discrepancy is preserved here rather than
quietly tidied.

**Re-measured on the corrected instrument**, at fixed N = 70 with the arc radius held constant and only
the end-gap varied, after the enclosure detector and cluster connectivity were both fixed:

| end-gap | closed | seeds |
|---|---|---|
| 3.4 σ | **5/5** | 5 |
| 6.7 σ | **4/5** | 5 |
| 10.1 σ | **1/10** | 10 |

Interpolating between 0.8 and 0.1 puts the 50% point near **8 σ** — a capture radius. The widest gap
carries 10 seeds because at 5 seeds the only outcome that could reach p < 0.05 against a contrasting
condition was a perfect sweep.

Gap values are quoted from the plant formula, not from the logged `R_mid`: that column is a median
distance from the aggregate centroid, and for an arc the centroid is offset from the ring centre, so it
reads about 10% low at span 0.75. The earlier series used the measured value and therefore understated
its gaps by 4–11%, all in the same direction, which leaves its ordering intact.

Two things the re-measurement changes. The widest-gap rate is **1/10, not 2/5** — better powered and
lower. And closure, when it happens, is **fast**: at 3.4 σ four of five seeds had closed by the first
checkpoint at 10 000 steps, against a 300 000-step budget. So the earlier reading that "even 9 σ closes
given time" is not supported at 10 σ; time is not the limiting variable, reach is.

The emergent vesicle is this process at work: a long meandering ribbon whose ends found each other. It
also explains the failures directly, **provided** emergent ribbons carry ends further apart than the
capture radius. That premise is **not measured**. Two attempts to quantify an end-to-end gap on saved
states have failed the same positive control: a closed ring, which has no termini at all, reads 134
tips under a tip-counting metric and 16 termini under a contact-degree metric. Local degree cannot
locate the end of a *bilayer*, where the two leaflets join in a rounded cap, so both metrics measure
boundary roughness instead. Until a detector passes that control, the statement that emergent ends are
too far apart rests on inspection of renders, not measurement, and is flagged here as such.

![flat stays flat](figures/04_flat_bilayer_does_not_curl.png)

*A planted flat bilayer after 200 000 steps with imposed 4/6-tail leaflet asymmetry: still straight,
fully intact. 0/5 closed.*

## Bending rigidity, measured without a spectrum

The undulation-spectrum route to kappa failed here: per-mode estimates spread 16.7x at 60 lipids and
1712x at 120, with a flat-in-q spectrum, meaning the estimator was measuring its own sampling noise.
The replacement is a plain energy difference between two PLANTED configurations of the same lipid
count -- a closed ring and a three-quarter arc -- at a known radius. No spectrum, no per-mode fit.

Geometry: the arc carries the same arc length at 1.333x the ring radius, verified numerically (ring
2*pi*11.65 = 73.2 against arc 0.75*2*pi*15.53 = 73.2). So

> E_ring - E_arc = 0.4375 * pi * kappa / R - 2 * lambda

Measured at N = 70, R_ring = 11.65, averaging E/lipid over steps >= 30 000, **10 independent seeds per
configuration**:

| | E/lipid |
|---|---|
| ring | -7.3415 +- 0.0588 |
| arc | -7.2498 +- 0.0371 |
| **difference** | **-6.4 +- 4.9 eps total (1.3 sigma)** |

With lambda = +2.8 +- 2.8 eps (below), this gives

> **kappa = -6.1 +- 56.3 eps = -13 +- 125 kT**, consistent with zero.

**What this establishes and what it does not.** The central value implies bending is essentially free,
which would make closure thermodynamically favourable at any size. But the ~150 kT threshold above
which closure stops being favoured sits only **1.3 sigma** from the centre, so the measurement is
*consistent with* favourable closure without establishing it tightly. A single radius also cannot
separate kappa from lambda -- the two are degenerate along the line above -- so this number depends on
the independent lambda. A second radius (N = 300) breaks the degeneracy and is in progress.

**Two cautions found while verifying it.** The measured `R_mid` column is NOT the ring radius for an
arc: the arc's centroid is offset from its ring centre, so R_mid reads about 10% low at span 0.75 and
worse as span falls. It is correct for a full ring. And an earlier single-seed version of this same
measurement gave -31.7 eps, five times the 10-seed value; the estimate fell monotonically as seeds were
added (-31.7, -9.6, -6.4), which is the signature of a noise-driven number rather than a real effect
being resolved.

**A stale figure corrected.** The project's standing brief carried lambda = +18.31 +- 7.07 eps. That
value was superseded by the re-measurement recorded below (+2.8 +- 2.8, traced to
`chi[TAIL,WATER] = 0.00`). Using the stale figure with the same energy data would give kappa = 508 +-
252 kT, placing closure far outside the favourable regime and contradicting the emergent vesicles
reported above.

## Limits

- **It is a vesicle with appendages, and the split is measured.** `shell_split()` counts which lipids
  line the lumen. Of 160 lipids, **~101 form the shell and ~59 are attached material**. Correcting the
  expectation for that, the shell alone reads **0.662-0.714** against **0.876** for a planted vesicle
  -- so the raw 0.28 understates shell quality by about 2.5x. `reach` is calibrated on a planted
  vesicle, which must return (120, 0): 2.5 gives 98/22 because it reaches only the inner leaflet,
  5.0 is where the control comes out clean.

  | structure | total | shell | appendage | raw | corrected |
  |---|---|---|---|---|---|
  | planted vesicle N=120 (control) | 120 | 120 | 0 | 0.876 | 0.876 |
  | emergent, persistence sd21 | 160 | 101 | 59 | 0.285 | 0.714 |
  | emergent, persistence sd22 | 160 | 102 | 58 | 0.281 | 0.691 |
  | emergent, frozen candidate | 160 | 102 | 58 | 0.269 | 0.662 |

  **The appendages are passengers, not load-bearing** -- settled with 10 seeds per condition, scored on
  the fraction of checkpoints closed over a common step range rather than on a single endpoint:

  | condition | closed fraction | never closed |
  |---|---|---|
  | bare 102-lipid shell | 0.594 +- 0.141 | 2/10 |
  | full 160-lipid object | 0.565 +- 0.119 | 0/10 |

  Difference **-0.029 +- 0.184, i.e. 0.2 sigma.** Deleting the 58 appendage lipids does not destabilise
  the closure, so the corrected ratio describes a self-supporting object. (An earlier version of this
  section claimed the opposite from a 5-seed endpoint read in which one seed was scored mid-run; that
  is withdrawn.)

  An independent check of `shell_split` fell out of building that state: with the appendages gone the
  RAW ratio is 0.656-0.657, which is the CORRECTED ratio computed with them present (0.662).
- **It is 2-D, and 3-D is out of practical reach.** The old blocker -- explicit solvent being fragmented
  droplets -- **is a chi_WW artefact and is retired**, with a positive control that reproduces the
  recorded phenomenon. At 6618 waters:

  | chi_WW | largest water cluster / all water |
  |---|---|
  | 1.00 (the value the void was recorded at) | **0.252, 0.202, 0.218** -- at or below the recorded 0.27-0.48 |
  | 0.50 | **1.000, 1.000, 1.000** | But the solvent was never the only
  obstacle. A 4-tail bilayer is ~9 sigma thick, so a patch reads as flat only above ~500 lipids and
  convincingly only near ~2000; a 3-D vesicle needs the same, since it too needs R > thickness. Runs at
  N = 60 and N = 200 are both **thicker than they are wide** and cannot show a bilayer even in
  principle -- the observed 3-D micelles (5/5 isotropic, thickness 4.5-5.5 sigma) are what a too-small
  box must produce. At N = 200 the cost was already 15+ hours, so the required system is a further
  order of magnitude beyond this setup.
- **The appendaged form is a kinetic trap, not a preferred morphology.** Real vesicles do bud and
  tubulate, so the shape is not by itself disqualifying -- but in this model it is measurably NOT the
  favoured state. A planted single 160-ring, same lipids and conditions, sits at **-7.502 +- 0.023**
  eps/lipid against the emergent structure's **-7.158 +- 0.033**: the emergent form is **+55 +- 6 eps
  (122 kT) higher, at 8.5 sigma**, and the single ring encloses ratio 0.76-0.85 against 0.28. Real
  budding is driven by excess area at fixed enclosed volume and by spontaneous curvature; this model
  has no volume constraint and, measured five different ways, no spontaneous curvature at all.
- **Survival from a known vesicle is 8/10 over 200 000 steps -- and this does NOT extend to the full
  run length.** Every vesicle in the corpus that was detected *before* its run's endpoint had dissolved
  by 1 600 000 steps (4 of 4: seeds 1000, 1002, 1101, 1203). The only vesicle present at an endpoint,
  seed 1007's, was first detected at that endpoint. Seed 1000's vesicle *was* the largest cluster (82
  lipids) when detected and the network is 116 lipids at the end, so it was consumed rather than merely
  lost to view. These vesicles are kinetic intermediates, not terminal states. That is consistent with
  the +262 eps vesicle-over-sponge result, which held the lipid count fixed: a 41-lipid vesicle beside a
  114-lipid network carries its own edge, and merging removes it, so the small coexisting vesicle was
  never the ground state. The 8/10 figure is scoped to 200 000 steps starting from a known vesicle and
  licenses no claim about the 800 000-1 000 000 step remainder of a full run.
  Measured on the persistence arms, which
  checkpoint every 10 000 steps -- eight times finer than the emergence runs. Six of ten runs dipped
  below the gate at least once, but **four of those recovered and ended closed**; only two ended open.
  So a first sub-threshold checkpoint is NOT a death time, and gate-crossings are mostly transient dips
  in a structure that is still present. Episode-based lifetime statistics computed on the coarse
  emergence checkpoints understate persistence for exactly this reason.

- **Seven formations observed, with mixed fates.**

  | seed | peak ratio | fate |
  |---|---|---|
  | em160 lineage | -- | persisted; 3/5 on restart |
  | long sd80 | 0.522 | dissolved by 1.12 M |
  | long sd82 | 0.196 | persisted 1.12 -> 1.6 M |
  | prev sd1000 | 0.131 | gate-flicker; object persisted ~1 M |
  | prev sd1002 | 0.249 | dissolved by 1.6 M |
  | prev sd1007 | 0.232 | present at run end |
  | prv2 sd1101 | 0.328 | dissolved by 1.04 M |

  **Peak score does not predict fate**: 0.522 and 0.328 both dissolved while 0.196 persisted.

  An eighth formation, in a 20 000-step-checkpoint arm, was present at one checkpoint only -- **lifetime
  under 40 000 steps**, beneath the 80 000-step resolution floor of every other arm. Coarse arms would
  have recorded it as an 80 000-step episode or missed it entirely, so the episode durations quoted
  elsewhere are resolution-limited upper bounds on the short end, not measurements.

  Two distinct failure modes, each documented more than once. **Genuine dissolution** -- the cluster
  changes size and the lumen goes to zero and stays there (seeds 80, 1002, 1101). **Gate-flicker** --
  the object is unchanged while its raw ratio crosses the 0.10 threshold (seed 1000, whose 82-lipid
  aggregate held an enclosure at 6 of 7 checkpoints while the score passed only 3 times).

  **The run-level figure, across the whole corpus.** Consecutive checkpoints within a run are not
  independent -- a vesicle persists across several -- so the independent unit is the run:

      12 of 70 dispersed runs produced a vesicle.   17.1%,  Wilson 95% CI  10.1% to 27.6%

  That figure pools runs of different lengths, which matters because one vesicle first appeared at
  1 500 000 steps of a 1.6M run -- later than any other in this project, and later than several arms
  ever ran. Restricting to the runs that all reached exactly 1.6M gives a cleaner, smaller sample:

      6 of 28 length-matched runs produced a vesicle.   21.4%,  Wilson 95% CI  10.2% to 39.5%

  The two overlap heavily and neither is the more correct number; the pooled figure has the tighter
  interval, the length-matched one is free of the truncation question. Both are lower bounds while that
  question is open -- a 2.4M arm is running to settle whether 1.6M cuts runs short.

  **The two instruments AGREE, once the better one has 20 runs:**

  | subset | rate | 95% CI |
  |---|---|---|
  | all-cluster scoring (can see coexisting vesicles) | 4/20 = **20.0%** | 8.1-41.6% |
  | largest-cluster scoring only | 5/36 = 13.9% | 6.1-28.7% |

  20.0% falls inside the largest-cluster interval, so **at this sample size the two cannot be
  distinguished**. That is a statement about resolution, not evidence of no bias.

  At the level of individual detections the bias is visible: **2 of the 5 hits in the all-cluster arms
  were coexisting vesicles**, invisible to largest-cluster scoring -- seed 1007 (a 41-lipid vesicle
  beside a 119-lipid network) and seed 1203 (twice). That is roughly 40%, which fits comfortably inside
  the overlapping intervals and would need far more than 20 runs to resolve. The pooled 16.1% should
  therefore be read as a **lower bound**.

  The clearest single demonstration: the 6-seed fine-resolution arm scores **1/6 by all-cluster and 0/6
  by largest-cluster**, because its only formations were coexisting. That arm would have been recorded
  as a clean zero by the older instrument.

  An earlier version of this section reported the all-cluster arm at 3/10 = 30% and flagged a possible
  undercount; the second ten came back **1/10**, so that particular figure was a high draw.

  The cleanest arm -- the only one scored with `count_vesicles` on every cluster at every checkpoint --
  gives 3/10, consistent with the pooled figure. Three of its runs are still short of full length, so
  the figure is a lower bound.

  **One of those hits was invisible to largest-cluster scoring.** In seed 1007 the largest cluster is a
  119-lipid open network with `n_enclosed = 0`; the vesicle is a separate **41-lipid** cluster (lumen
  124, ratio 0.232, stable across bead 1.0-3.0, shell 32 with 9 appendages). Under the older scoring that
  run counted as a clean zero. The geometric lumen-ratio threshold of 0.10 is weaker than first claimed. It was
  placed "inside a tenfold gap" between a branched net at 0.028 and a closed arc at 0.295, but nothing
  in that calibration was an appendaged vesicle. A **planted** vesicle measures **0.118** -- below the
  emergent seed 1301 at 0.151 -- because appendages add lipids without adding lumen. The gate's
  exposure is therefore false NEGATIVES, which makes the 16.1% rate a stronger lower bound. 

  **CORRECTION (supersedes the paragraph above).** Every ratio quoted above -- 0.232, 0.118, 0.151,
  0.028, 0.295 -- was computed with a cluster-connectivity routine that prefiltered on the mean of
  WRAPPED coordinates, which is meaningless for a molecule straddling the periodic boundary. On one
  N=80/L=46 state that prefilter rejected 35 real bead-contacts and split one 80-lipid aggregate into
  [27, 19, 15, 6, 2, ...]. The same defect made the enclosure detector blind to any aggregate sitting on
  a boundary: an identical planted ring scored n_enclosed 1 centred and 0 on the edge. Both causes are
  fixed and regression-tested at four ring positions.

  Re-derived with correct clustering, the DIRECTION of the claim above survives and its magnitude grows.
  A render-confirmed emergent vesicle (sd1306) reads raw ratio **0.032** and a PLANTED vesicle reads
  **0.092**, both BELOW the 0.10 gate. The reason is structural: when a vesicle is attached to a larger
  aggregate, its lumen is normalized against the whole merged cluster, so the ratio collapses. The gate
  therefore counts FREE-STANDING vesicles and systematically misses attached ones, which is why it finds
  only 5 hits across 78 emergent endpoint states.

  **RETRACTED: `lumen_water_density` as an independent check.** Corrected, lumen water sits near bulk
  for almost any enclosed region: render-confirmed vesicles span 0.586-1.332 and render-confirmed
  tangles span 0.545-1.384, overlapping almost completely. Tested blind against 25 visually adjudicated
  states it agrees 7/25 = 0.280, against 0.720 on the buggy metrics. It rules out dry sealed artifacts
  and nothing more. **RETRACTED: shell normalization** as a fix for the appendage bias -- corrected, it
  returns ratios of 8.0, 11.8 and 172.8, which are geometrically impossible, because `shell_split`
  assigns almost every lipid of a merged cluster to "appendage".

  The driver's radial `lumenW` column is a separate matter and remains unusable for this purpose: it
  measures water near the whole aggregate's centroid and returns 0 for any vesicle sitting off to one
  side.

  "Coexisting-only" is a detection category, not a distinct physical
  mode: the largest-cluster sizes overlap completely between the two categories (64, 67, 82, 92, 119,
  132), so the label records only that the vesicle happened to be smaller than the biggest aggregate in
  the box. There is one kind of vesicle here, scored by two instruments.
  Small vesicles coexisting with larger networks are real and are only
  counted by `count_vesicles`.

  An earlier version compared two arms at checkpoint level (0/210 against 4/60) and called the
  difference unexplained. That was **pseudo-replication**: at run level it is 0/10 against 3/5,
  Fisher p = 0.022 -- notable, but a post-hoc comparison and far weaker than the checkpoint framing
  implied. The physics is identical across arms: rerunning `rate` seed 30 under the current binary
  reproduces steps 0, 80 000 and 160 000 exactly.

  Extending the rate arm to 3.2 million -- a window that does contain the 1.96-million formation time --
  added almost nothing: **1/210 checkpoints, 1 onset in 10 runs, 0/10 holding a vesicle at the end.**
  So the earlier "mis-specified window" explanation accounts for only a small part of the shortfall.
- **It does not improve with time.** Over 600 000 steps and five seeds the composition is static --
  shell 100-110, appendages 50-60 -- and one seed degraded outright (shell 26, lumen 45). The shell
  closed at ratio 0.501 and was at its best the moment it formed.

## Reproducing

```bash
bazel build //projects/vivarium:_mixture
# dispersed start, N=160 in L=65
OMP_NUM_THREADS=1 VIVARIUM_CHI_HT=-0.25 VIVARIUM_CHI_WW=0.50 \
  bazel-bin/projects/vivarium/_mixture 1600000 2 160 0.0 65.0 0.45 0.55 random <seed>
```

Score any saved state with `vesicle_call()` in `_lumen_field.py`. The frozen candidate is
`docs/states/vesicle_candidate_frozen.npz`.

Full chronology, including every retraction, is in [AUTONOMOUS_LOG.md](AUTONOMOUS_LOG.md).
