"""The ``World`` state — dense SoA arrays for the Slice-0 substrate.

PLAN.md §6 lists a full world tensor (hidden/plastic/orient cell channels for
the NCA). Slice 0 is the *physical substrate only* (PLAN.md §15.3 defers
everything learned), so this ``World`` carries just what the physics and the
hand-coded forager read: the physical fields, per-cell stored energy, and an
alive mask. The hidden/plastic/orient channels enter at M2 with the NCA rule.

Everything is a pure function ``World -> World`` downstream; ``World`` is the
single mutable state, double-buffered by the tick loop for synchrony (I7).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum

import numpy as np

from env.config import WorldConfig

DTYPE = np.float64  # conservation headroom over long horizons (IMPLEMENTATION_PLAN §D4)


class Field(IntEnum):
    """Index of each physical channel in ``World.fields[:, :, c]``."""

    NUTRIENT = 0
    WASTE = 1
    HEAT = 2
    PHEROMONE = 3


N_FIELDS = len(Field)
FIELD_NAMES: tuple[str, ...] = ("nutrient", "waste", "heat", "pheromone")


@dataclass
class World:
    """Single mutable simulation state (SoA over the grid)."""

    fields: np.ndarray  # [H, W, N_FIELDS] float64
    energy: np.ndarray  # [H, W] float64  — per-cell stored energy reserve
    alive: np.ndarray   # [H, W] float64  — alive-probability in [0, 1]
    tick: int
    cfg: WorldConfig
    rng: np.random.Generator

    @property
    def height(self) -> int:
        return self.fields.shape[0]

    @property
    def width(self) -> int:
        return self.fields.shape[1]

    def copy(self) -> "World":
        """Deep copy of the mutable arrays (config is immutable, rng is shared-by-ref
        intentionally: the tick loop owns rng advancement)."""
        return replace(
            self,
            fields=self.fields.copy(),
            energy=self.energy.copy(),
            alive=self.alive.copy(),
        )

    def state_hash(self) -> str:
        """Stable content hash of the trajectory-relevant state (P5, PLAN.md I8).

        Excludes ``rng`` and ``cfg`` (not part of the observable world state);
        includes ``tick`` so two worlds at different ticks never collide.
        """
        import hashlib

        h = hashlib.sha256()
        h.update(np.ascontiguousarray(self.fields).tobytes())
        h.update(np.ascontiguousarray(self.energy).tobytes())
        h.update(np.ascontiguousarray(self.alive).tobytes())
        h.update(np.int64(self.tick).tobytes())
        return h.hexdigest()


def _forager_start(cfg: WorldConfig) -> tuple[int, int]:
    """Where the single Slice-0 forager is seeded.

    Static source: a few cells off ``(cx, cy)`` so it must climb the gradient.
    Moving source: at the orbit's tick-0 center so it starts fed and then chases.
    """
    src = cfg.scenario.source
    if src and src.get("kind") == "moving":
        orbit = float(src.get("orbit_radius", min(cfg.height, cfg.width) / 4.0))
        r = int(round(cfg.height / 2.0 + orbit))  # cos(0)=1
        c = int(round(cfg.width / 2.0))           # sin(0)=0
        return (min(max(r, 0), cfg.height - 1), min(max(c, 0), cfg.width - 1))
    if src and "cx" in src and "cy" in src:
        cx, cy = int(src["cx"]), int(src["cy"])
        return (min(cx + 3, cfg.height - 1), min(cy + 3, cfg.width - 1))
    return (cfg.height // 2, cfg.width // 2)


def from_config(cfg: WorldConfig, seed: int | None = None) -> World:
    """Construct the initial world deterministically from a config + seed.

    Fields start at zero except heat, which starts at its ambient (the cooling
    target). One forager is placed with a small initial energy buffer; the
    nutrient gradient builds over the first ticks as the source injects.
    """
    h, w = cfg.height, cfg.width
    fields = np.zeros((h, w, N_FIELDS), dtype=DTYPE)
    fields[:, :, Field.HEAT] = cfg.fields["heat"].ambient

    energy = np.zeros((h, w), dtype=DTYPE)
    alive = np.zeros((h, w), dtype=DTYPE)

    fy, fx = _forager_start(cfg)
    alive[fy, fx] = 1.0
    energy[fy, fx] = 1.0  # initial buffer; tuned in Step 5 so removal → death

    rng_seed = cfg.seed if seed is None else seed
    return World(
        fields=fields,
        energy=energy,
        alive=alive,
        tick=0,
        cfg=cfg,
        rng=np.random.default_rng(rng_seed),
    )
