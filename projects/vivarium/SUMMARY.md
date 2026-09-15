# vivarium — executive summary

*Updated 2026-09-14. **Scope: 2-D only** — 3-D is archived, see Roadmap. Current state only. History lives in `docs/RESEARCH_LOG.md`; every experiment and
its result in **[`docs/ROADMAP.md`](docs/ROADMAP.md)**, the single consolidated roadmap.*

## Objective

Can a **lipid vesicle** — a hollow bubble with a two-layer skin, the basic unit of a cell membrane —
build itself in a simulation where **every force is a transformer attention operation**? Each molecule
is a token; each step is one forward pass. The rule that makes the question meaningful: nothing may be
put in that already contains the answer, so a "make the membrane bend" term is refused — a bubble that
forms because we told it to bend has not emerged. **A 2-D vesicle does emerge**, verified by picture
and metric, from a scattered start with nothing planted; it forms by a ribbon wrapping until its two
ends meet, not by curving. **The full objective is not met**: the goal names excluded volume, van der
Waals *and electrostatics*, and the model has the first two; emergence is rare. **Scope narrowed to
2-D on 2026-09-14** — every open question that matters (does a patch bend? what selects a size? which
gate defines a vesicle?) is answerable in 2-D and unanswered there, so 3-D at ~29× the cost is the
wrong order.

## Requirements

- **R1 — Transformer-only.** Every force is a masked attention head; one forward pass equals one step.
  Verified end-to-end by `tests/test_physical_realism.py`, which checks each head against the equation
  it claims to compute and cross-checks a published membrane potential expressed in the same primitives.
- **R2 — Nothing that contains the answer.** No spontaneous-curvature term, no "bend here" knob. New
  terms are *derived* from geometry or standard physics, never fitted to make a vesicle appear.
- **R3 — An energy ledger.** Forces must be `−grad U`. Without it, temperature, line tension and
  bending modulus are undefined. This is what forbids softmax (it breaks Newton's third law).
- **R4 — Instruments must SEPARATE their controls**, not merely score the intended case well — a
  known-answer case *and* a null case. Nineteen rules in `docs/MEASUREMENT_DISCIPLINE.md`, each bought
  with a defect; in every case the physics was fine and the instrument was wrong.
- **R5 — Look at the picture before believing the number.** Every structural claim needs a render.
- **R6 — Criteria before data.** Gates registered in `specs/` before the run, scored mechanically,
  amendments dated.
- **R7 — Results are regenerable.** Every number traces to an append-only TSV in `docs/results/`.
- **R8 — One implementation per concept.** Two force paths that disagreed silently voided a
  48-CPU-hour experiment.
- **R9 — Faithful to nature before favourable to the result.** In a doubtful modelling choice, take
  what nature does even if it makes a vesicle less likely. A correct term that lowers the vesicle rate
  is a success and is reported as one. Departures are catalogued in the roadmap's fidelity audit.

## How success is measured

Two separate questions, two separate answers. Conflating them is how this project has repeatedly
claimed more than it had.

### 1. Is the physics real? — `tests/test_physical_realism.py`, 13 gates, all passing

Every force is checked against the equation it claims to compute, not against a docstring:

| what is checked | against | result |
|---|---|---|
| non-bonded head | `−(1/r)·dU/dr` for `U = ε[core(s) + well(s)·χ]` analytically | < 1e-12 |
| bond head | Hooke's law `−k(r−r₀)/r` | < 1e-12 |
| the content term `q·k` | the χ interaction table | < 1e-12 |
| all heads summed | `field.forces` | exact |
| Newton's third law | `ΣF = 0` | < 1e-9 |
| force is a gradient | `F = −∇U`, central differences | < 1e-4 |
| translational + rotational invariance | space has no origin and no preferred direction | < 1e-8 |
| energy conservation | thermostat off | < 2% |
| equipartition | the temperature requested | < 10% |
| **the oracle** | a published membrane potential (Yuan–Li–Zhang) rewritten *exactly* as attention | < 1e-10 |

`core(s) = h(1−s)²` is excluded volume; `well(s)` is the van der Waals term; `χ_ij = q_i·k_j` is the
interaction matrix *and* the query–key inner product — they are the same numbers.

**This settles realism of the LAW only.** It does not test realism of the *molecule* — every departure
in the roadmap's fidelity audit (no electrostatics, zero chain bending rigidity, no hydrodynamics,
2-D) would pass it. And it does not test the *measurements*, which is where every failure this project
has had actually lives.

### 2. Is it a vesicle? — `vesicle_gate.vesicle()`, two clauses, no free parameters

**A vesicle is a connected lipid aggregate whose enclosed void is bounded by that aggregate arranged
as a bilayer.** That is the whole definition, and both clauses are physical:

- **CLOSED** — *some* connected aggregate encloses exactly one void, stably across a dilation ladder.
  Existential, not "the largest": in the flagship sd509 state the largest aggregate is an **open
  ribbon** and the vesicle is a smaller separate cluster. Requiring *one* aggregate is what rejects
  three micelles that jointly surround a pocket.
- **BILAYER** — of that aggregate's lipids, the fraction whose head points inward. Two leaflets sit
  near 0.5; a monolayer loop sits at 0 or 1. Per-molecule, which is why it survives thermal noise
  where three distributional attempts did not. **Measured contribution: none, on current data.** All
  24 enclosing states score 0.368–0.540, so closure alone yields the same set. It is carried on its
  physics — it would reject a closed monolayer — not on demonstrated discrimination, and no monolayer
  loop occurs in this data to test it against.

Score is graded (`closure × bilayer`), so a sweep can be gated on it where a 3 % binary event cannot.

| | score |
|---|---|
| sd915 / sd904 / sd903 / planted ring / sd509 | **0.955 / 0.857 / 0.848 / 0.750 / 0.737** |
| three micelles (scored 0.5997 on the old curl metric) | **0.000** — rejected by closure; its bilayer reads 0.41 |
| arc 0.75 — open but nearly closed, the hardest negative | **0.000** |
| flat ribbon, dispersed | **0.000** |

**Margin 0.737.** `vesicle_gate.validate()` is the panel and runs in the suite.

**What this replaced.** `vesicle_call` needed a lumen-ratio threshold of 0.10 whose own docstring says
it exists to reject "a branched network that happens to enclose one incidental pocket" — a *size*
proxy for a *structural* question. Asking the structural question directly removes the constant.

### The older pair, kept for comparison — and they disagree by fourteen-fold

Two gates are applied to the same runs and disagree by fourteen-fold:

| gate | what it requires | rate over 148 production runs |
|---|---|---|
| enclosure | any enclosed pocket at any checkpoint | **60/148 — 41%** |
| `vesicle_call` | enclosure stable across *every* dilation 1.0–3.0, **and** lumen ratio ≥ 0.10 | **5/148 — 3%** |

Both numbers are real and describe the same physics; they ask different questions. The strict gate
exists because the loose one once passed a 69-cell pocket that vanished under dilation, and a
branched network that enclosed an incidental hole. **Which one defines a vesicle has never been
decided, and no further run can decide it.**

Neither gate checks that the shell is a **bilayer** — two leaflets, heads facing out. Three attempts
to measure that on 2026-09-14 all failed their controls (one could not fail at all; one rejected a
genuine thin bilayer; one could not tell a relaxed planted ring from an emergent state). **So the
defining structural property of the headline result is currently unmeasured.**

### The rule that would have caught all of it

Every gate must ship with a control panel of **positives and negatives it must separate, at the
thermal noise of real data, including a marginal case.** Validating on clean planted states at step 0
is what produced all four broken metrics: a flat ribbon and a closed ring both read ≈0.6 on a
curvature metric once relaxed, and `aspect` survives only because it is a global shape measure rather
than a local one.

## System design

```
                    ┌──────────────────────────────────────────────┐
   experiment  ───► │  HARNESSES        gap_closure · emerge_reduced │
   specs/           │                   curl · curl_witness · phase  │
                    └───────────────┬──────────────────────────────┘
                                    │  build system, step, score
                    ┌───────────────▼──────────────┐   ┌─────────────────────┐
                    │  _mixture.build()            │   │  INSTRUMENTS        │
                    │  make_step_engine(engine=…)  │──►│  _lumen_field (2-D) │
                    └───────────────┬──────────────┘   │  _lumen3d    (3-D)  │
                                    │                  │  bilayer_metrics    │
              ┌─────────────────────┴──────────┐       │  phase · curl       │
              ▼                                ▼       └─────────┬───────────┘
     ┌──────────────────┐            ┌───────────────────┐       │ renders
     │ field.Field      │            │ transformer       │       ▼
     │  energy(X)       │◄──_env()──►│  attention(X)     │   gap_shot / _shot
     │  forces(X)       │  ONE source│  forward(X,v,…)   │      → PNG
     └────────┬─────────┘  of truth  └───────────────────┘
              │ optional
     ┌────────▼─────────┐        ┌──────────────────────────────┐
     │ manybody         │        │  server.py + viewer.html     │
     │  ShapeMLP  (σ)   │        │  GET /  GET /state  (:8090)  │
     │  ManyBodyMLP (χ) │        │  → tailscale /vivarium       │
     └──────────────────┘        └──────────────────────────────┘
```

### Components

- **`field.py`** — the potential and its exact gradient. `Field(species, bonds, L, chi=,
  sigma_species=, bend_r0=, manybody=, shape=)` → `.energy(X)`, `.forces(X)`, `.coordination(X)`.
- **`transformer.py`** — the same force law as three masked attention heads (non-bonded, bond, 1-3
  stiffener). Unnormalised, no softmax. `q·k` equals the χ table to 1e-12, but **the force law reads χ
  from `field._env`, not from `q·k`** — see Known gaps.
- **`_mixture.py`** — system builder and step engine; velocity Verlet with an Ornstein–Uhlenbeck
  thermostat.
- **`manybody.py`** — optional per-token modulators: `ShapeMLP` (σ from coordination), `ManyBodyMLP`
  (χ from coordination). Both carry the `∂U/∂n · ∂n/∂x` force term. `n_ref` has no default, by design.
- **Instruments** — `_lumen_field`, `_lumen3d`, `bilayer_metrics`, `phase`, `curl`. Each has a
  `validate()` that must separate its controls.
- **Harnesses** — one per registered experiment, append-only TSV. `curl_witness.py` renders a run
  while it is in flight, because the gates only save a state when they pass.
- **`server.py`** — read-only HTTP viewer; `GET /state` returns positions, species, gate verdict.

### Design decisions

- **One source of truth for σ and χ: `field._env()`**, called by *both* force paths — two
  implementations disagreeing silently is the most expensive defect this project has had. **Its
  unnoticed cost:** the token channel is no longer on the force path (Known gaps).
- **No softmax.** Row-stochastic weights give `w_ij ≠ w_ji`, so momentum is not conserved and force
  becomes intensive. Required by R3.
- **Weights are constructed, not learned.** `Wq`/`Wk` are the eigendecomposition of χ. No training.
- **Derived constants, never picked.** Free parameters are declared as such; a reference value wrong
  by 30× made two experiments report a null for a term that was doing nothing.
- **States saved the moment a gate passes**, not only at the end — a transient vesicle was lost twice.
- Explicit constructor arguments over environment variables; append-only results with fsync per row;
  scatter-add via `bincount` (8.4×, bit-identical); viewer auto-pauses at a derived step cap.
- **12 workers, not 24** — the box has 16 physical cores, and 12-way out-throughputs 24-way by 1.53×.

## Roadmap

Full experiment list with results: **[`docs/ROADMAP.md`](docs/ROADMAP.md)**.

- **DONE — the transformer formulation is exact and free.** Forces match the ordinary force law to
  1e-13; one forward pass equals one step; no measurable time cost.
- **DONE — 2-D vesicles emerge, with pictures.** Four, all from a scattered start with nothing
  planted, each with its exact recipe in **[`docs/SUCCESSES.md`](docs/SUCCESSES.md)**. The cleanest is
  35 molecules out of 112.
- **QUALIFIED — how the vesicle closes is only half understood.** Two closed at *constant size*, by
  their two ends meeting. This was written up as "ends meeting, **not** curving"; that is wrong — in
  2-D a sheet's rim *is* its two ends, so those are the same event, not alternatives. What is really
  unresolved is what *drives* it. Real membranes close when the cost of an exposed rim beats the cost
  of bending, a competition that fixes a critical size. Here the rim cost was **measured as
  indistinguishable from zero** and the bending stiffness is **not measurable by any of three routes** —
  so what we see is equally consistent with two floppy ends meeting by chance, which would explain the
  1-in-20 rate. **Measuring the bending stiffness would settle it and has never been done.**
- **DONE — the chemistry reduces.** Five hand-set numbers plus the water become one attraction plus a
  size ratio, with no loss on closing a ready-made ribbon (19/20 vs 10/10). **But it loses the
  strictest test** (11/20 vs 18/20) and degrades self-assembly (2/20 vs 13/20).
- **DONE — the good idea from the sister simulation was ported over, with gates.** `polar_pack` is
  expressive but has no energy ledger, so nothing measured in it is a physical quantity. What it had
  that we wanted: its network changes a molecule's *shape*, not its stickiness — and shape is what sets
  curvature. That is now in our force law and passes every check we could put on it (the two force
  routines agree exactly; the term is provably zero on a flat sheet so it cannot smuggle in the answer;
  it measurably engages on a curved one; the force is still the exact derivative of an energy). Left
  behind on purpose: the softmax, and the electrostatic head that was found not to conserve momentum.
- **DONE — molecules can now change with their surroundings, and it works.** A molecule's head grows
  when it is less crowded, and the forces stay exactly derivable from an energy. Turning that up turns
  a flat sheet into small round balls — exactly what the standard theory of molecular shape predicts,
  and the first time anything here has been shown to move that lever.
  **Two things this is NOT, because the name has been misleading.** It is not an "MLP": it is one
  number in, one number out, through a fixed curve — there is no network, no hidden layer, no learned
  weight, and no matrix multiply anywhere in the file. And it is not *running*: it is **off in every
  production run**, including all four vesicles, and is switched on only by the experiment that tests
  it. The one thing in the project that *is* architecturally a network — a hidden layer with a
  residual, inside the transformer — is wired to nothing and has a single caller, a test. **So no
  network is in the loop, in either sense.**
- **RETRACTED — the two earlier "the MLP does nothing" results.** Both divided by a reference number
  wrong by ~30×, so the thing tested was effectively a constant.
- **BLOCKED — making anything bend.** Six attempts, all null. Five are pair forces, and the standing
  explanation covers them: a force between two molecules cannot tell the two layers apart. The sixth
  is not a pair force, so that explanation does not cover it — **but it is not a clean test either**,
  because the term took the sheet apart before it could bend it.
- **BLOCKED — making emergence reliable.** Still 1–2 runs in 20. Three geometric levers failed;
  whatever limits it is not the geometry we have been varying.
- **ARCHIVED — 3-D.** Not blocked, *descoped*, 2026-09-14. Its foundation was already retracted (the
  "bending fix" stretches molecules 67% rather than stiffening them) and it costs ~29× per run. It is
  kept and reversible: `manifest.THREE_D = False` gates it, and every 3-D test is **skipped, not
  deleted** — 22 of them — so the coverage returns by flipping one line.
- **NOT STARTED — fusing and dividing.** Never observed.
- **NEEDS A DECISION — [`docs/HANDOFF_2026-09-12.md`](docs/HANDOFF_2026-09-12.md).** A molecule's own
  internal channel is not wired to the forces. **Nothing is pushed until it is settled.**
- **NEXT** — the order is [`docs/ROADMAP.md`](docs/ROADMAP.md) §9; 3-D is no longer on it. The first four:
  (1) settle the open decision above, then get the suite green and push;
  (2) build the starting sheet at the spacing the model settles at rather than a hand-picked one that
  is 16% too spread out — the cheapest experiment most likely to move the bending question, ~1 h;
  (3) give the molecules the long-range repulsion between charged heads that real ones have, because
  clumps here grow without limit and a vesicle is an object with a preferred size. **Not a fresh
  idea** — the sister simulation already tried it, its version turned out not to conserve momentum for
  three months undetected, and it never produced assembly. Any version here needs that check from the
  first commit;
  (4) the rest of the network's abilities, which need (1) first.
## Known gaps

- **The test suite is RED** (`1 failed, 255 passed, 22 skipped`), and has been since 2026-09-09.
  The 22 skips are the archived 3-D tests. Five of those were FAILING before they were skipped
  (net momentum NaN, wrap NaN, unit-axis drift) for reasons never isolated — `aliveness.py` was
  cleared by direct comparison (identical to 1.11e-16 in 2-D *and* 3-D) and the new test files by a
  run without them (248 passed / same 6 failed). Recorded as unexplained rather than given a cause;
  it is archived code and every 2-D arm of those tests passes. The one real failure is: Changing a
  molecule's own channel no longer changes the forces on it: the force law reads the interaction table
  directly instead of through that channel. The two agree to twelve decimal places, so **no measured
  number is affected** — what is lost is the *ability* for a molecule's channel to change its physics,
  which the next MLP work needs. Introduced by the commit that fixed a worse bug, and unnoticed
  because nobody ran the suite. **Do not make it green by weakening the test.**
- Emergence is rare and uncontrolled. The one lever that predicts closure — how close a ribbon's two
  ends are — is a property of a ribbon that already exists, not something we can set.
- The historical "2 of 18" result is **uncheckable**: a looser test, and its states were overwritten.
  Not refuted; unverifiable.
- ~~The tree is not consolidated~~ — **DONE 2026-09-13.** 59 dead files / 4 999 lines removed
  (146 → 87 modules) after building the real dependency graph: the keep-set is the production path,
  the oracles, the live harnesses, the instruments, and everything the tests import. Verified by
  build + full suite before and after — identical result, so nothing load-bearing went. Kept on merit
  despite having no callers: `_kappa` and `_linetension` (they measure the two quantities the open
  bending question needs) and the renderers (R5).
- Emergence is rare and uncontrolled. The one lever that predicts closure — how close a ribbon's two
  ends are — is a property of a ribbon that already exists, not something we can set.
- The historical "2 of 18" result is **uncheckable**: a looser test, and its states were overwritten.
  Not refuted; unverifiable.
- **The tree is NOT consolidated.** The production *path* is single and clear —
  `_mixture.make_step_engine(engine="transformer")` → `transformer.VivariumTransformer(field.Field)`.
  But several other force laws live alongside it with real dependents: `dpd_reference.py`
  (Groot–Warren DPD, **18 importers**), `polar_pack.py` (softmax-based, **12**), `ylz.py` /
  `attention_ylz.py`, `bilipid.py`, `cooke_deserno.py`. Two of those are *deliberate* controls, written
  to sit outside the transformer constraint so the transformer results have something to be checked
  against — they are not cruft. The rest is genuine duplication (`plant` in 18 files, `build` in 15,
  `step` in 12), and consolidating is real work, not a file move: what looks like dead legacy is
  usually a builder the viewer or four tests depend on.
