# The MLP as the missing MANY-BODY term

**Registered 2026-09-07, before any implementation is run.** 2-D first.

## The structural problem this addresses

`docs/RESULTS.md` states the blocker as close to a theorem, not an empirical failure:

> **This force field cannot curve a flat bilayer.** ... The reason is structural: chi terms are
> symmetric pair interactions, and spontaneous curvature is by definition a difference between the two
> leaflets.

Every candidate curvature source has come back a measured null with the membrane intact: `chi_TW`
(lambda = +2.8 +- 2.8, null WITH power), `chi_HH` (0/5 over ten runs), lipid shape, **imposed leaflet
thickness asymmetry (0/5)**, **imposed leaflet area asymmetry (0/5)**. Even handing the membrane an
asymmetry did not curl it.

No amount of chi tuning escapes this, because the obstruction is the FORM of the interaction, not its
parameters.

## The reaction-diffusion reading

| reaction-diffusion | transformer |
|---|---|
| `D grad^2 u` -- spatial coupling between sites | **attention** -- pairwise coupling over a mask |
| `f(u)` -- pointwise nonlinear reaction | **MLP** -- per-token nonlinear map on local state |

Turing patterns require BOTH. Pure diffusion relaxes to uniformity; it cannot break symmetry. Vivarium
today is the pure-diffusion half: every molecule is rigid, carries no evolving internal state, and the
only coupling is pairwise.

**And the MLP is not merely zeroed -- it is never called.** `transformer.attention()` and
`transformer.forward()` do not invoke `mlp()`; the only caller in the repository is
`tests/test_transformer.py:130`. So `docs/RESULTS.md`'s gate *"MLP is live, not decorative"* exercises
a code path the simulation never executes. That is recorded here as a claim-vs-code gap.

## What is actually missing, stated in membrane terms

The standard theory of vesiculation is **area-difference elasticity (ADE)**: the bending energy carries
a term proportional to `(dA - dA_0)^2`, where `dA` is the area difference between the two leaflets.
That term is **non-local and many-body** -- it depends on an aggregate over each leaflet, not on any
pair. A sum of symmetric pair potentials cannot express it, which is exactly the obstruction
`RESULTS.md` identified from the other direction.

An MLP acting on a per-token invariant aggregate CAN express a density-dependent, many-body
contribution. That is the specific reason to wire it in, and it is a structural argument rather than a
hope that more parameters will help.

## The mechanism, DERIVED not fitted

Solvation energy scales with **solvent-accessible surface area**. This is the standard SASA model in
biophysics, not an invention for this project. A head bead that is crowded by neighbours exposes less
surface to water and is therefore less solvated than an exposed one:

    chi_HW_eff(i) = chi_HW * f_exposed(i),     f_exposed(i) = max(0, 1 - n_i / n_max)

where `n_i` is the head's coordination among lipid beads within the well range, and `n_max` is the
close-packing coordination number -- **geometrically fixed, not chosen**: 6 in 2-D, 12 in 3-D.

There is **no free parameter**. `chi_HW = 0.75` is the existing production value; `n_max` is geometry.

## Why this is not smuggling in the answer

The rule is that nothing may be supplied which already contains the answer, and a "make the membrane
bend" term is refused. This term says only *a buried head is less solvated than an exposed one*, which
is true independently of vesicles and mentions neither curvature nor leaflets.

**Its null behaviour is the check.** In a FLAT bilayer both leaflets are equally exposed, so
`f_exposed` is equal on both sides, no asymmetry is generated, and the term cannot produce spontaneous
curvature. It can only respond to curvature that already exists -- amplifying or damping it. **Which
sign it takes is genuinely unknown to me at registration time**, and that is the strongest evidence
that the answer is not being supplied.

## Gates, in order. Each can fail.

**G1 -- the existing correctness gate must survive.** With the MLP disabled, one forward pass must
still equal `Inertial.step` bit-for-bit and the attention sum must still equal `field.forces()`. The
MLP is additive and off by default; if this breaks, the wiring is wrong.

**G2 -- the null control.** On a planted FLAT bilayer, the MLP must produce equal `f_exposed` on the
two leaflets, to within thermal noise. If it produces an asymmetry on a flat membrane, the term is
manufacturing curvature and must be rejected.

**G3 -- the mechanism engages.** On a planted CURVED bilayer (a ring), the two leaflets must show
measurably different `f_exposed`, with the inner leaflet more crowded. If not, the term is inert and
nothing downstream is worth running.

**G4 -- the experiment.** Planted FLAT ribbon, does it curl? This is the exact protocol on which
every prior candidate returned **0/5 with the membrane intact**, so the null is established and
unusually well characterised.

```
G4 PASSES iff  curl rate >= 3/10 with the MLP on  AND  0-1/10 with it off, same seeds
```

## What each outcome means, written before running

- **G4 passes.** A many-body term is what the model was missing, and it was derivable rather than
  chosen. This would be the first positive on a protocol with five recorded nulls.
- **G4 fails, G3 passes.** The mechanism engages but does not drive curvature. The many-body term is
  real but this particular one is not the missing piece; ADE proper (an explicit leaflet-area-difference
  term) becomes the next candidate, and it is a much harder sell under the no-smuggling rule.
- **G2 fails.** The term manufactures asymmetry on a flat membrane. Reject it and say so -- that would
  mean it does contain the answer.
- **G1 fails.** Implementation error, not physics.

## Threats

- The MLP's current input is the summed attention SCORE, a force-like quantity, not a coordination
  count. Implementing `n_i` requires passing a different invariant message. That is a change to the
  architecture's inputs and is noted as such, not hidden.
- A live MLP breaks the "one forward pass = one integrator step" identity in the general case. G1
  preserves it only for the MLP-off path. The project's strongest correctness claim therefore becomes
  conditional, and any result here must state that.
- `chi_HW` only exists with explicit solvent. This mechanism is defined for the 2-D production
  chemistry and does NOT transfer to the solvent-free arms without a separate derivation.

---

## G2 and G3 — PASSED, 2026-09-07

Planted geometries, N = 56 lipids (the size of the confirmed emergent vesicle), L = 100, phi = 0.55.

| geometry | outer leaflet | inner leaflet | asymmetry |
|---|---|---|---|
| **FLAT bilayer (G2, the null)** | 0.5000 | 0.5000 | **0.0000 exactly** |
| **RING, curved (G3)** | 0.5000 | 0.3821 | **+0.1179** |

**G2 PASSES.** The term is identically zero on a flat membrane, so it cannot manufacture curvature --
which is the check that it does not contain the answer. **G3 PASSES.** On a ring the inner leaflet is
measurably more buried, so the mechanism engages.

0.5000 for an exposed head is correct by inspection: a head on a flat surface has half its perimeter
facing solvent.

### A conceptual error the controls caught before it reached the dynamics

The first implementation treated EVERY bead as an occluder, including water. But the probe *represents*
a water molecule -- water cannot block water's access; it is the thing being granted access. With that
error, heads in a normal flat bilayer read as 85% buried and the numbers inverted:

    spurious FLAT asymmetry 0.0222   >   real RING signal 0.0093

i.e. the noise exceeded the signal and both gates failed. Fixed by passing lipid beads as the only
occluders. Had this gone straight into the dynamics it would have been a force term driven mostly by
solvent packing noise.

`_sasa.validate()` separates four known-answer cases, including one with an exact analytic value: two
expanded circles of radius 1.0 whose centres are 1.0 apart occlude arccos(1/2) = 60 degrees either
side, so 120 of 360 degrees are blocked and exactly 2/3 remains. It reads 0.6667.

## Amendment 1 — the implementation scales ALL of a head's interactions, not only `chi_HW`

The derivation above justifies `chi_HW_eff = chi_HW * f_exposed`. The natural implementation in this
architecture scales the token's channel, `h_i <- f_i * h_i`, and since `q = h @ Wq`, that scales every
interaction the head takes part in: `chi_HW` by `f_i`, and `chi_HH` by `f_i * f_j`.

**Stated rather than hidden, because it is broader than what was derived.** The physical justification
extends: if interactions are mediated by exposed surface, then a buried head engages less with
everything, not only with water. A pair term scaling as `f_i * f_j` is the correct form for a
surface-mediated interaction between two partially buried objects. But `chi_HT` and `chi_HH` are
scaled as a consequence of the architecture rather than as a consequence of the SASA argument, and any
result must say so.

Tails are NOT scaled. The hydration shell is a property of the polar head group; tail beads are
hydrophobic and carry none.

---

## Amendment 2 — 2026-09-08: the MLP IS usable. Demonstrated, not argued.

Two objections were raised against a live MLP. One was real and one was not.

**Not a blocker: the MLP.** `manybody.py` gives each token a scalar internal state -- a smooth
coordination number over lipid beads, `n_i = sum_j (1 - (r/rc)^2)^2` -- and an MLP maps it to an
exposure `f_i` that modulates the pair chemistry as `chi_ij = chi0_ij * f_i * f_j`. Symmetric in the
pair, so antisymmetry of the pair force is preserved.

**Real, and solved:** with `chi` configuration-dependent the force is no longer the radial derivative
alone. `field.forces` and `transformer.attention` both compute `dudr = eps*(duc + duw*chi)/sig` with
chi held constant, so both would silently omit

    - sum_ij eps * well(r_ij) * chi0_ij * [ f_j * df_i/dx_k + f_i * df_j/dx_k ]

Omitting it makes the dynamics non-conservative: energy drifts, temperature is undefined, and the
thermostat fights a non-gradient force. This is the same embedding-density term EAM and many-body DPD
carry, and it is why the descriptor is a smooth coordination number rather than exact SASA -- the arc
geometry is more accurate but piecewise, and an underivable descriptor is exactly how a
non-conservative force gets in unnoticed.

### The gate: does F equal -grad U?

Central differences at h = 1e-6, worst relative error over probed coordinates:

| MLP scale | max rel. error |
|---|---|
| 0.0 (off) | 1.079e-06 |
| 0.5 | 1.072e-06 |
| 1.0 | 1.072e-06 |
| 2.0 | 1.071e-06 |

That is the central-difference truncation floor, flat in MLP strength. **The force is exact.** And the
term is not inert: `||F_on - F_off|| / ||F_off|| = 0.0076`.

### What still cannot cross over from polar_pack

**Softmax.** Row-stochastic weights give `w_ij != w_ji`, so `F_ij != -F_ji`: Newton's third law fails
and momentum is not conserved. Normalisation also makes the force INTENSIVE -- a bead with 100
neighbours feels the same total as one with 3. Symmetrising restores the third law but destroys
row-stochasticity, so it is no longer softmax. polar_pack can use it because it has no energy ledger.

### Amendment 3 — the G4 gate as registered is too weak, corrected BEFORE any data

Registered: `on >= 3/10 AND off <= 1/10`. Computed power:

| true rate, if the MLP does nothing | P(false pass) |
|---|---|
| 0.10 | 0.052 |
| 0.20 | **0.121** |

and the boundary case the gate would PASS, 3/10 vs 1/10, is **Fisher p = 0.291** -- not significant.
The gate licenses a non-result.

**Corrected gate, no data yet seen:**

```
G4 PASSES iff  on >= 6/12  AND  off <= 1/12  AND  Fisher one-sided p <= 0.05
```

Twelve seeds per arm rather than ten, and an explicit significance clause. Changing a gate after
seeing data would be the failure this spec exists to prevent; changing one found broken before any run
is not, and the correction is recorded here rather than made silently.

### Remaining free parameter, declared

`ManyBodyMLP.scale` multiplies the coordination before the exposure map, and `n_ref = 6.0` is the
close-packed 2-D coordination number (geometry). `scale = 1.0` is the natural value and is what the
gradient gate was run at, but it IS a knob and must not be tuned to make G4 pass. If G4 is run at more
than one `scale`, every value must be reported.

---

## G4, FIRST ATTEMPT — VOID. The two arms were the same simulation.

Caught 2026-09-09 01:12, 1h19m into a 2h run, before it produced a verdict.

    max|X_off - X_mlp| after 400 steps = 0.000e+00

**The MLP never reached the dynamics.** `manybody` was wired into `field.forces`, but the production
engine runs `transformer.attention`, which is a SECOND implementation of the same force law and
recomputes chi from its own frozen one-hot channel. It never consulted `field.manybody`.

Had this run to completion it would have reported **"G4 fails, the MLP does nothing"** -- the exact
opposite of the truth, backed by 24 runs and 48 CPU-hours.

**This is the duplication defect, not a typo.** The same session's audit counted `def plant` in 18
files, `def build` in 15, `def step` in 12, and `largest_cluster` in 5, and noted that competing
implementations are how the wrong one gets called. Here there were two force laws and only one was
changed. The signature was visible in the log an hour before the direct test confirmed it: `sd=700`,
`sd=702`, `sd=703` and `sd=704` reported *character-identical* aspect values in both arms.

### Fix, and the gate that should have existed from the start

The many-body term is now carried by both paths, and they are checked against each other:

| | field vs transformer, max abs diff / \|F\| |
|---|---|
| scale = 0.0 | **0.000e+00** |
| scale = 1.0 | **0.000e+00** |
| scale = 2.0 | **0.000e+00** |

and the arms now diverge: `max|X_off - X_mlp| = 9.7e-01` after 400 steps.

**G1 is amended to require agreement between the two force paths at every MLP scale**, not merely that
each is internally conservative. Both were internally consistent; they were consistent with different
physics. An off-state bit-identity check cannot catch that, because with the MLP off they agree
trivially.

---

## G4 — RESULT: FAILS. The many-body term engages, and does not curl a flat ribbon.

24 runs, seeds 700-711, both arms, N = 56, L = 100, 300,000 steps.

| arm | curled (aspect_max >= 0.45) | mean aspect_max |
|---|---|---|
| MLP off | **0/12** | 0.0330 |
| MLP on, scale 1.0 | **0/12** | 0.0378 |

    Fisher one-sided p = 1.0000
    GATE (on >= 6/12 AND off <= 1/12 AND p <= 0.05): FAILS

No state crossed the threshold, so there was nothing to render. Every run started at aspect 0.0024 and
the largest excursion in 24 runs was 0.0607 -- against 0.5042 for a planted arc. **The ribbons stayed
flat.**

**This is a real comparison, unlike attempt 1.** The arms differ seed by seed (sd 700: 0.0224 off
against 0.0083 on), so the MLP demonstrably reached the dynamics.

### The registered reading, written before the data

> *"G4 fails, G3 passes. The mechanism engages but does not drive curvature. The many-body term is real
> but this particular one is not the missing piece; ADE proper (an explicit leaflet-area-difference
> term) becomes the next candidate, and it is a much harder sell under the no-smuggling rule."*

That is exactly the outcome. G3 measured the term engaging on a curved membrane (+0.1179 against
0.0000 flat); G4 shows it does not make a flat one bend.

### What this sharpens

The flat-ribbon protocol now has **six independent nulls**: `chi_TW` (null with power), `chi_HH` (0/5
at two values), lipid shape, imposed leaflet THICKNESS asymmetry (0/5), imposed leaflet AREA asymmetry
(0/5), and now a derived many-body solvation term (0/12).

The first five were all symmetric pair interactions, and `docs/RESULTS.md` explains them structurally:
a pair potential cannot express a difference between leaflets. **That explanation no longer covers the
data.** This term is not a pair interaction -- it is a per-token aggregate over the neighbourhood --
and it still does not curl the membrane. So the obstruction is narrower and more specific than "pair
potentials are insufficient", and whatever it is, being many-body is not by itself enough to overcome
it.

### Honest limits

- ONE value of `scale` was run (1.0, the declared natural value). It was not tuned, and no second
  value was tried, so this does not exclude a stronger coupling working. Reporting a single value is
  the honest description of what was done.
- 300,000 steps. A slower instability would be missed.
- The mean aspect_max is marginally HIGHER with the MLP on (0.0378 vs 0.0330), which is within noise
  and is not evidence of anything.

---

## G4, SHAPE CHANNEL — ALSO FAILS, 2026-09-09

24 runs, seeds 800-811, `ShapeMLP(amp=0.25)` modulating `sigma_head` from head-only coordination.

| arm | curled | mean aspect_max |
|---|---|---|
| off | **0/12** | 0.0354 |
| shape, amp 0.25 | **0/12** | 0.0317 |

    Fisher p = 1.0000     GATE: FAILS

**Both MLP channels are null.** Affinity (`chi`) 0/12; shape (`sigma_head`) 0/12. The shape channel was
built specifically because the affinity channel's feedback sign was diagnosed as stabilising flatness,
and its own sign was corrected (head-only descriptor, -0.0661 vs +0.2004) before it ran. It still does
not curl a flat ribbon.

**The flat-ribbon protocol now has seven nulls**: `chi_TW`, `chi_HH`, lipid shape, imposed leaflet
thickness asymmetry, imposed leaflet area asymmetry, MLP-affinity, MLP-shape. The first five are
symmetric pair terms and `docs/RESULTS.md` explains them structurally. **The last two are not pair
terms and that explanation does not cover them.**

What remains untested rather than refuted: only one `amp` was run (0.25, declared, untuned), 300,000
steps, and the descriptor is instantaneous rather than relaxational. None of those is a reason to
believe the mechanism works; they are the honest boundary of the negative.

---

## Amendment 4 — 2026-09-11: `n_ref = 6.0` is a DEFECT. Both G4 verdicts are uninformative.

**Written before any run at a corrected value.** This is not a reinterpretation of the data; it is a
statement that the term the data was collected on was, by construction, nearly a constant.

### What was registered

> `n_ref = 6.0` is the close-packed 2-D coordination number (geometry), **not a fit**.

### What the descriptor actually is

`coord_weight` returns a smooth *kernel weight*, not a neighbour count:

    w(r) = (1 - (r/rc)^2)^2,   rc = 2.5 sigma for a head-head pair

Two things follow, and both were missed:

1. **A weight is not a count.** At the head-head spacing of a planted flat bilayer, 2.050 sigma,
   `w = 0.1073`. A head with two neighbours therefore scores 0.21, not 2.
2. **A 2-D leaflet is a LINE.** Close packing in 2-D gives 6 neighbours to a bead in a *bulk*
   arrangement. A leaflet is one-dimensional, so a head has exactly **two** in-leaflet head
   neighbours, not six. The descriptor was also changed from all-lipid to **head-only** on 2026-09-09
   to fix the feedback sign, and `n_ref` was never re-derived afterwards.

### Measured consequence

Head-only coordination, measured through `Field.coordination` (the same code the force reads):

| state | mean head coordination |
|---|---|
| planted flat bilayer, N=56 L=100 | **0.2070** |
| planted closed ring | 0.2603 |
| dispersed, N=112 L=54.4 | 0.2557 |

With `n_ref = 6.0` the shape channel's bracket is

    1 + amp*(1 - n/n_ref) = 1 + 0.25*(1 - 0.035) = 1.2414

for **every head in every state**, with a spread of 0.0045 across a curved membrane — a **uniform 24%
inflation with a 0.4% modulation**. The outer-minus-inner wedge on a planted ring, which is the entire
mechanism, is **+0.10%**. At a derived `n_ref` the same ring gives **+3.77%**, 38x larger.

The affinity channel carries the identical error, less severely. Its descriptor counts **all** lipid
beads (it declares no `neighbours`), so it reads 0.687 in a flat bilayer and 0.852 on a ring against
the same `n_ref = 6.0`. The realised exposure `f = 1/(1 + n/n_ref)` spans 0.894-0.944 on the flat
membrane and 0.866-0.892 on the ring: a **3-6% spread about ~0.9**, where the map's full range is
(0, 1]. The measured engagement `||F_on - F_off||/||F_off|| = 0.0076` was recorded at the time and
read as "small but non-zero" rather than as a calibration failure.

### What this does to the two G4 verdicts

Both are **withdrawn as tests of the registered mechanism**, and neither is replaced by a positive.

- **G4 affinity, 0/12.** Tested a ~1% modulation of chi. Uninformative about a many-body affinity term.
- **G4 shape, 0/12.** Tested, in effect, **uniformly 24% larger heads** — a chemistry change, not an
  environment-dependent shape. That is a real null and is retained as one: *a uniform 24% head
  enlargement does not curl a flat ribbon.* It is not the registered mechanism.

The flat-ribbon protocol therefore has **five** nulls against pair terms plus one against a uniform
head enlargement, not seven against seven distinct mechanisms. `docs/ROADMAP.md` and `SUMMARY.md` are
corrected in the same commit.

### The derivation, fixed

    n_ref = n_in_leaflet * w(a0; rc),   n_in_leaflet = 2 (a 2-D leaflet is a line)

`a0` is the **equilibrium** head-head spacing. It must not be taken from the planter, whose lattice
constant is its own choice: the planter builds at 2.050 sigma while the four confirmed self-assembled
vesicles sit at a median of **1.653 sigma**, 24% tighter. `a0` is therefore measured on a planted flat
ribbon **relaxed under the dynamics with the modulator off** — the state in which `sigma = sigma0` is
by definition correct.

`amp` remains the one free parameter and is still declared as such.

### The measurement, run before the ladder

Six seeds, planted flat ribbon, 100 000 steps under the production chemistry with the modulator OFF,
probed every 20 000 steps through `Field.coordination` — the same code the force reads.

| quantity | planted (step 0) | relaxed (step 100 000) |
|---|---|---|
| head-head spacing `a0` | 2.0500 | **1.7651 ± 0.0732** |
| head coordination `n` | 0.2070 | **0.3335 ± 0.0464** |

**Registered value: `n_ref = 0.3335`** — the descriptor's own value in the state where `sigma = sigma0`
is by definition correct. The geometric formula is a cross-check, not the source:
`2 * w(1.7651) = 0.5031`, within 1.5× of the direct measurement. They differ because a real ribbon is
not an ideal line — it has two ends, its spacing is not uniform, and it sheds a few lipids (56 heads
at step 0, 46-49 at step 100 000, with the modulator off).

Against the registered `n_ref = 6.0` this is **18× smaller**.

### A declared property of the protocol, not hidden

The planter builds the ribbon at 2.0500 σ, 16% more dilute than the relaxed 1.7651 σ. So every on-arm
starts from a membrane the term reads as *under-crowded*, and every head is inflated at step 0 before
any dynamics. Measured mean `sigma_head` at step 0: **1.094** at `amp = 0.25`, **1.360** at
`amp = 1.0`, **1.631** at `amp = 2.0`, **1.898** at `amp = 4.0`, against 1.000 in the off arm.
This is a real
property of starting from a planted state and is the same for every amp; the off arm is unchanged, and
the comparison is still paired seed by seed. It is also the main reason the top of the ladder is
expected to fail the intactness control rather than the curl gate.

### Guards added, so this class of defect fails loudly

- `n_ref` has **no default** on either modulator. A default is how 6.0 survived the descriptor change.
- `manybody.assert_calibrated` raises if the descriptor's mean is more than 4x from `n_ref`. `curl.py`
  calls it at step 0, before spending 2.4 CPU-hours per run.
- `Field.coordination(X)` exposes the descriptor the force actually reads, so a harness cannot check a
  re-derivation of it.
- `tests/test_manybody.py` — twelve gates, committed. It pins that `n_ref = 6.0` is rejected, that the
  modulation is not a uniform offset, that `field.forces` and `transformer.attention` agree at every
  amp, and that the force is `-grad U`. Three of these existed only as one-off scripts, each after it
  had already caught a defect that voided an experiment.

---

## G5 — the shape channel at a DERIVED `n_ref`, as a dose-response. Registered 2026-09-11, no data.

**Hypothesis.** An environment-dependent head size — the packing-parameter mechanism, `P = v/(a0*l)` —
makes a planted flat ribbon curl, at some amplitude, without destroying it.

**Strongest baseline, named:** the existing `amp = 0` arm, seeds 800-811, 0/12 curled, already on disk
in `docs/results/curl.tsv`. Paired: the same seeds drive both the build and the thermostat.

**Arms.** `amp` in **{0.25, 1.0, 2.0, 4.0}** — a factor-of-two ladder spanning 16x, declared here in
full. 0.25 is the originally registered natural value, now evaluated at a `n_ref` that is not broken.
12 seeds each (800-811), 300 000 steps, N=56, L=100, exactly the off arm's protocol. Run order is
1.0, 2.0, 0.25, 4.0 so that whole cells complete first if the machine runs out of time; every value
run is reported whatever it says.

**G5 PASSES** iff **at least one amp** satisfies the G4 gate as amended:

```
curled AND intact >= 6/12   AND   off <= 1/12   AND   Fisher one-sided p <= 0.05
```

**G5b — the criterion this can fail by winning.** `curled` now requires `intact`: the largest lipid
aggregate at the end must hold >= 90% of the lipids. A ribbon torn into fragments is isotropic and
scores a high `aspect` for the opposite of the reason we care about. If curl appears **only** at an
amp where intactness has collapsed, **G5 FAILS** — the term destroys membranes, it does not bend them.
A method that merely perturbs harder cannot pass this; one that curves a membrane can.

**G5c — shape, reported not gated.** A real mechanism should show curl rate rising with `amp` before
intactness falls. A single amp winning with both neighbours at zero is recorded as suspect.

**What each outcome means, written now.**

- **PASSES at an amp with intactness held.** The packing parameter is the missing lever, the term was
  derived rather than fitted, and the flat-ribbon protocol has its first positive.
- **FAILS with intactness held at every amp.** The mechanism is genuinely null for this model at up to
  16x its natural amplitude. That is a much stronger negative than the one being withdrawn, and it
  closes the MLP-morphology line rather than leaving it open.
- **Curl only where the membrane fragments.** Recorded as a FAIL and as evidence that `aspect` alone
  is not a sufficient endpoint — which is why G5b exists.
