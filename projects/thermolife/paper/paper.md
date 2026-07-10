# Folding Embeddings into Worlds: Grounded, Local, Thermodynamic Transformers as Simulators

**thermolife — working paper (draft, 2026-07).** *A toy-scale study; all claims are at the
scale stated and reported with their negative results.*

---

## Abstract

A transformer block is a programmable interaction engine: attention lets latent entities
condition each other, and the pointwise MLP updates each entity's internal state. Iterated,
this is a learned dynamical system — and the underexplored opportunity is to train those
dynamics not merely to emit an answer, but to *maintain and evolve a useful latent world*.
We pursue this concretely in a deliberately minimal setting where each token embedding is
rendered as a 2-D contour "blob," and we report four findings, including two that refute our
own hypotheses. **(1) Grounded readout:** decoding attention query/key and the drawn contour
from one shared linear map makes the attention score *equal* the overlap integral of the two
drawn shapes (by Parseval) — the picture cannot lie about the computation. **(2) Docking is
learnable but obstructed by collapse:** trained on a lock-and-key retrieval objective, the
fold reaches 99.75% held-out matching — but only with per-iteration ("deep") supervision;
final-step supervision plateaus at chance because iterated global attention destroys the scene
(rank collapse) before the loss can act. A longer unroll (T=24) *fails to train from scratch*,
opposite to the naive expectation. **(3) A grid-free thermodynamic substrate:** we build a
conserved-energy economy over a token population with a drifting resource source, and show a
sharp *real-stakes* threshold — below a critical drift a forager survives, above it the whole
population starves, while a frozen control starves at any speed (conservation holds to ~1e-12
throughout). **(4) Locality vs. trainability:** replacing global softmax with a
bounded-confidence (Hegselmann–Krause) rule resists collapse (8–47× more spread retained) but
*cannot be trained* by gradients (dead gradients at the threshold), whereas a smooth
distance-penalized softmax both resists collapse *and* trains. The decisive axis is **smooth
vs. hard**, not local vs. global; we adopt distance-penalized attention as the interaction
operator and lay out the substrate for open-ended, *computed* (irreducible) emergence.

---

## 1. Introduction

> A transformer block is a programmable interaction engine. Attention lets latent entities
> condition each other; MLPs update each entity's internal state. Repeated over depth, time,
> recurrence, or scratchpad tokens, this becomes a learned dynamical system. The underexplored
> opportunity is to train these dynamics not merely to emit answers, but to maintain and
> evolve useful latent worlds.

This is the thesis. The one caveat our experiments force onto it — and the reason the
opportunity is *underexplored* rather than merely *unexploited* — is that the default fate of
these dynamics is **collapse**, not worlds. Iterated self-attention is a contraction: it drives
token representations toward a single point (rank collapse, doubly-exponentially in depth
[Dong+2021]; single-cluster consensus as the generic attractor of the particle dynamics
[Geshkovski+2023]). Maintaining a latent world is therefore something one must engineer and
train *against the grain of the mechanism*. Every result below is, in effect, a way of fighting
or measuring that collapse.

We work in a maximally legible instance of the thesis, inspired by Hinton's remark that a
token's embedding *folds* as it passes through attention blocks, like a protein. We render each
token's embedding as one 2-D **contour blob** and iterate a small transformer block, so a
"fold" is literally a visible trajectory of morphing shapes, and complementary shapes docking
is literally attention. The minimality is the point: ~10²–10³ parameters, `d=4`, pure numpy +
a hand-written autodiff, no deep-learning framework — small enough that every claim is
mechanistic and every number is reproducible from one command.

**Contributions.** (i) A *grounded* readout that makes the rendered geometry provably identical
to the attention computation (§2). (ii) A learned lock-and-key docking result, with an honest
account of why it needs deep supervision and why a longer horizon trains *worse* (§3). (iii) A
grid-free thermodynamic population substrate with a conserved ledger and a sharp real-stakes
gate (§4). (iv) A controlled study of local attention operators — bounded-confidence vs.
distance-penalized — resolving which to use where, by measurement rather than assertion (§5–6).
Throughout, we hold to a discipline borrowed from the project's sibling: **no result is an
eyeballed pattern, and nothing rewards "order" directly** — emergence, if claimed, must be a
measured, non-rewarded observable.

## 2. Grounded Fourier-contour attention (S0)

**Setup.** `N` tokens, embeddings `X ∈ ℝ^{N×d}` (`d` small, default 4). One linear map produces
*both* the drawn shape and the attention query:
```
C   = X · W_c ∈ ℝ^{N×2K}          # K angular harmonics per token
r_i(θ) = ρ₀ + Σ_k ( C[i,2k-1] cos kθ + C[i,2k] sin kθ )   # the blob outline
Q   = C ;  K = C · M ;  V = X · W_v
A   = softmax_row( Q Kᵀ / √2K )
X ← LayerNorm(X + A V) ; X ← LayerNorm(X + MLP(X))    # weight-tied, iterated
```

**Grounding (the key property, J1/J6).** Because `Q` and `K` are the *harmonic coefficients of
the drawn contour*, Parseval's theorem makes the attention score equal the overlap integral of
the two rendered shapes: `⟨Q_i, K_j⟩ ∝ ∮ contour_i(θ)·(M·contour_j)(θ) dθ`. The number drawn as
"fit" is the number attention uses. `M` is a fixed **complementarity** metric — a π-rotation
(harmonic `k` scaled by `(−1)^k`) — so a high score means a *bump meets a pocket*, not that two
shapes are identical. A perturbation to any embedding provably moves its blob and its attention
row together; the renderer reads nothing the mechanism does not. This forecloses the standard
failure mode of "interpretable" visualizations that quietly diverge from the model.

## 3. Learned lock-and-key docking (M2)

**Task.** A vocabulary of `K` complementary *pairs* (2K learned type-embeddings). A *scene* is
all types in shuffled order, each perturbed by Gaussian noise (σ=0.6), *no positional encoding*
— a token can find its partner only by content. Loss is attention cross-entropy
`L = −mean log A[i, partner(i)]` — the readout is the attention *structure*, not a token.
Collapse is self-defeating under this loss (identical embeddings ⇒ uniform `A` ⇒ `L` pinned at
`log N`), so anti-collapse needs no extra term. Trained with a ~300-parameter hand-written
reverse-mode autodiff (a framework would be unjustified).

**Result and the deep-supervision finding.** Final-step-only supervision **plateaus near chance**
(~0.20): the untrained weight-tied fold rank-collapses the scene before iteration `T`, so there
is no signal at the final step. Averaging the loss over *every* iteration ("deep supervision")
teaches docking to form early and persist, reaching **99.75% held-out** matching (fresh shuffles
+ noise). This is a concrete, small-scale instance of the introduction's claim: the useful
latent structure has to be *held against* the mechanism's contraction, iteration by iteration.

**A negative result worth stating.** We expected a longer unroll to give richer, more watchable
dynamics. Instead, training from scratch at **T=24 failed** (held-out accuracy 0.25, stuck),
while T=8 reached 0.9975. Longer horizons compound the collapse and worsen credit assignment
through more identical maps; deep supervision helps but does not rescue a cold start at that
depth. Longer-horizon dynamics need a curriculum (warm-start and extend), not a bigger cold run
— or a non-settling *drive* (§4), not a longer *unroll*.

## 4. A grid-free thermodynamic substrate (E0)

To move from "settling to a fixed point" toward "sustained interaction," we place the token
population inside a conserved-energy economy — **grid-free**: a token's position is a continuous
point in ℝ^d, "space" is the embedding space itself, and a neighborhood is proximity realized
through attention, never a lattice.

**Mechanism.** Per tick (fully vectorized): `inject → harvest → move → metabolism → death →
reproduction → drift`. Energy is a closed ledger over three books — unharvested `pool`, living
tokens' `Σe`, and cumulative `dissipated` heat — and the system is closed except for a booked
injection `S`. Harvest is *local* (a Gaussian of distance to the source) and *depletable*
(finite pool, competed for); motion costs `∝‖Δx‖²`; metabolism drains a baseline; tokens die
when they cannot pay and reproduce (splitting energy, mutating a heritable **gene**) when rich.
The source **drifts** on an orbit, so any static configuration falls out of reach and starves.

**Conservation and real stakes (P1, P8).** The per-tick ledger residual holds at **~3.6e-12**
over thousands of ticks (derivation: every process moves energy *between* books; the deltas sum
to exactly `S`). The economy has genuine stakes, with a sharp threshold: a hand-forager that
tracks the source survives indefinitely for drift `v ≲ 0.25`, collapses to extinction for
`v ≳ 0.29` (`v* ≈ 0.26`), while a **frozen control starves at every speed** (~60–70 ticks).
Survival requires motion — non-settling is *forced by the environment*, not rewarded (an order
reward would be gameable and is forbidden by design).

| drift `v` | forager (final N) | frozen control |
|---:|---:|---:|
| 0.06 | thrives (→ cap) | starves (~67) |
| 0.25 | survives (182) | starves |
| 0.27 | collapses (24) | starves |
| ≥0.29 | **extinct** | starves |

## 5. The interaction operator: locality vs. trainability

Global softmax attention is the collapse engine of §2–3. We asked whether a **local** operator
— tokens interacting only with a nearby subset — resists collapse while preserving diversity,
and whether it remains trainable. We compared three operators, all sharing the grounded dock
score `s_ij = ⟨C_i, C_j·M⟩/√2K`:

- **global softmax:** `A = softmax_j(s)` (the baseline).
- **bounded-confidence (Hegselmann–Krause):** interact only with `{j : s_ij > τ}`, aggregated
  by a hard uniform average or masked softmax — a *discrete* confidence set.
- **distance-penalized softmax:** `A = softmax_j(s_ij − λ‖x_i − x_j‖²)` — a *smooth* physical
  locality; λ=0 recovers global softmax.

**Related work.** The idea of bounded-confidence attention is recent (Krause Synchronization
Transformers, [Liu+2026]) but uses a *positional* window; a representation-space confidence set
with a dynamics analysis appears open. Theory says local masking only *slows* collapse
[Wu+2024]; multi-cluster softmax states are *metastable*, exponentially long-lived but not
equilibria [Geshkovski+2024], whereas HK dynamics converge in finite time to *frozen* clusters
[HK2002] — the selling point (real multi-cluster equilibria) and the risk (frozen ⇒ dead
gradients) at once. Attention sinks are a global-normalization artifact [Xiao+2023, Gu+2024],
which local normalization avoids.

**Experiment A — untrained dynamics** (N=64, d=4, T=200, 5 seeds; random weights). Metrics
(measured, never rewarded): single-linkage cluster count, scale-aware effective rank, mean
pairwise spread.

| operator | clusters | spread |
|---|---:|---:|
| global softmax | 1.2 | **0.024** |
| HK-dock τ=0.5 | 1.4 | 0.636 |
| HK-dock τ=1.0 | 2.2 | 0.760 |
| dist λ=0.2 | 1.4 | 0.724 |
| dist λ=0.5 | 1.6 | 1.123 |
| *(anchor)* classic-HK, pure avg | 54.4 | 3.848 |

Both local operators retain 8–47× more spread than global softmax; the classic-HK anchor
reproduces textbook multi-cluster freezing (implementation validated). We note honestly that
collapse of the *dressed* fold (residual+LN+MLP) is **seed-dependent** — LayerNorm admits
equilibria of any rank [Wu+2024] — so these are averages, and weak λ (≤0.1) still collapses.

**Experiment B — trainability** (M2 docking, T=8, 800 iters; chance = 0.125). Does local
attention remove the deep-supervision crutch?

| operator × supervision | held-out acc |
|---|---:|
| global softmax, final-only | 0.235 |
| global softmax, deep | **0.639** (→0.9975 at length) |
| HK-dock, final-only | 0.125 (chance) |
| HK-dock, deep | 0.233 |
| distance-penalized (λ=0.3), final-only | 0.125 (chance) |
| distance-penalized (λ=0.3), deep | **0.521 and climbing** (0.14→0.24→0.32→0.46→0.53) |

**Two findings, one refuted hypothesis.** (i) *Locality does not remove the deep-supervision
crutch:* every final-only arm sits at chance — local attention slows but does not prevent
within-horizon collapse [Wu+2024], so there is still no final-step signal. (ii) *But smooth
locality trains and hard locality does not:* with deep supervision, distance-penalized attention
climbs steeply (still rising at 800 iters) while bounded-confidence is stuck near chance. The
HK threshold zeroes exactly the cross-token gradients the retrieval loss needs at random init
(the hard-selection/MoE gradient-death phenomenon); the distance penalty merely *reweights*
them, so gradients survive. **The operative axis is smooth vs. hard, not local vs. global** —
the redirect that produced the distance-penalized variant was decisive. Global softmax + deep
remains the strongest *trainer* (0.639); distance-penalized is the strongest *collapse-resistant
and trainable* operator, and is what we adopt for the interaction substrate (§6).

## 6. E1 — attention as the interaction operator

We wire the chosen operator (distance-penalized dock attention) into the E0 substrate as the
population's per-tick physics — locality is now *physical* particle proximity, exactly the right
inductive bias for a docking system, and the same operator remains available to gradient or
evolutionary training later. A
token's interface `C_i = x_i·W_c + g_i·G_c` is **gene-modulated**: selection (future work) acting
on `g` reshapes the drawn binding surface *and* the interaction graph together (groundedness
carried). An MLP head decodes three actions from own-state plus the attention-aggregated message
plus a local chemotactic sense (the resource field and its gradient — never the source location
directly): **move**, **harvest**, and **transfer** (energy routed along attention edges,
enabling trade and predation). Transfer is lossless within `Σe` and row-capped by a token's
energy — overdraw is a fail-fast invariant, never a silent clamp — so the ledger stays exact
across every operator and ablation arm (residual < 1e-9). With fixed random weights the
population still faces real stakes (it starves at fast drift); *learning* to forage is deferred
to an evolutionary/meta-learned stage. Observables (attention-graph entropy, transfer-on-edge
mass, interaction degree) are measured but wired one-way — a structural test forbids them from
feeding back into dynamics or reward.

## 7. Honest limitations and negative results (collected)

- **Refuted hypotheses, reported prominently:** longer unroll trains *worse* (§3, T=24 fails);
  bounded-confidence attention *cannot be trained* for docking (§5, Exp B); and locality of any
  kind *does not* remove the deep-supervision requirement (§5, all final-only arms at chance).
- **Toy scale:** N≤256, d=4, single head, weight-tied. The linear-complexity argument for local
  attention was *not* tested (irrelevant at this N) and is not claimed.
- **Seed variance:** dressed-fold collapse is seed-dependent; Exp A/B report averages over
  stated seeds, and the reported numbers are what the committed regression gates pin.
- **No emergence claim yet:** §4–6 build and instrument the substrate. The irreducibility /
  many-body / non-settling verdicts that would substantiate *computed* emergence are future work
  (E2 meta-learning, E3 per-token selection), and are gated on measured observables, not on
  appearance.

## 8. Conclusion

Transformers can be read as programmable interaction engines whose iterated dynamics are the
product, not a byproduct — but the mechanism's contraction bias means a useful latent world must
be actively maintained against collapse. In a maximally legible toy we made the interpretation
faithful (grounded readout), earned a non-trivial learned behavior (docking, with the honest
cost of deep supervision), built a conserved substrate with real thermodynamic stakes, and
resolved by measurement which local attention operator belongs where. The road to the goal —
sustained, *computed*, irreducible emergence — runs through non-settling drives and selection
on the heritable interface, with every step gated by falsifiable observables rather than by how
alive it looks.

## References

*(informal; full bibliographic detail in `RESEARCH_HK.md`.)*
[Dong+2021] Attention is Not All You Need, arXiv:2103.03404.
[Geshkovski+2023] The emergence of clusters in self-attention dynamics, arXiv:2305.05465.
[Geshkovski+2024] Dynamic metastability in the self-attention model, arXiv:2410.06833.
[HK2002] Hegselmann & Krause, Opinion dynamics and bounded confidence, JASSS 5(3).
[Wu+2024] On the Role of Attention Masks and LayerNorm in Transformers, arXiv:2405.18781.
[Xiao+2023] Efficient Streaming LMs with Attention Sinks, arXiv:2309.17453.
[Gu+2024] When Attention Sink Emerges, arXiv:2410.10781.
[Liu+2026] Krause Synchronization Transformers, arXiv:2602.11534.
