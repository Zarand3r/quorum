"""Per-step cost must scale sub-quadratically with bead count.

The force field materialized the FULL (n, n) attention matrix every step and then read only the
neighbour pairs from it. At 13 336 beads that is 178 million entries, and it cost 92% of the entire
runtime: the explicit-solvent membrane ran at 1.01 steps/s against 100 steps/s for a 1500-bead implicit
one, roughly 70x worse than linear. Evaluating the same query-key inner product only on the pairs that
can contribute gave 9.54 steps/s, a 9.4x speedup, with values identical to 2.8e-17.

The existing performance test pins throughput at ONE size, so it could not see this: a quadratic term
is invisible until the system is large. This gate compares two sizes, which is the only way a scaling
defect shows up.
"""

from __future__ import annotations

import time

import numpy as np

from _mixture import build
from field import Field


def _per_step(n_lip, n_water, L, reps=6):
    X, species, bonds, mols, wi, chains = build(0, n_lip, n_water, L, 2, plant="random",
                                                branched=True, seed=0)
    f = Field(species, bonds, L)
    f.forces(X)                                    # warm the neighbour list
    t0 = time.perf_counter()
    for _ in range(reps):
        f.forces(X)
    return (time.perf_counter() - t0) / reps, len(X)


def test_cost_grows_sub_quadratically_with_bead_count():
    """4x the beads at fixed density must cost far less than 16x. Quadratic would be ~16x."""
    t_small, n_small = _per_step(60, 900, 40.0)
    t_big, n_big = _per_step(240, 3600, 80.0)
    grow = n_big / n_small
    ratio = t_big / t_small
    assert ratio < 0.35 * grow ** 2, (
        f"{n_small} -> {n_big} beads ({grow:.1f}x) cost {ratio:.1f}x; "
        f"quadratic would be {grow ** 2:.1f}x -- the dense (n,n) path is back")


def test_pairwise_content_matches_the_full_attention_matrix():
    """The optimization must not change the physics: same inner product, fewer evaluations."""
    X, species, bonds, mols, wi, chains = build(0, 40, 300, 30.0, 2, plant="random",
                                                branched=True, seed=0)
    f = Field(species, bonds, 30.0)
    d, r, iu = f._pairs(X)
    assert np.abs(f.content()[iu] - f.content_pairs(*iu)).max() < 1e-12
