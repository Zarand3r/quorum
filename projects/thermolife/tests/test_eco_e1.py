"""E1 — attention as the interaction operator (IMPLEMENTATION_PLAN.md Steps 7–8).

Gates: transfer follows attention (+ conserves), gene-modulated groundedness
(P7), no order reward in dynamics (P2), determinism with the attention policy,
edge routing, and the ablation harness moving observables in the predicted
directions.
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import numpy as np

from eco.ablations import MODES, run_arm
from eco.config import load_eco_config
from eco.engine import EcoEngine, run
from eco.interaction import (
    decode_actions,
    interaction_graph,
    interface_coeffs,
    make_attention_policy,
)
from eco.observables import attention_entropy, transfer_on_edges
from eco.state import init_state

_CFG = Path(__file__).resolve().parent.parent / "configs" / "eco.yaml"


def _cfg(**over):
    cfg = load_eco_config(_CFG)
    return cfg if not over else dataclasses.replace(cfg, **over)


# ---- Step 7: the operator ---------------------------------------------------


def test_transfer_follows_attention_and_conserves() -> None:
    """P1 + edge routing: all transferred energy rides the sender's off-diagonal
    attention shares; the full tick still closes the ledger."""
    cfg = _cfg()
    policy = make_attention_policy(cfg, seed=3)
    eng = EcoEngine(cfg, policy=policy)
    eng.tick()
    a = policy.last_attention
    st = eng.state
    dx, gate, t = decode_actions(st, a[: st.n, : st.n] if a.shape[0] != st.n else a,
                                 policy.weights, cfg)
    assert np.allclose(np.diag(t), 0.0)                     # never send to self
    assert np.all(t.sum(axis=1) <= st.e + 1e-9)             # no overdraw
    assert transfer_on_edges(t, a if a.shape[0] == st.n else a[: st.n, : st.n]) > 0.99
    # 200 more ticks: ledger stays closed under interaction + transfer
    for _ in range(200):
        r = eng.tick()
        assert abs(r) < 1e-9, r


def test_e1_conserves_longrun_all_modes() -> None:
    """P1 across every ablation arm: interaction changes dynamics, not physics."""
    cfg = _cfg()
    for mode in MODES:
        res = run_arm(cfg, mode, ticks=500, seed=0)
        assert res["max_abs_residual"] < 1e-9, (mode, res["max_abs_residual"])


def test_e1_determinism() -> None:
    """P4 with the attention policy (incl. births/deaths and gene mutation)."""
    cfg = _cfg()
    a = EcoEngine(cfg, policy=make_attention_policy(cfg, seed=1))
    b = EcoEngine(cfg, policy=make_attention_policy(cfg, seed=1))
    for _ in range(300):
        a.tick(); b.tick()
    assert a.state.state_hash() == b.state.state_hash()


def test_groundedness_gene_modulates_surface_and_graph() -> None:
    """P7: perturbing token i's GENE moves its interface coefficients (the drawn
    blob) and its interaction row TOGETHER; other tokens' surfaces are unmoved."""
    cfg = _cfg()
    policy = make_attention_policy(cfg, seed=5)
    st = init_state(cfg)
    w = policy.weights
    c0 = interface_coeffs(st.x, st.g, w)
    a0 = interaction_graph(st.x, st.g, w, cfg.hk_tau)
    g2 = st.g.copy()
    g2[3] += 2.0
    c2 = interface_coeffs(st.x, g2, w)
    a2 = interaction_graph(st.x, g2, w, cfg.hk_tau)
    assert not np.allclose(c0[3], c2[3])            # its surface changed
    assert not np.allclose(a0[3], a2[3])            # its interaction row changed
    others = [i for i in range(st.n) if i != 3]
    assert np.allclose(c0[others], c2[others])      # only token 3's surface moved


def test_no_order_reward_in_dynamics() -> None:
    """P2: dynamics modules contain no order/complexity scoring and do not
    import the observables module (import direction is one-way)."""
    import eco

    root = Path(eco.__file__).parent
    for mod in ("engine", "interaction", "policies", "resource", "state", "config"):
        src = (root / f"{mod}.py").read_text()
        assert "observables" not in src, f"{mod}.py imports observables (P2)"
        low = src.lower()
        for banned in ("entropy", "cluster_count", "complexity", "novelty"):
            assert banned not in low, (mod, banned)


def test_vectorized_no_per_token_loop_e1() -> None:
    """P5 extended to the E1 operator."""
    from eco.interaction import decode_actions as da, interaction_graph as ig
    for fn in (da, ig, interface_coeffs):
        assert "for " not in inspect.getsource(fn), fn.__name__


# ---- Step 8: interaction does real work + ablations -------------------------


def test_edge_routing_zero_attention_zero_transfer() -> None:
    """Severing off-diagonal attention (freeze arm) zeroes energy transport."""
    cfg = _cfg()
    res = run_arm(cfg, "freeze_attention", ticks=100, seed=0)
    assert res["mean_interaction_degree"] == 0.0
    # and the remove_transfer arm keeps interaction but moves no energy
    policy = make_attention_policy(cfg, seed=0, mode="remove_transfer")
    eng = EcoEngine(cfg, policy=policy)
    st = eng.state
    _, _, t = policy(st, cfg)
    assert float(np.abs(t).sum()) == 0.0


def test_ablation_harness_predicted_directions() -> None:
    """Each arm moves the observables the way its severing predicts.

    Directional facts (empirical, worth stating): the hard HK kernel is UNIFORM
    over its confidence set, so its entropy can exceed peaked global softmax —
    locality ≠ low entropy. The robust predictions are: freeze arm at zero
    entropy/degree; interacting arms strictly above it; harness deterministic."""
    cfg = _cfg()
    hk = run_arm(cfg, "hk", ticks=150, seed=0)
    frozen_a = run_arm(cfg, "freeze_attention", ticks=150, seed=0)
    softmax = run_arm(cfg, "softmax", ticks=150, seed=0)
    assert hk["mean_interaction_degree"] > 0.0          # interaction exists
    assert frozen_a["mean_attention_entropy"] < 1e-9    # self-only = zero entropy
    assert frozen_a["mean_interaction_degree"] == 0.0
    assert softmax["mean_attention_entropy"] > 0.0
    assert hk["mean_attention_entropy"] > 0.0
    rerun = run_arm(cfg, "hk", ticks=150, seed=0)
    assert rerun == hk                                  # deterministic harness


def test_e1_random_theta_still_faces_real_stakes() -> None:
    """P8 carried to E1: at fast drift the random-θ population starves — the
    physics still bites regardless of the operator. (Random θ is NOT expected
    to survive slow drift; learning to forage is E2's job, not E1's.)"""
    cfg = _cfg(drift_v=0.35)
    res = run(cfg, ticks=600, policy=make_attention_policy(cfg, seed=0))
    assert res["final_n"] == 0
    assert res["max_abs_residual"] < 1e-9


def test_attention_entropy_bounds() -> None:
    n = 8
    assert attention_entropy(np.eye(n)) < 1e-9                       # frozen
    assert abs(attention_entropy(np.full((n, n), 1 / n)) - np.log(n)) < 1e-9
