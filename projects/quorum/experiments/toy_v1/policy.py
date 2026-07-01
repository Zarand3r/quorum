"""Policy contract + backends.

The hot-path commitment from PLAN.md §6 / I3 / I4:

- **I3 Single-pass**: each call to `policy.step(prompts)` triggers exactly
  ONE underlying forward pass — never N. Whether N agents become N rows in
  a batched tensor (LLMPolicy) or N entries in a flat draw (MockPolicy), the
  contract holds: one call to `step` = one forward call.
- **I4 Latent reasoning**: action is read out via logit projection on the
  action-vocab token IDs, never via autoregressive `.generate()`.

This module exposes:

- ``Policy``       — protocol the runner depends on.
- ``MockPolicy``   — deterministic test backend, no torch dependency.
- ``LLMPolicy``    — real backend wrapping a HF causal LM. Imported lazily,
                     only when torch is installed. The unit tests do NOT
                     load it; smoke tests do.

The cleanest way to gate `.generate()` away is to make the type system do
the work: ``Policy.step`` returns ``list[str]`` derived from logits, and
neither backend has any code path that calls `.generate()`. The mock keeps
a counter for paranoia (test_policy.py).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from toy_v1.actions import LABELS


@runtime_checkable
class Policy(Protocol):
    """Population policy interface.

    A policy turns a batch of agent prompts into a batch of action labels
    via ONE underlying forward pass per call. The runner calls ``step`` once
    per tick.
    """

    def step(self, prompts: list[str], rng: np.random.Generator) -> list[str]:
        """Return one action label per prompt. Must call the underlying
        model exactly once (I3) and must NOT autoregressively decode (I4)."""
        ...


# ---------- MockPolicy ----------


class MockPolicy:
    """Deterministic policy backend used by unit + integration tests.

    No torch dependency. Samples each action from ``{"S", "M"}`` with a
    Bernoulli probability of ``p_stay`` for "S". The sampling uses the
    caller-supplied RNG so the runner stays replay-deterministic (I8).

    Two instrumented counters expose what the policy actually did, so the
    I3 and I4 invariants can be verified in tests:

    - ``forward_call_count`` increments on every ``step()`` call.
    - ``generate_call_count`` stays 0 by construction — there is no decode
      path in this class. It's checked in tests as a paranoid gate.
    """

    __slots__ = ("seed", "p_stay", "forward_call_count", "generate_call_count")

    def __init__(self, seed: int, p_stay: float = 0.5) -> None:
        if not (0.0 <= p_stay <= 1.0):
            raise ValueError(f"p_stay must be in [0, 1], got {p_stay}")
        self.seed = seed
        self.p_stay = float(p_stay)
        self.forward_call_count = 0
        self.generate_call_count = 0

    def step(self, prompts: list[str], rng: np.random.Generator) -> list[str]:
        # I3 gate: one call to step → one "forward" (here a vectorized draw).
        self.forward_call_count += 1
        # Vectorized Bernoulli draw — N actions in a single rng.random call,
        # mirroring how LLMPolicy gets N actions out of one model forward.
        draws = rng.random(size=len(prompts))
        return ["S" if d < self.p_stay else "M" for d in draws]


# ---------- LLMPolicy (real, optional) ----------


def make_llm_policy(model_name: str):  # pragma: no cover — exercised via smoke
    """Construct a real LLM-backed policy. Requires torch + transformers.

    Lazily imported so unit tests stay torch-free. The unit test suite uses
    ``MockPolicy``; this constructor is invoked only from ``toy_v1.main``
    (the CLI runner) and from any future smoke test.
    """
    try:
        from toy_v1._llm_policy import LLMPolicy  # local import; needs torch
    except ImportError as e:
        raise RuntimeError(
            "LLMPolicy requires the [llm] extra. "
            "Install with: uv sync --extra dev --extra llm"
        ) from e
    return LLMPolicy(model_name=model_name)


__all__ = ["Policy", "MockPolicy", "make_llm_policy", "LABELS"]
