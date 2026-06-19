# Monorepo root

A polyglot monorepo. Each project lives in `projects/<name>/` with its own dependencies, lockfile (or build manifest), and `PLAN.md`. Projects are **fully independent** — no cross-project imports.

## Active projects

| Project | Language / build | Brief |
|---|---|---|
| [`projects/market/`](projects/market/) | Python (uv) | Real-time news-impact market state estimator. The LLM extracts evidence; a filter updates beliefs; predictions are logged before outcomes and joined to realized returns to grow a training dataset. **The LLM never decides trades.** Read [`projects/market/PLAN.md`](projects/market/PLAN.md) and [`projects/market/README.md`](projects/market/README.md). |
| [`projects/quorum/`](projects/quorum/) | Bazel | Empty bootstrap. Bzlmod (`MODULE.bazel`) workspace with `.bazelversion` and `.bazelrc` wired; no targets yet. Designed to grow into whatever needs the hermetic build / polyglot strengths bazel is good at. |

Add a new project by creating `projects/<name>/` with whatever toolchain it needs (`pyproject.toml` for Python via uv, `MODULE.bazel` for Bazel, `Cargo.toml` for Rust, `go.mod` for Go, `package.json` for TS, etc.). Python projects are picked up automatically by the uv workspace via the glob in the root `pyproject.toml`; bazel and other toolchains govern themselves within their own subdir.

## Tooling

- **Python:** [uv](https://docs.astral.sh/uv/) workspaces. The root `pyproject.toml` declares `[tool.uv.workspace] members = ["projects/*"]`; every Python project under `projects/` gets its own `[project].dependencies` resolved into the shared root `uv.lock`. Python is pinned to 3.12 via `.python-version`.
- **Non-Python projects:** each brings its own toolchain. uv only governs Python.
- **Skill library:** the [`eng-skills`](https://github.com/Zarand3r/claude-skills) plugin is auto-installed when Claude Code trusts this folder (see `.claude/settings.json`). It provides the `strategic-engineering-planner` → `implementation-plan` → `principal-production-engineer` planning + build flow, plus the autonomous `elves` overnight harness. See `CLAUDE.md` for the full routing table.

## Setup

```bash
# one-time on a fresh machine
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/Zarand3r/quorum.git
cd quorum
uv sync --all-extras                          # install every Python member + all dev extras
```

## Working on a specific project

### `market` (Python via uv)

From the repo root:

```bash
uv run --package market pytest projects/market -q   # run pytest in the market member
uv sync --package market --extra dev                # install only market + its dev deps
```

Or equivalently from within the project directory:

```bash
cd projects/market
uv run pytest -q
```

Both forms use the shared workspace lock at the root.

### `quorum` (Bazel)

```bash
cd projects/quorum
bazel build //...        # build everything (none yet)
bazel test //...         # test everything (none yet)
bazel mod graph          # inspect the Bzlmod dep graph
```

Bazel manages its own deps via `MODULE.bazel`. It does not interact with the uv workspace.

## Repo layout

```
.
├── CLAUDE.md                       # repo-wide skill routing + non-negotiables
├── README.md                       # this file
├── .claude/settings.json           # auto-installs the eng-skills plugin
├── .python-version                 # 3.12 (repo-wide)
├── .gitignore                      # repo-wide
├── pyproject.toml                  # uv workspace root (no runtime deps)
├── uv.lock                         # shared resolution for all Python members
└── projects/
    ├── market/                     # Python: news-impact market state estimator
    │   ├── CLAUDE.md               # project-specific anchors
    │   ├── README.md               # project quickstart
    │   ├── PLAN.md                 # design source of truth
    │   ├── USAGE.md                # how-to
    │   ├── pyproject.toml          # project's own deps (isolated)
    │   ├── market/                 # package
    │   ├── tests/
    │   └── docs/
    │       ├── constitution.md     # ungameable promises (elves Judge enforces)
    │       └── ELVES_SETUP.md      # overnight harness prerequisites
    └── quorum/                     # Bazel: empty bootstrap
        ├── MODULE.bazel            # Bzlmod workspace declaration
        ├── BUILD.bazel             # root build file (empty)
        ├── .bazelversion           # bazel version pin
        ├── .bazelrc                # build config
        ├── CLAUDE.md
        └── README.md
```

## License

MIT.
