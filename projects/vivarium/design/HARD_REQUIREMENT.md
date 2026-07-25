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
- **Unnormalised kernel-attention pair heads** (added 2026-07-25 — see the amendment below).
  A head of the form `Σ_j gate(content_i, content_j) · K(‖Δp‖) · v_ij`, where `gate` is a bounded
  elementwise nonlinearity (`sigmoid`/`tanh`), `K` is an RBF/Gaussian distance kernel
  `exp(−λ‖Δp‖²)`, and `v_ij` is a relative-position readout. This is attention with the softmax
  normalisation removed — the linear/kernel-attention family — NOT a hand-coded force law.
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
- `pure.py` and `pack.py` comply. The `1/d²` clash-repel was replaced by a bounded repulsive
  attention head; the forbidden-pattern grep also strips `#` comments first, so design prose that
  merely *mentions* an energy does not trip the ledger guard.
- Coverage note (2026-07-25): the grep originally checked only `pure.step` / `pack.step`. It now
  also covers `polar_pack`'s hooks (`_extra_force`, `_post_morph`, `_sh_basis`, `_axial_coeffs`,
  `_rotate_toward`, `_near_face`) — previously the newest and least-audited code was unchecked.

## Status of engines

| Engine | Compliant? | Note |
|---|---|---|
| `pure.py` | ✅ yes | attention moves + morphs; skew / non-reciprocal / diffusion are architecture mods |
| `pack.py` | ✅ yes | repel is a bounded attention head; conservative attract/repel are unnormalised kernel-attention (see amendment) |
| `polar_pack.py` | ✅ yes | electrostatic head is a bounded relative-bearing (RoPE-family) readout; 3-D uses real spherical harmonics; same kernel-attention caveat |
| `engine.py` (force-based) | ❌ no (legacy) | hand-coded force law; kept for history, NOT the transformer-only line |

## Amendment (2026-07-25) — conservative kernels vs. row-softmax

Making structures emerge requires **conservative** pair forces (`F_ij = −F_ji`), so the system
relaxes to a free-energy minimum instead of being stirred by a phantom net force. This creates a
real, unavoidable tension with canonical attention:

> **Row-stochastic softmax cannot be conservative.** Each row is normalised by its own
> denominator, so `A_ij ≠ A_ji` in general, and `Σ_i F_i ≠ 0`. Momentum is not conserved.

So the conservative heads deliberately drop the softmax normaliser and use an **unnormalised
bounded kernel** instead. What is retained, and why this is still inside the requirement:

| Attention property | Retained? |
|---|---|
| score from content (contour/radius inner products) + relative position | ✅ |
| bounded weights (`sigmoid`/`tanh`, never divergent) | ✅ |
| distance kernel `exp(−λ‖Δp‖²)` (RBF — a standard attention kernel) | ✅ |
| value = relative-position readout at the relative bearing (RoPE-family) | ✅ |
| fixed token count, no energy ledger, no `1/d` | ✅ |
| **row-stochastic normalisation** | ❌ **dropped on purpose** |

This is the linear/kernel-attention family (attention minus the softmax denominator), not a
hand-coded force law: nothing here divides by a distance and every weight is bounded. Symmetry
itself is an *additional physics constraint we impose*, not a property attention gives us.

**Honest caveat:** calling these "attention heads" is a defensible but not free reading. They are
attention-shaped; they are not canonical softmax attention. The non-conservative softmax paths
still exist in the code (`conservative=False`) and remain canonical.

**Known deviation:** the per-token `maxvel` speed cap is applied *after* the force sum and is not
a pair force, so when it binds it injects/removes momentum. It is deliberate overshoot control,
not physics. `tests/test_polar3d.py` pins both facts: the pair forces sum to zero, and the cap is
the only op that breaks it.

*See also:* [`dynamics_zoo.md`](dynamics_zoo.md) (the transformer-only boundary discussion),
[`dock_and_morph.md`](dock_and_morph.md).
