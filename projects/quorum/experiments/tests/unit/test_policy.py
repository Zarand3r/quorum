"""Tests for the Policy protocol + MockPolicy.

The hardest invariants in the system live here:

- **I3 Single-pass**  — `policy.step(prompts, rng)` triggers exactly ONE
  underlying forward call per tick (no per-agent loop). Tested by the
  MockPolicy's instrumented call counter.
- **I4 Latent reasoning** — Tier-1 reads action logits via projection.
  No `.generate()` is called. Tested by Mock instrumentation.
- **I8 Replay determinism** — same RNG state → same actions.

LLMPolicy itself is exercised in the smoke test, not here. Unit tests are
torch-free on purpose.
"""

from __future__ import annotations

import numpy as np
import pytest

from toy_v1 import policy
from toy_v1.policy import MockPolicy, Policy


class TestPolicyProtocol:
    def test_mock_satisfies_protocol(self):
        m = MockPolicy(seed=0)
        # Static structural check: MockPolicy implements Policy.
        assert isinstance(m, Policy)

    def test_step_returns_one_action_per_prompt(self):
        m = MockPolicy(seed=42)
        rng = np.random.default_rng(42)
        actions = m.step(["p1", "p2", "p3"], rng=rng)
        assert len(actions) == 3
        for a in actions:
            assert a in {"S", "M"}


class TestSinglePassGate:
    def test_one_step_one_forward_call(self):
        """I3: one call to step() == one underlying forward pass."""
        m = MockPolicy(seed=0)
        rng = np.random.default_rng(0)
        before = m.forward_call_count
        m.step(["a", "b", "c", "d", "e"], rng=rng)
        after = m.forward_call_count
        assert after - before == 1, "step() did not call forward exactly once"

    def test_ten_steps_ten_forward_calls(self):
        """Population size N does not change the per-tick forward count."""
        m = MockPolicy(seed=0)
        rng = np.random.default_rng(0)
        for _ in range(10):
            m.step(["a", "b", "c"], rng=rng)
        assert m.forward_call_count == 10


class TestNoGenerate:
    def test_no_generate_called_on_step(self):
        """I4: no autoregressive decode. MockPolicy crashes if anyone calls
        .generate() on it (the attribute exists only to be asserted absent)."""
        m = MockPolicy(seed=0)
        rng = np.random.default_rng(0)
        m.step(["a", "b"], rng=rng)
        assert m.generate_call_count == 0


class TestDeterminism:
    def test_same_rng_same_actions(self):
        """I8 substrate: same RNG state → same action sample."""
        m1 = MockPolicy(seed=42)
        m2 = MockPolicy(seed=42)
        r1 = np.random.default_rng(7)
        r2 = np.random.default_rng(7)
        a1 = m1.step(["p", "q", "r"], rng=r1)
        a2 = m2.step(["p", "q", "r"], rng=r2)
        assert a1 == a2

    def test_different_rngs_diverge(self):
        m = MockPolicy(seed=42)
        a1 = m.step(["p"] * 20, rng=np.random.default_rng(1))
        a2 = m.step(["p"] * 20, rng=np.random.default_rng(2))
        assert a1 != a2, "different seeds produced identical actions (likely degenerate)"


class TestMockBias:
    def test_uniform_default(self):
        """Default MockPolicy samples uniformly across the action vocab."""
        m = MockPolicy(seed=0)
        rng = np.random.default_rng(0)
        actions = m.step(["x"] * 1000, rng=rng)
        n_stay = actions.count("S")
        # 1000 samples at p=0.5 — within ±5σ ≈ ±80.
        assert 420 < n_stay < 580

    def test_biased_policy_obeys_bias(self):
        """A MockPolicy biased toward MOVE samples M >> S."""
        m = MockPolicy(seed=0, p_stay=0.05)
        rng = np.random.default_rng(0)
        actions = m.step(["x"] * 1000, rng=rng)
        n_stay = actions.count("S")
        assert n_stay < 100, f"expected sparse STAY at p=0.05, got {n_stay}"


class TestUnknownAction:
    def test_invalid_p_stay_rejected(self):
        with pytest.raises(ValueError):
            MockPolicy(seed=0, p_stay=1.5)
        with pytest.raises(ValueError):
            MockPolicy(seed=0, p_stay=-0.1)
