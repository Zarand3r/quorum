"""The hand-coded Slice-0 forager (PLAN.md §15.1, M1 baseline).

A single forager that climbs the nutrient gradient: each tick it requests
capacity-limited uptake at its own cell and, if a von-Neumann neighbor holds
more nutrient, intends to move there (paying ``cost_move``). It is a pure
function of its local neighborhood (locality, I5) and reads a constant number of
cells — there is no loop over grid cells (P6). Movement is *intended* here and
executed by the tick loop only if the move cost is afforded (P7).
"""

from __future__ import annotations

import numpy as np

from env.config import WorldConfig
from env.fields import Field, World

# Nutrient a forager attempts to take per tick (hand-coded baseline constant).
APPETITE = 0.5

# von-Neumann neighborhood offsets (a constant 4-tuple, not a grid loop).
_NEIGHBORS = ((-1, 0), (1, 0), (0, -1), (0, 1))

Move = tuple[tuple[int, int], tuple[int, int]]  # ((from_y, from_x), (to_y, to_x))


def forager_position(world: World) -> tuple[int, int] | None:
    """Location of the single live forager, or ``None`` if it is dead."""
    idx = np.argwhere(world.alive >= world.cfg.lifecycle.alive_threshold)
    if len(idx) == 0:
        return None
    return int(idx[0, 0]), int(idx[0, 1])


def forager_intents(
    world: World, cfg: WorldConfig
) -> tuple[np.ndarray, np.ndarray, Move | None]:
    """Return ``(uptake_demand[H,W], action_cost[H,W], move_or_None)``.

    Uptake is capped so converted energy cannot exceed ``e_max`` (bounds the
    reserve so source removal is lethal in bounded time). The move targets the
    richest neighbor strictly better than the current cell.
    """
    h, w = world.height, world.width
    uptake = np.zeros((h, w), dtype=world.energy.dtype)
    cost = np.zeros((h, w), dtype=world.energy.dtype)

    pos = forager_position(world)
    if pos is None:
        return uptake, cost, None
    fy, fx = pos

    nutrient = world.fields[:, :, Field.NUTRIENT]
    room = max(0.0, cfg.energy.e_max - float(world.energy[fy, fx]))
    demand = min(APPETITE, room / cfg.energy.eta) if cfg.energy.eta > 0 else 0.0
    uptake[fy, fx] = demand

    best_yx = (fy, fx)
    best_n = float(nutrient[fy, fx])
    for dy, dx in _NEIGHBORS:
        ny, nx = fy + dy, fx + dx
        if 0 <= ny < h and 0 <= nx < w and float(nutrient[ny, nx]) > best_n:
            best_n = float(nutrient[ny, nx])
            best_yx = (ny, nx)

    move: Move | None = None
    if best_yx != (fy, fx):
        cost[fy, fx] = cfg.energy.cost_move
        move = ((fy, fx), best_yx)
    return uptake, cost, move
