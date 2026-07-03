"""Field physics: vectorized diffusion, decay, cooling, and source injection.

All operations are whole-grid array ops (no per-cell loop, P6). Diffusion uses a
5-point Laplacian with zero-flux (Neumann) boundaries, so a pure-diffusion step
conserves total field mass to float tolerance (P1) and, for ``D <= 0.25``, is a
convex combination of non-negative inputs, hence non-negativity-preserving (P2).

Ledger note (PLAN.md I1): the conservation ledger tracks nutrient + energy +
waste only. Heat is dissipative stress (cooled toward ambient), not a conserved
quantity, so cooling is *not* booked. The single ledger-relevant sink here is
waste decay; :func:`diffuse_and_decay` returns the waste removed so the caller
(the tick loop) can book it.
"""

from __future__ import annotations

import numpy as np

from env.config import WorldConfig
from env.fields import Field, World


def laplacian(a: np.ndarray) -> np.ndarray:
    """5-point discrete Laplacian with zero-flux (edge-replicated) boundaries.

    Sum over the grid is ~0 (discrete no-flux divergence theorem), so
    ``a + D*laplacian(a)`` conserves total mass.
    """
    p = np.pad(a, 1, mode="edge")
    return p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4.0 * a


def inject_sources(world: World, tick: int) -> float:
    """Inject the scenario nutrient source for this tick; returns amount injected.

    A static source injects ``rate`` into each cell within ``radius`` of
    ``(cx, cy)`` until ``removal_tick`` (the Slice-0 gate, PLAN.md §15.2), after
    which it is off. Returns the total nutrient added (a ledger source, I1).
    """
    src = world.cfg.scenario.source
    if not src or src.get("kind") != "static":
        return 0.0
    removal = world.cfg.scenario.removal_tick
    if removal is not None and tick >= removal:
        return 0.0

    cx, cy = int(src["cx"]), int(src["cy"])
    radius = int(src["radius"])
    rate = float(src["rate"])
    yy, xx = np.ogrid[: world.height, : world.width]
    mask = (yy - cx) ** 2 + (xx - cy) ** 2 <= radius**2
    world.fields[:, :, Field.NUTRIENT] += rate * mask
    return float(rate * mask.sum())


def diffuse_and_decay(world: World, cfg: WorldConfig) -> float:
    """Diffuse every field, decay waste/pheromone, cool heat toward ambient.

    Mutates ``world.fields`` in place. Returns the amount of **waste** removed by
    decay (the only conservation-ledger sink in this step, PLAN.md I1).
    """
    f = world.fields
    fc = cfg.fields

    # Diffusion (mass-conserving) for every channel.
    for name, idx in (
        ("nutrient", Field.NUTRIENT),
        ("waste", Field.WASTE),
        ("heat", Field.HEAT),
        ("pheromone", Field.PHEROMONE),
    ):
        f[:, :, idx] += fc[name].diffusion * laplacian(f[:, :, idx])

    # Waste decay — a named ledger sink.
    waste = f[:, :, Field.WASTE]
    waste_decayed = float(fc["waste"].decay * waste.sum())
    waste *= 1.0 - fc["waste"].decay

    # Pheromone decay (not in the conservation ledger — signal, not mass).
    f[:, :, Field.PHEROMONE] *= 1.0 - fc["pheromone"].decay

    # Heat cooling toward ambient (dissipative stress, not conserved).
    heat = f[:, :, Field.HEAT]
    heat -= fc["heat"].decay * (heat - fc["heat"].ambient)

    return waste_decayed
