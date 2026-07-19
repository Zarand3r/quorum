"""E2 — the gate on the evolved economy chemistry θ (train/es_eco.py).

THE E2 GATE: the committed evolved θ (configs/eco_theta.npz), driving the E1
attention operator under the E0-gate drift, keeps the population far more viable
than an untrained random θ and at least matches the hand-forager — on HELD-OUT
init seeds the trainer never saw. Plus honest ablation measurement: which parts
of the learned interaction are load-bearing (measured, never rewarded — P2).

Budget kept small (4 held-out seeds × 180 ticks) so the suite stays fast; the
margins below have generous headroom over the full 8-seed/220-tick report.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np

from eco.ablations import run_arm
from eco.config import load_eco_config
from eco.interaction import EcoWeights, make_attention_policy
from eco.policies import hand_forager
from train.es_eco import (
    _rank_normalise,
    _rollout_population_ticks,
    flatten,
    load_theta,
    save_theta,
    unflatten,
)

_ROOT = Path(__file__).resolve().parent.parent
_CFG = _ROOT / "configs" / "eco.yaml"
_THETA = _ROOT / "configs" / "eco_theta.npz"

_HELD_OUT = tuple(range(9000, 9004))     # seeds disjoint from training + validation
_TICKS = 180


def _cfg():
    return load_eco_config(_CFG)


def _mean_pop_ticks(policy, cfg, seeds, ticks) -> float:
    return float(np.mean([_rollout_population_ticks(policy, cfg, s, ticks) for s in seeds]))


# ---- THE E2 GATE -------------------------------------------------------------

def test_evolved_beats_random_and_matches_forager() -> None:
    """The evolved θ must (a) crush a random θ and (b) at least match the
    hand-forager on unseen initial populations — otherwise ES learned nothing
    transferable. Measured with the SAME dist operator the viewer runs."""
    cfg = _cfg()
    evolved = load_theta(_THETA, cfg)
    random_t = EcoWeights.random(cfg, 4, 16, 0)

    ev = _mean_pop_ticks(make_attention_policy(cfg, mode="dist", weights=evolved),
                         cfg, _HELD_OUT, _TICKS)
    rnd = _mean_pop_ticks(make_attention_policy(cfg, mode="dist", weights=random_t),
                          cfg, _HELD_OUT, _TICKS)
    frg = _mean_pop_ticks(hand_forager, cfg, _HELD_OUT, _TICKS)

    assert ev > 8.0 * rnd, f"evolved {ev:.0f} not ≫ random {rnd:.0f} ({ev/rnd:.1f}×)"
    assert ev > frg, f"evolved {ev:.0f} did not beat hand-forager {frg:.0f}"


def test_evolved_ablations_measured() -> None:
    """Honest ablation of the LEARNED chemistry (P2 — measured, not rewarded).

    The full dist operator is the best arm; two findings are asserted as
    regressions: (1) removing interaction entirely (freeze A=I) costs viability —
    interaction helps; (2) SHUFFLING partners (same mass, wrong targets) is the
    most damaging arm, and is worse than freezing — the interaction *structure*
    is load-bearing, not just its magnitude. This is the empirical E3 motivation:
    individual foraging carries the base, structured interaction adds to it."""
    cfg = _cfg()
    evolved = load_theta(_THETA, cfg)
    pt = {}
    for mode in ("dist", "freeze_attention", "shuffle_edges", "remove_transfer"):
        pt[mode] = float(np.mean([
            run_arm(dataclasses.replace(cfg, seed=s), mode, _TICKS, seed=0, weights=evolved)["pop_ticks"]
            for s in _HELD_OUT
        ]))
    assert pt["dist"] == max(pt.values()), f"dist not the best arm: {pt}"
    assert pt["freeze_attention"] < pt["dist"], "interaction did not help (freeze ≥ dist)"
    assert pt["shuffle_edges"] < 0.7 * pt["dist"], \
        f"scrambling partners barely hurt ({pt['shuffle_edges']/pt['dist']:.2f}×) — " \
        "structure not load-bearing"
    assert pt["shuffle_edges"] < pt["freeze_attention"], \
        "wrong-partner interaction not worse than no interaction"


# ---- es_eco unit tests -------------------------------------------------------

def test_flatten_unflatten_roundtrip_excludes_M() -> None:
    """θ packs/unpacks exactly, and the fixed metric M is never in the vector."""
    cfg = _cfg()
    w = EcoWeights.random(cfg, 4, 16, 7)
    vec = flatten(w)
    w2 = unflatten(vec, w)
    for k in ("W_c", "G_c", "W_v", "W1", "b1", "W2", "b2"):
        assert np.array_equal(getattr(w, k), getattr(w2, k)), k
    # a perturbed vector must NOT change M (M is borrowed from the template)
    w3 = unflatten(vec + 1.0, w)
    assert np.array_equal(w3.M, w.M), "M leaked into the evolved vector"


def test_theta_save_load_roundtrip(tmp_path) -> None:
    """Persisted θ round-trips, and M is reconstructed identically from k."""
    cfg = _cfg()
    w = EcoWeights.random(cfg, 4, 16, 3)
    p = tmp_path / "theta.npz"
    save_theta(p, w, cfg, 4, 16)
    w2 = load_theta(p, cfg)
    for k in ("W_c", "G_c", "M", "W_v", "W1", "b1", "W2", "b2"):
        assert np.array_equal(getattr(w, k), getattr(w2, k)), k


def test_rank_normalise_ties_cancel() -> None:
    """Tied fitnesses get equal (averaged) ranks, so an antithetic pair with the
    same fitness contributes zero gradient — no phantom step in the tie-heavy
    extinction regime. Distinct-rank argsort would break this."""
    f = np.array([5.0, 5.0, 5.0, 5.0])         # all tied
    u = _rank_normalise(f)
    assert np.allclose(u, 0.0), f"tied fitnesses did not map to equal ranks: {u}"
    # a genuine ordering is still monotone
    g = np.array([1.0, 3.0, 2.0])
    ug = _rank_normalise(g)
    assert ug[0] < ug[2] < ug[1]
