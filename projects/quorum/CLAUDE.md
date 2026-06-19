# quorum — project-specific instructions

Empty Bazel workspace bootstrap. The repo-wide CLAUDE.md at the root has the skill routing and engineering rules; this file just records the project conventions for anyone (human or agent) working inside it.

## Conventions

- **Build system: Bazel (Bzlmod).** External deps come from `MODULE.bazel`. Do **not** introduce a parallel toolchain (pip, cargo, npm) at this level — bazel-native rules (`rules_python`, `rules_rust`, `rules_nodejs`, …) wrap those tools and keep builds hermetic.
- **Version pin: `.bazelversion`** is a hard pin. Bumping it is a deliberate act; document why in the commit.
- **`.bazelrc` is the project's build config.** Per-user overrides live in `.bazelrc.user` (gitignored). Do not commit per-machine flags to `.bazelrc`.
- **Targets are public-by-default-No.** Use explicit `visibility = ["//visibility:public"]` or package-scoped visibility groups. Don't leak implementation details.
- **Tests:** `bazel test //...` is the universal gate. Add `BUILD.bazel` test targets alongside the code, not in a separate tree.
- **No targets exist yet.** When you add the first one, also add it to the elves checklist (or whatever supersedes it) so the verification gate stays honest.

## Working here

```bash
cd projects/quorum
bazel build //...
bazel test //...
bazel mod graph                  # Bzlmod dep graph
bazel query 'deps(//...)'        # all transitive deps
```

## Repo context

This is one project in a polyglot monorepo; the sibling [`projects/market/`](../market/) is Python under `uv` and is fully independent. Don't import or build across project boundaries — keep this one self-contained.
