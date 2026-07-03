"""Step 2 — field physics (IMPLEMENTATION_PLAN.md Step 2). Gates P1, P2."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from env import fields as F
from env.config import load_world_config
from env.diffusion import diffuse_and_decay, inject_sources, laplacian

_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "world.yaml"


def _world(seed=42):
    return F.from_config(load_world_config(_CONFIG, scenario="static_gradient"), seed)


def test_laplacian_conserves() -> None:
    rng = np.random.default_rng(0)
    a = rng.random((16, 16))
    assert abs(float(laplacian(a).sum())) < 1e-9  # no-flux ⇒ sum ≈ 0


def test_pure_diffusion_conserves_nutrient() -> None:
    # P1: nutrient has zero decay, so diffusion alone preserves total mass.
    w = _world()
    w.fields[:] = 0.0
    w.fields[:, :, F.Field.HEAT] = w.cfg.fields["heat"].ambient
    w.fields[30, 30, F.Field.NUTRIENT] = 100.0
    before = w.fields[:, :, F.Field.NUTRIENT].sum()
    for _ in range(200):
        diffuse_and_decay(w, w.cfg)
    after = w.fields[:, :, F.Field.NUTRIENT].sum()
    assert np.isclose(before, after, rtol=0, atol=1e-9)


def test_waste_decay_is_an_exact_sink() -> None:
    w = _world()
    w.fields[:] = 0.0
    w.fields[:, :, F.Field.HEAT] = w.cfg.fields["heat"].ambient
    w.fields[20:25, 20:25, F.Field.WASTE] = 5.0
    before = w.fields[:, :, F.Field.WASTE].sum()
    removed = diffuse_and_decay(w, w.cfg)
    after = w.fields[:, :, F.Field.WASTE].sum()
    # diffusion conserves; decay removes exactly `removed`.
    assert np.isclose(after, before - removed, atol=1e-9)
    assert removed > 0.0


def test_non_negativity() -> None:
    # P2: convex-combination diffusion (D ≤ 0.25) + decay keeps fields ≥ 0.
    w = _world()
    rng = np.random.default_rng(1)
    w.fields[:] = rng.random(w.fields.shape) * 3.0
    for _ in range(300):
        diffuse_and_decay(w, w.cfg)
    assert w.fields.min() >= 0.0


def test_determinism() -> None:
    a, b = _world(), _world()
    for _ in range(50):
        diffuse_and_decay(a, a.cfg)
        diffuse_and_decay(b, b.cfg)
    assert np.array_equal(a.fields, b.fields)


def test_source_injection_respects_removal() -> None:
    w = _world()
    removal = w.cfg.scenario.removal_tick
    assert removal is not None
    assert inject_sources(w, tick=0) > 0.0            # source on
    assert inject_sources(w, tick=removal) == 0.0     # source removed at gate
    assert inject_sources(w, tick=removal + 100) == 0.0
