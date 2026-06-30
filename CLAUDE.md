# Repository Instructions for Claude

This is a polyglot monorepo with two build systems coexisting at the root: a **uv workspace** for Python (`pyproject.toml` + `uv.lock`) and a **Bazel workspace** for everything else (`MODULE.bazel` + `BUILD.bazel` + `.bazelversion` + `.bazelrc`). Each project under `projects/<name>/` picks one; projects are dependency-isolated. Cross-project imports are not used.

## Active projects

| Project | Build system | Brief |
|---|---|---|
| [`projects/market/`](projects/market/) | Python (uv) | Real-time news-impact market state estimator. See `projects/market/PLAN.md`. |
| [`projects/quorum/`](projects/quorum/) | Bazel | Placeholder package in the repo-wide bazel workspace. Empty `BUILD.bazel`; no targets yet. |

When working on a specific project, also load its own `CLAUDE.md` (e.g. `projects/market/CLAUDE.md`) for project-specific framing, invariants, and document pointers. Claude Code merges all CLAUDE.md files on the path to cwd; the two are additive.

## Skill library + harness

Skills come from the **`eng-skills`** plugin in the [`claude-skills`](https://github.com/Zarand3r/claude-skills) marketplace, auto-installed when this folder is trusted (see `.claude/settings.json`). Claude auto-invokes them by description. Read a skill's `SKILL.md` before acting on its domain.

The autonomous overnight harness is the **`elves`** skill; per-project prerequisites live in each project's `docs/ELVES_SETUP.md`, and the ungameable promises the Judge enforces live in each project's `docs/constitution.md`.

## Skills — use these automatically

| Skill | Load it when… |
|---|---|
| **karpathy-guidelines** | Always, for any writing/reviewing/refactoring of code. Avoid overcomplication, make surgical changes, surface assumptions, define verifiable success criteria. |
| **principal-production-engineer** | Implementing, reviewing, refactoring, or hardening production code in any language. **Single entry point** — enforces simple design, dense data, explicit ownership, visible failure, minimal abstraction, honest verification, pipeline discipline. Routes to the rest. |
| **strategic-engineering-planner** | *Before* implementation when work is architecturally significant, ambiguous, multi-file, distributed, performance-sensitive, concurrency-heavy, or likely to need multiple passes (i.e. most non-trivial work in this repo). Produces a written roadmap first. Skip for trivial fixes and obvious CRUD. |
| **spec-driven-development** | *Before* coding on complex or ambiguous work, to prevent drift. Turns a goal into an executable spec — EARS requirements, binary acceptance criteria, scope/invariants, requirement→test traceability — that code and tests are derived from. Sits between the planner and implementation-plan. |
| **implementation-plan** | *After* the design is locked, *before* code. Turns a design doc into a checklist-first `IMPLEMENTATION_PLAN.md` with vertical-slice steps and binary acceptance gates. |
| **test-driven-verification** | Implementing or hardening any nontrivial change. Derive tests from acceptance criteria first, loop red→green→refactor, capture re-runnable evidence (unit/property tests, Playwright/tmux artifacts), and gate merges on binary criteria. |
| **cpp-systems-internals** | Writing or reviewing C++ where hardware behavior, codegen cost, ownership vocabulary, API style, or kernel paging matters (lambdas, templates, cache lines, vtables, smart pointers/spans/arenas, `mmap`/`madvise`, AoS/SoA). Load only the relevant topic file. |
| **data-oriented-design** | Hot-path / real-time / low-latency / SIMD / parser / allocator / codec / HPC work. Cache-line layouts, SoA, indices-over-pointers, branchless control flow, SWAR, radix sort, arenas, measure-first protocol. |
| **python-style** | Writing or reviewing Python where style/design matters — flattening logical branches (guard clauses, dispatch/`match` over `if`/`elif`), enums/`StrEnum` over magic strings, fail-fast validation (narrow `except`, no silent fallbacks), no optional imports (`try`/`except ImportError`) or redundancy, choosing abstractions (ABC vs `Protocol`, composition over inheritance). Load only the relevant topic file. |
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

- **Python:** [uv](https://docs.astral.sh/uv/) with one shared `uv.lock` at the root (see root `pyproject.toml`). Each Python project under `projects/<name>/` has its own `[project] dependencies` and is fully isolated. Default: `uv sync --all-extras` from root. Non-Python projects must be listed in `[tool.uv.workspace].exclude` so uv stops looking for a `pyproject.toml` there.
- **Bazel:** one repo-wide workspace at the root — `MODULE.bazel` (Bzlmod), `BUILD.bazel`, `.bazelversion`, `.bazelrc`. `bazel` commands work from anywhere in the tree (bazel walks up to find `MODULE.bazel`). New bazel-built work lands under `projects/<name>/` with its own `BUILD.bazel` and is reachable as `//projects/<name>/...`. External rules / libraries (`rules_python`, `rules_rust`, `rules_go`, `rules_oci`, …) are declared in the root `MODULE.bazel` via `bazel_dep(...)`, not in subdirs.
- **Python version:** pinned at the repo root via `.python-version` (currently `3.12`); uv fetches it if missing.
- **`.bazelversion`** pins bazel repo-wide; bumping it is a deliberate, single-commit act.
