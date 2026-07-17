# M2 blocked: the collapse / drift-dragging negative result, and the option space

> **Status:** M0–M3 built and green; **M2 (emergent *irreducible* life) is NOT met** by the
> current one-clock local-predictive-plasticity design plus tuning. This documents the measured
> negative result, its two root causes, and the four design options — with **Option 1
> (anti-collapse regularizer) chosen to try first** (per decision 2026-07-17), then re-evaluate.

## 1. What we measured (the negative result)

The ungameable aliveness harness (Step 3) caught two failure modes that eyeballing would have
missed:

**Failure A — freeze (weak drive).** At the default drift (0.02–0.2) the colony *converges*:
motion decays `0.31 → 0.0000`, Lyapunov `≈ −0.3` (contracting), loss pins at the drift floor
`½·drift²`. Measured aliveness = **0** (`gate_motion = 0`). Death by convergence — the
equilibrium attractor; the drive `J` is too weak to sustain motion.

**Failure B — drift-dragging (strong drive), and P6 fails.** At drift = 0.5 (λ = 0.5) aliveness
*looks* high (~0.95), but the P6 ablation shows it is **not** from interaction (seeds 0–4, final
aliveness):

| arm | seed0 | seed1 | seed2 | seed3 | seed4 | alive |
|---|---|---|---|---|---|---|
| **none** (real interaction) | 0.95 | 0.00 | 0.00 | 0.99 | 0.00 | 2/5 |
| **identity** (drift only, no interaction) | 0.69 | 0.96 | 0.00 | 0.81 | 0.00 | **3/5, higher mean** |
| **shuffle** (wrong partners) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0/5 |

Ablating interaction (identity) is **as good or better** than keeping it. So the aliveness at
strong drive is the **external field dragging independent agents coherently**, not emergent
interaction. **P6 (interaction load-bearing) fails.**

## 2. Root cause

Two coupled causes, both predicted by the theory docs:

- **The interaction collapses (dark room).** Predictive plasticity minimises surprise the
  *trivial* way — by homogenising the colony (identical agents ⇒ trivially predictable). The
  learned `W_v` drives the state toward a consensus point; the interaction then carries no
  distinguishing information, so removing it (identity) costs nothing.
- **The drive can fake life.** Because the observable target includes absolute position (which
  the season `s(t)` moves), a *self-only* agent following the drift already produces coordinated
  motion — the metric's `coherence`/`structure` are satisfied by everyone obeying the same
  external field. Interaction is not *needed*.

Net: with weak drive → freeze; with strong drive → drift-dragging. There is no drive setting
where the *current* design makes interaction load-bearing.

## 3. The four options

Each attacks a different part of the root cause. Columns: **what it changes**, **which failure
it targets**, **how to test**, **cost**, **keeps one clock / plain numpy / measure-not-rewarded?**

### Option 1 — Anti-collapse regularizer (Route A+) — **CHOSEN FIRST**
**Mechanism.** Add a **local diversity term** to the plasticity objective (a VICReg/JEPA analog,
kept local to preserve P1): penalise an agent's message for being too similar to its neighbours'.
With `agg = A·X` and `da = (I − A)·agg` (each agent's deviation from its attention-weighted
neighbourhood), the message deviation is `d = da·W_v`; reward `‖d‖` (a variance floor) so the
plasticity is pushed **away** from homogenising. Gradient is linear in `W_v`
(`g_ac = −(β/n)·(daᵀda)·W_v`), so it stays a hand-derived one-step delta — still Route A.
**Targets:** collapse (root cause A) directly; by keeping the colony diverse it *may* also let us
lower the drift (less drift-dragging, helping B).
**Test:** re-run the P6 ablation; expect `none ≫ identity`.
**Cost:** moderate (one term + a `β` knob + re-tune). **One clock ✓ plain numpy ✓ measure-not-
rewarded ✓** (it regularises *prediction*, never aliveness).
**Why first:** attacks the deepest root cause (the interaction is useless because it collapses);
is the documented primary fallback (§D-e); smallest change that could make interaction matter.

### Option 2 — Intrinsic rotational term (F4 skew)
**Mechanism.** Add a **non-gradient** skew term to the dynamics,
`X ← LN(X + A·V + Ω·(X·J))` with `Ω` skew-symmetric — perpetual motion from *within* (the morph
fix; Helmholtz rotational component, `potential_flux.md`). Lets us **lower the external drift**, so
aliveness can't be drift-dragged.
**Targets:** drift-dragging (B) — replaces the *external* drive with an *intrinsic* one; then
re-test whether interaction becomes load-bearing.
**Test:** lower drift, add Ω, re-run P6.
**Cost:** small (one fixed skew matrix + a gain). **One clock ✓ plain numpy ✓ measure-not-
rewarded ✓**. **Risk:** a rotational drive can *also* be interaction-independent (each agent
orbits alone) — may not fix P6 by itself; likely pairs with Option 1 or 3.

### Option 3 — Make interaction necessary (reframe the target)
**Mechanism.** Change *what* is predicted so the target is a **neighbour-only** quantity the self
+ drift cannot supply — e.g. predict the *relative configuration* of neighbours (pairwise offsets,
local shape complementarity), not absolute position (which the drift sets). Then the identity
ablation **cannot** match the real run *by construction*.
**Targets:** drift-dragging (B) directly, at the definition of the task — makes P6 load-bearing by
design.
**Test:** P6 — identity should be structurally unable to predict a relative target.
**Cost:** moderate (reframe `observe`/target; re-derive the delta). **One clock ✓ plain numpy ✓
measure-not-rewarded ✓**. **Risk:** doesn't stop collapse (A) — a collapsed colony has trivial
relative structure too; likely pairs with Option 1.

### Option 4 — Stop & write up the negative
**Mechanism.** Accept the measured result: one-clock local predictive plasticity, as designed,
does not yield irreducible aliveness — it collapses, or the drive fakes it. Document it as a
*measured* negative (the ungameable metric working as intended) and defer design changes.
**Cost:** none (writing). **Value:** honest; but premature before trying the targeted fixes.

## 4. Plan

1. **Option 1 first** (this doc's choice). Implement the local anti-collapse term behind a `β`
   knob (default off, so nothing regresses until deliberately enabled), tune `β` on the P6 probe,
   and re-evaluate.
2. **Re-evaluate.** If P6 passes (`none ≫ identity`, sustained) → M2 met; commit + re-stamp golden.
   If collapse is fixed but drift still fakes it → add **Option 3** (relative target). If it still
   settles at low drive → add **Option 2** (rotational). If nothing clears P6 → **Option 4**
   (write up the negative honestly).
3. Only combine options as the data demands — no speculative stacking.

*The likely-honest expectation:* Option 1 alone may fix collapse but not fully P6 (drift can still
fake coordination), so a 1+3 combination is the probable endpoint. We proceed empirically.

*See also:* [`potential_flux.md`](potential_flux.md) (why a drive is mandatory and rotational vs
external), [`related_work.md`](related_work.md) §3 (Route A vs B; anti-collapse is the Route-B
bridge kept local here), [`../IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md) §D-e (dark-room
risk was pre-registered as a real acceptance risk, not a surprise).
