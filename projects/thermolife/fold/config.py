"""Config for the embedding-folding toy transformer (PLAN.md §4, §7).

Pure numpy mechanism (S0): no torch. Loaded from ``configs/fold.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FoldConfig:
    n_tokens: int          # N
    d: int                 # embedding dim (small; "minimal")
    k_harmonics: int       # K angular harmonics → contour coeff dim 2K
    tie_weights: bool      # weight-tied iteration (one repeated map) vs per-layer
    use_mlp: bool          # pointwise block after attention
    mlp_width: int
    seed: int
    rho0: float            # base contour radius
    amp: float             # harmonic amplitude scale (keeps blobs gentle)
    r_min: float           # clamp radius ≥ r_min so the blob stays renderable
    render_scale: float    # blob size in the position plane
    init_scale: float      # embedding init std
    contour_points: int    # samples per contour polyline (P)
    edge_threshold: float  # min attention weight to draw a bond
    reseed_on_converge: bool     # once a fold settles, start a fresh one (fold gallery)
    converge_eps: float          # fold_step below this ⇒ converged
    min_iters_before_reseed: int # show each fold at least this many iterations


_DEFAULTS: dict = {
    "n_tokens": 8,
    "d": 4,
    "k_harmonics": 4,
    "tie_weights": True,
    "use_mlp": True,
    "mlp_width": 16,
    "seed": 0,
    "rho0": 1.0,
    "amp": 0.5,
    "r_min": 0.05,
    "render_scale": 0.5,
    "init_scale": 1.5,
    "contour_points": 64,
    "edge_threshold": 0.15,
    "reseed_on_converge": True,
    "converge_eps": 1e-3,
    "min_iters_before_reseed": 40,
}


def load_fold_config(path: str | Path) -> FoldConfig:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    d = {**_DEFAULTS, **{k: raw[k] for k in _DEFAULTS if k in raw}}
    cfg = FoldConfig(
        n_tokens=int(d["n_tokens"]),
        d=int(d["d"]),
        k_harmonics=int(d["k_harmonics"]),
        tie_weights=bool(d["tie_weights"]),
        use_mlp=bool(d["use_mlp"]),
        mlp_width=int(d["mlp_width"]),
        seed=int(d["seed"]),
        rho0=float(d["rho0"]),
        amp=float(d["amp"]),
        r_min=float(d["r_min"]),
        render_scale=float(d["render_scale"]),
        init_scale=float(d["init_scale"]),
        contour_points=int(d["contour_points"]),
        edge_threshold=float(d["edge_threshold"]),
        reseed_on_converge=bool(d["reseed_on_converge"]),
        converge_eps=float(d["converge_eps"]),
        min_iters_before_reseed=int(d["min_iters_before_reseed"]),
    )
    if cfg.d < 2:
        raise ValueError("d must be ≥ 2 (a 2D position projection is needed)")
    if cfg.k_harmonics < 1:
        raise ValueError("k_harmonics must be ≥ 1")
    if cfg.contour_points < 8:
        raise ValueError("contour_points must be ≥ 8 to render a blob")
    return cfg
