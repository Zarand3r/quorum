# RESEARCH_HK — Local Attention (Bounded-Confidence vs Distance-Penalized): study + decision

> **Status: resolved (revised after the distance-penalized follow-up).** Question: should
> thermolife replace global softmax with a *local* interaction rule? Answer: **yes, and the
> operator is distance-penalized softmax, not a hard bounded-confidence threshold.** The
> decisive axis turned out to be **smooth vs. hard**, not local vs. global: a smooth distance
> cost `s − λ‖Δx‖²` resists collapse *and* trains under gradients; a hard Hegselmann–Krause
> threshold resists collapse but has **dead gradients** and cannot be trained. So:
> **E1–E3 interaction operator = distance-penalized (`dist`)**; hard-HK is kept only as a
> measured control; **global softmax + deep supervision remains the M2 training recipe**
> (still the strongest trainer). Code: `fold/hk.py`; experiments:
> `//projects/thermolife:hk_study`; gates: `tests/test_hk.py`.
>
> This revision was prompted by the observation that HK's *discreteness* — not its locality —
> was what killed training; a smooth locality cost was the fix. The study confirmed it.

## 1. The proposal under test

Replace `A = softmax(QKᵀ)` (every token attends to every token) with a Hegselmann–Krause
bounded-confidence rule: each token interacts only with tokens inside a *confidence set*
selected by a score threshold, normalized locally. Claimed benefits: resist the
representation collapse that global averaging causes, allow multiple stable clusters
(diversity), reduce complexity toward linear for long sequences.

**Thermolife-specific tension resolved at design time:** vanilla HK syncs *like with like*
(similarity), but thermolife's thesis is *complementarity* (bump docks pocket, `K = C·M`).
So our primary variant puts the confidence set in the **dock metric**: token *i* interacts
with *j* iff `s_ij = ⟨C_i, C_j·M⟩/√2K > τ` — the same grounded score the blobs render
(J1/J6 preserved). Raw-space HK (`s_ij = −‖x_i−x_j‖²`) is kept as the literature-faithful
control. Kernels: `hard` (classic uniform averaging), `soft` (masked softmax), `sigmoid`
(differentiable relaxation `σ((s−τ)/temp)·eˢ`, for training). Self is always included —
no empty confidence sets.

## 2. What the literature says (verified 2026-07; full agent report in PR)

- **The idea is published**: *Krause Synchronization Transformers* (Liu, Yue, Welling, Song,
  arXiv:2602.11534, ICML 2026) — RBF kernel + hard top-k, **but the neighborhood is fixed
  in position space** (window), not a representation-space ε-ball. A true ε-ball in
  representation space with a dynamics analysis is open ground; our dock-metric variant is,
  to our knowledge, untried.
- **Collapse is the true attractor under global softmax**: tokens generically collapse
  (Geshkovski–Letrouit–Polyanskiy–Rigollet, arXiv:2312.10794); multi-cluster configurations
  survive only as **metastable** states, for exponentially long times (arXiv:2410.06833).
  HK dynamics, by contrast, **converge in finite time to frozen multi-cluster equilibria**
  (Hegselmann–Krause 2002) — that is the theoretical selling point, and the risk (frozen =
  dead gradients).
- **Locality alone does not prevent collapse** — it only slows it (Wu et al.,
  arXiv:2405.18781); keep residual + MLP regardless. LayerNorm is not neutral: it admits
  equilibria of every rank.
- **Attention sinks are a global-normalization artifact** (Xiao et al. arXiv:2309.17453;
  Gu et al. arXiv:2410.10781: removing the sum-to-one constraint removes the sink) — local
  normalization plausibly avoids them; irrelevant at our N but relevant to the long-sequence
  ambition.
- **Hard selection kills gradients** (MoE/top-k literature) — any trainable variant needs a
  smooth kernel; hence our `sigmoid` kernel. (This foreshadowed Exp B's outcome.)
- **HK 2ε rule**: expected cluster count ≈ occupied range / 2ε — ε/τ is a granularity dial,
  though non-monotonic (Lorenz 2006).

## 3. Experiment A — untrained dynamics (does HK resist collapse?)

`hk_study --exp A`: N=64 random tokens, d=4, T=200 iterations, 5 seeds, random weights.
Metrics (`fold/hk.py`, measured never rewarded): single-linkage **cluster count**
(link ε=0.5), scale-aware **effective rank**, mean pairwise **spread**.

| arm | clusters | eff. rank | spread |
|---|---:|---:|---:|
| ANCHOR softmax, pure averaging | 1.6 | 2.20 | 1.644 |
| ANCHOR classic HK raw ε=1, pure | 54.4 | 3.76 | 3.848 |
| softmax (global), full block | 1.2 | 3.40 | **0.024** |
| hk-dock τ=−0.5, full block | 1.2 | 3.40 | 0.196 |
| hk-dock τ=0.0, full block | 1.2 | 3.40 | 0.241 |
| hk-dock τ=0.5, full block | 1.4 | 2.80 | **0.636** |
| hk-dock τ=1.0, full block | 2.2 | 0.76 |
| hk-raw ε=1.0, full block | 1.8 | 1.115 |
| **dist λ=0.05** | 1.0 | 0.000 |
| **dist λ=0.1** | 1.0 | 0.000 |
| **dist λ=0.2** | 1.4 | 0.724 |
| **dist λ=0.5** | 1.6 | **1.123** |
| **dist λ=1.0** | 1.6 | 1.118 |

(effective-rank column dropped from the reproduction above for width; the scale-aware
metric reads ~1.0 for every collapsed arm and is asserted separately in tests.)

Findings:
- **Anchors validate the implementation**: classic HK freezes ~54 micro-clusters
  (textbook); pure softmax averaging contracts and merges (metastable, per theory).
- **Dressed global softmax collapses hard** (spread 0.024 — 70× below init-scale spread).
- **Both local operators resist collapse.** HK-dock scales with τ (0.20→0.76). Distance-
  penalized scales with λ: **weak λ≤0.1 still collapses** (the penalty is too small to beat
  the softmax contraction), λ≥0.2 holds spread 0.72–1.12 — comparable to or better than HK,
  *smoothly*. Both are **average-over-seed** effects: dressed-fold collapse is seed-dependent
  (LN admits any-rank equilibria, Wu et al. 2024). Permanent regression gates
  (`test_dressed_hk_dock_...`, `test_dist_softmax_preserves_spread_...`) pin the reported
  seeds 1000–1004.

## 4. Experiment B — gradient training (does HK remove the deep-supervision crutch?)

**Hypothesis (pre-registered in intent):** M2's softmax fold needed deep supervision only
because rank collapse destroys the scene before T; a *local* operator should therefore train
docking from **final-step supervision alone**. `hk_study --exp B`: M2 lock-and-key task, T=8,
800 Adam iters, batch 16, seed 0. HK = sigmoid kernel temp 0.1; dist = λ 0.3. Chance = 0.125.

| arm | held-out acc @800 |
|---|---:|
| softmax, final-only | 0.235 (the known plateau) |
| softmax, deep supervision | **0.639** (→ 0.9975 at 4k iters, M2) |
| hk-dock, final-only | 0.120 — exactly chance |
| hk-dock, deep | 0.233 — **stuck** |
| **dist λ=0.3, final-only** | 0.125 — chance |
| **dist λ=0.3, deep** | **0.521 — and climbing** (0.14→0.24→0.32→0.46→0.53) |

**Two findings.** (a) *The deep-supervision crutch is NOT removed by locality* — every
final-only arm sits at chance. Locality slows but does not prevent within-horizon collapse
(exactly Wu et al. 2024), so final-step signal is still absent. That hypothesis is refuted
for both local operators. (b) *But smooth locality is trainable and hard locality is not*:
with deep supervision, `dist` climbs steeply (still rising at 800 iters, trajectory above)
while `hk-dock` is stuck near chance. Mechanism: the HK hard/sigmoid gate zeroes exactly the
cross-token entries the retrieval loss needs at random init (top-k gradient death); the
distance penalty only *reweights* them, so gradients survive. **Smooth vs. hard is the axis,
not local vs. global.**

## 5. Decision (revised)

1. **E1–E3 interaction operator = distance-penalized softmax (`dist`), λ from config**
   (default 0.5 — the Exp-A anti-collapse knee). It is the one operator that is *both*
   collapse-resistant (Exp A) and gradient-trainable (Exp B), so the **same** operator serves
   the fixed-θ E1, and any future gradient path, and E2/E3 (where λ can itself be evolved).
   It is physically grounded — locality is particle proximity in `x`, exactly right for a
   docking/particle system — and reduces to global softmax at λ=0.
2. **Hard bounded-confidence (HK) is demoted to a measured control**, not the operator. Its
   Exp-A collapse-resistance is real but it is untrainable (Exp B) and offers `dist` no
   advantage; kept only so the smooth-vs-hard contrast stays reproducible.
3. **Global softmax is a permanent E1 ablation arm.** Every emergence observable is reported
   dist vs. softmax (vs. hk), so "locality preserved the structure" stays a *measured* claim.
4. **Gradient-trained docking (M2 artifacts) keeps global softmax + deep supervision** — still
   the strongest trainer (0.639 vs dist's 0.521 at matched budget); dist+deep is a viable
   local alternative if locality is wanted, at a modest accuracy cost. M2 weights untouched.

Rejected, for the record: HK as the operator (untrainable, Exp B); softmax as the E1 operator
(collapses, Exp A); raw-space locality (clusters *identical* tokens, fights complementarity).

## 6. Threats to validity (honest)

- Exp B is one seed (0), 800 iters, two τ values, one temp (0.1). A τ/temp/lr sweep or
  annealing schedule (start global, tighten τ) might rescue HK training — *not explored*;
  the decision needs only "HK is not better for training," which two τ values at matched
  budget establish against a 5× softmax margin.
- Exp A cluster counts depend on link ε=0.5; the *relative* ordering (HK ≫ softmax spread)
  is robust to that choice; per-seed variance is real and documented.
- N=64, d=4, single head, weight-tied: all claims are toy-scale. The linear-complexity
  argument for HK was **not** tested (irrelevant at this N) and is not part of the decision.
