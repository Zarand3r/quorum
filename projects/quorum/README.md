# projects/quorum

Placeholder package in the repo-wide bazel workspace. No targets yet — the empty `BUILD.bazel` exists so this directory is a valid bazel package, so the first bazel-built work has a sensible place to land.

The bazel workspace itself is declared at the repo root in [`/MODULE.bazel`](../../MODULE.bazel). One workspace, one cache, one version pin (`.bazelversion`) — see the [root README](../../README.md) for the rationale.

## Adding the first target

1. Decide what language. Bazel doesn't ship language rules in the core; bring them in via Bzlmod by uncommenting the relevant `bazel_dep(...)` line in `/MODULE.bazel` (e.g. `rules_go` for Go, `rules_rust` for Rust, `rules_oci` for container images).
2. Write a `BUILD.bazel` rule in this directory using the rules you imported.
3. Build it: `bazel build //projects/quorum:<target-name>`.

## Run from anywhere

Bazel finds the workspace by walking up to `MODULE.bazel`, so these all work:

```bash
bazel build //projects/quorum/...    # from the repo root
bazel test //projects/quorum/...     # from the repo root
cd projects/quorum && bazel build //...   # equivalent
```

## Context

This is one project in a polyglot monorepo. The sibling [`projects/market/`](../market/) is Python under `uv` and uses a different toolchain entirely; bazel doesn't see it (no BUILD files there). The two are dependency-isolated by construction.
