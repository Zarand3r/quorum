# DECISIONS

Significant decisions, why they were made, and **how we will know if they were wrong**. Append-only.
Each entry carries a falsifiable success metric so the decision can be reviewed against outcomes
rather than against how reasonable it sounded.

**Overall goal:** emergent vesicles by any well-known open-source method, then transfer the learnings
to the transformer-based Vivarium.

**Top-level success metric:** a closed bilayer with an interior solvent lumen, formed from a
disordered start, in a solvent that passes the health gate — reproduced across ≥3 seeds.

---

## D1 — Freeze the Vivarium parameter search and reset to a reference ladder

**Date:** 2026-08-10 · **Baseline frozen at:** `3a70fce`

**Context.** F48/F49 withdrew the 2-D self-assembly result: repairing the solvent alone, with lipid
chemistry byte-identical, dropped `bilayer_frac` 0.746 → 0.111, and a gated re-search found no window
at any tail cohesion. Every prior structural number was measured while the solvent was collapsing.

**Options considered.**
1. Keep sweeping Vivarium's chemistry under the new solvent gate.
2. Declare a negative architectural result and stop.
3. Reproduce known-good self-assembly first, then bound it, then transformerise it.

**Chosen: 3.** Option 1 repeats the error that produced the retraction — tuning many coupled things at
once with no known-good anchor. Option 2 is not supportable: the failing system was never calibrated
against a target equation of state, and DPD demonstrates bounded pairwise forces *can* make
amphiphile phases, so "the architecture cannot" does not follow from "these parameters did not".

**Success metric.** Each ladder rung reproduces its reference phenomenon before the next begins. If a
rung fails, the failure localises to that rung's single new ingredient.

**How we would know this was wrong.** If three ladder rungs pass and the transformer substitution
still fails for reasons the ladder cannot localise, the ladder was not buying diagnosis and we should
have gone straight at the architecture.

---

## D2 — Defer ladder stages A–C (LAMMPS, Martini, AOT); execute D→E→F in-repo

**Date:** 2026-08-10

**Context.** The roadmap's first three rungs are external reproductions. Neither LAMMPS nor GROMACS is
installed here (`lmp`, `gmx` absent).

**Chosen.** Defer A–C; build the DPD reference in-repo and proceed D→E→F.

**Rationale.** Installing MD engines is a heavy, outward-facing action that should be a deliberate
call, not something an autonomous run does silently. A–C are also the least diagnostic rungs for the
open question: they validate our *analysis stack* against conventional forces, whereas the
architectural question lives at D→E→F. The project already has this pattern — `cooke_deserno.py` is a
hard-coded conventional reference built in-repo for exactly this purpose, and it worked.

**Success metric.** D→E→F localises any failure without A–C. **Trigger to revisit:** if `bilayer_frac`
or the aggregate metrics disagree with DPD's own phase classification, we need an external
ground truth and A becomes necessary.

**Cost if wrong.** We would discover our metrics are miscalibrated only after building D and E.
Mitigated by re-validating metrics against DPD's planted structures at each rung.

---

## D3 — Build the DPD reference outside the transformer constraint

**Date:** 2026-08-10 · **Artifact:** `dpd_reference.py`

**Context.** Stage D must establish that bounded pairwise forces make amphiphile phases *at all*.

**Chosen.** Plain numpy, ordinary pair loops, real DPD thermostat, no attention primitives.

**Rationale.** Debugging physics and architecture simultaneously is what made every previous negative
ambiguous. If the bounded reference works and the transformer version does not, that difference is the
result. Conflating them means no result at all.

**Success metric.** D reproduces micellar → elongated → lamellar morphology with concentration.

---

## D4 — Carry the force across steps rather than re-evaluating twice per step

**Date:** 2026-08-10 · **Artifact:** `dpd_reference.step()`

**Context.** The first DPD solvent measured T = 0.51 against a target of 1.0 — an exact factor of two.

**Diagnosis.** A naive two-evaluation velocity-Verlet draws the random force twice per step: two kicks
of `dt/2` with variance `σ²/dt` give `0.5·dt·σ²` instead of `dt·σ²`. **Reusing the draw does not fix
it** — positions move between the evaluations, the pair list changes, and the cached noise vector no
longer matches, so a fresh draw happens regardless.

**Chosen.** Standard velocity-Verlet carrying `f` across steps: one force evaluation per `dt`, so the
noise enters exactly once by construction.

**Success metric.** `|T_measured − kT| < 0.10·kT`. **Result: 1.002–1.013 at kT=1.0 across a=5…60.**
Also 2× faster.

**Transferable lesson.** Same class as Vivarium's `speed` defect: fluctuation–dissipation must be
respected by the *discretisation*, not just by the formula. Both were invisible to structural metrics
and visible immediately in a thermostat check. **Any future integrator change re-runs the T check.**

---

---

## D5 — Accept Stage D: bounded pairwise forces with a calibrated solvent DO make mesophases

**Date:** 2026-08-10 · **Artifacts:** `dpd_reference.py`, gates 1–3

**Result.** All three Stage D gates pass.

| gate | metric | result |
|---|---|---|
| solvent EOS | T within 10% of kT; homogeneity < 0.35; MSD > 0.1 | T **1.013**, homog **0.12**, MSD **16.0** |
| species incompatibility | demixing separates from a measured random null | null 0.496 → **0.886** at Δa=10 |
| amphiphile mesophase | concentration-dependent morphology | micellar → elongated → extended bands |

    phi    aggs   mean   largest   aspect   morphology
    0.05      4    4.5         6      1.2   micellar
    0.12      5    9.6        23      2.2   elongated
    0.22      8   11.0        26      2.2   elongated
    0.35      2   70.0       123      1.4   EXTENDED BANDS (classifier wrong, see below)

**This settles the question that forced the reset.** A bounded, pairwise, coordination-extensive force
law with a *calibrated* solvent produces amphiphile self-assembly. Vivarium's failure was
parameterisation, not boundedness. The claim "transformer-only forces cannot make membranes" is
therefore not supportable, and the architectural question stays open — which is the point of the
ladder.

**Metric defect found and recorded (#29).** The radius-of-gyration aspect ratio called the phi=0.35
state "micellar" at aspect 1.4 with a 123-molecule aggregate. A lamellar phase that WRAPS the periodic
box is isotropic to a radius-of-gyration measure. The render shows extended bands with orange tail
cores and blue heads on both edges — bilayer ribbons, not micelles. This is the same failure that
retired this project's `aspect` metric before (same membrane, two boxes, 0.245 vs 0.109). **Any
morphology classifier used from here must be box-aware, and no morphology claim ships without a render.**

**How we would know this was wrong.** If Stage E (exact DPD inside Vivarium) fails to reproduce these
morphologies, the reference is not as solid as it looks and gate 3 should be repeated with seeds and a
box-aware classifier before blaming the engine.

---

## D6 — Next: Stage E, exact DPD inside the Vivarium engine

**Plan.** Port the identical model — same density, geometry, pair force, species matrix, bonds,
timestep, thermostat, topology, concentration, initialisation — into Vivarium's engine, initially
*without* transformer primitives.

**Success metric.** Reproduces the phi series above: micellar at 0.05, elongated at 0.12–0.22,
extended bands at 0.35, with T within 10% and solvent homogeneity < 0.35.

**Why this rung matters.** It separates "our engine/integrator/boundary conditions are wrong" from
"the transformer representation is wrong". Without it, a Stage F failure is uninterpretable — exactly
the ambiguity that produced the retraction.

---

## D7 — Move the DPD reference to 3-D

**Date:** 2026-08-10

**Context.** Stage D reached micelles, elongated ribbons, branched worms and lamellar bands in 2-D
with a healthy solvent — but no vesicle. A planted 2-D vesicle also DISSOLVES at almost every
parameter set tested (8 of 9), so self-assembly was being hunted into a state the force field will not
hold.

**The likely error: dimension.** Open-source DPD vesicle work is essentially all 3-D. A 2-D "vesicle"
is a closed RING — a different and much less studied object — and 2-D suffers far stronger
fluctuations. Staying in 2-D was inherited from Vivarium's geometry, not chosen for this goal.

**Chosen.** Make the DPD reference dimension-generic and run Stage D in 3-D, matching literature
practice: rho = 3, a = 25, Delta-a ~ 15-25, longer amphiphiles (H2-T3 / H3-T4 rather than H-T-T).

**Rationale.** The stated goal is to emerge vesicles by any well-known open-source method FIRST, then
transfer the learnings. Reproducing the regime where the literature succeeds is the point of the
ladder; insisting on 2-D at this rung imports Vivarium's constraint into the reference, which is
exactly the mistake the reset was meant to avoid.

**Success metric.** A closed vesicle from a disordered start in 3-D: a contiguous interior solvent
pocket enclosed by one aggregate, persisting over ≥6k steps, reproduced across ≥3 seeds, with the
solvent gate passing (T within 10%, homogeneity, non-zero diffusion).

**How we would know this was wrong.** If 3-D DPD also fails to make vesicles at literature-like
parameters, the fault is in my DPD implementation rather than in the dimension, and the next step is
to check it against published observables (pressure at rho=3/a=25, self-diffusion) rather than to keep
scanning morphology.

**Note on 2-D.** The 2-D results are kept: they are the geometry Vivarium actually uses, and the
finding that a planted 2-D vesicle is unstable at these parameters is itself a transferable warning.

---

## D8 — Use web search to get the model right, instead of reconstructing it

**Date:** 2026-08-10 · **Artifacts:** `dpd_reference.py` (bending), `_sl_model.py`, `_eos_check.py`

**Context.** Stage D produced micelles, worms and lamellar bands but no stable bilayer, in 2-D or 3-D.
Planted bilayers melted at every parameter set I tried. I had been reconstructing DPD membrane
parameters from background knowledge, and had been wrong three times about "the last missing piece".

**First: validate the engine, so a failure localises.** Groot-Warren give p = rho*kT + alpha*a*rho^2
with alpha ~ 0.101. Measured p/p_pred = 0.92, 0.93, 0.95, 0.96, 0.99, 0.99 across rho 3-6 and a 25-50,
converging toward 1 with density exactly as the asymptotic form should, with T on target at every
timestep from 0.005 to 0.04. **The engine was never the problem.**

**Then: search for the actual published model.** Three errors, all in the model rather than the code:

| | mine | literature |
|---|---|---|
| a_tail-water | 40-55 | **80** |
| a_head-water | 25 | **15** (head MORE compatible with water than water with itself) |
| architecture | H-T3, 1 head 1 short tail | **H3(C4)2** -- 3 heads, TWO 4-bead tails |
| chain stiffness | none | **three-body bending, k3 ~ 15** |

The bending term is the one that matters most: fully flexible tails COIL instead of packing into
leaflets, which is precisely what every amorphous blob looked like.

**Result: a bilayer.** Head/tail segregation for the first time in the project -- a tail core with
head layers on both faces, verified in a render, not just a metric.

**Success metric for this decision.** A planted or emergent bilayer with segregated leaflets. **MET.**
Next gate: a closed vesicle (lumen >= 25 cells) from a disordered start, >= 3 seeds.

**Transferable lesson, and the reason this is recorded.** I spent a long stretch reconstructing a
published model from memory and reading the failures as physics. The engine had been validated all
along; the model was wrong. When a reference exists, get the reference -- and validate the engine
against a published NUMBER before interpreting any physics from it.

**Bugs found on the way, each of which alone would have faked "membranes are impossible":**
thermostat off by exactly 2x (noise drawn twice per step); planted membrane at spacing 1.44 against
rc = 1.0, so the "bilayer" was rods that never touched; `enclosed` firing on micelles and branched
tangles; an aspect classifier calling a box-spanning lamella "micellar".

## Progress ledger

| rung | gate | metric | status |
|---|---|---|---|
| D1 | solvent EOS | T within 10%, homogeneity < 0.35, MSD > 0.1 | **PASS** (T 1.013, homog 0.12, MSD 16.0) |
| D2 | species incompatibility | demixing separates from measured null | **PASS** (0.496 null → 0.886) |
| D3 | amphiphile mesophase | concentration-dependent morphology | **PASS** (micellar → elongated → bands) |
| D4 | stable BILAYER with segregated leaflets | head/tail layering visible in a render | **PASS** (H3(C4)2 + bending) |
| D5 | closed vesicle from disordered start | lumen ≥ 25 cells, ≥3 seeds | running |
| E | exact DPD inside Vivarium | reproduces the phi series | **next** |
| F | transformerised DPD | reproduces E | pending |
| G | custom Vivarium chemistry | reproduces the phase family | pending |

**Stall policy.** If a rung fails twice with different approaches, re-examine that rung's *metrics*
before its physics — this project has retracted more conclusions to bad instruments than to bad
models. If still stuck, stop and escalate rather than sweeping parameters.

---

## D9 — D8's "first real bilayer" is withdrawn as a ranking; the 2-D ribbons are locally better

**Date:** 2026-08-10. **Supersedes the comparative claim in D8** (the SL slab's existence is not in
question; its superiority is).

### Context

D8 recorded the Shillcock-Lipowsky H3(C4)2 slab (`sl_f28_N12000_s1`) as the project's first real
bilayer, on the strength of a rendered slice and a transverse head/tail density profile. Asked
directly whether it was actually better than the earlier 2-D branched ribbons
(`big_phi20_nb3_da15_s1`), the honest answer required a measure that scores both fairly.

### The measurement problem

The transverse profile needs ONE membrane normal. A branched ribbon network has none, so projecting
it onto a global axis smears every leaflet orientation together. It scored the ribbons at -0.15 tail
excess, which is a geometry artifact, not a structural finding. Any ranking built on that profile is
void.

`harness.bilayer_fraction` encodes the correct local test but is 2-D only (defect #26). So the
comparison needed a dimension-generic rebuild: `_pairing.py`.

### Three failed versions, each caught by planted controls

1. Tail-CENTROID proximity read **0.000 on a planted bilayer** in both dimensions. The two leaflets'
   centroids sit ~1.8 apart because each is pulled back toward its own head; the beads that actually
   touch at the midplane are the terminal tail beads. Fixed by gating on tips.
2. Pairing alone then read **1.000 on a planted bilayer AND 1.000 on a planted micelle** -- a
   micelle's antipodal molecules are anti-aligned with tips meeting at the centre, satisfying every
   pair criterion. This independently reproduces the 1.000-vs-0.984 collision already recorded in
   `harness.bilayer_fraction`'s docstring. Fixed by conjoining local flatness.
3. The micelle pole was initially planted at an arbitrary 40 molecules, which over-packs it and makes
   it spuriously flat. Fixed by sizing it physically: tips meet at the centre, so the radius is one
   molecule length, which fixes M at 13 (2-D) and 56 (3-D).

Only the paired-AND-flat conjunction with a physically-sized micelle separates the poles:

| pole | bilayer_frac | paired | flat |
|---|---|---|---|
| 2-D planted bilayer | 0.967 | 1.000 | 0.967 |
| 2-D planted micelle (M=13) | **0.000** | 1.000 | 0.000 |
| 3-D planted bilayer | 1.000 | 1.000 | 1.000 |
| 3-D planted micelle (M=56) | **0.000** | 1.000 | 0.000 |

### Dimensional-bias control

`flat` thresholds a mean dot product, and a 3-D leaflet tilts in two transverse directions where a
2-D one tilts in one, so the threshold could penalise 3-D at equal membrane quality. Measured by
perturbing planted bilayers with matched angular sigma: the bias runs the OTHER way, 3-D scoring
1.03-1.39x HIGHER than 2-D across sigma 0.0-0.5 rad. The ribbons' lead below is therefore not a
dimensional artifact, and is if anything understated.

### Result

| state | dim | n | whole-box | largest-agg | paired | flat |
|---|---|---|---|---|---|---|
| `big_phi20_nb3_da15_s1` (2-D ribbons) | 2 | 400 | **0.315** | **0.310** (n=113) | 0.950 | 0.330 |
| `sl_f28_N12000_s1` (3-D SL slab) | 3 | 305 | 0.184 | 0.184 (n=305) | 0.787 | 0.210 |
| `sa_phi15_N12000_s1` | 3 | 450 | 0.089 | 0.089 (n=380) | 0.829 | 0.109 |
| `sl_f18_N12000_s1` | 3 | 196 | 0.046 | 0.050 (n=180) | 0.638 | 0.066 |

**The branched 2-D ribbons have ~1.7x better local bilayer structure than the SL slab.** Restricting
to the largest aggregate changes neither (the ribbons' bilayer-like molecules outnumber their largest
aggregate, so they are spread across many small well-ordered patches; the slab is one large poorly
ordered object).

### What each one actually has

- **Ribbons:** better local leaflet order, and genuine EDGES -- the thing a vesicle must close. They
  branch instead of closing.
- **SL slab:** a correct transverse head-tail-head profile (tail excess +0.74, head signal on both
  faces 0.94) across one connected 305-molecule membrane, in 3-D where the vesicle literature lives.
  It spans the periodic box, so it has no edges to close.

Neither is a vesicle; both have lumen 0. These are two different failure modes, not a ladder.

### Success metric

`bilayer_frac` (paired AND flat, this module) > 0.5 within the largest aggregate, with that aggregate
finite (not box-spanning) and a non-zero lumen. Nothing measured to date exceeds 0.32.

### How we would know this was wrong

If the flat threshold (0.90) is simply too strict for a thermally fluctuating membrane at kT=1, both
absolute numbers are depressed and only the ratio is meaningful. The planted-pole controls bound
this: at sigma=0.2 rad a planted bilayer still reads 0.93/0.97, so a genuinely well-ordered
fluctuating membrane should clear 0.5. Reading 0.18 is a real deficit, not a threshold artifact.

---

## D10 — The `bilayer_frac` success target is void; D9's ranking is retracted

**Date:** 2026-08-11. **Retracts D9's comparative ranking and the ">0.5" target set in D9.**

### Context

External review required calibrating `bilayer_frac` on planted, thermalized vesicles of the target
radii rather than on flat bilayers and micelles alone. Doing that exposed a deeper problem than a
mis-set threshold.

### The measurement

A planted FLAT bilayer -- a phase independently believed stable for this chemistry (box-spanning slab
exists, T=1.00, laterally fluid, intact 1.00 throughout) -- thermalized for 6000 steps:

| step | bilayer_frac | paired | flat | intact |
|---|---|---|---|---|
| 0 | 1.000 | 1.000 | 1.000 | 0.12 (lattice artifact) |
| 1500 | 0.117 | 0.875 | 0.125 | 1.00 |
| 3750 | 0.312 | 0.930 | 0.320 | 1.00 |
| 6000 | 0.125 | 0.922 | 0.125 | 1.00 |

A healthy, intact, fluid flat bilayer reads **0.117-0.312 at kT=1**. Every structure this project has
measured lies inside that band: 2-D ribbons 0.310, SL slab 0.184, planted R=9 vesicle 0.307, planted
R=7.5 vesicle 0.179.

### Consequences

1. The ">0.5 within a finite aggregate" target is unreachable by any thermalized membrane. It was
   calibrated on t=0 lattices at effectively zero orientational noise.
2. **D9's ranking is retracted.** "Ribbons 0.310 beat the slab 0.184 by 1.7x" compares two points
   inside a band whose reference oscillates 0.117 -> 0.312 -> 0.125 between consecutive snapshots of
   an unchanging membrane. That is sampling noise, not a difference. The dimensional-bias control in
   D9 was sound; it was simply answering a question that the thermal noise floor makes moot.
3. "Planted vesicles are unstable" is NOT established. The R=7.5 and R=9 decays match what a healthy
   flat bilayer does over the same interval.

### Which half broke

`paired` is robust under thermalization (flat slab 0.875-0.938) and orders structures by leaflet
population (flat > R=9 0.756 > R=7.5 0.411 > R=6 0.196). `flat` collapses 1.000 -> ~0.15 on an
unchanged membrane, because it thresholds a PER-MOLECULE dot product at 0.90 (25.8 deg) and
single-molecule thermal tilt at kT=1 is comparable to that. It was never a curvature measure at kT>0.

This is not the curvature failure the reviewer anticipated: the `s < 0.451R` bound is satisfied at
every radius tested (neighbour window 1.6 rc against a 2.7 rc bound at R=6), and `flat` reads 0.975 on
a planted R=6 vesicle at t=0. Thermal noise, not curvature, destroys it.

### Success metric (replacing D9's)

Until a robust flatness estimator exists, structural claims rest on `paired`, sealed lumen (water-
containing, flood-filled), intactness, and shell radius -- not on `bilayer_frac`. On those, planted
R=9 is the only vesicle behaving like one: sealed lumen 52 cells, intact 0.87, paired 0.756.

### How we would know this was wrong

If a thermalized planted MICELLE also reads paired ~0.75-0.9, then `paired` alone cannot discriminate
and the conjunction is irreplaceable, making a robust `flat` mandatory rather than optional. That
measurement is queued and is the single most important one outstanding.
