# HARD REQUIREMENT — strict transformer-only (2026-07-21)

> **Every dynamical operation in vivarium MUST be a transformer operation.** Adopted as a
> non-negotiable constraint going forward, on the user's instruction. This supersedes the
> softer "mostly transformer" framing in earlier docs.

## What counts as a transformer operation (ALLOWED)

- **Attention** in any form: softmax or linear attention; multi-head; grounded (dock-score)
  attention; **non-reciprocal** attention `A + β(A−Aᵀ)`; masked/local (k-NN) attention.
- **Position-wise MLP** (the reaction / per-token update).
- **LayerNorm** / residual connections.
- **Structured or learned linear maps** that are part of the block: `W_v`, `W_c` (grounded
  contour selection), the complementarity metric `M`, a fixed **skew** matrix `J` (a linear
  architecture mod), per-channel diffusion rates.
- **Architecture modifications** are explicitly permitted — new heads, new linear terms,
  new attention variants — *as long as the operation is attention / MLP / norm / structured
  linear.*
- **Fast-weight plasticity** (weights that learn while alive): permitted, because a Hebbian
  outer-product write `W_fast ← γ·W_fast + η·(kᵀv)` **is the fast-weight form of linear
  attention** (Schlag, Irie, Schmidhuber 2021, "Linear Transformers Are Secretly Fast Weight
  Programmers"; roots in Schmidhuber 1992). The decay `γ` is a gated-linear-attention forget
  gate (homeostasis). So a plastic fast-weight memory read via `z·W_fast` is a linear-attention
  head, not a bolted-on learning rule. **Constraint:** only the *fast* weights may learn; the
  *slow* weights that encode the physics/laws (grounding `W_c`, complementarity `M`, the energy
  `Φ`) stay **fixed** — changing those would be "learning different physics," which is out of
  scope (that is evolution, across generations, not plasticity within a life).

## What is FORBIDDEN (breaks the requirement)

- **Fixed radial force kernels** that are not attention — e.g. a raw `1/d²` repulsion computed
  geometrically (`Σ_j Δ_ij / d_ij³`). Excluded volume / cohesion must be expressed as an
  **attention head** (bounded, softmax- or content-weighted), not a divergent geometric force.
- **Energy ledgers / metabolism** (explicit energy variable + injection + consumption + a
  conservation book).
- **Variable token count** (birth/death/division/replication) — a transformer operates on a
  fixed token set.
- **Global (all-to-all, non-local) terms** used as dynamics — e.g. a spring to the global
  centroid. (Locality is also required for P6.)
- Any hand-coded geometric rule, controller, or clamp acting as a force.

## Consequences we accept

- **Boundaries are SOFT (strong-but-not-hard).** A bounded attention head gives a strong
  tendency not to overlap, not a guaranteed hard wall. True hard exclusion (a divergent
  repulsion) is out of scope under this requirement.
- **Cohesion is attention-based** (pull toward the local neighbourhood centroid via a broad
  attention kernel), not a Lennard-Jones radial. Surface tension is therefore softer.
- Some behaviours (literal division, hard walls, metabolism) are **permanently out of scope**
  unless the requirement is consciously relaxed by the user.

## Enforcement

- Each engine must pass a **`test_transformer_only`**-style check: grep the step path for
  forbidden patterns (raw `1/d`, `/ d2`, geometric force kernels, energy/ledger vars, token
  insert/delete), and a code review noting every term is attention / MLP / norm / linear.
- `pure.py` already complies. **`pack.py` currently violates it** (the `1/d²` clash-repel) and
  is being reworked to a bounded repulsive attention head.

## Status of engines

| Engine | Compliant? | Note |
|---|---|---|
| `pure.py` | ✅ yes | attention moves + morphs; skew / non-reciprocal / diffusion are architecture mods |
| `pack.py` | 🔧 being fixed | repel reworked from radial `1/d²` → bounded repulsive attention head |
| `engine.py` (force-based) | ❌ no (legacy) | hand-coded force law; kept for history, NOT the transformer-only line |

*See also:* [`dynamics_zoo.md`](dynamics_zoo.md) (the transformer-only boundary discussion),
[`dock_and_morph.md`](dock_and_morph.md).
