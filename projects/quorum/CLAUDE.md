# projects/quorum — project-specific instructions

Placeholder bazel package. The bazel workspace itself is the entire repo; see [`/MODULE.bazel`](../../MODULE.bazel) at the root. This file records the conventions for anyone (human or agent) building bazel-managed work into this directory.

## Conventions

- **Build system: bazel via Bzlmod.** External deps are declared at `/MODULE.bazel` (not here). When you need a language ruleset (`rules_python`, `rules_rust`, `rules_nodejs`, …), uncomment the appropriate `bazel_dep(...)` line at the root.
- **Do not introduce a parallel toolchain** (pip, cargo, npm, etc.) inside this directory. If you need third-party packages, route them through the relevant bazel-native rules so builds stay hermetic and cache-friendly.
- **`.bazelversion` is at the repo root and is a hard pin.** Bumping it is a deliberate act; do it in a single commit with a one-line justification.
- **Targets are public-by-default-No.** Use explicit `visibility = ["//visibility:public"]` or package-scoped visibility groups. Don't leak implementation details.
- **Tests:** `bazel test //projects/quorum/...` is the local gate; `bazel test //...` from the repo root is the global gate.
- **No targets exist yet.** When you add the first one, also add it to the elves checklist (or whatever supersedes it) so the verification gate stays honest.

## Working here

```bash
# Build everything bazel knows about, from anywhere in the repo:
bazel build //...

# Just this package, from anywhere in the repo:
bazel build //projects/quorum/...

# From inside this directory:
cd projects/quorum
bazel test //...
bazel mod graph                  # Bzlmod dep graph (resolves to the repo-root workspace)
bazel query 'deps(//projects/quorum/...)'
```

## Repo context

This is a polyglot monorepo with **one** bazel workspace at the root. The sibling [`projects/market/`](../market/) is Python under `uv` and is independent — bazel doesn't see it (no BUILD files there). Keep cross-project boundaries clean: don't add bazel rules that reach into `projects/market/`, and don't import from `projects/quorum/` into the Python project.
