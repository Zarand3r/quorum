# vivarium — executive summary

*Updated 2026-09-13. Current state only. History lives in `docs/RESEARCH_LOG.md`; every experiment and
its result in **[`docs/ROADMAP.md`](docs/ROADMAP.md)**, the single consolidated roadmap.*

## Objective

Can a **lipid vesicle** — a hollow bubble with a two-layer skin, the basic unit of a cell membrane —
build itself in a simulation where **every force is a transformer attention operation**? Each molecule
is a token; each step is one forward pass. The rule that makes the question meaningful: nothing may be
put in that already contains the answer, so a "make the membrane bend" term is refused — a bubble that
forms because we told it to bend has not emerged. **A 2-D vesicle does emerge**, verified by picture
and metric, from a scattered start with nothing planted; it forms by a ribbon wrapping until its two
ends meet, not by curving. **The full objective is not met**: the goal names excluded volume, van der
Waals *and electrostatics*, and the model has the first two; 3-D is blocked; emergence is rare.

## Requirements

- **R1 — Transformer-only.** Every force is a masked attention head; one forward pass equals one step.
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
- **DONE — a live MLP inside real physics, and it works.** Molecules change with their surroundings
  while forces stay exactly derivable from an energy. Making a head bigger when it is less crowded
  turns a flat sheet into small round balls — exactly what the standard theory of molecular shape
  predicts, and the first time anything here has been shown to move that lever. **Kept for the physics,
  not the vesicle count**; off by default until its one free number is derived.
- **RETRACTED — the two earlier "the MLP does nothing" results.** Both divided by a reference number
  wrong by ~30×, so the thing tested was effectively a constant.
- **BLOCKED — making anything bend.** Six attempts, all null. Five are pair forces, and the standing
  explanation covers them: a force between two molecules cannot tell the two layers apart. The sixth
  is not a pair force, so that explanation does not cover it — **but it is not a clean test either**,
  because the term took the sheet apart before it could bend it.
- **BLOCKED — making emergence reliable.** Still 1–2 runs in 20. Three geometric levers failed;
  whatever limits it is not the geometry we have been varying.
- **BLOCKED — 3-D.** Its foundation needs redoing: the "bending fix" stretches molecules 67% rather
  than stiffening them. ~29× the 2-D cost.
- **NOT STARTED — fusing and dividing.** Never observed.
- **NEEDS A DECISION — [`docs/HANDOFF_2026-09-12.md`](docs/HANDOFF_2026-09-12.md).** A molecule's own
  internal channel is not wired to the forces. **Nothing is pushed until it is settled.**
- **NEXT** — the order is [`docs/ROADMAP.md`](docs/ROADMAP.md) §9; the first four are:
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

- **The test suite is RED, and has been since 2026-09-09** (`1 failed, 253 passed`). Changing a
  molecule's own channel no longer changes the forces on it: the force law reads the interaction table
  directly instead of through that channel. The two agree to twelve decimal places, so **no measured
  number is affected** — what is lost is the *ability* for a molecule's channel to change its physics,
  which the next MLP work needs. Introduced by the commit that fixed a worse bug, and unnoticed
  because nobody ran the suite. **Do not make it green by weakening the test.**
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
