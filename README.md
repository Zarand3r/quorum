# quorum

A Bazel workspace hosting multiple projects.

## Active projects

| Project | Build system | Brief |
|---|---|---|
| [`projects/quorum/`](projects/quorum/) | Bazel | Single-pass LLM population simulator for emergent behavior. Goal: **computed** (irreducible) emergence, validated by Boids / Schelling baselines and an irreducibility test. See [`projects/quorum/PLAN.md`](projects/quorum/PLAN.md). Design only; no implementation yet. |
| [`projects/thermolife/`](projects/thermolife/) | Bazel (`rules_python`) | **Embedding folding as ligand–receptor docking** — a toy transformer whose token embeddings fold through iterated attention (Hinton's "embeddings fold like proteins"), each rendered as a **grounded** 2D contour blob (the drawn shape *is* the attention query/key: `Q·K` = contour overlap by Parseval) that docks with complementary blobs. Goal is **earned** meaningful folding (trained + objective-driven), not "pretty blobs." **Status: S0 (numpy mechanism) implemented; training is M2.** Read [`projects/thermolife/PLAN.md`](projects/thermolife/PLAN.md). |

## Repos this one is related to

- **[`Zarand3r/sentiment`](https://github.com/Zarand3r/sentiment)** — extracted on 2026-06-29. Previously `projects/market/` here; now a standalone repo. Real-time news-impact market state estimator; the Python package is still called `market`.
- **[`Zarand3r/claude-skills`](https://github.com/Zarand3r/claude-skills)** — the `eng-skills` plugin auto-installed when Claude Code trusts this folder (see `.claude/settings.json`).

## Tooling

- **Bazel.** One repo-wide workspace at the root — `MODULE.bazel` (Bzlmod), `BUILD.bazel`, `.bazelversion`, `.bazelrc`. `bazel` commands work from anywhere in the tree. `.bazelrc.user` (gitignored) holds per-user overrides.
- **Python via `rules_python` (no uv at the root).** The root `pyproject.toml` + `uv.lock` were removed when `projects/market/` was extracted on 2026-06-29. Python projects build hermetically through Bazel: a CPython 3.12 toolchain (mirrors `.python-version`) and a **per-project `pip.parse` hub** in `MODULE.bazel` reading a pinned `requirements_lock.txt` next to the project — dependency sets stay isolated by construction.
- **Skill library** auto-installed via `.claude/settings.json`. See `CLAUDE.md`.

## Setup

For bazel work, install bazel via [bazelisk](https://github.com/bazelbuild/bazelisk) (recommended — it reads `.bazelversion` and fetches the right bazel automatically).

```bash
git clone https://github.com/Zarand3r/quorum.git
cd quorum
bazel test //...                        # fetches the hermetic Python + pip deps, builds, runs all tests
```

## Working on a specific project

```bash
bazel build //projects/quorum/...            # quorum package targets (none yet)
bazel test  //projects/thermolife:test_suite # the embedding-fold J1-J6 gate
bazel run   //projects/thermolife:serve -- --port 8787   # live fold viewer
bazel test  //...                            # every bazel test in the repo
```

To change a Python project's dependencies, edit its `requirements_lock.txt` (a standard pinned requirements file) and re-run `bazel test //...`.

All bazel commands work from anywhere in the repo — bazel walks up to find `MODULE.bazel`.

## Repo layout

```
.
├── CLAUDE.md                       # repo-wide skill routing + non-negotiables
├── README.md                       # this file
├── .claude/settings.json           # auto-installs the eng-skills plugin
├── .python-version                 # 3.12 (mirrored by the rules_python toolchain)
├── .gitignore                      # repo-wide (includes bazel-* outputs)
│
├── MODULE.bazel                    # Bzlmod workspace declaration (module: quorum)
├── BUILD.bazel                     # root bazel package (empty)
├── .bazelversion                   # bazel version pin (repo-wide)
├── .bazelrc                        # bazel build/test config (repo-wide)
│
└── projects/
    ├── quorum/                     # Bazel: LLM population simulator (design only)
    │   ├── BUILD.bazel
    │   ├── CLAUDE.md
    │   ├── PLAN.md
    │   ├── README.md
    │   └── experiments/            # arrives via PR #4 (still open)
    │
    └── thermolife/                 # embedding folding as ligand–receptor docking (S0 built)
        ├── BUILD.bazel             # fold library + serve binary + J1-J6 test suite
        ├── requirements_lock.txt   # pinned deps (own pip hub: thermolife_deps)
        ├── CLAUDE.md · README.md · PLAN.md
        └── fold/ sim/ configs/ tests/   # mechanism · web control · fold.yaml · gate
```

## License

MIT.
