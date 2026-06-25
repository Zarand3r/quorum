"""Smoke test for the real LLM policy.

Marked ``@pytest.mark.smoke`` — opt-in only; skipped automatically when
torch is not installed (the default ``uv sync --extra dev`` does not
install torch). To run it:

    uv sync --extra dev --extra llm
    uv run pytest -m smoke -q

The smoke test does the cheapest thing that meaningfully exercises the
real LLM path: load a tiny model, run ONE step over 2 prompts, assert the
shape + invariants hold. It is NOT an emergence test (the runner does
that).
"""

from __future__ import annotations

import numpy as np
import pytest

# Skip the whole module when torch is absent.
torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

# Import after the importorskip so collection doesn't crash without torch.
from toy_v1._llm_policy import LLMPolicy   # noqa: E402


SMOKE_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"


@pytest.mark.smoke
class TestLLMPolicySmoke:
    def test_single_step_returns_one_action_per_prompt(self):
        p = LLMPolicy(model_name=SMOKE_MODEL)
        rng = np.random.default_rng(42)
        actions = p.step(["You are agent A. Answer:", "You are agent B. Answer:"], rng=rng)
        assert len(actions) == 2
        for a in actions:
            assert a in {"S", "M"}

    def test_one_step_one_forward_call(self):
        p = LLMPolicy(model_name=SMOKE_MODEL)
        rng = np.random.default_rng(0)
        before = p.forward_call_count
        p.step(["x"], rng=rng)
        assert p.forward_call_count - before == 1

    def test_no_generate_calls(self):
        p = LLMPolicy(model_name=SMOKE_MODEL)
        rng = np.random.default_rng(0)
        p.step(["a", "b", "c"], rng=rng)
        assert p.generate_call_count == 0
