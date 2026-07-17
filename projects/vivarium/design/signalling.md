# The signalling pivot — the approach, and an honest rigor review

> **Insight (user, 2026-07-17):** organisms don't *predict* their neighbours — they **signal,
> sense, and respond** (quorum sensing, flocking, molecules via photons). And attention *already
> is* signalling: `V = X·W_v` is the emitted signal, `A` is who-reads-whom, `A·V` is the sensed
> aggregate, the MLP is the response. The prediction objective was a mismatch bolted on top.

This documents the pivot it motivated, the **real** contribution (a provably better objective),
and — critically — the controls that show the observed "aliveness" is **not** yet emergent
learned life. Written to be the honest record, not a victory lap.

## 1. The pivot: predict the neighbourhood *relative to self*

Old objective (failed): predict neighbours' **absolute** next observable
`target_i = (A·obs)_i + season`. It failed two ways (`m2_collapse.md`): weak drive → freeze;
strong drive → the drift *dragged* independent agents coherently and **P6 failed** (ablating
interaction was as good or better).

New objective: predict the neighbourhood's next observable **relative to self**
```
target_i = ((A − I) · obs(X_next))_i
```
Only the target changes; the one-step local delta gradient is unchanged (the target is detached).

### 1.1 Two properties — proven, unit-tested (this part is real)
- **Drift-invariant.** `A` is row-stochastic ⇒ `A·s = s` for a uniform shift `s`, so
  `(A − I)·s = 0`. An external drive **cannot fake** this target. (test_target_is_drift_invariant)
- **Interaction load-bearing by construction.** Under the identity ablation `A = I`, the target
  is `(I − I)·obs ≡ 0` — no neighbours, nothing to model. (test_identity_ablation_makes_target_zero)

These are genuine: they fix the *objective's* pathology (drift-dragging) at the level of
definition, and they are the right expression of "signal→response, not predict-absolute-state."

## 2. What we then observed — and why it does NOT (yet) show emergent life

Empirically, with the pivot: identity aliveness collapses to a low cap (~0.25 without a drive)
while real interaction reaches ~0.93 on the seeds where the colony is alive — *looked* like a P6
win. But three controls, run before claiming anything, refute the strong reading:

### 2.1 Control A — frozen weights (lr = 0). **Learning barely matters.**
A random, **never-updated** block scores essentially the same aliveness as the learned one:

| seed | learned (lr>0) | frozen (lr=0) |
|---|---|---|
| 1 | 0.848 | **0.790** |
| 0 | ~0.93 | **0.950** |

Meanwhile the frozen run's prediction loss *grows* (4→5) while aliveness holds. **The measured
aliveness is decoupled from the learning.** The "learn while living" thesis is *not* demonstrated
here — the fixed random interaction already produces the motion.

### 2.2 Control B — P6 gap is fixed-dynamics + seed-dependent, not learned.
With frozen weights: seed 1 shows **no** P6 gap (none 0.790 ≈ identity 0.780); seed 0 shows a gap
(none 0.950 vs identity 0.665). So where a gap exists it is a property of the **fixed random
attention coupling**, and it is **seed-dependent** — not an emergent property the *learning* earns.

### 2.3 Control C — the metric saturates to "coherent motion".
Across alive runs `structure → 1.000`, so `aliveness ≈ gate·coherence·structure ≈ coherence` —
i.e. the score reduces to *"is the motion smooth and aligned."* A rigidly **coherent drift/flock**
(everyone moving in lockstep) satisfies it. The metric **cannot distinguish rich, irreducible
emergence from trivial coordinated translation.** This is a metric weakness, not a strength.

## 3. Honest verdict

- **Real and valuable:** the *objective* (relative-neighbour signalling target) is provably
  drift-invariant and load-bearing — the correct fix to the drift-dragging failure, and faithful
  to "attention is a signalling engine." The **measure-don't-reward discipline + the frozen-weights
  control did their job**: they caught an illusory result instead of letting it be reported.
- **Not shown:** emergent *learned* irreducible life. Learning is near-irrelevant to the current
  aliveness (Control A); the P6 gap is fixed-coupling and seed-fragile (B); and the metric rewards
  trivial coordination (C). The apparent 0.93 is mostly *coherent drift from a fixed random block*.

**So the pivot fixed the objective's mathematics but did not, by itself, produce life — and the
honest tooling proved it.** That is a genuine (negative/methodological) result, not the positive
one hoped for.

## 4. What this implies for any next step

Two problems must be fixed *before* robustness (Option 1) or a reframe (Option 3) can be judged:

1. **Strengthen the metric so it rewards *irreducibility*, not coherence.** Options: make the P6
   ablation-gap a *live* factor (`aliveness_none − aliveness_ablated`), or replace the
   velocity-alignment `structure` (which saturates at rigid lockstep) with a measure that is *low*
   for a coherent drift and *high* only for non-trivial spatial organisation (multi-cluster,
   relative-motion diversity, effective rank of the velocity field).
2. **Make the learning load-bearing.** In the current setup a fixed random block already produces
   the motion, so nothing forces the *learned* rule to matter. The objective or substrate must be
   such that the aliveness is unattainable without the *learned* interaction (e.g. a task the fixed
   random coupling fails, that learning must solve).

Until both hold, "aliveness" is measuring the wrong thing and learning isn't in the loop — so a
higher aliveness number would not mean progress.

*See also:* [`m2_collapse.md`](m2_collapse.md) (the option space), [`potential_flux.md`](potential_flux.md)
(drive-vs-fakeable), [`related_work.md`](related_work.md) §2 (measured-not-rewarded is exactly what
caught this).
