# quorum

A Bazel workspace. Currently one project; designed to host more.

## Active projects

| Project | Build system | Brief |
|---|---|---|
| [`projects/quorum/`](projects/quorum/) | Bazel | Single-pass LLM population simulator for emergent behavior. Goal: **computed** (irreducible) emergence, validated by Boids / Schelling baselines and an irreducibility test. See [`projects/quorum/PLAN.md`](projects/quorum/PLAN.md). Design only; no implementation yet. |

## Repos this one is related to

- **[`Zarand3r/sentiment`](https://github.com/Zarand3r/sentiment)** — extracted on 2026-06-29. Previously `projects/market/` here; now a standalone repo. Real-time news-impact market state estimator; the Python package is still called `market`.
- **[`Zarand3r/claude-skills`](https://github.com/Zarand3r/claude-skills)** — the `eng-skills` plugin auto-installed when Claude Code trusts this folder (see `.claude/settings.json`).

## Tooling

- **Bazel.** One repo-wide workspace at the root — `MODULE.bazel` (Bzlmod), `BUILD.bazel`, `.bazelversion`, `.bazelrc`. `bazel` commands work from anywhere in the tree. `.bazelrc.user` (gitignored) holds per-user overrides.
- **No uv / no Python at the repo root.** Following the extraction of `projects/market/` into [`Zarand3r/sentiment`](https://github.com/Zarand3r/sentiment) on 2026-06-29, the root `pyproject.toml` + `uv.lock` were removed. If a Python sub-project lands here later, declare a fresh `[tool.uv.workspace]` block at the root and add the member.
- **Skill library** auto-installed via `.claude/settings.json`. See `CLAUDE.md`.

## Setup

For bazel work, install bazel via [bazelisk](https://github.com/bazelbuild/bazelisk) (recommended — it reads `.bazelversion` and fetches the right bazel automatically).

```bash
git clone https://github.com/Zarand3r/quorum.git
cd quorum
bazel mod graph                         # inspect the Bzlmod dep graph (no targets yet)
```

## Working on a specific project

### `quorum` (Bazel)

```bash
bazel build //projects/quorum/...       # this package's targets (none yet)
bazel test  //...                       # every bazel test in the repo
bazel mod graph                         # Bzlmod dep graph
```

All bazel commands work from anywhere in the repo — bazel walks up to find `MODULE.bazel`.

## Repo layout

```
.
├── CLAUDE.md                       # repo-wide skill routing + non-negotiables
├── README.md                       # this file
├── .claude/settings.json           # auto-installs the eng-skills plugin
├── .python-version                 # leftover from the pre-extraction state; harmless
├── .gitignore                      # repo-wide (includes bazel-* outputs)
│
├── MODULE.bazel                    # Bzlmod workspace declaration (module: quorum)
├── BUILD.bazel                     # root bazel package (empty)
├── .bazelversion                   # bazel version pin (repo-wide)
├── .bazelrc                        # bazel build/test config (repo-wide)
│
└── projects/
    └── quorum/                     # Bazel: LLM population simulator (design only)
        ├── BUILD.bazel
        ├── CLAUDE.md
        ├── PLAN.md
        ├── README.md
        └── experiments/            # arrives via PR #4 (still open)
```

## License

MIT.
