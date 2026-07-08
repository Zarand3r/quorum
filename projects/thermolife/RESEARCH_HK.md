# RESEARCH_HK — Bounded-Confidence (Hegselmann–Krause) Attention: study + decision

> **Status: resolved.** Question: should thermolife replace global softmax attention with a
> local, bounded-confidence interaction rule (à la Krause dynamics)? Answer: **split by
> regime.** HK-dock attention becomes the **E1–E3 interaction operator** (gradient-free
> regime, where collapse-resistance is what matters); **global softmax + deep supervision
> remains the training recipe** for gradient-trained docking (M2-style), where HK is
> *harmful* — a hypothesis this study set out to confirm and instead **refuted**.
> Code: `fold/hk.py`; experiments: `//projects/thermolife:hk_study`; gates: `tests/test_hk.py`.

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
| hk-dock τ=1.0, full block | 2.2 | 2.24 | **0.760** |
| hk-raw ε=0.5, full block | 2.0 | 2.23 | 1.130 |
| hk-raw ε=1.0, full block | 1.8 | 2.21 | 1.115 |

Findings:
- **Anchors validate the implementation**: classic HK freezes ~54 micro-clusters
  (textbook); pure softmax averaging contracts and merges (metastable, per theory).
- **Dressed global softmax collapses hard** (spread 0.024 — 70× below init-scale spread).
- **HK-dock resists, scaling with τ**: 8–30× more spread than softmax; τ≥0.5 keeps
  multiple clusters. **On average across seeds** — individual seeds can still collapse
  (consistent with "locality slows, not prevents"). This average is now a permanent
  regression gate (`test_dressed_hk_dock_preserves_more_spread_than_softmax`).

## 4. Experiment B — gradient training (does HK remove the deep-supervision crutch?)

**Hypothesis (pre-registered in intent):** M2's softmax fold needed deep supervision only
because rank collapse destroys the scene before T; HK-dock should therefore train docking
from **final-step supervision alone**. `hk_study --exp B`: M2 lock-and-key task, T=8,
800 Adam iters, batch 16, seed 0; HK = sigmoid kernel, temp 0.1. Chance = 1/8 = 0.125.

| arm | held-out acc @800 |
|---|---:|
| softmax, final-only | 0.235 (the known plateau) |
| softmax, deep supervision | **0.639** (→ 0.9975 at 4k iters, M2) |
| hk-dock τ=0.5, final-only | 0.125 — exactly chance |
| hk-dock τ=0.5, deep | 0.233 |
| hk-dock τ=0.0, final-only | 0.120 — chance |
| hk-dock τ=0.0, deep | 0.241 |

**The hypothesis is refuted.** HK-dock fails to train the docking task at either τ, with or
without deep supervision. Mechanism (consistent with the top-k gradient literature): at
random init, dock scores concentrate near 0, so the gate suppresses or flattens exactly the
cross-token entries the retrieval loss `−log A[i, partner]` needs; the same locality that
freezes diversity (Exp A) starves the learning signal (Exp B). Locality's virtue and vice
are the same property.

## 5. Decision

**Split by regime — adopt HK where its virtue matters and its vice doesn't:**

1. **E1–E3 interaction operator = `hk-dock`, hard kernel, τ from config** (default 0.5).
   The emergence path is **gradient-free** (E1 fixed θ; E2 ES; E3 selection): dead gradients
   are irrelevant, and collapse-resistance is exactly what a population substrate needs —
   a collapsed population is a dead simulation. Grounded (the confidence set lives in the
   same M-metric the blobs draw), local (structure can live in the attention graph), and
   with a granularity dial (τ) that E2/E3 may evolve.
2. **Gradient-trained docking (M2 artifacts) keeps global softmax + deep supervision.**
   Measured: HK harms it. The committed M2 weights and gates are untouched.
3. **Global softmax becomes a permanent E1 ablation arm** — every emergence observable is
   reported HK vs softmax, so "locality preserved the structure" stays a measured claim.

Rejected options, for the record: (a) HK everywhere — refuted by Exp B; (b) softmax
everywhere — leaves E1's substrate exposed to the collapse that Exp A quantifies;
(c) raw-space HK — clusters *identical* tokens, fights the complementarity thesis, and
offers no advantage over dock-space in Exp A.

## 6. Threats to validity (honest)

- Exp B is one seed (0), 800 iters, two τ values, one temp (0.1). A τ/temp/lr sweep or
  annealing schedule (start global, tighten τ) might rescue HK training — *not explored*;
  the decision needs only "HK is not better for training," which two τ values at matched
  budget establish against a 5× softmax margin.
- Exp A cluster counts depend on link ε=0.5; the *relative* ordering (HK ≫ softmax spread)
  is robust to that choice; per-seed variance is real and documented.
- N=64, d=4, single head, weight-tied: all claims are toy-scale. The linear-complexity
  argument for HK was **not** tested (irrelevant at this N) and is not part of the decision.
