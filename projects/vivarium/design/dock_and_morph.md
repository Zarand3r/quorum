# The dock-and-morph substrate — motion by forces, P6 by construction

> The substrate redesign (2026-07-18) that followed the "flow the rules of life" +
> "attract/repel while morphing" insights. It removes the prediction/plasticity machinery
> entirely and makes the dynamics the rule: **attract/repel forces move agents; the block
> morphs their shape.** This finally makes interaction *load-bearing by construction* — and
> exposes the next real problem: **crystallization**.

## The rule

Each agent's embedding splits into **position** `p` (first 2 channels) and a **morphing
sub-embedding** `z` (shape + hidden). One fixed-rule step:

- **Motion (position) = neighbour forces.** `p ← clip(p + γ_a·(A−I)·p + γ_r·repel(p, A))`:
  attract toward complementary (attention-weighted) neighbours, repel at short range. Both
  forces derive from the interaction graph `A`, so **A = I (identity ablation) ⇒ zero force ⇒
  no motion.** Interaction is load-bearing for the dynamics *by construction*.
- **Morph (z) = the block.** `z ← LN(z + A·V + morph_spin·(z·J_spin)); z ← LN(z + MLP(z))`:
  induced-fit conformational change, with a **skew-symmetric spin** so the shape never settles
  (non-gradient ⇒ no fixed point).
- **Grounded:** the drawn contour `C = z·W_c` is the attention query (P8). Fixed rule on the
  fast clock (no per-tick learning).

## Why this is the right structure (and what every prior attempt got wrong)

Every earlier substrate let an agent move via its own per-agent MLP, so removing interaction
(identity) still left it moving — **P6 kept failing** (the "aliveness" was N independent agents,
or an external drive dragging them). Here motion *only* comes from neighbour forces, so:

- **P6 holds by construction** — verified: `test_identity_ablation_freezes_positions`
  (identity → positions never move; measured motion 0.0000). No seed-dependence, no drift-dragging.
- This is the Particle-Life / Boids / molecular-dynamics structure: **an agent moves because of
  forces from neighbours**, which is *why* interaction is irreducible in those systems.

## The finding: crystallization (the next real problem)

With **symmetric** attract/repel, the colony **settles to a stable packing** — a crystal:
positions reach equilibrium, motion → ~0.01 jitter, **deformation → 0.005** (near-rigid). The
morph-spin keeps `C`/`A` shifting, but small `A`-changes cannot reconfigure a robust packing.
Under the rigorous metric (which requires genuine reconfiguration), measured aliveness → 0.

This is exactly potential_flux's prediction: a **gradient** force system (symmetric forces derive
from a potential) **settles to a minimum → dead.** Getting *sustained active motion* is the
genuine hard problem of artificial life, and it needs one of:

1. **Non-reciprocal forces** — make the interaction asymmetric (i attracts j, j repels i → chase
   dynamics). This is how Particle Life gets moving "cells" and how active matter sustains flow.
   Concretely: an asymmetric complementarity metric `M ≠ Mᵀ`, or an explicit non-reciprocal term.
2. **Self-propulsion** — a persistent intrinsic velocity/heading (active Brownian particles). But
   this risks re-introducing interaction-independent motion (P6 care needed).
3. **Macro selection** — random fixed rules crystallize ~always; *select* the rare rules that
   produce sustained active (non-crystallizing) motion. The base rate is ~0, so selection has a
   crisp target. This is where the slow-clock "learning" (survival/persistence) would earn its keep.

## Status

- **Done + tested (37 tests):** the force-based substrate; P6 by construction; grounded render;
  determinism, boundedness, locality; the strengthened aliveness metric (translation + rotation
  excluded via structure + deformation).
- **Open:** crystallization — symmetric forces settle. Next is non-reciprocal forces (Option 1,
  smallest change) or macro selection (Option 3, the slow-clock learning).

*See also:* [`signalling.md`](signalling.md) (why prediction failed → dock-and-morph),
[`potential_flux.md`](potential_flux.md) (gradient settles / needs non-equilibrium),
[`m2_collapse.md`](m2_collapse.md) (the option lineage).
