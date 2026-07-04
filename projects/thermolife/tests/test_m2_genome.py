"""M2.0 — model foundation (IMPLEMENTATION_PLAN_M2.md M2.0)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from model.config import load_model_config
from model.genome import Genome
from model.state import NCAState

_MODEL = Path(__file__).resolve().parent.parent / "configs" / "model.yaml"


def _cfg():
    return load_model_config(_MODEL)


def test_config_loads_nca_section() -> None:
    cfg = _cfg()
    assert cfg.hidden_dim == 8
    assert cfg.directions == 4
    assert len(cfg.diffusivity) == cfg.hidden_dim
    assert 0.0 <= cfg.advection_gain <= 1.0


def test_genome_shapes_and_determinism() -> None:
    cfg = _cfg()
    a = Genome.random(cfg, seed=7)
    b = Genome.random(cfg, seed=7)
    assert a.W_lig.shape == (cfg.hidden_dim, cfg.directions, cfg.iface_dim)
    assert a.W1.shape == (2 * cfg.hidden_dim + 1, cfg.mlp_width)
    assert a.W2.shape == (cfg.mlp_width, cfg.hidden_dim)
    assert np.array_equal(a.W_lig, b.W_lig)
    assert np.array_equal(a.W1, b.W1)
    assert not np.array_equal(a.W_lig, Genome.random(cfg, seed=8).W_lig)


def test_state_shapes_and_mass() -> None:
    cfg = _cfg()
    s = NCAState.seed(64, 64, cfg, seed=42)
    assert s.hidden.shape == (64, 64, cfg.hidden_dim)
    assert s.mass.shape == (64, 64)
    assert s.mass.sum() > 0.0
    assert s.mass.min() >= 0.0
    assert NCAState.seed(64, 64, cfg, 42).state_hash() == s.state_hash()
