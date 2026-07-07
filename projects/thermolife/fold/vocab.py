"""Lock-and-key vocabulary + synthetic scenes (M2, PLAN.md §8).

The vocabulary is K complementary pairs → 2K token *types*, each with a learned
base embedding. A training **scene** is all K pairs present in shuffled order,
each token's start embedding = its type embedding + Gaussian noise. There is no
positional encoding, so the fold can only identify a partner by *content* — the
noise forces it to actually denoise/morph toward canonical shapes rather than
memorize vectors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VocabConfig:
    n_pairs: int      # K → 2K token types, N = 2K tokens per scene
    d: int            # embedding dim (matches FoldConfig.d)
    noise_sigma: float  # per-token start noise (the denoising pressure)
    init_scale: float   # base-embedding init std


def init_type_embeddings(cfg: VocabConfig, seed: int) -> np.ndarray:
    """[2K, d] learnable base embeddings; types 2p and 2p+1 are pair p."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((2 * cfg.n_pairs, cfg.d)) * cfg.init_scale


def partner_of(types: np.ndarray) -> np.ndarray:
    """Partner *type* id for each type id (2p ↔ 2p+1)."""
    return types ^ 1


def sample_scene(
    cfg: VocabConfig, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """One scene: all K pairs in shuffled order + per-token noise.

    Returns (types [N] type ids, partner [N] scene index of each token's
    partner, noise [N,d]). The start embeddings are assembled by
    :func:`scene_embed` — *inside* the differentiable path, so gradients reach
    the vocabulary's base embeddings.
    """
    n = 2 * cfg.n_pairs
    types = rng.permutation(n)                      # every type exactly once
    noise = rng.standard_normal((n, cfg.d))
    # scene position of each token's partner type
    pos_of_type = np.empty(n, dtype=np.int64)
    pos_of_type[types] = np.arange(n)
    partner = pos_of_type[partner_of(types)]
    return types, partner, noise


def scene_embed(e_types, types, noise, sigma: float):
    """X0 = e_types[types] + σ·noise. Plain indexing/adds so it works under
    both numpy (engine) and autograd (training)."""
    return e_types[types] + sigma * noise
