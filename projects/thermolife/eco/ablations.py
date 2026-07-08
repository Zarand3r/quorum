"""Ablation harness (IMPLEMENTATION_PLAN.md Step 8; RESEARCH_HK.md §5.3).

Matched-compute arms over the SAME config/seed/tick budget, differing only in the
interaction operator: any claim about the E1 substrate must be reported as the
default arm's observable vs these. Modes (eco/interaction.py):

  hk                — the E1 default (bounded-confidence dock attention)
  softmax           — global softmax (the collapse-prone operator, per the study)
  freeze_attention  — A = I: no interaction at all
  shuffle_edges     — permuted columns: same mass, wrong partners
  remove_transfer   — interaction intact, energy transport severed
"""

from __future__ import annotations

import numpy as np

from eco.config import EcoConfig
from eco.engine import EcoEngine
from eco.interaction import make_attention_policy
from eco.observables import attention_entropy, interaction_degree

MODES = ("hk", "softmax", "freeze_attention", "shuffle_edges", "remove_transfer")


def run_arm(cfg: EcoConfig, mode: str, ticks: int, seed: int = 0) -> dict:
    """One matched-compute rollout; returns observables (read-only, P2)."""
    policy = make_attention_policy(cfg, seed=seed, mode=mode)
    eng = EcoEngine(cfg, policy=policy)
    max_resid = 0.0
    entropies, degrees = [], []
    survived = ticks
    for _ in range(ticks):
        max_resid = max(max_resid, abs(eng.tick()))
        if policy.last_attention is not None and policy.last_attention.size:
            entropies.append(attention_entropy(policy.last_attention))
            degrees.append(interaction_degree(policy.last_attention))
        if eng.state.n == 0:
            survived = eng.state.t
            break
    return {
        "mode": mode,
        "survived": survived,
        "final_n": eng.state.n,
        "max_abs_residual": max_resid,
        "mean_attention_entropy": float(np.mean(entropies)) if entropies else 0.0,
        "mean_interaction_degree": float(np.mean(degrees)) if degrees else 0.0,
    }


def run_all(cfg: EcoConfig, ticks: int, seed: int = 0) -> list[dict]:
    return [run_arm(cfg, mode, ticks, seed) for mode in MODES]
