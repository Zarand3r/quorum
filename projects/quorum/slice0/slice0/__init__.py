"""Slice 0 of the quorum architecture — LLM Boids on a 32×32 toroidal grid.

Design: PLAN.md §15.1. This is the smallest end-to-end configuration that
produces a real signal (mean-nearest-neighbor distance monotonically lower
under the LLM population than under a uniform-random baseline, Mann-Whitney U
p < 0.01 over ≥10 seeds).

Subpackages / modules (arriving in dependency order):

- ``substrate`` — toroidal grid + agent positions + synchronous step.
- ``actions``   — {N, S, E, W, Z} vocab; single-letter tokens.
- ``prompts``   — flocking-objective prefix (I10) + per-agent local observation (I1, I11).
- ``metrics``   — mean-nearest-neighbor distance + cross-agent decorrelation.
- ``policy``    — Policy protocol + UniformRandomPolicy baseline; LLMPolicy in _llm_policy.py.
- ``runner``    — tick loop; single batched forward pass per tick (I3, I4).
- ``verify``    — Mann-Whitney U + replay-diff harness (merge gate).
- ``main``      — CLI entry.
"""

__version__ = "0.1.0"
