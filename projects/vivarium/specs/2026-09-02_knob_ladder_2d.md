# The knob ladder — replace every hand-set affinity in the 2-D vesicle model, one at a time

**Registered 2026-09-02, before any rung is run.** 2-D only. The 3-D track stays parked behind
`docs/REVIEWER_HANDOFF_2026-08-31.md`.

## Objective

The 2-D model emerges a vesicle. Its chemistry is six hand-set pair affinities — numbers a person
chose. The claim we want is that vesicles follow from **physics and geometry**, so every one of those
six must either be **replaced by a geometric or thermodynamic mechanism** or **shown to be
irreducible**. Replace, not delete: deleting a term and watching the system still clump proves
nothing, because clumping is not the target behaviour.

## Why the endpoint changes

Every knob test so far was scored on **self-assembly vesicle rate**, which is 2/18 ~ 11%. At six seeds
per arm that design cannot resolve anything: the previous rung returned 0/6 vs 0/6, and 0/6 is the
*expected* result for both arms. Roughly 300 seeds per arm would be needed to detect even a doubling.
Two full-length runs were spent learning this.

The project already has a far better endpoint. Closure is controlled by the ribbon's **end-to-end
gap** — the one reaction coordinate here that has ever been validated — and it gives a steep,
well-powered dose-response (`docs/RESULTS.md`):

| end-gap | closed |
|---|---|
| 3.4 sigma | 5/5 |
| 6.7 sigma | 4/5 |
| 10.1 sigma | 1/10 |

Fisher on the two extremes is p = 0.0020 (computed, not quoted). Closure is also *fast* — 4/5 seeds closed by step 10,000
against a 300,000 budget — so each run is ~30x cheaper than a self-assembly run. This converts a rare
event into a graded measurement, which is the only way to test six knobs in one session.

**Geometry of the assay, re-derived and checked.** `_mixture._plant_ring(span=s)` puts `n` lipids on
an arc at `R_mid = n*lat/(4*pi*s)`, `lat = 2` for a branched 4-tail lipid, so the missing sector's arc
length is

    gap = 2*pi*R_mid*(1 - s) = (n*lat/2) * (1 - s)/s

Checked against the two radii published with the table: N=70 at gap 10.1 gives R_mid 12.75 (published
12.8); N=300 at gap 10.1 gives 49.35 (published 49.3). The harness inverts this to place a requested
gap.

## Instrument gate — runs BEFORE any rung, and can fail

The assay is only usable if it reproduces the published dose-response **under production chemistry**.

    GATE I: closure at 3.4 sigma  >=  4/5      AND
            closure at 10.1 sigma <=  3/10     AND
            Fisher one-sided p    <=  0.05

`closed` is fixed here as **`n_enclosed >= 1` at any checkpoint** — the detector the published table
names. `vesicle_call` is recorded alongside but is NOT the gate; choosing between them after seeing
data is exactly the yardstick failure this project has already committed once.

If GATE I fails, no rung is run and the session's finding is that the reaction coordinate does not
reproduce — which is itself a result worth having, since two documents depend on it.

## Instrument controls, run before the gate (2026-09-02)

The detector must read the PLANT as not-closed, or the assay measures the plant. On the freshly built
arc at step 0, with no dynamics:

| planted arc, step 0 | n_enclosed @ bead 1.0 / 1.5 / 2.0 / 3.0 | vesicle_call |
|---|---|---|
| gap 3.4 sigma | `[0, 0, 0, 1]` | False |
| gap 6.7 sigma | `[0, 0, 0, 0]` | False |
| gap 10.1 sigma | `[0, 0, 0, 0]` | False |
| gap 20 sigma | `[0, 0, 0, 0]` | False |
| **closed ring, gap 0 (positive control)** | `[1, 1, 1, 1]` | **True** |

The registered endpoint uses **bead = 1.0** and reads 0 on every planted arc, so it responds to
dynamics rather than to geometry handed in at step 0. The positive control fires at every dilation.

Worth stating plainly: at dilation **3.0 the detector bridges a 3.4 sigma gap by itself**. Had the
endpoint been `vesicle_call` -- whose gate 1 requires a stable count across dilations 1.0-3.0 -- the
near arm would have been partly an artifact of the instrument. It was registered as `n_enclosed` at
bead 1.0 before this control was run, which is the only reason the choice was not made by the data.

## The ladder

`chi_TT = 0.70` is **kept and declared irreducible**: it is dispersion between alkane-like tails, the
one cohesive interaction, and there is no geometry that can stand in for "matter attracts". A model
with zero attractions has no condensed phase. Removing it is not a knob reduction, it is deleting the
physics. This is stated now so it cannot later look like the one term we happened not to test.

| rung | knob | current | replaced by | mechanism |
|---|---|---|---|---|
| 1 | `chi_HT` | -0.25 | 0.00, with `sigma_head` < `sigma_tail` | amphiphilicity as **geometry** — a head that is a different size, not a head that dislikes tails |
| 2 | `chi_HH` | +0.20 | 0.00 | heads keep excluded volume only |
| 3 | `chi_HW` | +0.75 | solvent-averaged | Flory-Huggins |
| 4 | `chi_TW` | 0.00 | solvent-averaged | Flory-Huggins |
| 5 | `chi_WW` | +0.50 | solvent-averaged | Flory-Huggins |
| 6 | explicit water | phi = 0.55 | removed | the hydrophobic effect becomes an **effective** tail-tail attraction |

Rungs 3-6 are one physical idea applied stepwise. `field.solvent_averaged_chi` already implements it:
`eff[i,j] = chi[i,j] + chi[WW] - chi[i,W] - chi[j,W]`. That is the standard reduction of a solvent to
an effective interaction, not a deletion — the water terms reappear inside `chi_TT_eff`. Rungs 3-5
zero each water term singly (so a single-variable A/B exists for each), rung 6 does the full
substitution and removes the solvent.

## Per-rung protocol

Each rung is a single-variable A/B against the rung below it, **not** against production, so the
ladder composes:

- arms: `previous rung's chemistry` vs `previous + this replacement`
- gaps: 3.4 and 10.1 sigma, 10 seeds per gap per arm (40 runs per rung)
- steps: 300,000, checkpoint every 10,000
- fresh seeds per rung, never reused across rungs

```
RUNG PASSES iff   closure(3.4) is not degraded:  arm >= 6/10  AND  Fisher vs baseline p > 0.05
            AND   the coordinate still discriminates: closure(3.4) > closure(10.1), Fisher p <= 0.05
```

The second clause is the criterion **we can fail by winning**. A replacement that made everything
close at every gap would pass the first clause and fail this one, and it would deserve to: it would
have destroyed the reaction coordinate rather than preserved the physics. A knob replacement must keep
the *shape* of the dose-response, not merely keep the numbers high.

## Secondary, reported but never gating

Self-assembly aggregation quality at the end of each rung, so a replacement that preserves closure but
destroys assembly is visible. Not gating, because it is the low-power endpoint this spec exists to
stop relying on.

## What each outcome means, written before the data

- **All six rungs pass.** The 2-D vesicle needs one attraction (tail-tail) plus geometry. That is a
  real claim and the strongest available from this project.
- **A rung fails.** That knob is load-bearing and we have located *which* physics is not being
  captured by geometry. More informative than a pass; the ladder stops there and the failure is
  characterised.
- **GATE I fails.** The reaction coordinate does not reproduce. Everything resting on the gap result
  needs re-examination before any knob work continues.
- **Rungs pass but assembly collapses.** Closure and assembly need different chemistry; the
  reduction is real for one and not the other, and must be reported that way.

## Threat register

- `n_enclosed` is a **2-D** detector and is broken in 3-D. This spec is 2-D only, inside its
  validated domain.
- The arc assay tests **closure given a membrane**, not assembly-then-closure. Stated as a scope
  limit, not worked around; the secondary endpoint is the partial cover.
- The assay hands the system its curvature. It therefore cannot show that curvature *emerges* — only
  that a knob replacement preserves closure once curvature exists. Both this and the point above mean
  a full pass supports "the chemistry reduces", NOT "vesicles emerge from geometry alone".

---

## Amendment 1 — 2026-09-02, before any rung runs

**Every rung gets a REMOVAL arm as well as a REPLACEMENT arm.** As first written, rung 1 changed two
things at once (`chi_HT -> 0` and `sigma_head -> 0.95`), so a pass could not distinguish

- *geometry substitutes for the affinity* (the claim), from
- *the affinity was never load-bearing* (a much weaker statement, and the likelier one).

Each rung therefore runs three arms against the same gaps and seeds:

| arm | chemistry | what a pass means |
|---|---|---|
| **A** baseline | the rung below, unchanged | the control |
| **B** removal | knob zeroed, nothing added | the knob was not load-bearing |
| **C** replacement | knob zeroed + the geometric/thermodynamic mechanism | the mechanism carries it |

Readings:

- **B passes** -> the knob was decoration. Report it as removed, and say plainly that no replacement
  was needed. Do NOT credit the mechanism in C for work that B shows was unnecessary.
- **B fails, C passes** -> the substitution is real. This is the only pattern that supports
  "physics and geometry replace the hand-set number."
- **B fails, C fails** -> the knob is load-bearing and the proposed mechanism does not cover it. Stop
  the ladder and characterise.
- **B passes, C fails** -> the added mechanism is harmful. Keep the removal, discard the replacement.

Cost: 3 arms x 2 gaps x 10 seeds = 60 runs per rung, ~11 min each, ~66 min wall at 10 workers.

**Stated in advance so a rung-1 pass is not over-read.** Production amphiphilicity does not rest on
`chi_HT` alone. Heads are held in water by `chi_HW = 0.75` while tails are indifferent at
`chi_TW = 0.00`, and that solvophobic contrast is probably the larger driver. So arm B passing at
rung 1 is the *expected* outcome, and `sigma_head` is expected to be a weak lever. The head-area
sweep that would have told us this (H1/H2, 39 runs) was scored on the 3-D-broken `n_enclosed` and
establishes nothing. Rung 1 is the first honest test of head size on a working endpoint.

---

## GATE I — PASSED, 2026-09-02

20 runs, production chemistry, N=70, L=45, kT=0.45, phi=0.55, 300,000 steps, seeds 100-109.

| gap | closed (registered endpoint) | published | vesicle_call |
|---|---|---|---|
| 3.4 sigma | **10/10** | 5/5 | 9/10 |
| 10.1 sigma | **2/10** | 1/10 | 0/10 |

    rung 0 (production): near 10/10 vs far 2/10, Fisher one-sided p = 0.0004
      coordinate still discriminates (near > far, p <= 0.05): True
      GATE I (reproduces the published dose-response): True

Both criteria met (near >= 4/5, far <= 3/10, p <= 0.05). The reaction coordinate reproduces on the
production stack, and the strict `vesicle_call` gate separates the arms even harder than the
registered endpoint does (9/10 vs 0/10).

**Checked against renders, not believed from the count.** `docs/figures/gap_3.4_closed.png` is a
continuous closed bilayer ring with a water-filled lumen, heads on both faces and a tail core between.
`docs/figures/gap_10.1_open.png` is an open C with two free ends that never met. The metric and the
picture agree.

Two rendering notes worth keeping. The first render plotted `np.mod(X, L)` and put the ring in the
four corners of the box, where it reads as four separate fragments -- `_plant_ring` builds around the
origin. `gap_shot.py` now recentres on the CIRCULAR mean of the lipid beads, which is defined across a
periodic boundary where an arithmetic mean is not. And re-running seed 100 for 40,000 steps reproduced
the 300,000-step result exactly (closed at step 10,000, `vesicle_call` true), so the engine is
deterministic under this harness.

## Amendment 2 — 2026-09-02, before rung 1

**Two changes, both to cost, neither to the registered endpoint.**

1. **The baseline arm is not re-run.** Rung N's arm A is rung N-1's winning arm, already measured on
   the same gaps and the same seeds. Each rung is therefore 2 arms x 2 gaps x 10 seeds = 40 runs, not
   60.
2. **A run stops 50,000 steps after its first closure** instead of always running 300,000. The
   registered primary endpoint is "n_enclosed >= 1 at ANY checkpoint", so stopping after the first
   one is exactly equivalent for it -- the value is already determined. Runs that never close are
   unaffected and still run the full 300,000.

The 50,000-step tail is not padding: it converts `n_enc_final` and `vesicle_call` into a **persistence**
check -- did the ring that formed survive 50,000 further steps of thermal noise. `steps_run` is
recorded per row so nothing is hidden.

**The cost of this, stated plainly.** For rungs >= 1 the secondary `vesicle_call` is evaluated at
closure + 50,000 steps rather than at a fixed 300,000, so it is NOT comparable across rung 0 and later
rungs. The primary endpoint is comparable throughout; the secondary is comparable only among rungs
1-6. Measured saving: ~40% of the step budget per rung.

### Amendment 2a — seeds are PAIRED across arms, not fresh per rung

The original protocol said "fresh seeds per rung, never reused across rungs". Amendment 2 reuses rung
N-1 as rung N's baseline arm, which requires the SAME seeds. The two rules contradict, so this states
which wins and why.

**Seeds 100-109 are used for every arm of every rung.** A knob replacement is compared against its
baseline on the *same initial conditions*, which is a paired design and strictly more powerful than
independent seeds: it removes between-seed variation in how closure-prone a given planted arc is.

The cost is that a seed which happens to favour closure favours it in both arms. That inflates the
*absolute* rate, not the *difference*, and the difference is what every rung gate tests. Where an
absolute rate is quoted (e.g. "10/10 at 3.4 sigma"), it is a property of these ten arcs, not a
population estimate, and is written that way.

Fresh seeds still matter for REPLICATION -- H5 is using seeds 7-18 precisely because seeds 1-6
generated its hypothesis. That is a different purpose from pairing arms within a rung.

---

## RUNG 1 — chi_HT — BOTH ARMS PASS, 2026-09-02

40 runs, seeds 100-109 paired against the rung-0 baseline.

| arm | chemistry | near 3.4 sigma | far 10.1 sigma | Fisher (near vs far) |
|---|---|---|---|---|
| A (rung 0) | production, `chi_HT = -0.25` | 10/10 | 2/10 | 0.0004 |
| **B** removal | `chi_HT = 0` | **9/10** | **0/10** | 0.0001 |
| **C** replacement | `chi_HT = 0`, `sigma_head = 0.95` | **10/10** | **0/10** | 0.0000 |

Gate: near >= 6/10 (both pass), not degraded against baseline (9/10 and 10/10 against 10/10, no
degradation), coordinate still discriminates (both pass, p <= 0.05).

### The verdict, read by Amendment 1's rules

**B passes, so `chi_HT` was decoration.** It is removed, and NO replacement was needed. Per the
reading fixed before the data: *"Do NOT credit the mechanism in C for work that B shows was
unnecessary."* Arm C also passes, and slightly more cleanly (10/10 against 9/10), but that difference
is one seed and is not evidence for head size doing anything.

This is the outcome registered in advance as the expected one, and the reason matters: production
amphiphilicity does not rest on `chi_HT`. Heads are held in water by `chi_HW = 0.75` while tails are
indifferent at `chi_TW = 0.00`, and that solvophobic contrast is the larger driver. The knob that was
described in `field.py` as "THE HEAD-TAIL CROSS TERM IS WHAT MAKES AN AMPHIPHILE" is, on this
endpoint, not what makes an amphiphile.

**The chemistry carried into rung 2 is arm B** -- `chi_HT = 0`, `sigma_head = 1.0`. Arm C's head size
is dropped, because adding a geometric parameter that buys nothing is a knob gained, not a knob
removed, and the point of the ladder is the count.

### An unregistered observation, flagged as such

The far arm fell from 2/10 at baseline to **0/10 in both rung-1 arms**. Removing `chi_HT` appears to
have *sharpened* the coordinate rather than blunting it. This was not a registered endpoint, n is
small, and the project has watched three effects this size evaporate. Recorded, not claimed.

### Render check

`docs/figures/rung1B_closed.png` -- seed 100 at gap 3.4 with `chi_HT = 0` is a closed ring with a
water-filled lumen. The heads are visibly less well segregated than in the baseline render, which is
what removing the head-tail term should look like, and the ring closed regardless.

## Rung 2 design note — some knobs have no replacement other than removal

`chi_HH = 0.20` is head-head attraction. The "mechanism that replaces it" in the ladder table is
"heads keep excluded volume only", which is *exactly what setting it to zero does*. Arms B and C would
be the same run, so **rung 2 has only arm B, 20 runs**. If it fails, a genuine arm C (head size
compensating for the lost head-head cohesion) becomes the next thing to try, and would be registered
then.

---

## RUNG 2 — chi_HH — PASS, 2026-09-02

20 runs, one arm (B and C would be the identical run; see the rung 2 design note).

| arm | chemistry | near 3.4 sigma | far 10.1 sigma | Fisher |
|---|---|---|---|---|
| A (rung 1B) | `chi_HT = 0` | 9/10 | 0/10 | 0.0001 |
| **2B** | `chi_HT = 0`, `chi_HH = 0` | **8/10** | **0/10** | 0.0004 |

Gate: near 8/10 >= 6/10, not degraded against the 9/10 baseline, coordinate still discriminates.
**PASS.** Two of six hand-set affinities are now gone, with nothing added in their place.

Render: `docs/figures/rung2B_closed.png`, seed 100 at gap 3.4 -- a closed ring with a water-filled
lumen and no head-head or head-tail term anywhere in the chemistry.

Trend across the ladder so far, at the near gap: 10/10 -> 9/10 -> 8/10. Each step is within one seed
of the last and each passes its gate, but the direction is monotone downward and worth watching. If it
continues, the ladder will fail on a cumulative slide rather than on any single rung, and the gate as
registered ("not degraded against the rung below") cannot see that. **Registered now, before rung 3:
if the near arm reaches <= 6/10 at any rung, the cumulative comparison against rung 0 (10/10) is
reported alongside the per-rung one, whatever the per-rung gate says.**

## Rungs 3-5 are REMOVAL-ONLY; rung 6 is the replacement

Flory-Huggins solvent averaging is `eff[i,j] = chi[i,j] + chi_WW - chi[i,W] - chi[j,W]`. It cannot be
applied to one water term in isolation -- it is a single substitution that consumes all three at once
and removes the solvent with them. So rungs 3, 4 and 5 zero `chi_HW`, `chi_TW` and `chi_WW` singly, as
REMOVAL arms whose purpose is to locate which water term is load-bearing, and rung 6 performs the
actual replacement. Stated here so the absence of a C arm in rungs 3-5 is not later read as an
omission.

`chi_HW = 0.75` against `chi_TW = 0.00` is the contrast rung 1 identified as the true amphiphilic
driver. **Rung 3 is therefore the first rung expected to FAIL**, and a failure is the informative
outcome: it would locate the physics that geometry has to reproduce.

---

## H5 — the assembly-side enclosure replication — FAILS, 2026-09-02

Registered in `specs/2026-09-02_H5_enclosure_replication.md`. Fresh seeds 7-18, 12 per arm, 1e6 steps.

| | seeds with >= 1 enclosure | vesicle calls | mean largest |
|---|---|---|---|
| `chi_HT = -0.25` (knob IN) | **4/12** | 0 | 111.8 |
| `chi_HT = 0.00` (removed) | **4/12** | 0 | 117.5 |

    Fisher one-sided p = 0.6666
    GATE: removed >= 6/12 (False), baseline <= 2/12 (False), p <= 0.05 (False)  ==> FAILS

The original signal was 4/6 against 0/6, p = 0.0303, post-hoc. It is gone. Note *which* half moved:
the baseline's 0/6 was the fluctuation -- it now returns 4/12, the same as the removed arm. The effect
was never in the treatment.

**This is the fourth small-sample effect to evaporate on replication in this project**, and the
outcome registered in advance for exactly this pattern was: *"The knob is neutral; report and move
on."* Which is also, independently, what rung 1 concluded from a completely different endpoint --
`chi_HT` does not matter. Two methods, one answer, and the honest one.

It is also the strongest available argument for the endpoint change. Twelve seeds per arm at 1e6 steps
cost about 3.3 CPU-hours per run and returned p = 0.67. The gap assay answered the same question at
higher confidence in a fraction of the time. **Neither arm produced a single vesicle in 24 runs**, so
the self-assembly endpoint remains unable to resolve anything at any n this project can afford.

---

## RUNG 3 — chi_HW — PASSES THE REGISTERED GATE, but degrades persistence

20 runs, seeds 100-109.

| arm | chemistry | near closed | far closed | Fisher | near **persisted** | vesicle_call |
|---|---|---|---|---|---|---|
| A (rung 2B) | `chi_HT = chi_HH = 0` | 8/10 | 0/10 | 0.0004 | 8/10 | 8/10 |
| **3B** | `+ chi_HW = 0` | **8/10** | **0/10** | 0.0004 | **5/10** | **5/10** |

**Gate verdict: PASS.** Near 8/10 >= 6/10, identical to the rung below (p = 0.709, no degradation),
coordinate still discriminates. Recorded as a pass because that is what the registered gate says, and
the gate was fixed before the data.

**But the registered gate cannot see what happened.** Persistence -- still enclosed at closure + 50,000
steps -- is the column that moved: 8/10 to 5/10. Through rungs 0-2 every ring that closed also
persisted; at rung 3 three of eight closures reopened. Seed 105 is the artifact: `closed = 1` at step
10,000, `n_enc_final = 0` at 60,000, and the render
(`docs/figures/rung3B_sd105_closed_notvesicle.png`) shows a thin breach at lower right. It closed and
came back open.

**The honest strength of this: NOT ESTABLISHED.** 8/10 against 5/10 is one-sided p = **0.1749** at
n = 10. It is a suggestion, not a result, and this project has watched four effects of about this size
evaporate. It is being powered rather than believed (see Amendment 3).

This is nonetheless the first rung where anything at all was lost, and it is the term predicted in
advance to be load-bearing: `chi_HW = 0.75` against `chi_TW = 0.00` is the solvophobic contrast rung 1
identified as the real amphiphilic driver once `chi_HT` turned out to be decoration.

## Rung 4 — chi_TW — VACUOUS, no run performed

`chi_TW` is **already 0.00 in the production chemistry**. Removing it is a no-op: the arm would be
bit-identical to rung 3B. No run was made, and none should be.

This matters for the ladder's headline count. Of the "six hand-set affinities", one of them was
already sitting at the value that means *no interaction*. `field.py` says so directly -- "At 0.00 a
tail is INDIFFERENT to water... With no cost to an exposed edge there is no drive to close one". So
the honest count of knobs that ever did anything is **five, not six**, and any final claim must say
five.

## Amendment 3 — 2026-09-02, after rung 3, before rung 5

**Persistence becomes a REPORTED co-primary from here on**, alongside the registered closure endpoint.
Defined as `n_enc_final >= 1`: still enclosed at the end of the run. It is reported for every rung
including the ones already run, since it is already in the results file and needs no new runs.

It does **not** retroactively change rung 3's verdict. The gate was fixed before the data and rung 3
passed it; moving the goalposts after seeing a number is the failure this whole spec exists to
prevent. What changes is what gets *reported*, not what counts as a pass.

**Rung 3 is being extended to 20 seeds (110-119 added) to power the persistence comparison.** At
n = 10 it is p = 0.17; the extension either establishes the loss or dissolves it. This is registered
before those runs exist, and the direction of the extension was not chosen by the data -- rung 3 is
extended because it is the *only* rung where persistence moved at all.

**Why this matters for the ladder's central claim.** Rungs 3-5 remove the water terms; rung 6 replaces
them with Flory-Huggins solvent averaging. If removing `chi_HW` genuinely costs persistence and the
solvent-averaged substitution restores it, that is the one clean demonstration in this whole project
of a hand-set chemical parameter being replaced by physics rather than merely deleted. If the rung-3
loss is not real, rung 6 has nothing to restore and the ladder's result is the weaker "these numbers
did not matter".
