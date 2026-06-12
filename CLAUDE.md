# Repository Instructions for Claude

This project (a real-time market state estimator — see `PLAN.md`) is architecturally significant, performance-sensitive, concurrency-heavy, and safety-relevant (financial signals, closed-loop estimation). Apply the engineering skills below automatically; do not wait to be asked.

## Skill library + harness

Skills come from the **`eng-skills`** plugin in the [`claude-skills`](https://github.com/Zarand3r/claude-skills) marketplace. They are auto-installed when this folder is trusted (see `.claude/settings.json`), and Claude auto-invokes them by description. Read a skill's `SKILL.md` before acting on its domain.

The autonomous overnight harness is the **`elves`** skill. Repo prerequisites and launch checklist live in `docs/ELVES_SETUP.md`; the ungameable promises the Judge enforces live in `docs/constitution.md`.

## Skills — use these automatically

| Skill | Load it when… |
|---|---|
| **karpathy-guidelines** | Always, for any writing/reviewing/refactoring of code. Avoid overcomplication, make surgical changes, surface assumptions, define verifiable success criteria. |
| **principal-production-engineer** | Implementing, reviewing, refactoring, or hardening production code in any language. **Single entry point** — enforces simple design, dense data, explicit ownership, visible failure, minimal abstraction, honest verification, pipeline discipline. Routes to the rest. |
| **strategic-engineering-planner** | *Before* implementation when work is architecturally significant, ambiguous, multi-file, distributed, performance-sensitive, concurrency-heavy, or likely to need multiple passes (i.e. most non-trivial work in this repo). Produces a written roadmap first. Skip for trivial fixes and obvious CRUD. |
| **implementation-plan** | *After* the design is locked, *before* code. Turns a design doc into a checklist-first `IMPLEMENTATION_PLAN.md` with vertical-slice steps and binary acceptance gates. |
| **cpp-systems-internals** | Writing or reviewing C++ where hardware behavior, codegen cost, ownership vocabulary, API style, or kernel paging matters (lambdas, templates, cache lines, vtables, smart pointers/spans/arenas, `mmap`/`madvise`, AoS/SoA). Load only the relevant topic file. |
| **auto-research** | Iteratively optimizing a measurable outcome unattended/overnight — loss, latency (p50/p95/p99), throughput, MFU, memory/binary/model size, compile time. Enforces a fixed eval harness, append-only results log, keep-on-improvement / reset-on-regression. |
| **elves** | Executing a *development plan* unattended/overnight — user says "run overnight," "implement this plan," "keep going without me," "I'll be back in the morning." Breaks the plan into sprint-sized batches, implements with tests + PR-based review, and keeps durable memory (survival guide, learnings, execution log) for compaction recovery. Requires `git` + `gh`. |

**Default flow for non-trivial work in this repo:** `strategic-engineering-planner` (plan) → `implementation-plan` (checklist) → `principal-production-engineer` (implement, routing into `cpp-systems-internals` as needed), with `karpathy-guidelines` governing throughout.

**Unattended/overnight runs:** pick by goal — `auto-research` when success is *one number on a fixed harness*; `elves` when success is *a development plan with test/PR gates* (see `docs/ELVES_SETUP.md`).

## Non-negotiable engineering rules

- Prefer simple, direct code; flat, explicit control flow. No speculative abstractions.
- Shape hot code around data flow and dense memory; prefer arrays/spans/IDs over pointer graphs and dict-of-dict soup. In Python, that means `numpy`/`polars`/`pyarrow`/dataclasses-with-`__slots__` before generic containers on hot paths.
- Make ownership explicit at API boundaries. Prefer values/references/spans before owning pointers; unique ownership before shared.
- No hidden allocation, I/O, blocking, threads, throwing, or retries behind innocent-looking names. Especially relevant for the ingestion → extraction → estimator pipeline.
- Explicit expected failure: return-tuples / `Result`-style returns in Python, `(value, error)` in Go, `Result<T, E>` in Rust, `[[nodiscard]] bool noexcept` or `Result<T, E> noexcept` in C++. Exceptions are not control flow.
- Fail fast on invariant violations and semantic corruption. Degrade only through designed, bounded, observable fallback. Never silent fallback.
- Bounded queues, bounded retries, bounded caches. One slow consumer must not block unrelated work.
- Add or update tests with every behavior change; add benchmarks with every performance claim. State invariants as tests, assertions, or metrics.
- Report verification truthfully — including what was not run, and why.

## Required workflow for complex changes

Explore → Map data flow & ownership → State invariants → State failure model → Plan minimal change → Implement narrowly → Verify → Self-review → Simplify → Report.

## Review output shape

Verdict; blocker/major/minor findings; invariant gaps; ownership/lifetime issues; failure semantics; data/performance risks; complexity issues; minimal staged redesign; verification required before merge. Severity rubric and full review gate live in the `principal-production-engineer` skill's `reference/` and `checklists/` directories.

## Project-specific anchors

- **Plan** — `PLAN.md` is the source of truth for scope, invariants (I1–I10), risks (R1–R10), and milestones (Slice 0 → M1–M6). Read it before proposing changes that cross layers.
- **Constitution** — `docs/constitution.md` lists the ungameable promises the elves Judge enforces every batch.
- **Harness setup** — `docs/ELVES_SETUP.md` is the prerequisites checklist before launching an overnight run.
