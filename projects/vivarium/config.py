"""Config for vivarium (dock-and-morph dynamics substrate).

A frozen dataclass of the substrate's knobs. The per-agent embedding `x_i ∈ ℝ^d`
splits into three channel groups, *derived* from `d` and `n_harmonics`:

    position  (pos_dim = 2)              where the agent sits — moved by NEIGHBOUR FORCES
    shape     (shape_dim = 2·n_harmonics) the grounded contour C = z·W_c (drawn blob)
    hidden    (hidden_dim)                working memory

Motion (position) comes from attract/repel forces from neighbours — attract to
complementary neighbours (the dock score), repel at short range — so with no
neighbours an agent does not move (P6 holds by construction). The shape/hidden
sub-embedding `z` morphs through the block (induced-fit conformational change).

Validation fails fast: a `d` too small to host all three channels, or a
neighbourhood ≥ the population, is a construction error, not a clamp.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

POS_DIM = 2  # DEFAULT dish dimensionality (legacy engines import this). Per-config `pos_dim` wins:
#   set pos_dim=3 for a 3-D dish. Only pack.py / polar_pack.py honour it; block/pure stay 2-D.


@dataclass(frozen=True)
class VivariumConfig:
    N: int              # number of agents (bacteria)
    d: int              # embedding dim per agent
    n_harmonics: int    # K — angular harmonics of the grounded contour (shape_dim = 2K)
    n_neighbors: int    # k — local neighbourhood size (k-NN), must be < N
    dist_lambda: float  # λ in dock − λ‖Δp‖²  (attention locality strength)
    force_attract: float  # γ_a — pull toward complementary (attention-weighted) neighbours
    force_repel: float    # γ_r — short-range excluded-volume repulsion
    force_chase: float    # γ_c — NON-RECIPROCAL transport (A−Aᵀ): i chases j but not vice versa
    force_typed: float    # γ_t — Particle-Life typed force: persistent non-reciprocal K[type_i,type_j]
    n_types: int          # number of agent types for the typed force (Dale's-principle / E–I)
    pos_dim: int        # 2 = flat dish, 3 = volumetric dish. In 3-D the contour switches from
    #   circular harmonics {cos kθ, sin kθ} to REAL SPHERICAL HARMONICS Y_lm — the same grounded
    #   readout ⟨C, basis(bearing)⟩, one dimension up (see docs/BILAYER_REVIEW.md).
    momentum: float     # velocity inertia in [0,1): smooths jittery force into coherent motion
    morph_spin: float   # skew/rotational gain on the morph z (non-settling; keeps shape morphing)
    pos_bound: float    # dish half-size; positions are clipped to [−pos_bound, pos_bound] (P7)
    seed: int

    @property
    def shape_dim(self) -> int:
        # 2-D: 2K coefficients (a_k, b_k) for k=1..K.
        # 3-D: real spherical harmonics l=1..K → Σ(2l+1) = K(K+2) coefficients.
        # l=0 / k=0 is deliberately absent from BOTH: the contour is the charge DEVIATION (net
        # neutral). Physical size lives in its own radius channel (pack.py: rad_idx).
        return 2 * self.n_harmonics if self.pos_dim == 2 else self.n_harmonics * (self.n_harmonics + 2)

    @property
    def hidden_dim(self) -> int:
        return self.d - self.pos_dim - self.shape_dim

    @property
    def z_dim(self) -> int:
        """The morphing sub-embedding (shape + hidden) = everything but position."""
        return self.d - self.pos_dim


DEFAULTS: dict = {
    "N": 64,
    "d": 16,
    "n_harmonics": 3,   # shape_dim = 6 → hidden_dim = 16 − 2 − 6 = 8
    "n_neighbors": 8,
    "dist_lambda": 0.5,
    "force_attract": 0.1,
    "force_repel": 0.05,
    "force_chase": 0.0,
    "force_typed": 0.0,
    "n_types": 4,
    "pos_dim": 2,
    "momentum": 0.0,
    "morph_spin": 0.1,
    "pos_bound": 6.0,
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
        pos_dim=int(merged["pos_dim"]),
        dist_lambda=float(merged["dist_lambda"]),
        force_attract=float(merged["force_attract"]),
        force_repel=float(merged["force_repel"]),
        force_chase=float(merged["force_chase"]),
        force_typed=float(merged["force_typed"]),
        n_types=int(merged["n_types"]),
        momentum=float(merged["momentum"]),
        morph_spin=float(merged["morph_spin"]),
        pos_bound=float(merged["pos_bound"]),
        seed=int(merged["seed"]),
    )
    _validate(cfg)
    return cfg


def save_config(cfg: VivariumConfig, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(asdict(cfg), sort_keys=True))


def _validate(cfg: VivariumConfig) -> None:
    if cfg.N < 2:
        raise ValueError("N must be ≥ 2 (a population needs at least two agents)")
    if cfg.pos_dim not in (2, 3):
        raise ValueError(f"pos_dim must be 2 or 3; got {cfg.pos_dim}")
    if cfg.n_harmonics < 1:
        raise ValueError("n_harmonics must be ≥ 1")
    if cfg.hidden_dim < 1:
        raise ValueError(
            f"d={cfg.d} too small: pos({cfg.pos_dim}) + shape({cfg.shape_dim}) leaves "
            f"hidden_dim={cfg.hidden_dim} < 1 — raise d or lower n_harmonics"
        )
    if not (1 <= cfg.n_neighbors < cfg.N):
        raise ValueError(f"n_neighbors must be in [1, N) = [1, {cfg.N}); got {cfg.n_neighbors}")
    for name in ("dist_lambda", "force_attract", "force_repel", "force_chase", "force_typed", "morph_spin"):
        if getattr(cfg, name) < 0.0:
            raise ValueError(f"{name} must be ≥ 0")
    if cfg.n_types < 1:
        raise ValueError("n_types must be ≥ 1")
    if cfg.pos_bound <= 0.0:
        raise ValueError("pos_bound must be > 0")
    if not (0.0 <= cfg.momentum < 1.0):
        raise ValueError("momentum must be in [0, 1)")
