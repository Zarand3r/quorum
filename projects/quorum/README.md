# quorum

Empty Bazel workspace bootstrap. No targets, no language rules wired yet — just the minimum scaffolding needed for `bazel` to recognize this as a workspace and for future build files to land in a sane place.

## Files

| File | Purpose |
|---|---|
| `MODULE.bazel` | Bzlmod module declaration. Add `bazel_dep(...)` lines as you bring in external rules (rules_python, rules_rust, rules_go, rules_oci, …). |
| `BUILD.bazel` | Root package marker; no targets yet. |
| `.bazelversion` | Pins the bazel version (currently `7.4.1`). Bumping it is a deliberate act, not drift. |
| `.bazelrc` | Build/test config: Bzlmod on, strict action env for cache hygiene, sensible test output, optional per-user overrides via `.bazelrc.user`. |

## Run

```bash
cd projects/quorum
bazel build //...     # builds every target (none yet)
bazel test //...      # runs every test (none yet)
bazel mod graph       # show the Bzlmod dep graph
```

## Adding a language

Bazel doesn't ship language rules in the core; you bring them in via Bzlmod. Examples to paste into `MODULE.bazel`:

```python
bazel_dep(name = "rules_python", version = "0.40.0")
bazel_dep(name = "rules_rust",   version = "0.55.0")
bazel_dep(name = "rules_go",     version = "0.51.0")
bazel_dep(name = "rules_oci",    version = "2.0.0")
```

Then write `BUILD.bazel` files in your source subdirectories that `load()` the rules and declare targets.

## Why bazel here

This project shares a repo with [`projects/market/`](../market/), which is Python under `uv` and lives in its own dependency-isolated world. They do not interact — uv governs the Python workspace, bazel governs this one. The repo is set up so each project picks the build system that fits.

See the [repo root README](../../README.md) for the full multi-project layout.
