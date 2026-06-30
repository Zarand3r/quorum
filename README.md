# Monorepo root

A polyglot monorepo with **two build systems coexisting at the root**:

- **uv workspace** for Python (`pyproject.toml` + `uv.lock`).
- **Bazel workspace** for everything else, present and future (`MODULE.bazel` + `BUILD.bazel` + `.bazelversion` + `.bazelrc`).

They look for different files (uv → `pyproject.toml` in members; bazel → `BUILD.bazel` packages) so they do not collide. Each project under `projects/<name>/` picks whichever applies; projects are dependency-isolated.

## Active projects

| Project | Build system | Brief |
|---|---|---|
| [`projects/market/`](projects/market/) | Python (uv) | Real-time news-impact market state estimator. The LLM extracts evidence; a filter updates beliefs; predictions are logged before outcomes and joined to realized returns to grow a training dataset. **The LLM never decides trades.** Read [`projects/market/PLAN.md`](projects/market/PLAN.md) and [`projects/market/README.md`](projects/market/README.md). |
| [`projects/quorum/`](projects/quorum/) | Bazel | Placeholder package in the repo-wide bazel workspace. Empty `BUILD.bazel`; no targets yet. The first bazel-built work will land here. |

Add a new project by creating `projects/<name>/` with whichever toolchain it needs. Python projects (with a `pyproject.toml`) are picked up automatically by the uv workspace; bazel-built work just gets a `BUILD.bazel` and is reachable as `//projects/<name>/...`. New non-Python projects must also be added to the `[tool.uv.workspace].exclude` list in the root `pyproject.toml` so uv stops looking for a `pyproject.toml` there.

## Tooling

- **Python:** [uv](https://docs.astral.sh/uv/) workspaces. The root `pyproject.toml` declares `[tool.uv.workspace] members = ["projects/*"]`; every Python project under `projects/` gets its own `[project].dependencies` resolved into the shared root `uv.lock`. Python is pinned to 3.12 via `.python-version`.
- **Bazel:** one workspace for the whole repo, declared in `MODULE.bazel` (Bzlmod). `.bazelversion` pins the bazel version repo-wide. `.bazelrc` carries the shared build config; `.bazelrc.user` (gitignored) holds per-user overrides.
- **Skill library:** the [`eng-skills`](https://github.com/Zarand3r/claude-skills) plugin is auto-installed when Claude Code trusts this folder (see `.claude/settings.json`). It provides the `strategic-engineering-planner` → `implementation-plan` → `principal-production-engineer` planning + build flow, plus the autonomous `elves` overnight harness. See `CLAUDE.md` for the full routing table.

## Setup

```bash
# one-time on a fresh machine
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/Zarand3r/quorum.git
cd quorum
uv sync --all-extras                          # install every Python member + all dev extras
```

For bazel work, install bazel via [bazelisk](https://github.com/bazelbuild/bazelisk) (recommended — it reads `.bazelversion` and fetches the right bazel automatically).

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

### Bazel work (anywhere under `projects/`)

```bash
bazel build //...                       # build every bazel target in the repo
bazel test //...                        # run every bazel test
bazel build //projects/quorum/...       # just one package's targets
bazel mod graph                         # inspect the Bzlmod dep graph
```

All bazel commands work from anywhere in the repo — bazel walks up to find the root `MODULE.bazel`.

## Repo layout

```
.
├── CLAUDE.md                       # repo-wide skill routing + non-negotiables
├── README.md                       # this file
├── .claude/settings.json           # auto-installs the eng-skills plugin
├── .python-version                 # 3.12 (repo-wide)
├── .gitignore                      # repo-wide (includes bazel-* outputs)
│
├── pyproject.toml                  # uv workspace root (no runtime deps; excludes non-Python projects)
├── uv.lock                         # shared resolution for all Python members
│
├── MODULE.bazel                    # Bzlmod workspace declaration (module: quorum)
├── BUILD.bazel                     # root bazel package (empty)
├── .bazelversion                   # bazel version pin (repo-wide)
├── .bazelrc                        # bazel build/test config (repo-wide)
│
└── projects/
    ├── market/                     # Python: news-impact market state estimator (uv)
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
    │
    └── quorum/                     # Bazel: placeholder package (no targets yet)
        ├── BUILD.bazel             # empty package marker
        ├── CLAUDE.md
        └── README.md
```

## License

MIT.
