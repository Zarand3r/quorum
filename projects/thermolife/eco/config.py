"""Config for the E0 viability substrate (IMPLEMENTATION_PLAN.md Step 0).

Pure numpy, no torch. Loaded from ``configs/eco.yaml``. Every field is a physical
knob of the conserved economy; the drift speed ``drift_v`` is the E0-gate knob (P8):
below a critical value a forager tracks the source and lives, above it the population
falls behind and starves, while a frozen control starves at any speed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class EcoConfig:
    d: int             # embedding-space dim (position lives in R^d — NO grid, P3)
    d_g: int           # interface-gene dim (heredity; inert at E0, drives Q/K at E1)
    n_init: int        # initial population
    n_max: int         # hard population cap (P6)
    seed: int

    # resource economy
    inject: float      # S — resource injected into the pool each tick
    sigma_r: float     # harvest locality width (Gaussian around the source)
    harvest_rate: float  # max uptake per token per tick at weight 1
    eta: float         # harvest efficiency in (0,1]; (1-eta) is dissipated

    # costs (energy out → dissipated)
    c_base: float      # metabolic drain per tick (existing is not free)
    c_move: float      # kinetic cost coefficient: cost = c_move * ||dx||^2
    e_init: float      # starting energy per token
    e_div: float       # reproduction threshold

    # source drift (P8) — an orbit so the source stays bounded but never rests
    orbit_radius: float
    drift_v: float     # linear speed of the source along its orbit (THE gate knob)

    # hand-forager policy (E0)
    forager_gain: float  # step = gain * (mu - x), clipped to max_step
    max_step: float      # max displacement per tick (bounds a forager's top speed)

    # reproduction
    repro_pos_noise: float  # offspring position jitter
    sigma_g: float          # gene mutation std on reproduction

    # E1 interaction operator (RESEARCH_HK.md: distance-penalized dock attention)
    dist_lambda: float       # locality strength λ in s = dock − λ‖Δx‖² (0 = global softmax)
    hk_tau: float            # HK control-arm threshold (measured control only, not default)
    transfer_frac_max: float # max fraction of a token's energy sendable per tick


_DEFAULTS: dict = {
    "d": 4,
    "d_g": 2,
    "n_init": 24,
    "n_max": 256,
    "seed": 0,
    "inject": 6.0,
    "sigma_r": 0.6,
    "harvest_rate": 0.6,
    "eta": 0.85,
    "c_base": 0.02,
    "c_move": 0.20,
    "e_init": 1.0,
    "e_div": 3.0,
    "orbit_radius": 2.0,
    "drift_v": 0.06,
    "forager_gain": 0.5,
    "max_step": 0.20,
    "repro_pos_noise": 0.03,
    "sigma_g": 0.05,
    "dist_lambda": 0.5,
    "hk_tau": 0.5,
    "transfer_frac_max": 0.25,
}


def load_eco_config(path: str | Path) -> EcoConfig:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    d = {**_DEFAULTS, **{k: raw[k] for k in _DEFAULTS if k in raw}}
    cfg = EcoConfig(
        d=int(d["d"]),
        d_g=int(d["d_g"]),
        n_init=int(d["n_init"]),
        n_max=int(d["n_max"]),
        seed=int(d["seed"]),
        inject=float(d["inject"]),
        sigma_r=float(d["sigma_r"]),
        harvest_rate=float(d["harvest_rate"]),
        eta=float(d["eta"]),
        c_base=float(d["c_base"]),
        c_move=float(d["c_move"]),
        e_init=float(d["e_init"]),
        e_div=float(d["e_div"]),
        orbit_radius=float(d["orbit_radius"]),
        drift_v=float(d["drift_v"]),
        forager_gain=float(d["forager_gain"]),
        max_step=float(d["max_step"]),
        repro_pos_noise=float(d["repro_pos_noise"]),
        sigma_g=float(d["sigma_g"]),
        dist_lambda=float(d["dist_lambda"]),
        hk_tau=float(d["hk_tau"]),
        transfer_frac_max=float(d["transfer_frac_max"]),
    )
    _validate(cfg)
    return cfg


def _validate(cfg: EcoConfig) -> None:
    if cfg.d < 2:
        raise ValueError("d must be ≥ 2 (source orbit + 2D projection need two dims)")
    if cfg.d_g < 1:
        raise ValueError("d_g must be ≥ 1")
    if not (0.0 < cfg.eta <= 1.0):
        raise ValueError("eta must be in (0, 1]")
    if cfg.n_init > cfg.n_max:
        raise ValueError("n_init must be ≤ n_max")
    if cfg.e_div <= cfg.e_init:
        raise ValueError("e_div must exceed e_init or nothing ever forages before splitting")
    for name in ("inject", "harvest_rate", "c_base", "c_move", "max_step"):
        if getattr(cfg, name) < 0.0:
            raise ValueError(f"{name} must be ≥ 0")
    if cfg.sigma_r <= 0.0:
        # sigma_r divides the harvest weight AND the chemotaxis sense gradient;
        # 0 → division by zero → NaN energy that silently corrupts the ledger.
        # Fail fast at load rather than degrade silently.
        raise ValueError("sigma_r must be > 0 (it is a Gaussian width; 0 → NaN energy)")
    if not (0.0 <= cfg.transfer_frac_max < 1.0):
        raise ValueError("transfer_frac_max must be in [0, 1) — a token cannot send "
                         "more than it has")
