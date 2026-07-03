# thermolife — project-specific instructions

This project is a continuous thermodynamic neural cellular automaton — a resource-constrained NCA on a 2D grid with learned binding interfaces and online plasticity. It is architecturally significant, performance-sensitive (fully-vectorized grid physics + NCA rule in the hot path; TBPTT meta-training), and methodologically delicate (the difference between *earned* adaptation and "pretty blobs" is the entire point). The repo-root `CLAUDE.md` has the universal skill routing and engineering rules; this file adds the project-specific anchors.

## Project anchors

- **Plan** — [`PLAN.md`](PLAN.md) is the source of truth for scope, invariants (I1–I15), risks (R1–R14), architecture (§5), the per-tick pipeline (§10.1), the explicit physics (§10.3), the average-reward objective (§10.4), the binding mechanism (§9.3–9.4), Slice 0 (§15), and milestones M1–M7 (§16). Read it before proposing changes that cross layers.
- **Workspace** — Bazel `rules_python`, like every project in this repo. When Slice 0 code lands, add a `thermolife_deps` `pip.parse` hub in the root `MODULE.bazel` reading `projects/thermolife/requirements_lock.txt` (start with `numpy`/`pyyaml`; `torch`/`matplotlib` when M2 needs them) and a `py_test` for the invariant gate. No deps for milestones that don't exist yet.
- **No implementation yet.** The first batch's job is Slice 0 (§15.1) and its always-on invariant tests (§17.1) — **not** M1+ components. Slice 0 has zero learning on purpose: physics + a hand-coded forager only.

## Domain-specific reminders

- **env/ is the only mutator of physical channels.** `model/` emits *action intents* and *transfer requests*; `env/apply_conservative_transactions` debits energy first (I12) and enforces conservation (I1, I3). This one boundary is what makes conservation checkable in one place. If model code writes a field directly, that's the bug.
- **No per-cell Python loop in the hot path (I6).** Neighborhoods are shifted tensors / `unfold` / conv stencils, vectorized over the whole `[B,H,W,C]` world. A `for cell in cells:` in `tick()` is a violation; there's a structural test *and* a wall-clock gate.
- **Conservation is a ledger, not a re-sum (I1, R3).** Check the running `TransactionLedger` against the field totals; every source/sink is a named logged entry. Float/op-order drift accumulates over long horizons — fixed transaction order + the long-horizon drift test catch it.
- **Plasticity ≠ training (I9).** Within a rollout chunk, base weights `θ,φ` are frozen. Only `h` (every tick), interface expression (every `k` ticks), and `z` (slow, bounded) change. The outer optimizer steps **only** at *detached* TBPTT chunk boundaries. Applying `θ.grad` mid-chunk is a violation.
- **Thermodynamic honesty (I10) — the anti-gaming invariant.** The reward contains **no** direct "lower entropy / more order / more structure" term. Organization must *emerge* from viability soft-barriers + action/plasticity cost. Any term that scores order directly is constitutional and forbidden. This is thermolife's analogue of quorum's "computed, not retrieved."
- **Interface groundedness (I11).** The rendered ligand/receptor contour `R(φ)` is a pure function of the *same* code that drives the binding kernel `κ`. A hand that morphs on screen ⟺ its interaction kernel changed. The renderer must read nothing the kernel doesn't. No decorative hands.
- **Determinism / replay (I8).** Same seed + same `state_0` ⇒ byte-identical trajectory. Set `torch.use_deterministic_algorithms(True)`, pin CUDA, log RNG state — CUDA non-determinism (R14) silently breaks this.
- **The seven ablations (§18) are verification, not an afterthought.** A metric improvement that survives none of them is not a result. Any comparison claim needs a **matched-compute control** (M4's frozen-plasticity control, M3's lesion specificity, M5's unseen-schedule holdout).
- **No aesthetic claims.** "Interesting emergent pattern" judged by eye is failure mode F-Aesthetic. Report against the four metric families (§2.2) and the ablations, and report what was **not** run.

## Milestone discipline

- **Slice 0 only for the first batch of work.** Scope is capped at PLAN.md §15.1. No learned interfaces, no NCA rule, no plasticity, no prediction, no evolution, no particles until Slice 0 is green *and* the hand-coded forager demonstrably dies when the gradient is removed.
- **Grid before particles; plasticity before evolution.** Particles are M7, gated behind a working grid. Reproduction/selection is M6, gated behind working within-lifetime plasticity (M4). Do not reorder.

## Working inside this project (when code exists)

```bash
# All bazel commands work from anywhere — bazel walks up to find MODULE.bazel.
bazel test //projects/thermolife/...                       # build + run every target
bazel test //projects/thermolife:test_suite               # the PLAN.md I1-I15 gate (§17.1)
bazel test //projects/thermolife:test_suite --test_arg=-k --test_arg=conservation   # I1/I2/I3/I12
```

## Repo context

One project in a polyglot monorepo. Its methodological sibling is [`projects/quorum/`](../quorum/) — same discipline that emergence must be *earned*, not faked. Keep cross-project boundaries clean; no cross-project imports.
