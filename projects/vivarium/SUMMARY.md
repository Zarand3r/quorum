# vivarium — executive summary

*Updated 2026-09-13. Current state only; history lives in `docs/RESEARCH_LOG.md`, experiments and their
results in **[`docs/ROADMAP.md`](docs/ROADMAP.md)** — the single consolidated roadmap.*

## Objective

Can a **lipid vesicle** — a hollow bubble with a two-layer skin, the basic unit of a cell membrane —
build itself in a simulation where **every force is a transformer attention operation**? Each molecule
is a token; each simulation step is one forward pass. The rule that makes the question meaningful:
nothing may be put in that already contains the answer, so a "make the membrane bend" term is refused —
a bubble that forms because we told it to bend has not emerged. **A 2-D vesicle now does emerge**,
verified by picture and metric, from a scattered start with nothing planted. It forms by a ribbon
wrapping until its two ends meet, not by curving. Making that reliable, and reaching 3-D, is open.

## Requirements

- **R1 — Transformer-only.** Every force is a masked attention head; one forward pass equals one
  simulation step. No force may be computed outside that form.
- **R2 — Nothing that contains the answer.** No spontaneous-curvature term, no "bend here" knob. New
  terms must be *derived* from geometry or standard physics, never fitted to make a vesicle appear.
- **R3 — An energy ledger.** Forces must be `-grad U` of a scalar potential. Without it, temperature,
  line tension and bending modulus are undefined and nothing can be compared to published values.
  This is what forbids softmax attention (it breaks Newton's third law).
- **R4 — Every instrument validated against cases it must SEPARATE**, not merely score well — a
  known-answer case *and* a null case. Twenty-six defects on record, all instruments or constants,
  none physics. The newest: a constant described as "geometry" that was wrong by ~30×, which made two
  experiments report a null for a term that was not doing anything.
- **R5 — Look at the picture before believing the number.** Every structural claim needs a render.
  On 2026-09-12 a run scored 0.5997 on the curl metric against a 0.45 bar; the picture is three round
  blobs, not a bent sheet. A second, pre-registered check caught it — not the metric.
- **R6 — Criteria before data.** Gates are registered in `specs/` before the run and scored
  mechanically. Amendments are dated, never silent edits.
- **R7 — Results are regenerable.** Every number traces to an append-only TSV in `docs/results/`.
- **R8 — One implementation per concept.** Two force paths that disagreed silently voided a
  48-CPU-hour experiment.
- **R9 — Faithful to nature before favourable to the result.** In any doubtful modelling choice, take
  what nature does, even if it makes a vesicle less likely. Nature is not ideal, and a model tuned
  toward the answer stops being evidence for it. Known departures are listed in the roadmap's fidelity
  audit; a correct term that lowers the vesicle rate is reported as a success.

## System design

```
                    ┌──────────────────────────────────────────────┐
   experiment  ───► │  HARNESSES        gap_closure · emerge_reduced │
   specs/           │                   curl · phase · vesicle3d     │
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

- **`field.py`** — the potential and its exact gradient. `Field(species, bonds, L, chi=, sigma_species=,
  bend_r0=, manybody=, shape=)` → `.energy(X)`, `.forces(X)`. Verlet + cell-list neighbours.
- **`transformer.py`** — the *same* force law as three masked attention heads (non-bonded, bond,
  1-3 stiffener). `q·k` equals the χ table to 1e-12 (pinned by a test). Unnormalised — no softmax.
  **But the force law reads χ from `field._env`, not from `q·k`** — see the red test below.
- **`_mixture.py`** — system builder (`build`) and step engine (`make_step_engine`), velocity Verlet
  with an exact Ornstein–Uhlenbeck thermostat.
- **`manybody.py`** — optional per-token modulators: `ShapeMLP` (σ from coordination), `ManyBodyMLP`
  (χ from coordination). Both carry the extra `∂U/∂q · ∂q/∂n · ∂n/∂x` force term.
- **Instruments** — `_lumen_field` (2-D enclosure + `vesicle_call`), `_lumen3d` (3-D enclosure),
  `bilayer_metrics`, `phase`, `curl`. Each has a `validate()` that must separate its controls.
- **Harnesses** — one per registered experiment, writing append-only TSV.
- **`server.py`** — read-only HTTP viewer; `GET /state` returns positions, species and the gate verdict.

### Design decisions

- **One source of truth for σ and χ: `field._env()`**, called by *both* force paths. Two
  implementations disagreeing silently is the most expensive defect this project has had. **That fix
  has a cost that was not noticed at the time**: the token channel is no longer on the force path, so
  the per-molecule channel cannot change interactions. See the red test below.
- **No softmax.** Row-stochastic weights give `w_ij ≠ w_ji`, so `F_ij ≠ −F_ji` — momentum is not
  conserved and force becomes intensive. Required by R3.
- **Weights are constructed, not learned.** `Wq`/`Wk` are the eigendecomposition of χ; the MLP
  expresses a derived law. There is no training phase.
- **Explicit over environment.** `bend_r0` and chemistry are constructor arguments; a process-global
  env var once gave two A/B arms the same value.
- **Append-only results, fsync per row**, so a killed sweep costs one run, not the night.
- **States saved at the moment a gate passes**, not only at the end — a transient vesicle was lost
  twice by saving only the final frame.
- **Scatter-add via `bincount`, not `np.add.at`** — 8.4×, bit-identical.
- **Viewer auto-pauses** at a derived step cap (200 k formed / 600 k dispersed) so an unattended tab
  cannot run forever.

## Roadmap

Full experiment list with results: **[`docs/ROADMAP.md`](docs/ROADMAP.md)**.

- **DONE — transformer formulation is exact and free.** Forces match the ordinary force law to 1e-13;
  one forward pass equals one step; no measurable time cost.
- **DONE — 2-D vesicles emerge, and we have the pictures.** Four now, all from a scattered start with
  nothing planted, all recorded with their exact recipe in **[`docs/SUCCESSES.md`](docs/SUCCESSES.md)**
  so none can be lost the way the original was. The cleanest is 35 molecules out of 112.
- **DONE — the mechanism is identified.** Two independent vesicles closed at *constant size* (56 and
  116 molecules) — two ends of a ribbon meeting, not curving.
- **DONE — the chemistry reduces.** Five hand-set numbers plus the water become one attraction plus a
  size ratio, with no loss on closing a ready-made ribbon (19/20 vs 10/10). **But it loses on the
  strictest test** (11/20 vs 18/20) and it degrades self-assembly (2/20 vs 13/20).
- **DONE — a live MLP inside real physics, and it demonstrably works.** Molecules can now change with
  their surroundings while forces stay exactly derivable from an energy. Making a molecule's head
  bigger when it is less crowded turns a flat sheet into small round balls — which is precisely what
  the standard theory of molecular shape says should happen, and it is the first time anything in this
  project has been shown to move that lever. The effect grows with the strength of the term and is
  overwhelming (the sheet survives 12 times out of 12 with the term off, and 2, 0 and 0 times out of 12
  as it is turned up).
  **Kept for the physics, not for the vesicle count** (decision 2026-09-11): before it, every force was
  a function of one distance between two molecules and a molecule could know nothing about its own
  situation. It stays **off by default** while its one free number is undetermined, and any vesicle
  appearing with it on is reported as "with a curvature-capable term present", never as "from nothing".
- **RETRACTED — the two earlier "the MLP does nothing" results.** Both divided by a reference number
  wrong by a factor of about thirty, so the molecule's size barely changed: the thing being tested was
  effectively a constant. Re-derived from measurement and re-run.
- **BLOCKED — making anything bend.** Six attempts, all null. Five are forces between pairs of
  molecules, and the standing explanation covers them: a force between two molecules cannot tell the
  two layers apart. The sixth — the shape term above — is *not* a pair force, so that explanation does
  not cover it, **but it is not a clean test either**: the term took the sheet apart before it could
  bend it, so "would it bend a sheet that stayed whole?" is still unanswered. Answering it needs the
  starting sheet built at the spacing the model itself settles at, which is the top of the next list.
- **BLOCKED — 3-D.** Its foundation needs redoing: the "bending fix" was found to stretch molecules 67%
  rather than stiffen them. Costs ~29× more per run than 2-D.
- **NOT STARTED — fusing and dividing.** Never observed.
- **BLOCKED — making emergence reliable.** Three separate attempts to move the rate by changing the
  system's size or crowding have now failed; it sits at 1-2 runs in 20 regardless. Whatever limits it
  is not the geometry we have been varying.
- **NEEDS A DECISION — [`docs/HANDOFF_2026-09-12.md`](docs/HANDOFF_2026-09-12.md).** A molecule's own
  internal channel is not wired to the forces. Details in Known gaps; **nothing is pushed until it is
  settled.**
- **NEXT**, in order — (1) settle the one open decision in the handoff, because everything else is
  downstream of what the project claims, then get the test suite green and push; (2) finish the last
  untested strength of the shape term (it is set up and takes about an hour); (3) build the starting
  sheet at the spacing the model settles at rather than a hand-picked one — it is 16% too spread out,
  which is why the term wrecks the sheet before it can bend it, and this is the single experiment most
  likely to move the bending question; (4) try adding the repulsion between charged heads that real
  lipids have and this model is missing — clumps here grow without limit, which is the signature of a
  model with no preferred size, and a vesicle is an object with a preferred size; (5) decide which test
  defines a vesicle, because the old headline used a looser one; (6) rebuild 3-D with inextensible
  bonds before spending compute there.

## Known gaps

- **The test suite is RED, and has been since 2026-09-09.** `1 failed, 253 passed`. The failure is
  `tests/test_transformer.py::test_mlp_is_live_not_decorative`: changing a molecule's own channel no
  longer changes the forces on it, because the force law now reads the interaction table directly
  instead of through that channel. The two agree to twelve decimal places, so every number measured so
  far is unaffected — what is lost is the *ability* for a molecule's channel to change its physics.
  It was introduced by the commit that fixed a worse bug (two force routines that disagreed), and it
  went unnoticed because nobody ran the suite. **Do not make it green by weakening the test**: putting
  the channel back on the force path would shift every trajectory in the last decimal place and would
  need every stored result re-derived. That is a decision about what the project claims, and it is
  written up for review rather than taken unattended.
- Emergence is rare and we cannot yet control it. The one lever that predicts closure — how close a
  ribbon's two ends are — is a property of a ribbon that already exists, not something we can set.
- The historical "2 of 18" result is **uncheckable**: it used a looser test and its saved states were
  overwritten. Not refuted; unverifiable.
- The same concept is implemented many times over — `plant` in 18 files, `build` in 15, `step` in 12.
  Two force paths that disagreed silently once voided a 48-CPU-hour experiment. Consolidating this is
  real work, not a file move: the files that look like dead legacy are in fact the builders the viewer
  and four tests depend on.
