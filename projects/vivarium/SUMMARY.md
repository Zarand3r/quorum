# vivarium — executive summary

*Updated 2026-09-11. Current state only; history lives in `docs/RESEARCH_LOG.md`, experiments and their
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
  known-answer case *and* a null case. Twenty-five defects on record, all instruments, none physics.
- **R5 — Look at the picture before believing the number.** Every structural claim needs a render.
- **R6 — Criteria before data.** Gates are registered in `specs/` before the run and scored
  mechanically. Amendments are dated, never silent edits.
- **R7 — Results are regenerable.** Every number traces to an append-only TSV in `docs/results/`.
- **R8 — One implementation per concept.** Two force paths that disagreed silently voided a
  48-CPU-hour experiment.

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
  1-3 stiffener). `q·k` **is** the χ table. Unnormalised — no softmax.
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
  implementations disagreeing silently is the most expensive defect this project has had.
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
- **DONE — 2-D vesicles emerge, and we have the pictures.** Three now, all from a scattered start with
  nothing planted, all recorded with their exact recipe in **[`docs/SUCCESSES.md`](docs/SUCCESSES.md)**
  so none can be lost the way the original was. The cleanest is 35 molecules out of 112.
- **DONE — the mechanism is identified.** Two independent vesicles closed at *constant size* (56 and
  116 molecules) — two ends of a ribbon meeting, not curving.
- **DONE — the chemistry reduces.** Five hand-set numbers plus the water become one attraction plus a
  size ratio, with no loss on closing a ready-made ribbon (19/20 vs 10/10). **But it loses on the
  strictest test** (11/20 vs 18/20) and it degrades self-assembly (2/20 vs 13/20).
- **DONE — a live MLP inside real physics.** Molecules can now change with their surroundings while
  forces stay exactly derivable from an energy. **It does not bend membranes** (0/12 in both channels).
- **BLOCKED — making anything bend.** Seven independent attempts, all null. The standing explanation
  ("symmetric pair forces cannot differ between the two layers") no longer covers the last two, which
  are not pair forces.
- **BLOCKED — 3-D.** Its foundation needs redoing: the "bending fix" was found to stretch molecules 67%
  rather than stiffen them. Costs ~29× more per run than 2-D.
- **NOT STARTED — fusing and dividing.** Never observed.
- **NEXT** — (1) raise the 2-D emergence rate, since only ~1 run in 32 succeeds; (2) decide which test
  defines a vesicle, because the old headline used a looser one; (3) rebuild 3-D with inextensible
  bonds before spending compute there.

## Known gaps

- Emergence is rare and we cannot yet control it. The one lever that predicts closure — how close a
  ribbon's two ends are — is a property of a ribbon that already exists, not something we can set.
- The historical "2 of 18" result is **uncheckable**: it used a looser test and its saved states were
  overwritten. Not refuted; unverifiable.
- The same concept is implemented many times over — `plant` in 18 files, `build` in 15, `step` in 12.
  Two force paths that disagreed silently once voided a 48-CPU-hour experiment. Consolidating this is
  real work, not a file move: the files that look like dead legacy are in fact the builders the viewer
  and four tests depend on.
