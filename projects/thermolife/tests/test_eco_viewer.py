"""Step 6 — the economy viewer path (IMPLEMENTATION_PLAN.md Step 6).

Gates: the render snapshot schema, and P4 — driving the engine through the
controller (the viewer's path) produces the byte-identical state history as
headless stepping, i.e. rendering never perturbs dynamics.
"""

from __future__ import annotations

from pathlib import Path

from eco.config import load_eco_config
from eco.engine import EcoEngine
from eco.interaction import make_attention_policy
from eco.policies import hand_forager
from sim.controller import SimController

_CFG = Path(__file__).resolve().parent.parent / "configs" / "eco.yaml"


def _cfg():
    return load_eco_config(_CFG)


def test_eco_snapshot_schema() -> None:
    cfg = _cfg()
    eng = EcoEngine(cfg, policy=hand_forager)
    for _ in range(120):
        eng.step()
    snap = eng.snapshot()
    for key in ("status", "tick", "n", "n_max", "pool", "dissipated", "energy",
                "residual", "source", "harvest_radius", "e_max", "tokens", "edges"):
        assert key in snap, key
    assert snap["tick"] == 120 and snap["n"] > 0
    assert len(snap["tokens"]) == snap["n"]
    tok = snap["tokens"][0]
    assert len(tok["pos"]) == 2 and "e" in tok
    assert len(snap["source"]) == 2
    assert abs(snap["residual"]) < 1e-9              # ledger honest in the view


def test_eco_snapshot_shows_transfer_edges_under_attention() -> None:
    """The E1 attention operator produces transfer edges; the forager does not."""
    cfg = _cfg()
    forager = EcoEngine(cfg, policy=hand_forager)
    attn = EcoEngine(cfg, policy=make_attention_policy(cfg, seed=0))
    for _ in range(20):
        forager.step(); attn.step()
    assert forager.snapshot()["edges"] == []          # forager never transfers
    assert len(attn.snapshot()["edges"]) > 0          # attention routes energy


def test_eco_viewer_readonly_matches_headless() -> None:
    """P4: stepping via the controller (viewer path, snapshotting each tick)
    yields the identical state hash as pure headless stepping — rendering is
    side-effect free."""
    cfg = _cfg()
    headless = EcoEngine(cfg, policy=hand_forager)
    for _ in range(200):
        headless.step()

    c = SimController(lambda s: EcoEngine(cfg, policy=hand_forager),
                      default_seed=0, autostart_thread=False)
    c.start(seed=0)
    for _ in range(200):
        c._tick_now()
        c.snapshot()                                  # render every tick (as the UI does)
    assert c._engine.state_hash() == headless.state_hash()


def test_eco_snapshot_readonly_for_stochastic_policies() -> None:
    """P4 (the sharp case): snapshot() recomputes edges by calling the policy.
    For a STOCHASTIC arm (shuffle_edges draws a permutation) that recompute must
    still not perturb the trajectory. Regression for the latent bug where a
    per-call ablation RNG was advanced by every render, desyncing the next tick.
    hand_forager (zero transfer, no RNG) can't catch this — these policies can."""
    cfg = _cfg()
    for mode in ("dist", "shuffle_edges"):
        headless = EcoEngine(cfg, policy=make_attention_policy(cfg, seed=1, mode=mode))
        rendered = EcoEngine(cfg, policy=make_attention_policy(cfg, seed=1, mode=mode))
        for _ in range(60):
            headless.step()
            rendered.step()
            rendered.snapshot()                           # render every tick (UI path)
        assert rendered.state_hash() == headless.state_hash(), \
            f"snapshot() perturbed the {mode} trajectory (P4 violation)"


def test_eco_controller_snapshot_ok() -> None:
    """The controller serves the eco engine's snapshot without touching it."""
    cfg = _cfg()
    c = SimController(lambda s: EcoEngine(cfg, policy=hand_forager),
                      default_seed=0, autostart_thread=False)
    c.start(seed=0)
    for _ in range(50):
        c._tick_now()
    snap = c.snapshot()
    assert snap["tick"] == 50 and snap["n"] > 0 and "source" in snap
