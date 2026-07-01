# Toy v1 — LLM Schelling

> The smallest faithful runnable demo of quorum's hot path. Implementation lives in [`toy_v1/`](toy_v1/) alongside this spec.

## What it is

A 2D grid populated with RED / BLUE agents. Each tick:

1. Every agent observes only its 8-neighbor color breakdown (own / other / empty counts).
2. The entire population advances in **one batched LLM forward pass**, with each agent rendered as its own sequence in the batch.
3. The action — `STAY` or `MOVE` — is read out as a single token via logit projection (no autoregressive decode).
4. Movers are placed at a random empty cell synchronously, after all actions have been computed.

Emergence signal: the **mean fraction of same-color neighbors among each agent's non-empty neighbors** — the canonical Schelling segregation metric — rises from ~0.5 (random) toward ~0.7+ (clustered).

## Why Schelling (not Boids or GoL)

- Smallest substrate that produces *social* emergence. Quorum's lens (PLAN.md §4) is divergent / emergence with a social flavor; Schelling matches.
- Cheaper than Boids on a discrete grid: STAY / MOVE is a clean 2-action vocab.
- The macro signal is a single scalar that's monotonic-in-emergence, which makes the success criterion trivial to assert.
- Caveat: Schelling is in the LLM's prior, so we **cannot** make irreducibility claims on this toy (see PLAN.md §17.2, I6). It validates *mechanics*, not emergence quality.

## Invariants the toy implements + verifies

Each invariant has a test that fails if it is violated.

| ID | Invariant | Where verified |
|---|---|---|
| **I1** | Locality — agent prompt contains only the agent's neighborhood counts | `test_prompts.py::test_prompt_contains_only_local_state` |
| **I2** | Synchronous tick — actions computed from `state_t`, applied to form `state_{t+1}` | `test_grid.py::test_step_is_synchronous_no_in_flight_state` |
| **I3** | Single-pass — `policy.step` triggers exactly one model forward call per tick | `test_policy.py::test_one_forward_call_per_step` (via `MockPolicy` instrumented counter) |
| **I4** | Latent reasoning — no autoregressive decode; action is a logit projection | `test_policy.py::test_no_generate_called` (mock + LLM both) |
| **I8** | Replay determinism — fixed seed → byte-identical trajectory | `test_replay_determinism.py::test_two_runs_identical` |
| **I10** | Shared prefix — system prompt prefix is byte-identical across batch members | `test_prompts.py::test_shared_prefix_across_batch` |
| **I11** | No global-view leakage — no agent prompt contains state outside its neighborhood | `test_prompts.py::test_prompt_does_not_contain_other_agents` |

## Deliberate omissions (these arrive at PLAN.md M1+)

- Tier 0 memoization
- Tier 2 reflection (no `.generate()` call anywhere in the toy)
- Hypernetwork-generated personas
- FM-as-judge / irreducibility test
- Adversarial coevolution (Digital Red Queen style)
- Persona heterogeneity beyond per-agent random seed

The toy has **one shared system prompt for the entire population**. R2 (diversity inversion / herding) is therefore *expected* to manifest; the toy is the first place we get to feel it.

## Architectural commitments

```
substrate (numpy)        prompt rendering         single batched
   |                          |                    forward pass
   |   neighbor counts        |                    (LLM or Mock)
   v                          v                    |
[ N agents ] -- locality --> [ N prompts ] -----> [ N action ]
                                                   logits
                                                   |
                                                   v
                                              ┌─────────────┐
                              I3 gate ────►  │ fwd_passes  │
                                              │ == 1        │
                                              └─────────────┘
                                                   |
                                                   v
                                              [ N actions ]
                                                   |
synchronous step (numpy)                          |
   ^                                              |
   |                                              |
state_{t+1} ◄── apply moves to state_t snapshot ◄─┘
```

The substrate, prompt rendering, and metrics are pure numpy / Python (no torch). Only the `LLMPolicy` imports torch + transformers; tests run against `MockPolicy`.

## Configuration (defaults)

| Knob | Value | Reason |
|---|---|---|
| Grid | 8 × 8 | Smallest substrate where Schelling signal is visible in < 100 ticks |
| Population | 30 agents | ~47% occupancy; enough empty cells for movement |
| Color split | 50 / 50 RED / BLUE | Symmetric baseline |
| Action vocab | `S`, `M` (single-letter tokens) | Guaranteed one-token-per-action across all BPE tokenizers |
| Default LLM | `HuggingFaceTB/SmolLM2-135M-Instruct` | CPU-runnable, instruct-tuned, ~135M params |
| Ticks | 40 | Long enough for segregation to lift off baseline; short enough to run in seconds |
| Seed | 42 | Documented in tests for replay diff |

## Success criteria

For v1 to be considered "working" the following all hold on a clean run with the defaults above:

1. `uv run pytest -q` is green (every invariant + every unit + integration test passes).
2. `uv run python -m toy_v1.main` runs for 40 ticks without exception.
3. The per-tick `fwd_passes=1` line is printed every tick (I3 runtime gate).
4. The same seed yields a byte-identical trajectory across two runs (I8 runtime gate).
5. With a real LLM (SmolLM2-135M-Instruct), the final same-color fraction is strictly greater than the initial fraction on at least 7 of 10 seeded runs. (Failure here is fine — it means R2 / R6 is dominating; the *mechanics* still pass.)

## Limitations (acknowledged on purpose)

- **Not Slice 0.** Slice 0 is Boids on 32×32 with N=64, vLLM, bazel-built. This is the toy that precedes that.
- **No emergence quality claim.** Schelling is retrievable from the LLM prior.
- **No torch in the unit tests.** Means `LLMPolicy` is exercised only via smoke runs, not CI.
- **One shared persona.** Decorrelation (PLAN.md I5 / R2) is not addressed; that's deferred to a follow-up toy or directly to Slice 0 M3.
