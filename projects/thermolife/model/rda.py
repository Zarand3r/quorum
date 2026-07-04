"""The reaction-diffusion-advection tick (M2.3, PLAN.md §10.5) — the transformer
Game-of-Life step, one batched synchronous pass over the whole grid:

    hidden ← (1−leak)·hidden + D_c·∇²hidden + F_θ(hidden, message, mass)
    mass   ← advect(mass, gain·attention)

All terms are computed from ``state_t`` and written into fresh arrays (double-
buffered, synchrony I7/Q5). A small ``leak`` relaxes hidden toward zero
(homeostasis) so the fixed-random genome stays bounded over long runs.
"""

from __future__ import annotations

import numpy as np

from model.advection import advect, advection_weights
from model.attention import interface_heads, neighbor_attention
from model.config import ModelConfig
from model.genome import Genome
from model.reaction import reaction
from model.state import NCAState

_LEAK = 0.02  # hidden-state relaxation (homeostasis; keeps fixed-θ runs bounded)


def _laplacian_periodic(field: np.ndarray) -> np.ndarray:
    """5-point Laplacian on a toroidal grid (per channel), via np.roll."""
    return (
        np.roll(field, 1, axis=0)
        + np.roll(field, -1, axis=0)
        + np.roll(field, 1, axis=1)
        + np.roll(field, -1, axis=1)
        - 4.0 * field
    )


def rda_step(state: NCAState, g: Genome, cfg: ModelConfig) -> tuple[NCAState, float]:
    """Advance one tick. Returns (new_state, mass moved by advection)."""
    hidden, mass = state.hidden, state.mass

    # coupling operator (from state_t)
    ligand, receptor, value = interface_heads(hidden, g)
    alpha, message = neighbor_attention(ligand, receptor, value, cfg)

    # (1) diffusion (per-channel Turing knob) + (3) reaction (morph) + leak
    lap = _laplacian_periodic(hidden)
    diffusivity = np.asarray(cfg.diffusivity)
    new_hidden = (
        (1.0 - _LEAK) * hidden
        + lap * diffusivity
        + reaction(hidden, message, mass, g, cfg)
    )

    # (2) advection (movement) — conserved
    alpha_out = advection_weights(alpha, cfg.advection_gain)
    new_mass, moved = advect(mass, alpha_out)

    return NCAState(hidden=new_hidden, mass=new_mass, tick=state.tick + 1), moved
