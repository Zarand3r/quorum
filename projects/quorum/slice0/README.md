# slice0

> Slice 0 of the quorum architecture. Design: [`../PLAN.md`](../PLAN.md) §15.1.

**LLM Boids on a 32×32 toroidal grid, N=64, one batched forward pass per tick, Qwen 2.5 1.5B-Instruct via vLLM.** Deliberately no Tier 0 memoization, no Tier 2 reflection, no hypernetwork, no FM-as-judge. This is the *smallest end-to-end* configuration that produces a real signal.

## Success criterion (from PLAN.md §15.1)

Mean nearest-neighbor distance (MNND) under the LLM population is **monotonically lower than under a uniform-random action baseline by a statistically significant margin (Mann-Whitney U, p < 0.01 over ≥ 10 seeds)**. The `verify` target automates this and is the merge gate for this slice.

## Decisions resolved from PLAN.md §22

| Question | Resolution | Where documented |
|---|---|---|
| Q1 base model | Qwen 2.5 1.5B-Instruct (fp16 → ~3 GB VRAM) | LLMPolicy commit |
| Q2 inference engine | vLLM with prefix cache | LLMPolicy commit |
| Q3 substrate library | Custom numpy, toroidal grid | substrate.py |
| Q4 action vocab | 5 single-letter tokens `{N, S, E, W, Z}`, `Z`=stay | actions.py |
| Q5 hardware | Local — RTX PRO 6000 (97 GB VRAM) | This box |
| Q7 determinism vs throughput | Strict determinism; measure the throughput cost | verify.py |

Deferred to M1+: Q6 memoization abstraction, Q8 FM-judge, Q11 reflection policy, Q12 surrogate distillation.

## Layout

```
slice0/
├── BUILD.bazel
├── pyproject.toml
├── requirements_lock.txt
├── pytest.ini
├── README.md
├── slice0/
│   ├── __init__.py
│   ├── substrate.py      # toroidal grid + synchronous step (I2)
│   ├── actions.py        # {N, S, E, W, Z}
│   ├── prompts.py        # locality (I1, I11) + shared prefix (I10)
│   ├── metrics.py        # MNND + decorrelation
│   ├── policy.py         # Policy protocol + UniformRandomPolicy baseline
│   ├── _llm_policy.py    # LLMPolicy via vLLM (deferred until [llm] extra ships)
│   ├── runner.py         # tick loop; I3 gate
│   ├── verify.py         # Mann-Whitney U + replay diff (merge gate)
│   └── main.py           # CLI
└── tests/
    ├── unit/
    └── integration/
```

## Run

```bash
# baseline sim (no LLM)
bazel run //projects/quorum/slice0:main -- --policy uniform_random --ticks 100 --seed 42

# LLM sim (requires the [llm] extra lock)
bazel run //projects/quorum/slice0:main -- --policy llm --model "Qwen/Qwen2.5-1.5B-Instruct" --ticks 100 --seed 42

# success-criterion harness (the merge gate)
bazel run //projects/quorum/slice0:verify

# tests
bazel test //projects/quorum/slice0:test_suite
```
