"""Real-LLM smoke test.

Marked ``@pytest.mark.llm`` and gated with ``pytest.importorskip`` — the
module is auto-skipped when torch is absent. To run:

    uv sync --extra dev --extra llm
    bazel test //projects/quorum/slice0:test_suite --test_arg=-m --test_arg=llm

Loads a tiny model (SmolLM2-135M by default; override via env), does ONE
step over a small batch, asserts:

- 1 forward call per step (I3 gate against the real model).
- 0 generate calls (I4 gate against the real model).
- Correct action shape.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

# torch import can raise OSError when the wheel is present but its native CUDA
# runtime isn't loadable (missing libcudart, mismatched CUDA driver). pytest's
# importorskip only catches ImportError, so we widen it here to keep the
# suite collectable on CPU-only / mismatched-driver machines.
try:
    import torch  # noqa: F401
    import transformers  # noqa: F401
except Exception as e:  # ImportError, OSError, ValueError (torch cuda preload)
    pytest.skip(f"torch/transformers not loadable: {e}", allow_module_level=True)

from slice0._llm_policy import LLMPolicy   # noqa: E402


# Smoke default: tiny model so the test runs on CPU in a few seconds. Override
# with SLICE0_SMOKE_MODEL to run the real Qwen 2.5 1.5B if you want.
SMOKE_MODEL = os.environ.get("SLICE0_SMOKE_MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")


@pytest.mark.llm
class TestLLMPolicySmoke:
    def test_step_returns_one_action_per_prompt(self):
        p = LLMPolicy(model_name=SMOKE_MODEL)
        rng = np.random.default_rng(42)
        actions = p.step(
            prompts=[
                "Answer N, S, E, W, or Z:",
                "Answer N, S, E, W, or Z:",
                "Answer N, S, E, W, or Z:",
            ],
            rng=rng,
        )
        assert len(actions) == 3
        for a in actions:
            assert a in {"N", "S", "E", "W", "Z"}

    def test_one_forward_call_per_step(self):
        p = LLMPolicy(model_name=SMOKE_MODEL)
        rng = np.random.default_rng(0)
        before = p.forward_call_count
        p.step(prompts=["x"], rng=rng)
        assert p.forward_call_count - before == 1

    def test_no_generate_calls_on_real_model(self):
        p = LLMPolicy(model_name=SMOKE_MODEL)
        rng = np.random.default_rng(0)
        p.step(prompts=["a", "b", "c"], rng=rng)
        assert p.generate_call_count == 0
