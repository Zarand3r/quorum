"""Policy contract + UniformRandomPolicy baseline.

The Slice 0 merge gate (PLAN.md §15.1) is: mean-nearest-neighbor distance
under the LLM strictly lower than under a uniform-random baseline
(Mann-Whitney U p < 0.01 over ≥ 10 seeds). ``UniformRandomPolicy`` IS that
baseline — it defines what "no policy at all" looks like.

The contract mirrors the toy_v1 shape:

- **I3 Single-pass** — one call to ``step()`` → one underlying forward call.
  Instrumented via ``forward_call_count``.
- **I4 Latent reasoning** — logit projection over the action vocab; no
  autoregressive decode. Instrumented via ``generate_call_count`` which is
  always 0 by construction and asserted in tests.
- **I8 Replay determinism** — sampling uses the caller-supplied RNG.

The LLM backend (``LLMPolicy``) lives in ``_llm_policy`` and is imported
lazily via ``make_llm_policy`` so unit tests stay torch-free.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np

from slice0.actions import LABELS


Observation = dict[str, Any]
"""Structured per-agent observation. Currently ``{"occupancy": int}``.
Passed alongside prompts so rule-shaped backends can decide without
regex-parsing the prompt text."""


@runtime_checkable
class Policy(Protocol):
    """Population policy interface.

    A policy turns a batch of prompts into a batch of action labels via ONE
    underlying forward pass per call. The runner calls ``step`` once per tick.
    """

    def step(
        self,
        prompts: list[str],
        rng: np.random.Generator,
        observations: list[Observation] | None = None,
    ) -> list[str]:
        """Return one action label per prompt. Must call the underlying
        forward exactly once (I3) and must NOT autoregressively decode (I4)."""
        ...


# ---------- UniformRandomPolicy ----------


class UniformRandomPolicy:
    """Uniform-random over the 5-symbol vocab. The Slice 0 baseline.

    No torch. Vectorized draw per tick, mirroring how ``LLMPolicy`` gets N
    actions out of one model forward. Ignores prompts and observations by
    design — the whole point of this baseline is that it uses no information
    from the environment.
    """

    __slots__ = ("seed", "forward_call_count", "generate_call_count")

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)
        self.forward_call_count = 0
        self.generate_call_count = 0

    def step(
        self,
        prompts: list[str],
        rng: np.random.Generator,
        observations: list[Observation] | None = None,  # ignored
    ) -> list[str]:
        self.forward_call_count += 1
        idxs = rng.integers(0, len(LABELS), size=len(prompts))
        return [LABELS[int(i)] for i in idxs]


# ---------- LLMPolicy (deferred to the [llm] extra) ----------


def make_llm_policy(model_name: str, **kwargs: Any) -> Policy:  # pragma: no cover
    """Construct the vLLM-backed policy. Requires the ``[llm]`` extra
    (torch + vllm)."""
    if "_llm_policy" not in _lazy_llm_import():
        raise RuntimeError(
            "LLMPolicy requires the [llm] extra (torch + vllm). Install with "
            "`uv sync --extra dev --extra llm` then regenerate the lock."
        )
    from slice0._llm_policy import LLMPolicy  # local import
    return LLMPolicy(model_name=model_name, **kwargs)


def _lazy_llm_import() -> dict[str, bool]:
    try:
        import slice0._llm_policy  # noqa: F401
    except ImportError:
        return {}
    return {"_llm_policy": True}


__all__ = [
    "Policy",
    "Observation",
    "UniformRandomPolicy",
    "make_llm_policy",
    "LABELS",
]
