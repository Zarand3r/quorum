# thermolife

> **A continuous thermodynamic neural cellular automaton.** Status: **design only, no implementation yet.** See [`PLAN.md`](PLAN.md) for the full system design.

A 2D grid world in which a **single shared local neural rule** gives every cell a fast hidden state and a slow *plastic* state, learned **ligand/receptor interfaces** that selectively bind and trade resources with energetic consequences, and a local **predictor** whose errors reshape the plastic state online — no inference/training boundary inside a lifetime. An explicit, conservation-checked abstract **physics** (nutrient/waste/heat fields, per-action energy cost, death → decomposition) makes organized behavior contingent on exploiting external gradients: you cannot get something for nothing.

It is a resource-constrained **neural cellular automaton (NCA)**: Growing-NCA machinery, but the fixed target image is replaced with *persistent viability in a changing world*. The objective is continuing **average-reward viability** — never a target shape, and **never a direct reward for "order"** (that would be trivially gamed; see invariant I10).

## The one question this platform is built to answer

> Do locally-learned, visually-interpretable binding interfaces plus online predictive plasticity produce **measurably better** long-horizon viability and recovery than **matched systems without them** — or are they decorative?

The strongest result is *not* "it made pretty blobs." It is beating the seven mandatory ablations (freeze plasticity, randomize interfaces, remove costs, remove prediction, freeze environment, delete cells, shuffle messages — [`PLAN.md`](PLAN.md) §18).

## What to read

- **[`PLAN.md`](PLAN.md)** — full system design: invariants **I1–I15**, risks **R1–R14**, architecture, per-tick pipeline, the explicit physics, the average-reward objective, the hand–receptor binding mechanism, vertical **Slice 0**, milestones **M1–M7**, and mandatory ablations. **Read this first.**
- **[`CLAUDE.md`](CLAUDE.md)** (here) — project-specific anchors for Claude Code sessions. The repo-root `CLAUDE.md` has the universal skill routing; this one has the thermolife-specific reminders.
- **[`configs/`](configs/)** — declarative design artifacts for the first experiment: `world.yaml`, `model.yaml`, `curriculum.yaml`.

## Current state

- `PLAN.md` — system design, complete, pre-implementation.
- `README.md` / `CLAUDE.md` — this file and the project anchors.
- `configs/*.yaml` — the first-experiment configuration (PLAN.md §12), as design.
- `env/ model/ train/ eval/ viz/ tests/` — package skeleton; each `__init__.py` is a docstring stub pointing at its PLAN.md section. **No logic yet.**

No source code, no passing tests. Implementation begins with **Slice 0** per `PLAN.md` §15.1.

## When implementation starts — Slice 0 only

Slice 0 (PLAN.md §15.1) builds the **physical substrate with zero learning**: nutrient/waste/heat diffusion, conservative nutrient→energy conversion, action costs, death + decomposition, and **one hand-coded forager**. Its job is to prove the physics has real stakes —

> the forager survives on a static nutrient gradient and **dies when the gradient is removed** —

while the always-on invariants hold: conservation (I1), non-negativity (I2), no free energy (I3), dead-cell inertness (I4), replay determinism (I8).

Do **not** start M1+ (learned interfaces, the NCA rule, plasticity, evolution, particles) until Slice 0 is green. Milestones then land in order M1 → M7 (PLAN.md §16).

## Build + test (once Slice 0 exists)

Built with Bazel `rules_python`, like every project in this repo. When Slice 0 code lands, a `thermolife_deps` pip hub is added to the root `MODULE.bazel` (reading `requirements_lock.txt` here) and a `py_test` target for the invariant gate. All bazel commands work from anywhere — bazel walks up to find `MODULE.bazel`.

```bash
bazel test //projects/thermolife/...              # build + run every target
bazel test //projects/thermolife:test_suite       # the PLAN.md I1-I15 invariant gate
bazel build //projects/thermolife:configs         # the declarative design configs
```

## Repo context

One project in a bazel-only monorepo. Its methodological sibling is [`projects/quorum/`](../quorum/) — same "emergence must be earned, not faked" discipline (quorum validates by *irreducibility*, thermolife by *thermodynamic honesty* + matched ablations). Cross-project boundaries stay clean; no cross-project imports.
