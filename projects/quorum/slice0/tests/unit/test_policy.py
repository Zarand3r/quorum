"""Policy tests. Baseline backend only — LLMPolicy lands in a later commit."""

from __future__ import annotations

import numpy as np
import pytest

from slice0 import policy
from slice0.policy import Policy, UniformRandomPolicy


class TestPolicyProtocol:
    def test_uniform_random_satisfies_protocol(self):
        p = UniformRandomPolicy(seed=0)
        assert isinstance(p, Policy)

    def test_returns_one_action_per_prompt(self):
        p = UniformRandomPolicy(seed=0)
        rng = np.random.default_rng(0)
        acts = p.step(prompts=["a", "b", "c", "d"], rng=rng)
        assert len(acts) == 4
        for a in acts:
            assert a in policy.LABELS

    def test_step_is_single_call_i3_gate(self):
        """I3: one call to step → one 'forward'. UniformRandomPolicy's
        forward is a vectorized draw, mirroring how LLMPolicy uses one
        model forward per step()."""
        p = UniformRandomPolicy(seed=0)
        rng = np.random.default_rng(0)
        before = p.forward_call_count
        p.step(prompts=["a"] * 8, rng=rng)
        assert p.forward_call_count - before == 1

    def test_generate_never_called_i4_gate(self):
        """I4: no autoregressive decode. Counter stays at 0 by construction."""
        p = UniformRandomPolicy(seed=0)
        rng = np.random.default_rng(0)
        p.step(prompts=["x", "y"], rng=rng)
        assert p.generate_call_count == 0

    def test_deterministic_with_same_seed(self):
        """I8 substrate: same RNG state → same actions."""
        p1 = UniformRandomPolicy(seed=0)
        p2 = UniformRandomPolicy(seed=0)
        a1 = p1.step(prompts=["p"] * 20, rng=np.random.default_rng(42))
        a2 = p2.step(prompts=["p"] * 20, rng=np.random.default_rng(42))
        assert a1 == a2

    def test_different_rngs_diverge(self):
        p = UniformRandomPolicy(seed=0)
        a1 = p.step(prompts=["p"] * 40, rng=np.random.default_rng(1))
        a2 = p.step(prompts=["p"] * 40, rng=np.random.default_rng(2))
        assert a1 != a2

    def test_actions_uniform_over_vocab(self):
        """Over a large batch, each label should appear ~batch/5 times.
        Not a tight statistical test — just guards against a bug that maps
        everything to one label."""
        p = UniformRandomPolicy(seed=0)
        acts = p.step(prompts=["p"] * 5000, rng=np.random.default_rng(0))
        counts = {lbl: acts.count(lbl) for lbl in policy.LABELS}
        # 5000 / 5 = 1000; within ±5σ ≈ ±150 comfortably.
        for lbl, c in counts.items():
            assert 800 < c < 1200, f"label {lbl!r} count={c} (expected ~1000)"

    def test_observations_optional(self):
        """The Policy protocol accepts ``observations`` optionally so a
        future LLMPolicy or rule-based policy can consume them.
        UniformRandom ignores them."""
        p = UniformRandomPolicy(seed=0)
        rng = np.random.default_rng(0)
        acts = p.step(prompts=["x"], rng=rng, observations=[{"occ": 3}])
        assert len(acts) == 1
