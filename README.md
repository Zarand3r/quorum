# Monorepo root

A monorepo built entirely with **Bazel** (Bzlmod): one repo-wide workspace at the root — `MODULE.bazel` + `BUILD.bazel` + `.bazelversion` + `.bazelrc`. Every project under `projects/<name>/` has its own `BUILD.bazel` targets and is reachable as `//projects/<name>/...`. Projects are dependency-isolated; cross-project imports are not used.

Python projects use [`rules_python`](https://github.com/bazelbuild/rules_python) with a hermetic 3.12 toolchain and a **per-project `pip.parse` hub** (declared in `MODULE.bazel`) that reads a pinned `requirements_lock.txt` committed next to the project. Isolation is by construction — there is no shared lock.

## Active projects

| Project | Build system | Brief |
|---|---|---|
| [`projects/market/`](projects/market/) | Bazel (`rules_python`) | Real-time news-impact market state estimator. The LLM extracts evidence; a filter updates beliefs; predictions are logged before outcomes and joined to realized returns to grow a training dataset. **The LLM never decides trades.** Read [`projects/market/PLAN.md`](projects/market/PLAN.md) and [`projects/market/README.md`](projects/market/README.md). |
| [`projects/quorum/`](projects/quorum/) | Bazel (`rules_python`) | **Single-pass LLM population simulator for emergent behavior.** A Game-of-Life–style engine where the local rule is an LLM but the common-case update for the *entire population* is one batched forward pass; expensive generations are reserved for rare reflection. Goal is **computed** (irreducible) emergence — validated by Boids / Schelling baselines and an irreducibility test. Design only; a toy v1 (LLM Schelling) lives under [`experiments/`](projects/quorum/experiments/). Read [`projects/quorum/PLAN.md`](projects/quorum/PLAN.md). |
| [`projects/thermolife/`](projects/thermolife/) | Bazel (`rules_python`) | **Continuous thermodynamic neural cellular automaton** — a resource-constrained NCA with learned binding interfaces + online plasticity on a 2D grid. Goal is **earned** adaptation (learned interfaces + predictive plasticity beat matched ablations on long-horizon viability), not "pretty blobs." **Status: design only.** Read [`projects/thermolife/PLAN.md`](projects/thermolife/PLAN.md). |

Add a new Python project by creating `projects/<name>/` with a `BUILD.bazel`, a `requirements_lock.txt`, and a `pip.parse` hub in the root `MODULE.bazel`; it is then reachable as `//projects/<name>/...`. Non-Python work just gets a `BUILD.bazel` and the relevant `bazel_dep(...)` in `MODULE.bazel`.

## Tooling

- **Bazel:** one workspace for the whole repo, declared in `MODULE.bazel` (Bzlmod). `.bazelversion` pins the bazel version repo-wide. `.bazelrc` carries the shared build config; `.bazelrc.user` (gitignored) holds per-user overrides. Build/test everything with `bazel test //...`.
- **Python:** `rules_python` with a hermetic CPython 3.12 (mirrored from `.python-version`). Each project has its own `pip.parse` hub; BUILD files reference deps via `requirement("<pkg>")`. Tests run through a tiny `tests/pytest_main.py` `py_test` entry point that invokes pytest with the project's `pytest.ini`.
- **Skill library:** the [`eng-skills`](https://github.com/Zarand3r/claude-skills) plugin is auto-installed when Claude Code trusts this folder (see `.claude/settings.json`). It provides the `strategic-engineering-planner` → `implementation-plan` → `principal-production-engineer` planning + build flow, plus the autonomous `elves` overnight harness. See `CLAUDE.md` for the full routing table.

## Setup

```bash
# one-time on a fresh machine — install bazel via bazelisk (reads .bazelversion)
# see https://github.com/bazelbuild/bazelisk
git clone https://github.com/Zarand3r/quorum.git
cd quorum
bazel test //...                              # fetches the hermetic Python + pip deps, builds, runs all tests
```

Bazelisk is recommended — it reads `.bazelversion` and fetches the right bazel automatically. The first `bazel` invocation downloads the hermetic Python interpreter and the pinned pip wheels; subsequent runs are cached.

## Working on a specific project

All bazel commands work from anywhere in the repo — bazel walks up to find the root `MODULE.bazel`.

```bash
bazel test //...                        # build + test every target in the repo
bazel test //projects/market:test_suite # just the market test suite (52 tests)
bazel test //projects/quorum/experiments:test_suite   # the toy v1 Schelling suite
bazel build //projects/thermolife/...   # build one project's targets
bazel mod graph                         # inspect the Bzlmod dependency graph
```

To change a Python project's dependencies, edit its `requirements_lock.txt` (a standard pinned requirements file) and re-run `bazel test //...`.

## Repo layout

```
.
├── CLAUDE.md                       # repo-wide skill routing + non-negotiables
├── README.md                       # this file
├── .claude/settings.json           # auto-installs the eng-skills plugin
├── .python-version                 # 3.12 (mirrored by the rules_python toolchain)
├── .gitignore                      # repo-wide (includes bazel-* outputs)
│
├── MODULE.bazel                    # Bzlmod workspace: rules_python + per-project pip hubs
├── BUILD.bazel                     # root bazel package
├── .bazelversion                   # bazel version pin (repo-wide)
├── .bazelrc                        # bazel build/test config (repo-wide)
│
└── projects/
    ├── market/                     # news-impact market state estimator
    │   ├── BUILD.bazel             # py_library + py_test targets
    │   ├── requirements_lock.txt   # pinned deps (own pip hub: market_deps)
    │   ├── pytest.ini              # pytest config for the py_test entry point
    │   ├── CLAUDE.md · README.md · PLAN.md · USAGE.md
    │   ├── market/                 # package
    │   ├── tests/                  # tests + pytest_main.py entry point
    │   └── docs/                   # constitution.md · ELVES_SETUP.md
    │
    ├── quorum/                     # single-pass LLM population simulator (design)
    │   ├── BUILD.bazel             # placeholder package marker
    │   ├── CLAUDE.md · README.md · PLAN.md
    │   └── experiments/            # toy v1 (LLM Schelling): BUILD.bazel + requirements_lock.txt
    │
    └── thermolife/                 # thermodynamic neural cellular automaton (design)
        ├── BUILD.bazel             # configs filegroup + py_library skeleton
        ├── CLAUDE.md · README.md · PLAN.md
        └── configs/ env/ model/ train/ eval/ viz/ tests/
```

## License

MIT.
