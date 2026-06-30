# quorum

> **Single-pass LLM population simulator for emergent behavior.** Status: **design only, no implementation yet.** See [`PLAN.md`](PLAN.md) for the full system design.

A Game-of-Life–style emergence engine in which the local rule is an LLM, but the common-case update for the *entire population* is **one batched forward pass**. Expensive autoregressive generations are reserved for rare, decision-critical moments. The goal is **computed** (irreducible) emergence — macro-structure absent from the local rule and from the model's prior — not retrieved emergence.

The project sits at the **divergent / emergence** pole of LLM-driven social simulation, opposite the convergent / fidelity pole (Simile / Stanford Generative Agents) which validates by predictive accuracy on real individuals. Quorum validates by **irreducibility** (the macro outcome cannot be predicted by asking the LLM directly), **decorrelation** (rule-level heterogeneity prevents the herding that fakes emergence), and **beats-baseline** (zero-intelligence agents lose). See [`PLAN.md`](PLAN.md) §4.

## What to read

- **[`PLAN.md`](PLAN.md)** — full system design: invariants I1–I12, risks R1–R12, architecture, data structures, vertical Slice 0, milestones M1–M7, references. **Read this first.**
- **[`CLAUDE.md`](CLAUDE.md)** (here) — project-specific anchors for Claude Code sessions. The repo root `CLAUDE.md` has the universal skill routing; this one has the project-specific reminders.
- **[`/MODULE.bazel`](../../MODULE.bazel)** — the repo-wide bazel workspace (this project is one package within it).

## Why bazel

The system is a natural polyglot: pure-Python orchestrator + GPU inference (vLLM-class) + likely CUDA kernels for fast neighborhood extraction at large N + possibly C++ substrate cores. Slice 0 is pure Python, but anything past M6 (Sugarscape scaling, multi-GPU sharding, custom kernels) will want hermetic builds, repo-wide caching, and one version pin across languages. Bazel is here to absorb that growth without a tooling rewrite.

## Current state

- `BUILD.bazel` — empty package marker; no targets yet.
- `PLAN.md` — system design, complete, pre-implementation.
- `README.md` — this file.
- `CLAUDE.md` — project-specific anchors.

No source code, no tests, no scenarios. Implementation begins with Slice 0 per `PLAN.md` §15.1.

## When implementation starts

Slice 0 — Boids on a grid, single GPU, single batched forward pass per tick. Concrete configuration in `PLAN.md` §15.1. The first commit's job is to land the Bazel build graph: `rules_python` declared at the root `MODULE.bazel`, a `py_library` for the orchestrator, a `py_binary` for the runner, a `py_test` for the I3 / I10 / I11 / I8 invariant tests. Then the components in §12 land in dependency order — `Environment` first, then `PromptRenderer`, then `BatchedInferenceEngine`, then `ActionReadout`, then the tick loop.

Open questions to resolve before writing code: §22 of `PLAN.md`.
