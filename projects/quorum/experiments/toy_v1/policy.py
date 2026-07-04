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


Observation = dict[str, int]
"""Structured per-agent observation. Currently ``{"own": int, "other": int,
"empty": int}`` — same counts the prompt renders as text. Passed alongside
prompts so rule-based backends can decide without regex-parsing the prompt."""


@runtime_checkable
class Policy(Protocol):
    """Population policy interface.

    A policy turns a batch of agent prompts into a batch of action labels
    via ONE underlying forward pass per call. The runner calls ``step`` once
    per tick.

    ``observations`` is an optional structured mirror of the prompt content
    (see the ``Observation`` alias). LLM-shaped backends ignore it and read
    the prompt; rule-shaped backends read it and ignore the prompt.
    """

    def step(
        self,
        prompts: list[str],
        rng: np.random.Generator,
        observations: list[Observation] | None = None,
    ) -> list[str]:
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

    def step(
        self,
        prompts: list[str],
        rng: np.random.Generator,
        observations: list[Observation] | None = None,  # ignored by mock
    ) -> list[str]:
        # I3 gate: one call to step → one "forward" (here a vectorized draw).
        self.forward_call_count += 1
        # Vectorized Bernoulli draw — N actions in a single rng.random call,
        # mirroring how LLMPolicy gets N actions out of one model forward.
        draws = rng.random(size=len(prompts))
        return ["S" if d < self.p_stay else "M" for d in draws]


# ---------- SchellingRulePolicy ----------


class SchellingRulePolicy:
    """Classical Schelling rule as a policy backend.

    Not an LLM — no forward pass. Deterministic given the observations. Serves
    two purposes:

    1. **A working baseline that actually produces emergence**, so the viz
       shows same-color clustering rather than random noise. This is what a
       correctly-prompted LLM policy is supposed to approximate.
    2. **An architectural sanity check.** Same ``Policy`` protocol as
       MockPolicy and LLMPolicy — the substrate + runner + metrics don't care
       which backend produced the actions.

    Rule: an agent moves iff the fraction of its non-empty neighbors that
    share its color is < ``threshold``. Isolated agents (no non-empty
    neighbors) stay put.

    ``threshold = 0.3`` (Schelling's original) usually produces visible
    segregation in ~30–80 ticks at ~50% grid occupancy.
    """

    __slots__ = ("threshold", "forward_call_count", "generate_call_count")

    def __init__(self, threshold: float = 0.3) -> None:
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        self.threshold = float(threshold)
        self.forward_call_count = 0
        self.generate_call_count = 0

    def step(
        self,
        prompts: list[str],
        rng: np.random.Generator,
        observations: list[Observation] | None = None,
    ) -> list[str]:
        if observations is None:
            raise RuntimeError(
                "SchellingRulePolicy requires structured observations; "
                "the runner supplies them, but a caller passed None."
            )
        if len(observations) != len(prompts):
            raise ValueError(
                f"observations length {len(observations)} != prompts length {len(prompts)}"
            )
        self.forward_call_count += 1
        actions: list[str] = []
        for obs in observations:
            own = obs["own"]
            other = obs["other"]
            non_empty = own + other
            if non_empty == 0:
                actions.append("S")  # isolated → stay
                continue
            same_frac = own / non_empty
            actions.append("S" if same_frac >= self.threshold else "M")
        return actions


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


__all__ = [
    "Policy",
    "Observation",
    "MockPolicy",
    "SchellingRulePolicy",
    "make_llm_policy",
    "LABELS",
]
