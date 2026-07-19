"""Step 0 — config load / validate / round-trip (IMPLEMENTATION_PLAN.md Step 0).

`VivariumConfig` is a frozen dataclass; the channel split (position / shape /
hidden) is *derived* from `d` and `n_harmonics`, so validation must fail fast
when `d` is too small to host all three, or when the neighbourhood is bigger
than the population.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import DEFAULTS, VivariumConfig, load_config, save_config


def test_defaults_load() -> None:
    cfg = load_config_from_dict({})
    assert cfg.N == DEFAULTS["N"]
    assert cfg.hidden_dim >= 1
    # channels partition d exactly.
    assert cfg.pos_dim + cfg.shape_dim + cfg.hidden_dim == cfg.d


def test_channel_split_derives_from_harmonics() -> None:
    cfg = load_config_from_dict({"d": 16, "n_harmonics": 3})
    assert cfg.pos_dim == 2
    assert cfg.shape_dim == 6  # 2 * n_harmonics
    assert cfg.hidden_dim == 8


def test_rejects_d_too_small_for_channels() -> None:
    with pytest.raises(ValueError, match="hidden"):
        load_config_from_dict({"d": 8, "n_harmonics": 3})  # 2 + 6 = 8 → hidden 0


def test_rejects_neighbourhood_ge_population() -> None:
    with pytest.raises(ValueError, match="n_neighbors"):
        load_config_from_dict({"N": 8, "n_neighbors": 8})


def test_rejects_negative_knobs() -> None:
    with pytest.raises(ValueError):
        load_config_from_dict({"force_attract": -0.1})


def test_roundtrip(tmp_path: Path) -> None:
    cfg = load_config_from_dict({"N": 32, "d": 12, "n_harmonics": 2, "n_neighbors": 6})
    p = tmp_path / "cfg.yaml"
    save_config(cfg, p)
    assert load_config(p) == cfg


# --- helper: build a config from an override dict via a temp file --------------
def load_config_from_dict(overrides: dict) -> VivariumConfig:
    import tempfile

    import yaml

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(overrides, f)
        path = f.name
    return load_config(path)
