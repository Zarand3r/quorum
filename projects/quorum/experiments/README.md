# quorum/experiments

> Pre-Slice-0 prototypes. Used to validate architectural claims in [`../PLAN.md`](../PLAN.md) before committing to the full Slice 0 build graph.

These are *toy models*. They are not Slice 0 and they are not on the path to v1. They exist to:

1. **Make architectural claims falsifiable cheaply.** PLAN.md says "one batched forward pass per tick" produces emergence. A 200-line toy with mock + real backends lets us hold that claim against a runnable artifact, not just against a design doc.
2. **Establish the geometric/spatial baseline** that quorum will have to beat (or honestly admit losing to) at PLAN.md §16 M6.
3. **Force us to internalize the engineering refinements** Sakana's Petri Dish NCA and Digital Ecosystems papers found necessary — *before* applying any of them to the LLM substrate.

## The two toys

| | v1 — LLM Schelling | v2 — PD-NCA |
|---|---|---|
| **Doc** | [`TOY_v1_SCHELLING.md`](TOY_v1_SCHELLING.md) | [`TOY_v2_PDNCA.md`](TOY_v2_PDNCA.md) |
| **Status** | Implementation (this PR) | Spec only — implementation deferred |
| **Local rule** | Frozen LLM forward pass on text | Trainable small conv-net per species |
| **What it tests** | Quorum's hot-path invariants (I1–I4, I8, I10) on a runnable artifact | The other side of the bet — what NCA-as-rule actually delivers |
| **Why it exists** | Smallest faithful demo of the quorum architecture | Baseline that quorum must beat on geometric/spatial tasks at PLAN.md M6 |

### Read order

1. [`TOY_v1_SCHELLING.md`](TOY_v1_SCHELLING.md) — the v1 spec; the implementation in `toy_v1/` realizes it.
2. [`TOY_v2_PDNCA.md`](TOY_v2_PDNCA.md) — the v2 spec; **the next implementation slot after v1 ships**.

## Tactical decisions about the build

- **Built with bazel `rules_python`.** Deps come from the `experiments_deps` pip hub (root `MODULE.bazel`), pinned in `requirements_lock.txt`. The substrate + tests need only `numpy` + `pytest`.
- **Torch is optional and not a bazel dependency.** The unit suite uses a `MockPolicy` (numpy only). The real `LLMPolicy` (torch + transformers) is imported lazily, and the smoke test `pytest.importorskip("torch")`s, so it skips cleanly when torch is absent — keeping `bazel test` fast (<1 s) and GPU-free. To run the real LLM path, provide torch in the environment or add it to the lock.

## Running

All bazel commands work from anywhere — bazel walks up to find `MODULE.bazel`.

```bash
# unit + integration tests (fast, no torch)
bazel test //projects/quorum/experiments:test_suite

# run the toy (default MockPolicy, no torch)
bazel run //projects/quorum/experiments:main -- --ticks 40 --seed 42
```

## How this relates to PLAN.md

| Toy demonstrates | PLAN.md section |
|---|---|
| One batched forward pass per tick (Tier 1 only) | §3, §10, I3 |
| Locality enforced at prompt-render time | §6, I1, I11 |
| Synchronous tick (state_t → state_{t+1}) | §6, I2 |
| Single-token action via logit projection | §6, I4, §12.4 |
| Replay determinism with seeded RNG | §6, I8, §17.3 |
| Schelling segregation as the emergence signal | §15.1 (Slice 0 uses Boids instead; same shape) |
| The Tier 0 / Tier 2 / hypernet / FM-judge layers | **deferred** — toys exercise the hot path only |
