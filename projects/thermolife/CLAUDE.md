# thermolife — project-specific instructions

thermolife visualizes **embedding folding as ligand–receptor docking**: a toy
transformer whose token embeddings morph through iterated attention (Hinton's
"embeddings fold like proteins"), each rendered as a **grounded 2D contour blob**
that docks with complementary blobs. The repo-root `CLAUDE.md` has the universal
skill routing and engineering rules; this file adds the project-specific anchors.

## Project anchors

- **Plan** — [`PLAN.md`](PLAN.md) is the source of truth: the mechanism (§4), the
  visualization contract (§5), invariants **J1–J6** (§6), the `fold/` module map (§7),
  milestones **S0–M3** (§8), and §9 (what changed from the earlier thermodynamic-grid
  design). Read it before changes that cross layers.
- **Workspace** — Bazel `rules_python`, like every project in this repo. Deps come
  from the `thermolife_deps` `pip.parse` hub (numpy + pyyaml today; **torch** arrives
  at M2 training). `bazel test //projects/thermolife:test_suite` runs the J1–J6 gate.
- **S0 is built.** `fold/` (numpy, random init) + `sim/` (web control). Learned
  docking (M2, torch) and the drifting objective (M3) are design only.

## Domain-specific reminders (the invariants that make this *this*)

- **Groundedness is the soul (J1/J6).** The drawn contour is a pure function of
  `C = X·W_c`, and that same `C` is the attention **query**; the **key** is `C·M`. By
  Parseval the attention score `Q_i·K_j` **equals** the overlap of the two contours.
  A blob that morphs ⟺ its binding changed. **If the renderer reads anything the
  attention math doesn't, that's the bug.** No decorative shapes.
- **No spatial grid.** The embedding space *is* the space; tokens are free vectors, and
  a token's canvas position is a fixed 2D projection of its embedding. Do not
  reintroduce a physical grid, diffusion fields, or nutrient/energy physics — those
  were the old design (PLAN.md §9).
- **No per-token Python loop in the mechanism (J3).** `fold/transformer.py` and
  `fold/interface.py` are batched matmuls over all N tokens. Loops over the 4 harmonics
  or serialization loops in `engine.snapshot` are fine; a `for i in range(n_tokens)` in
  the fold math is not (there's a structural test).
- **Synchrony (J4).** `block_step` reads `X` and returns a fresh `X`; it mutates
  nothing. `X^{t+1}` is a pure function of `X^{t}`.
- **Determinism / replay (J2).** Same seed ⇒ byte-identical fold trajectory, including
  the fold-gallery reseeds (`FoldEngine._instantiate` is seeded deterministically).
- **Honest emergence.** No term rewards "nice docking"; at S0 the weights are random
  and the fold either docks or doesn't — report what happens. No eyeballed-pattern
  claims (failure mode F-Aesthetic). The objective that *earns* meaningful folding is
  M2 (trained) / M3 (viability under drift), not a hand-tuned pretty picture.

## Milestone discipline

- **S0 is the mechanism only** (PLAN.md §8): the fold + the grounded blob viewer, J1–J6
  green. No training, no learned interfaces, no objective.
- **Order is S0 → M1 (designed) → M2 (trained, torch) → M3 (objective-driven).** M2
  before M3: you need a trainable fold before an objective can shape it. Do not
  reorder; do not add torch before M2.

## Working inside this project

```bash
bazel test //projects/thermolife:test_suite               # the J1-J6 gate (§6)
bazel run  //projects/thermolife:serve -- --port 8787     # live blob viewer
./projects/thermolife/sim/host.sh                         # host it on the tailnet
```

## Repo context

One project in a polyglot bazel-only monorepo. Keep it **conceptually separate** from
its siblings `market` and `quorum` — do not import their vocabulary, objectives, or
mechanisms. No cross-project imports.
