"""Conserved attention advection — movement (M2.2, PLAN.md §10.5, gates Q1/Q2).

Attention routes *conserved mass*: cell i sends fraction ``alpha_out[i,d]`` of its
mass to neighbor d. On a toroidal grid (periodic ``np.roll``) total mass is
preserved exactly — every unit that leaves a cell arrives at exactly one other.
The **flux limiter** (Σ_d alpha_out ≤ 1, alpha_out ≥ 0) guarantees non-negativity:
``new_mass[i] = mass[i]·(1 − Σ_d alpha_out) + inflow`` with both terms ≥ 0.

This is the discrete transport (advection) term −∇·(𝐯·mass); the velocity 𝐯 is
attention (the direction of strongest ligand/receptor match).
"""

from __future__ import annotations

import numpy as np

from model.attention import DIRS


def advection_weights(alpha: np.ndarray, gain: float) -> np.ndarray:
    """Turn softmax attention (sums to 1 over directions) into flux fractions.

    ``gain`` ∈ [0,1] is the max fraction of a cell's mass that may move per tick,
    so ``Σ_d alpha_out = gain ≤ 1`` — the flux limiter holds by construction.
    """
    return gain * alpha


def advect(mass: np.ndarray, alpha_out: np.ndarray) -> tuple[np.ndarray, float]:
    """Move mass along ``alpha_out`` (periodic). Returns (new_mass, total moved).

    Conserves ``mass.sum()`` exactly and stays non-negative when the flux limiter
    (``alpha_out ≥ 0``, ``Σ_d alpha_out ≤ 1``) holds.
    """
    new_mass = mass * (1.0 - alpha_out.sum(axis=-1))
    moved = 0.0
    for d, off in enumerate(DIRS):
        out_d = alpha_out[:, :, d] * mass
        new_mass = new_mass + np.roll(out_d, shift=(off[0], off[1]), axis=(0, 1))
        moved += float(out_d.sum())
    return new_mass, moved
