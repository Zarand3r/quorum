# Pre-registration: a vesicle at a size where a vesicle can exist

**Registered:** 2026-08-30, before any run at N >= 1000 existed.

---

## 1. Why every previous attempt could not have worked

A vesicle is a closed shell of a membrane with finite thickness. It is only a coherent object if its
radius comfortably exceeds that thickness. Measured here: bilayer thickness ~4.0 sigma (planted
reference 4.40; the Cooke-Deserno oracle reads 4.05 under the same instrument).

| N lipids | vesicle R | **R / thickness** | patch side |
|---|---|---|---|
| 200 | 3.3 | **0.82** | 11.6 |
| 400 | 4.6 | **1.16** | 16.4 |
| 1000 | 7.3 | 1.83 | 26.0 |
| 1600 | 9.3 | 2.32 | 32.9 |

**Every sweep in this project used N = 200 or 400**, i.e. a shell no thicker than its own membrane.
Head area, temperature, attraction width and excluded volume were each swept across wide ranges
against a target that could not exist. That is a better explanation of four null results than any of
the four hypotheses proposed during them, and it required arithmetic rather than simulation.

## 2. The second condition, from the paper rather than from us

Cooke & Deserno (JCP 123, 224710, 2005), section III: *"a bilayer patch quickly self-assembled,
which, at the correct box size could zip up to span the box... **If the box was too big, the patch
either remained free, or (sometimes) closed upon itself to form a vesicle.**"*

A patch that spans a periodic box has no edges and therefore nothing to gain by closing. Every box in
this project was sized for density and never checked against the spanning threshold. Box must exceed
the patch side (26.0 sigma at N = 1000).

## 3. Hypothesis

**H3.** At N = 1000 (R/thickness = 1.83) with the box above the spanning threshold, a dispersed start
produces a closed vesicle, where the same chemistry at N = 200-400 cannot.

## 4. Arms

| | |
|---|---|
| lipids | **1000**, CD architecture: linear 3-bead (1 head, 2 tails), `sigma_head` 0.95 |
| box | L in {30, 36} -- 15% and 38% above the 26.0 spanning threshold |
| chemistry | `cooke_chi`: tail-tail attraction only, heads purely steric |
| w_c / kT | 1.4 / 1.0 -- inside the fluid band of our own reproduced phase map |
| bonds | k_bond 30 (CD's stiffness constant) |
| start | random dispersion |
| engine | ours, `VIVARIUM_ENGINE=transformer` |
| seeds | 3 per box |
| steps | 400,000 (CD reach a bilayer at 4000 tau, dt 0.01, i.e. 400k) |

**Control, run in the same grid:** the vendored `cooke_deserno.py` oracle at identical N, L and
parameters. Ours and theirs are scored by the same instrument, so a disagreement localises to the
engine and an agreement validates both.

Measured cost: 23.1 ms/step at 3000 beads, so ~2.6 h per seed; 12 runs fit in one parallel pass.

## 5. Endpoint

Scored with `bilayer_metrics`, validated on four synthetic controls (vesicle / sheet / blob / gas)
that it must SEPARATE, not merely score one well:

    vesicle   thickness 2.85   hollow 0.000   L1/L3 0.83
    sheet     thickness 7.00   hollow 0.573   L1/L3 0.21
    blob      thickness 3.11   hollow 0.987   L1/L3 0.89
    gas       thickness 0.10   hollow 0.493   L1/L3 0.83

A seed **forms a vesicle** iff, at two or more consecutive checkpoints:

    hollow < 0.25          (vesicle 0.000 vs sheet 0.573, blob 0.987)
    AND aniso L1/L3 > 0.5  (isotropic -- excludes the sheet at 0.21)
    AND thickness > 3.0    (a real bilayer -- excludes the gas at 0.10)

and a render confirms it. Metric AND picture, because in this project each has flattered the other.

```
PASS iff  any box gives >= 2/3 seeds forming, in OUR engine
```

### AC-2, the criterion we can fail by winning

**If the CD oracle also fails to form a vesicle at these N and L**, then the recipe is not sufficient
as stated and a null in our engine says nothing about our engine. H3 would be untested rather than
refuted, and the honest report is about the recipe, not about vivarium.

### AC-3

**If both form**, the engine is validated for 3-D vesicle assembly and the four null sweeps are
explained by infeasible geometry alone.

## 6. What each outcome means -- written before the data

- **Ours forms, oracle forms.** The engine can assemble a 3-D vesicle. Everything earlier was a
  size artifact. This is the project's first 3-D result.
- **Oracle forms, ours does not.** The difference is in our engine, and it is now bisectable against a
  working control: chain stiffness (CD's 1-3 spring is permanently stretched at rest length 4 sigma,
  ours merely makes straight the minimum), bond form (FENE vs harmonic), core form (divergent WCA vs
  bounded quadratic).
- **Neither forms.** N = 1000 is still too small (R/thickness 1.83), or 400k steps too short. Escalate
  to N = 1600 (R/thickness 2.32) before concluding anything.
- **Ours forms, oracle does not.** Suspect our instrument or harness before celebrating.

## 7. Threats

- N = 1000 gives R/thickness 1.83, workable but not comfortable; 1600 would be safer and costs ~1.6x.
- Bigger box prevents spanning but lowers density (0.111 at L=30, 0.070 at L=36, against CD's 0.192),
  which slows coarsening. The two requirements pull against each other and 400k steps may not suffice.
- Vesicle formation is explicitly stochastic in the source ("sometimes"), so 3 seeds may under-power.
- Our thickness (3.3) is below the oracle's (4.05), so our R/thickness is slightly better than tabled.

## 8. Amendment 1 — 2026-08-30: the oracle control is STAGED, not dropped

**Measured before the run, not extrapolated:** 2000 steps at N = 1000, both engines, same box.

    ours    13.6 s   ->  400k steps ~ 0.8 h
    oracle 416.2 s   ->  400k steps ~ 23.1 h

The oracle is **30x slower** (dense numpy, no efficient neighbour list at this size). Six oracle runs
is ~23 h of wall clock even fully parallel, against ~1 h for our six.

**Staged instead.** Our engine runs first at full power (2 boxes x 3 seeds). The oracle control runs
only if our engine FAILS, which is the branch where AC-2 actually matters -- its job is to decide
whether a null in our engine indicts the engine or the recipe. If our engine forms a vesicle, AC-3 is
satisfied without it, and the oracle becomes a confirmation rather than a discriminator.

**This is a deviation and it weakens the design**: if ours forms, the result rests on our engine and
our instrument with no simultaneous external control at this N. Stated here rather than discovered in
the writeup. The instrument itself is separately validated against four synthetic controls and against
the oracle at N = 200, where it correctly read a bilayer sheet of thickness 4.05.

---

## 9. Outcome — 2026-08-31

```
  engine      L     formed
    ours   30.0    0/3
    ours   36.0    0/3

  PASS (ours >= 2/3 in any box): False
  AC-2: NOT EVALUABLE -- no oracle runs on record.
```

**0 of 6. FAIL.** Final rows (thickness / hollow / aniso; vesicle needs < 0.25 hollow, > 0.5 aniso,
> 3.0 thickness):

    L=36 sd=1  3.176  0.507  0.578      L=30 sd=1  1.293  0.530  0.775
    L=36 sd=2  1.991  0.441  0.248      L=30 sd=2  1.250  0.547  0.276
    L=36 sd=3  0.098  0.474  0.519      L=30 sd=3  0.235  0.554  0.459

**`hollow` never moved.** It sat at 0.44-0.55 in all six runs from step 25,000 to step 400,000 --
2.4 million integrator steps in total with no drift toward the 0.000 vesicle reference. This is the
variable that must fall for a vesicle to exist.

**Membranes formed and dissolved rather than consolidating.** Thickness oscillated all run: L=30 sd=2
went 0.90 -> 2.99 -> 1.26 -> 2.44 -> 0.22 -> 1.25; L=36 sd=3 reached 4.02 at step 25k (a genuine
bilayer, matching the oracle's 4.05) and ended at 0.098, which is the GAS control's value. The
reference model's published trajectory coarsens monotonically and then zips shut. This does not
resemble it.

### Diagnosis: the two conditions are incompatible at N = 1000

The box must EXCEED the spanning threshold (26.0 sigma) or a patch spans and has no edges to lose. It
must also be DENSE enough for patches to survive and merge. At N = 1000 those cannot both hold:

    L = 30  ->  phi 0.111       L = 36  ->  phi 0.070       reference: phi 0.192

Both arms are 2-3x too dilute. Satisfying the spanning constraint forced a violation of the density
constraint, and the aggregates evaporated. **At fixed N the two pull in opposite directions, so the
fix is MORE LIPIDS, not a different box** -- N such that a box above the spanning threshold still
reaches phi ~ 0.19. That is roughly N = 2700 at L = 30 (8100 beads), about 8x the cost of these runs.

### AC-2 is NOT satisfied -- and the gate said it was

The scoring function reported "AC-2 (oracle also fails -> recipe untested): True" while **no oracle run
existed**: the oracle rate defaulted to 0 and `0 < 0.66` is trivially true. The gate asserted a
conclusion it had no data for. Fixed to report NOT EVALUABLE. Whether this null indicts our engine or
the recipe is **undecided**, and the staged oracle control is what would decide it.

**Status: H3 not supported. Not a clean refutation either** -- the density confound is a live
alternative explanation, and it was registered in section 7 as a threat before the run.

## 10. Amendment 2 — 2026-08-31: test the density diagnosis directly, before spending on the oracle

Section 9 attributes the 0/6 to dilution: aggregates formed and evaporated because phi was 0.070-0.111
against the reference's 0.192. **That is currently an inference from trajectories, not a measurement.**

Two ways forward, and the cheap one comes first:

- staged oracle at N=1000: ~23 h per seed, and answers "is the recipe sound", not "why did ours fail".
- **density series: ~1 h, and tests the stated mechanism directly.**

**Prediction, registered before the runs.** Hold N = 1000 fixed and vary only the box:

    L = 25 -> phi 0.192 (reference density, BELOW the 26.0 spanning threshold)
    L = 27 -> phi 0.152
    L = 30 -> phi 0.111 (failed arm)
    L = 36 -> phi 0.070 (failed arm)

If dilution is the cause, **thickness should consolidate and STAY high at phi >= 0.15, and oscillate
or decay at phi <= 0.11**. Scored as the mean and the minimum of thickness over the second half of
each run: a consolidated membrane holds a high minimum, an evaporating one does not.

**If thickness decays at every density**, dilution is NOT the cause, section 9's diagnosis is wrong,
and the failure is something about our engine that the oracle control must then decide. That is the
outcome that would refute my own explanation, which is why it is written down first.

2 seeds x 4 boxes, 100k steps. Note L = 25 is deliberately below the spanning threshold: this
experiment asks only whether membranes CONSOLIDATE, not whether they close.

### Outcome of Amendment 2 — the density diagnosis is REFUTED

    packing   mean thickness (2nd half of run, 2 seeds)
     0.034     1.58
     0.058     2.48
     0.080     1.51
     0.101     1.52

    monotone increasing with density (the prediction): False
    correlation(density, thickness) = -0.30    (prediction required strongly positive)
    best density is 0.058 -- the SECOND MOST DILUTE

**Section 9's explanation of the 0/6 is withdrawn.** Thickness does not rise with density; the
correlation is slightly negative and the best cell is near the dilute end. Every trace oscillates
between ~0.1 and ~3.3 at every density. Membranes fail to consolidate **everywhere**, not just when
thin.

**The stronger statement:** the best cell in the whole series reaches mean thickness 2.48, against a
random start of 1.31 and a real bilayer of 4.05-4.40. **At no density does this configuration hold a
membrane together.** The 0/6 is not about closure and not about dilution -- nothing gets far enough to
attempt closure.

**Unit error, recorded.** Section 9 quotes "phi 0.111 / 0.070 against reference 0.192". Those are
NUMBER DENSITIES (beads per sigma^3), not packing fractions; the true packing fractions are 0.058,
0.034 and 0.101. The comparison was ratio-consistent so the "2-3x more dilute" claim was arithmetically
fine, but the quantity was mislabelled throughout.

**This is the branch where the oracle earns its 23 h.** With density excluded, the candidates are our
engine (chain stiffness, bond form, bounded core) or the recipe/harness. The oracle at these settings
separates them: if a known-working model also fails to consolidate here, the fault is not our engine.

## 11. Amendment 3 — 2026-08-31: closure retest, now on a membrane that actually exists

Sections 9-10 are superseded in their *cause*, not their data. The 0/6 and the density null were both
produced by a model whose lipids had **zero harmonic bending stiffness** (1-3 spring resting at its own
geometric length gives a quartic, not quadratic, bending energy -- verified by algebra on our own
potential, V/delta^4 constant at 0.9375). With that fixed:

- a planted planar bilayer SURVIVES (min thickness 0.65 -> 2.87), Gate B;
- a membrane SELF-ASSEMBLES from a random start and persists (1.72 -> 3.41 mean thickness, 15% -> 77%
  of the way from random gas to a real bilayer, perfect 3v3 separation, p = 0.050).

**Only now is a closure test meaningful**, because every previous one asked an object that could not
persist to also close.

**Sizing, recomputed against the MEASURED thickness of 3.4** (not the 4.0 assumed earlier):

    N=1000  R=7.3  R/thick=2.15  patch side 26.0
    N=1600  R=9.3  R/thick=2.72  patch side 32.9
    N=2400  R=11.4 R/thick=3.34  patch side 40.2

**Arms:** N = 1600, boxes L in {36, 40} (9% and 22% above the 32.9 spanning threshold), k_theta = 33,
bend_r0 = 4.0, cooke_chi, kT = 1.0, w_c = 1.4, 3 seeds each, 150k steps.

**Endpoint unchanged from section 5:** hollow < 0.25 AND aniso L1/L3 > 0.5 AND thickness > 3.0, at two
or more consecutive checkpoints, plus a confirming render.

**Threat, stated now.** The density series that showed consolidation is independent of crowding was run
under the BROKEN bending term. It should not be assumed to transfer to the fixed model. If both boxes
fail, density returns as a live variable and must be retested on the fixed model rather than inherited.

### Outcome of Amendment 3 — membranes YES, vesicles NO

    L=36: formed 0/3   mean hollow 0.504
    L=40: formed 0/3   mean hollow 0.519
    VERDICT formed: 0/6

**The membranes are excellent.** thickness = 3.11, 5.27, 4.96, 3.56, 3.86, 4.07; mean **4.14** against a
reference bilayer of 4.05 and random gas of 1.31 -- **103% of the way**, with 3 of 6 at or above the
reference. Self-assembled from a random start. This is by a wide margin the best membrane the project
has produced.

**`hollow` did not move at all.** 0.512 +- 0.022, against 0.000 for a vesicle. Compare across every
configuration measured today:

    broken bending, N=200 planted spheres   0.995
    k_theta=100 planted spheres             0.652
    H3 assembly N=1000 (broken bending)     0.505
    assembly N=1000, bending FIXED          0.500
    closure  N=1600, bending FIXED          0.512

Once a membrane exists at all, `hollow` sits at ~0.50 and is **completely insensitive** to everything
that improved the membrane. Thickness went from "no membrane" to "better than reference" and this
number changed by less than its own scatter.

**The conclusion, stated carefully.** Closure is NOT downstream of membrane stability. The bending fix
was decisive for membranes -- planted bilayers survive, membranes self-assemble and persist -- and it
brought closure no closer whatsoever. The two are independent in this model.

That is a genuine and reportable negative, and it is a *different* negative from the earlier 0/6: then,
nothing survived long enough to attempt closure; now good membranes exist and simply stay open. The
question this finally poses cleanly is the closure mechanism itself -- edge energy versus bending
rigidity -- which could not be asked before because no stable membrane existed to ask it of.

**Density is NOT recovered as the explanation** (the threat registered above): both boxes give the same
`hollow` to within noise, and both produced reference-quality membranes.
