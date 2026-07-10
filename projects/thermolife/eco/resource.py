"""Resource access + harvest (IMPLEMENTATION_PLAN.md Step 2).

The pool is global but access is *local*: a token harvests in proportion to a Gaussian
of its distance to the source (far tokens get ≈0 — the locality that makes drift lethal,
P8). Demand across tokens is scaled down when it exceeds the pool, so a finite resource
is genuinely *competed* for (depletable — crowding near the source is self-limiting).
All energy movement is booked so the ledger closes exactly (P1).
"""

from __future__ import annotations

import numpy as np

from eco.config import EcoConfig


def access_weight(x: np.ndarray, mu: np.ndarray, sigma_r: float) -> np.ndarray:
    """Per-token harvest weight in (0, 1]: exp(-||x-mu||^2 / 2σ_r^2). Vectorized."""
    d2 = np.sum((x - mu) ** 2, axis=1)
    return np.exp(-d2 / (2.0 * sigma_r * sigma_r))


def harvest(
    x: np.ndarray,
    mu: np.ndarray,
    pool: float,
    gate: np.ndarray,
    cfg: EcoConfig,
) -> tuple[np.ndarray, float, float]:
    """Compute per-token energy uptake from the pool this tick.

    ``gate`` ∈ [0,1]^N is the policy's harvest intent per token. Returns
    ``(delta_e, pool_drawn, dissipated)`` where ``delta_e`` is energy credited to
    tokens (η share), ``pool_drawn`` leaves the pool, and ``dissipated`` is the
    (1-η) inefficiency. Conserves exactly: pool_drawn == sum(delta_e) + dissipated.
    """
    w = access_weight(x, mu, cfg.sigma_r)
    demand = cfg.harvest_rate * w * gate            # [N]
    total_demand = float(np.sum(demand))
    if total_demand <= 0.0:
        return np.zeros_like(demand), 0.0, 0.0
    scale = min(1.0, pool / total_demand)           # depletable: Σuptake ≤ pool
    uptake = demand * scale                         # [N]
    drawn = float(np.sum(uptake))
    delta_e = cfg.eta * uptake
    dissipated = (1.0 - cfg.eta) * drawn
    return delta_e, drawn, dissipated
