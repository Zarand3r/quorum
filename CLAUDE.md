# Repository Instructions for Claude

This is a monorepo built entirely with **Bazel** (Bzlmod): one repo-wide workspace at the root (`MODULE.bazel` + `BUILD.bazel` + `.bazelversion` + `.bazelrc`). Every project under `projects/<name>/` has its own `BUILD.bazel` targets and is reachable as `//projects/<name>/...`. Python projects use `rules_python` with a **per-project `pip.parse` hub** (declared in `MODULE.bazel`) reading a pinned `requirements_lock.txt` committed next to the project — so projects stay dependency-isolated. Cross-project imports are not used.

## Active projects

| Project | Build system | Brief |
|---|---|---|
| [`projects/market/`](projects/market/) | Bazel (`rules_python`) | Real-time news-impact market state estimator. See `projects/market/PLAN.md`. |
| [`projects/quorum/`](projects/quorum/) | Bazel (`rules_python`) | Single-pass LLM population simulator for emergent behavior. Goal: **computed** (irreducible) emergence, validated by Boids / Schelling baselines and an irreducibility test. See `projects/quorum/PLAN.md`. Design only; toy v1 experiment under [`experiments/`](projects/quorum/experiments/). |
| [`projects/thermolife/`](projects/thermolife/) | Bazel (`rules_python`) | Continuous thermodynamic neural cellular automaton — resource-constrained NCA with learned binding interfaces + online plasticity on a 2D grid. Goal: **earned** adaptation (learned interfaces + predictive plasticity beat matched ablations on long-horizon viability), not "pretty blobs." See `projects/thermolife/PLAN.md`. Design only; no implementation yet. |

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

- **Bazel everywhere.** One repo-wide workspace at the root — `MODULE.bazel` (Bzlmod), `BUILD.bazel`, `.bazelversion`, `.bazelrc`. `bazel` commands work from anywhere in the tree (bazel walks up to find `MODULE.bazel`). Work lands under `projects/<name>/` with its own `BUILD.bazel`, reachable as `//projects/<name>/...`. External rules/libraries (`rules_python`, and later `rules_rust`/`rules_go`/`rules_oci`) are declared in the root `MODULE.bazel` via `bazel_dep(...)`, not in subdirs. Build/test the whole repo with `bazel test //...`.
- **Python:** `rules_python` with a hermetic 3.12 toolchain. Each Python project has its **own** `pip.parse` hub in `MODULE.bazel` reading a pinned `projects/<name>/requirements_lock.txt`; BUILD files reference deps via `requirement("<pkg>")`. Isolation is by construction — no shared lock. Tests run through a small `tests/pytest_main.py` `py_test` entry point that invokes pytest with the project's `pytest.ini`. To change deps: edit the lock (it is a standard pinned requirements file) and re-run `bazel test //...`.
- **Python version:** pinned via `.python-version` (`3.12`) and mirrored by the `rules_python` toolchain in `MODULE.bazel`.
- **`.bazelversion`** pins bazel repo-wide; bumping it is a deliberate, single-commit act.
