"""M2.2 — conserved advection / movement (M2.2). Gates Q1, Q2, Q6(move)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from model.advection import advect, advection_weights
from model.attention import interface_heads, neighbor_attention
from model.config import load_model_config
from model.genome import Genome
from model.state import NCAState

_MODEL = Path(__file__).resolve().parent.parent / "configs" / "model.yaml"


def _cfg():
    return load_model_config(_MODEL)


def _attention_flux(state, g, cfg):
    lig, rec, val = interface_heads(state.hidden, g)
    alpha, _ = neighbor_attention(lig, rec, val, cfg)
    return advection_weights(alpha, cfg.advection_gain)


def test_advection_conserves_mass() -> None:
    """Q1: attention transport preserves total mass over many steps."""
    cfg = _cfg()
    g = Genome.random(cfg, seed=3)
    s = NCAState.seed(48, 48, cfg, seed=3)
    total0 = s.mass.sum()
    for _ in range(500):
        alpha_out = _attention_flux(s, g, cfg)
        s.mass, _ = advect(s.mass, alpha_out)
    assert np.isclose(s.mass.sum(), total0, atol=1e-9)


def test_flux_limiter_non_negative() -> None:
    """Q2: with the limiter, mass never goes negative."""
    cfg = _cfg()
    g = Genome.random(cfg, seed=5)
    s = NCAState.seed(48, 48, cfg, seed=5)
    for _ in range(300):
        alpha_out = _attention_flux(s, g, cfg)
        assert np.all(alpha_out.sum(axis=-1) <= 1.0 + 1e-12)  # limiter holds
        s.mass, _ = advect(s.mass, alpha_out)
        assert s.mass.min() >= 0.0


def test_blob_translates_under_directional_field() -> None:
    """Q6: a purely rightward attention field moves a mass blob right —
    movement is emergent from transport, with no hand-coded move action."""
    h = w = 32
    mass = np.zeros((h, w))
    mass[14:18, 6:10] = 1.0  # blob on the left
    cols = np.arange(w)

    def centroid_col(m):
        return float((m.sum(axis=0) * cols).sum() / m.sum())

    c0 = centroid_col(mass)
    alpha_out = np.zeros((h, w, 4))
    alpha_out[:, :, 3] = 1.0  # direction 3 = right, gain 1 → full translation
    for _ in range(8):
        mass, _ = advect(mass, alpha_out)
    assert centroid_col(mass) > c0 + 6.0  # moved ~8 cells right
    assert np.isclose(mass.sum(), (18 - 14) * (10 - 6), atol=1e-9)  # conserved
