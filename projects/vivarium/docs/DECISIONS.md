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

## Progress ledger

| rung | gate | metric | status |
|---|---|---|---|
| D1 | solvent EOS | T within 10%, homogeneity < 0.35, MSD > 0.1 | **PASS** (T 1.013, homog 0.12, MSD 16.0) |
| D2 | species incompatibility | demixing separates from measured null | **PASS** (0.496 null → 0.886) |
| D3 | amphiphile mesophase | concentration-dependent morphology | **PASS** (micellar → elongated → bands) |
| E | exact DPD inside Vivarium | reproduces the phi series | **next** |
| F | transformerised DPD | reproduces E | pending |
| G | custom Vivarium chemistry | reproduces the phase family | pending |

**Stall policy.** If a rung fails twice with different approaches, re-examine that rung's *metrics*
before its physics — this project has retracted more conclusions to bad instruments than to bad
models. If still stuck, stop and escalate rather than sweeping parameters.
