# quorum — project-specific instructions

This project is a single-pass LLM population simulator for emergent behavior — see [`PLAN.md`](PLAN.md). It is architecturally significant, performance-sensitive (batched GPU inference in the hot path), and methodologically delicate (the difference between *computed* and *retrieved* emergence is the whole point of the system, and easy to fake by accident). The repo-wide CLAUDE.md at the workspace root has the universal skill routing and engineering rules; this file adds the project-specific anchors.

## Project anchors

- **Plan** — [`PLAN.md`](PLAN.md) is the source of truth for scope, invariants (I1–I12), risks (R1–R12), architecture, components (§12), Slice 0 (§15.1), and milestones (M1–M7). Read it before proposing changes that cross layers.
- **Workspace** — bazel at the repo root ([`/MODULE.bazel`](../../MODULE.bazel)). The project is one package; build the orchestrator + runner + tests as bazel targets.
- **No implementation yet.** The first commit's job is to stand up the Slice 0 build graph and the invariant tests (PLAN.md §17.1) — *not* to start on M1+ components. Slice 0 disables Tier 0 / Tier 2 / hypernet / FM-judge on purpose.

## Domain-specific reminders

- **One batched forward pass per tick.** Anywhere you find yourself writing a per-agent generation loop in the hot path, you are violating I3. Read logits at the action position; never call `generate()` in Tier 1 (I4). Verify with the I3 gate counter.
- **Locality (I1, I11) is non-negotiable.** An agent's prompt contains only its neighborhood. No global view in the common case. Tier 2 may peek; nothing else may.
- **Synchrony (I2).** Actions are computed from `state_t` and applied atomically to form `state_{t+1}`. `Environment.step` reads no state mutated during the LLM call.
- **Fixed-size memory (I7).** If per-agent memory grows tick-over-tick, the single-pass economics collapse. Fix the memory update, don't widen the prompt.
- **Replay determinism (I8).** Same seeds + same `state_0` ⇒ byte-identical trajectory. CUDA non-determinism (R12) will silently make this fail — set `torch.use_deterministic_algorithms(True)`, pin CUDA, log RNG state.
- **Shared prefix (I10).** Every per-tick prompt begins with the same byte-equal prefix. Per-agent context lives in the suffix. KV-cache prefix reuse depends on this; drifting prefixes destroy throughput (R7).
- **No silent fallback (I12).** Reflection errors, cache misses interpreted as decisions, surprise misfires, and budget over-runs are logged with typed error codes — never substituted with neutral defaults.
- **Emergence is *computed*, not *retrieved*.** (I6.) Every claim of emergence is paired with the irreducibility test (PLAN.md §17.2): can the macro outcome be predicted by asking the LLM directly, without running the sim? If yes → retrieval, not emergence. A run that hasn't passed the irreducibility test hasn't produced emergence.
- **Slice 0 only for the first batch of work.** Scope is capped at PLAN.md §15.1. No Tier 0, no Tier 2, no hypernetwork, no FM-judge, no semantic targets until Slice 0 is green.

## Distinguishing this from convergent / fidelity systems

This project is **not** a behavior foundation model and **not** a chat simulator. We do not validate against real humans. Anything that drifts toward "make this agent talk more like a person" is going in the wrong direction; the divergent / emergence pole optimizes for *discovery* of irreducible structure, not for fidelity to any individual. The contrast with Simile / Stanford Generative Agents is laid out in PLAN.md §4 and §22 — keep the lens.

## Working inside this project (when code exists)

```bash
# From anywhere in the repo:
bazel build //projects/quorum/...
bazel test  //projects/quorum/...

# Just the invariant tests (the hard gate; PLAN.md §17.1):
bazel test //projects/quorum/tests:invariants

# Run a Slice 0 scenario:
bazel run //projects/quorum/runner:slice0 -- --scenario boids --ticks 100 --seed 42
```

All commands work from anywhere — bazel walks up to find `MODULE.bazel`. For Python deps the project pulls them in via `rules_python` declared at the root `MODULE.bazel`, not via uv. (uv only governs `projects/market/`; quorum is bazel-only.)

## Repo context

This is one project in a polyglot monorepo. The sibling [`projects/market/`](../market/) is Python under uv and is independent — keep cross-project boundaries clean.
