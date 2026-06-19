# Repository Instructions for Claude

This is a polyglot monorepo. Each project lives in `projects/<name>/` with its own dependencies, lockfile (or build manifest), and `PLAN.md`. Cross-project imports are not used; projects are fully independent.

## Active projects

| Project | Language | Brief |
|---|---|---|
| [`projects/quorum/`](projects/quorum/) | Python | Real-time news-impact market state estimator. See `projects/quorum/PLAN.md`. |

When working on a specific project, also load its own `CLAUDE.md` (e.g. `projects/quorum/CLAUDE.md`) for project-specific framing, invariants, and document pointers. Claude Code merges all CLAUDE.md files on the path to cwd; the two are additive.

## Skill library + harness

Skills come from the **`eng-skills`** plugin in the [`claude-skills`](https://github.com/Zarand3r/claude-skills) marketplace, auto-installed when this folder is trusted (see `.claude/settings.json`). Claude auto-invokes them by description. Read a skill's `SKILL.md` before acting on its domain.

The autonomous overnight harness is the **`elves`** skill; per-project prerequisites live in each project's `docs/ELVES_SETUP.md`, and the ungameable promises the Judge enforces live in each project's `docs/constitution.md`.

## Skills — use these automatically

| Skill | Load it when… |
|---|---|
| **karpathy-guidelines** | Always, for any writing/reviewing/refactoring of code. Avoid overcomplication, make surgical changes, surface assumptions, define verifiable success criteria. |
| **principal-production-engineer** | Implementing, reviewing, refactoring, or hardening production code in any language. **Single entry point** — enforces simple design, dense data, explicit ownership, visible failure, minimal abstraction, honest verification, pipeline discipline. Routes to the rest. |
| **strategic-engineering-planner** | *Before* implementation when work is architecturally significant, ambiguous, multi-file, distributed, performance-sensitive, concurrency-heavy, or likely to need multiple passes (i.e. most non-trivial work in this repo). Produces a written roadmap first. Skip for trivial fixes and obvious CRUD. |
| **implementation-plan** | *After* the design is locked, *before* code. Turns a design doc into a checklist-first `IMPLEMENTATION_PLAN.md` with vertical-slice steps and binary acceptance gates. |
| **cpp-systems-internals** | Writing or reviewing C++ where hardware behavior, codegen cost, ownership vocabulary, API style, or kernel paging matters (lambdas, templates, cache lines, vtables, smart pointers/spans/arenas, `mmap`/`madvise`, AoS/SoA). Load only the relevant topic file. |
| **data-oriented-design** | Hot-path / real-time / low-latency / SIMD / parser / allocator / codec / HPC work. Cache-line layouts, SoA, indices-over-pointers, branchless control flow, SWAR, radix sort, arenas, measure-first protocol. |
| **auto-research** | Iteratively optimizing a measurable outcome unattended/overnight — loss, latency (p50/p95/p99), throughput, MFU, memory/binary/model size, compile time. Enforces a fixed eval harness, append-only results log, keep-on-improvement / reset-on-regression. |
| **elves** | Executing a *development plan* unattended/overnight — user says "run overnight," "implement this plan," "keep going without me," "I'll be back in the morning." Breaks the plan into sprint-sized batches, implements with tests + PR-based review, and keeps durable memory (survival guide, learnings, execution log) for compaction recovery. Requires `git` + `gh`. |

**Default flow for non-trivial work:** `strategic-engineering-planner` (plan) → `implementation-plan` (checklist) → `principal-production-engineer` (implement, routing into `cpp-systems-internals` and/or `data-oriented-design` as needed), with `karpathy-guidelines` governing throughout.

**Unattended/overnight runs:** pick by goal — `auto-research` when success is *one number on a fixed harness*; `elves` when success is *a development plan with test/PR gates*.

## Non-negotiable engineering rules

- Prefer simple, direct code; flat, explicit control flow. No speculative abstractions.
- Shape hot code around data flow and dense memory; prefer arrays/spans/IDs over pointer graphs and dict-of-dict soup. In Python, that means `numpy`/`polars`/`pyarrow`/dataclasses-with-`__slots__` before generic containers on hot paths.
- Make ownership explicit at API boundaries. Prefer values/references/spans before owning pointers; unique ownership before shared.
- No hidden allocation, I/O, blocking, threads, throwing, or retries behind innocent-looking names.
- Explicit expected failure: return-tuples / `Result`-style returns in Python, `(value, error)` in Go, `Result<T, E>` in Rust, `[[nodiscard]] bool noexcept` or `Result<T, E> noexcept` in C++. Exceptions are not control flow.
- Fail fast on invariant violations and semantic corruption. Degrade only through designed, bounded, observable fallback. Never silent fallback.
- Bounded queues, bounded retries, bounded caches. One slow consumer must not block unrelated work.
- Add or update tests with every behavior change; add benchmarks with every performance claim. State invariants as tests, assertions, or metrics.
- Report verification truthfully — including what was not run, and why.

## Required workflow for complex changes

Explore → Map data flow & ownership → State invariants → State failure model → Plan minimal change → Implement narrowly → Verify → Self-review → Simplify → Report.

## Review output shape

Verdict; blocker/major/minor findings; invariant gaps; ownership/lifetime issues; failure semantics; data/performance risks; complexity issues; minimal staged redesign; verification required before merge. Severity rubric and full review gate live in the `principal-production-engineer` skill's `reference/` and `checklists/` directories.

## Workspace tooling

- **Python:** [uv](https://docs.astral.sh/uv/) with one shared `uv.lock` at the root (see root `pyproject.toml`). Each Python project under `projects/<name>/` has its own `[project] dependencies` and is fully isolated. Default: `uv sync --all-extras` from root.
- **Non-Python projects:** each brings its own toolchain (`Cargo.toml` / `go.mod` / `package.json` / `BUILD.bazel`). uv only governs the Python ones.
- **Python version:** pinned at the repo root via `.python-version` (currently `3.12`); uv fetches it if missing.
