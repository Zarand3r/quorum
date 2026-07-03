"""Step 6 — control state machine (gate P8). IMPLEMENTATION_PLAN.md Step 6.

Driven synchronously (``autostart_thread=False`` + ``_tick_now``) so the
properties are deterministic, not wall-clock dependent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from env.config import load_world_config
from sim.controller import ControllerError, SimController, SimEngine, SimStatus

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _cfg():
    return load_world_config(_CONFIG, scenario="static_gradient")


def _controller():
    return SimController(_cfg(), default_seed=42, autostart_thread=False)


def test_transitions_legal_and_illegal() -> None:
    c = _controller()
    assert c.status() == SimStatus.IDLE
    with pytest.raises(ControllerError):
        c.pause()  # illegal from IDLE
    with pytest.raises(ControllerError):
        c.restart()  # illegal from IDLE

    c.start(seed=42)
    assert c.status() == SimStatus.RUNNING
    with pytest.raises(ControllerError):
        c.resume()  # illegal from RUNNING

    c.pause()
    assert c.status() == SimStatus.PAUSED
    with pytest.raises(ControllerError):
        c.pause()  # illegal from PAUSED

    c.resume()
    assert c.status() == SimStatus.RUNNING
    c.stop()
    assert c.status() == SimStatus.IDLE


def test_pause_resume_does_not_perturb_trajectory() -> None:
    """P8: tick-N state is identical whether or not a pause happened."""
    cfg = _cfg()
    c = SimController(cfg, default_seed=42, autostart_thread=False)
    c.start(seed=42)
    n, k = 200, 80
    for _ in range(k):
        c._tick_now()
    c.pause()
    for _ in range(5):
        c._tick_now()  # no-ops while paused
    c.resume()
    for _ in range(n - k):
        c._tick_now()

    ref = SimEngine(cfg, 42)
    for _ in range(n):
        ref.step()
    assert c._engine.world.state_hash() == ref.world.state_hash()


def test_restart_reseeds_to_tick_zero() -> None:
    cfg = _cfg()
    c = SimController(cfg, default_seed=42, autostart_thread=False)
    c.start(seed=42)
    for _ in range(50):
        c._tick_now()
    c.restart()
    assert c._engine.tick == 0
    assert c._engine.world.state_hash() == SimEngine(cfg, 42).world.state_hash()
