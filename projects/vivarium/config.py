"""Config for vivarium (IMPLEMENTATION_PLAN.md Step 0).

A frozen dataclass of the substrate's knobs. The per-agent embedding `x_i ∈ ℝ^d`
splits into three channel groups, *derived* from `d` and `n_harmonics`:

    position  (pos_dim = 2)              where the agent sits in the 2-D dish
    shape     (shape_dim = 2·n_harmonics) the grounded contour C = x·W_c (drawn blob)
    hidden    (hidden_dim = d − 2 − 2K)   working memory for talking to neighbours

Validation fails fast (a core rule): a `d` too small to host all three channels,
or a neighbourhood ≥ the population, is a construction error, not a clamp.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

POS_DIM = 2  # the dish is 2-D; position always occupies the first two channels


@dataclass(frozen=True)
class VivariumConfig:
    N: int              # number of agents (bacteria / tokens)
    d: int              # embedding dim per agent
    n_harmonics: int    # K — angular harmonics of the grounded contour (shape_dim = 2K)
    n_neighbors: int    # k — local attention neighbourhood size (k-NN), must be < N
    dist_lambda: float  # λ in s = dock − λ‖Δp‖²  (locality strength; 0 = global softmax)
    drift_rate: float   # speed of the slow external field s(t) (the "season"; the J drive)
    lr: float           # local plasticity step size (used at M1)
    anticollapse: float # β — local diversity term strength in the plasticity (M2; 0 = off)
    seed: int

    @property
    def pos_dim(self) -> int:
        return POS_DIM

    @property
    def shape_dim(self) -> int:
        return 2 * self.n_harmonics

    @property
    def hidden_dim(self) -> int:
        return self.d - self.pos_dim - self.shape_dim


DEFAULTS: dict = {
    "N": 64,
    "d": 16,
    "n_harmonics": 3,   # shape_dim = 6 → hidden_dim = 16 − 2 − 6 = 8
    "n_neighbors": 8,
    "dist_lambda": 0.5,
    "drift_rate": 0.02,
    "lr": 0.05,
    "anticollapse": 0.0,
    "seed": 0,
}


def load_config(path: str | Path) -> VivariumConfig:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    merged = {**DEFAULTS, **{k: raw[k] for k in DEFAULTS if k in raw}}
    cfg = VivariumConfig(
        N=int(merged["N"]),
        d=int(merged["d"]),
        n_harmonics=int(merged["n_harmonics"]),
        n_neighbors=int(merged["n_neighbors"]),
        dist_lambda=float(merged["dist_lambda"]),
        drift_rate=float(merged["drift_rate"]),
        lr=float(merged["lr"]),
        anticollapse=float(merged["anticollapse"]),
        seed=int(merged["seed"]),
    )
    _validate(cfg)
    return cfg


def save_config(cfg: VivariumConfig, path: str | Path) -> None:
    # asdict drops the derived properties; only the stored fields round-trip.
    Path(path).write_text(yaml.safe_dump(asdict(cfg), sort_keys=True))


def _validate(cfg: VivariumConfig) -> None:
    if cfg.N < 2:
        raise ValueError("N must be ≥ 2 (a population needs at least two agents)")
    if cfg.n_harmonics < 1:
        raise ValueError("n_harmonics must be ≥ 1")
    if cfg.hidden_dim < 1:
        raise ValueError(
            f"d={cfg.d} too small: pos({cfg.pos_dim}) + shape({cfg.shape_dim}) leaves "
            f"hidden_dim={cfg.hidden_dim} < 1 — raise d or lower n_harmonics"
        )
    if not (1 <= cfg.n_neighbors < cfg.N):
        raise ValueError(f"n_neighbors must be in [1, N) = [1, {cfg.N}); got {cfg.n_neighbors}")
    for name in ("dist_lambda", "drift_rate", "lr", "anticollapse"):
        if getattr(cfg, name) < 0.0:
            raise ValueError(f"{name} must be ≥ 0")
