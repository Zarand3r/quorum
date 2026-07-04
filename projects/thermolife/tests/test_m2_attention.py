"""M2.1 — windowed attention (IMPLEMENTATION_PLAN_M2.md M2.1). Gates Q3."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from model.attention import interface_heads, neighbor_attention
from model.config import load_model_config
from model.genome import Genome
from model.state import NCAState

_MODEL = Path(__file__).resolve().parent.parent / "configs" / "model.yaml"


def _setup(seed=1):
    cfg = load_model_config(_MODEL)
    g = Genome.random(cfg, seed=seed)
    s = NCAState.seed(32, 32, cfg, seed=seed)
    return cfg, g, s


def test_shapes_and_softmax_normalized() -> None:
    cfg, g, s = _setup()
    lig, rec, val = interface_heads(s.hidden, g)
    assert lig.shape == (32, 32, cfg.directions, cfg.iface_dim)
    assert val.shape == (32, 32, cfg.hidden_dim)
    alpha, m = neighbor_attention(lig, rec, val, cfg)
    assert alpha.shape == (32, 32, cfg.directions)
    assert m.shape == (32, 32, cfg.hidden_dim)
    # softmax weights sum to 1 over the neighborhood per cell.
    assert np.allclose(alpha.sum(axis=-1), 1.0)
    assert alpha.min() >= 0.0


def test_locality() -> None:
    """Q3: a cell's message depends only on its 4-neighborhood."""
    cfg, g, s = _setup()
    lig, rec, val = interface_heads(s.hidden, g)
    _, m0 = neighbor_attention(lig, rec, val, cfg)

    s2 = s.copy()
    s2.hidden[0, 0, :] += 5.0  # perturb one corner cell
    lig2, rec2, val2 = interface_heads(s2.hidden, g)
    _, m1 = neighbor_attention(lig2, rec2, val2, cfg)

    # a cell far from (0,0) and its neighbors is unchanged.
    assert np.allclose(m0[16, 16], m1[16, 16])
    # a neighbor of (0,0) does change.
    assert not np.allclose(m0[1, 0], m1[1, 0])


def test_determinism() -> None:
    cfg, g, s = _setup()
    lig, rec, val = interface_heads(s.hidden, g)
    a1, m1 = neighbor_attention(lig, rec, val, cfg)
    a2, m2 = neighbor_attention(lig, rec, val, cfg)
    assert np.array_equal(a1, a2) and np.array_equal(m1, m2)
