# The three thermolife simulations

thermolife has one idea — **a transformer block is a programmable interaction
engine** — pointed at three different questions. Each is a *separate simulation*
(its own engine, state, dynamics, and objective) but they **share substrate**, not
concepts: the same grounded-contour readout, the same local attention operator, the
same web viewer. This document describes each one and what they share.

| | **Fold** | **Economy** | **Morph** |
|---|---|---|---|
| Question | can embeddings *match*? | can a population *survive*? | can embeddings *pattern*? |
| Engine | `fold/engine.py` `FoldEngine` | `eco/engine.py` `EcoEngine` | `fold/morph.py` `MorphEngine` |
| Objective | **trained** (docking loss) | **evolved** (ES survival fitness) | **none at runtime** (untrained) |
| Config | `configs/fold.yaml` | `configs/eco.yaml` | `configs/morph.yaml` |
| Run | `serve` (default) | `serve --eco` | `serve --morph` |
| Status | M2 done (>95% docking) | E0–E2 done (beats hand-forager) | built + aliveness-tuned (0.16) |

Deeper design docs: [`PLAN.md`](../PLAN.md) (fold), [`EMERGENCE_PLAN.md`](../EMERGENCE_PLAN.md)
(economy), [`RESEARCH_HK.md`](../RESEARCH_HK.md) (the local-attention study that all
three rely on).

---

## Shared substrate

All three stand on the same three pieces, so read these once:

1. **Grounded contour readout** (`fold/interface.py`). One linear map `C = x·W_c`
   turns an embedding into the Fourier coefficients of a closed 2D blob — and those
   same coefficients are the attention **query**; a fixed complementarity metric `M`
   (a π-rotation) turns them into the **key**. By Parseval, the attention score
   `Q_i·K_j` **equals** the overlap of the two drawn contours. **The shape you see
   *is* the interaction math.** A blob morphing on screen ⟺ its interaction changed.

2. **Local attention** (`fold/hk.py`, `distance_penalized_scores`). Global softmax
   attention is a diffusion operator with *infinite* range → it homogenizes → rank
   collapse (the project's central enemy). The chosen operator is distance-penalized:
   `s_ij = ⟨C_i, C_j·M⟩ − λ‖x_i − x_j‖²` — smooth, trainable, and collapse-resistant.
   The [HK study](../RESEARCH_HK.md) established the decisive axis is **smooth vs
   hard**, not local vs global. Every sim uses this operator.

3. **Web viewer** (`sim/`). A `SimController` state machine + stdlib HTTP `server`
   drive any engine implementing `step / tick / residual / snapshot / state_hash`.
   `viewer.html` draws contour blobs + interaction edges (fold, morph); `eco_viewer.html`
   draws energy-sized tokens + the drifting source (economy). Rendering is read-only
   (never perturbs dynamics — invariant P4). Host on a tailnet with `sim/host.sh`.

---

## 1. Fold — docking (trained)

**What it is.** A weight-tied toy transformer whose N token embeddings *fold*
through iterated attention until complementary shapes lock together like ligands
into receptors. This is the original thermolife (Hinton's "embeddings morph through
a transformer, like protein folding").

**Mechanism.** One block per iteration: `x ← LayerNorm(x + A·(x·W_v))` then an MLP,
with `A` the grounded dock attention. Iterating settles the embeddings into a docked
configuration; each token's contour blob is drawn at its projected position and bonds
to its partner.

**Objective — trained (M2).** Supervised. Training scenes are procedural
complementary **pairs** (`fold/vocab.py`): each token has a learned type-embedding +
per-scene noise + a shuffle, and a ground-truth partner. Loss = `−Σ_i log A_final[i,
partner(i)]` (attend to your complement), optimized by Adam through the unrolled fold
via autograd; the metric `M` stays fixed. **Gate: >95% held-out docking accuracy**
(committed weights: `configs/trained_fold.npz`, ~99.75%).

**Run.** `serve` (trained by default) or `serve --trained none` (untrained S0
gallery). Static render: `render`.

**Key files.** `fold/{weights,interface,transformer,engine,vocab}.py`,
`train/{train,diff_fold}.py`.

**Status.** S0 + M2 done. Gates: Parseval parity 1e-12, accuracy >95%, persistence
>90% at 2× horizon. A settled fold **holds** (no silent reseed); "New scene ▸"
advances the gallery.

---

## 2. Economy — survival (evolved)

**What it is.** A grid-free, conserved-energy **population** on the transformer
substrate. Tokens are organisms with position, energy, and a heritable interface
gene; they harvest a drifting resource, move, transfer energy, reproduce, and die.
No lattice — position is continuous in embedding space (invariant P3).

**Mechanism.** Each tick (`eco/engine.py`): inject resource → the attention operator
decides interactions → harvest (energy in, booked) → transfer along attention edges →
move (kinetic cost) → metabolism → death (can't pay) → reproduction (gene mutates) →
drift the source. Everything is booked to a **conservation ledger** (pool + Σenergy +
dissipated), residual ~1e-12 (invariant P1). The gene modulates the binding surface:
`C = x·W_c + g·G_c`, so selection reshapes the drawn shape and the interaction graph
together (P7).

**Objective — evolved (E2), no dataset.** There is no loss and no supervision; the
"forward pass" is a simulation rollout scored by a **fitness** = population-ticks
`Σ_t n_t` under the drifting source. Because survival routes through
death/reproduction (non-differentiable), it's optimized by **Evolution Strategies**
(`train/es_eco.py`, OpenAI-ES) — gradient-free. **No order/coordination term is ever
rewarded** (invariant P2, the anti-gaming rule); any structure that appears is
emergent, not incentivized. Committed evolved chemistry: `configs/eco_theta.npz`.

**Result.** Held-out: evolved θ = **43.7× random-θ** and **1.32× the hand-coded
forager** (it beats the baseline). Honest ablation of the learned θ: freeze-attention
−14%, remove-transfer −10%, **shuffle-partners −60%** → individual foraging carries
the base, but interaction *structure* is load-bearing.

**Run.** `serve --eco --eco-policy forager|attention|frozen` (add
`--eco-theta configs/eco_theta.npz` for the evolved policy). Sweep the survival gate:
`eco_run --sweep`. Train: `train_es`.

**Key files.** `eco/{config,state,ledger,resource,policies,interaction,engine,
observables,ablations}.py`, `train/es_eco.py`.

**Status.** E0 (viability substrate + starvation gate, v*≈0.26) → E1 (attention
operator) → E2 (ES meta-learning) all **done**. Next: **E3** (reproduction + evolving
genes; gated on the emergence trio — irreducibility, many-body, non-settling).

---

## 3. Morph — reaction–diffusion (untrained)

**What it is.** The transformer block run *as* a reaction–diffusion PDE. Shapes grow
from a **single seed** by cell division and move + morph continuously — morphogenesis.
This is the block's *intrinsic* dynamics with no goal; it's the newest mode.

**Mechanism** (`fold/morph.py`). One block = one RD step:

```
x ← LayerNorm( x + dt·[ D·(A·x − x)  +  R·MLP(x)  +  Ω·(x·J) ] )
                        diffusion        reaction     oscillation
```

- **Diffusion = attention.** `A·x − x` is a graph Laplacian — each token relaxes
  toward a *local* attention-weighted average of neighbours. It must be local, or
  it homogenizes (Turing's forbidden case; global softmax = infinite diffusion).
- **Reaction = MLP + oscillator.** The pointwise MLP is dissipative and alone has a
  single fixed point → the field would collapse to consensus. A conservative
  skew-symmetric rotation `Ω·(x·J)` (`xᵀJx = 0`) gives limit-cycle kinetics — the
  Belousov–Zhabotinsky / λ–ω condition for *sustained* patterns.
- **LayerNorm** keeps the field bounded (on a shell). Growth: one seed divides every
  `split_every` ticks up to `n_max` (bounded, like the economy).

**Objective — none at runtime.** The weights are **random and untrained**; nothing is
optimized while it runs. The *only* place an objective enters is **offline**: an
ungameable **aliveness** score (`train/aliveness.py`) —
`gate_finite · gate_spread · gate_motion · structure · coherence`, measured on the
asymptotic window, hard-zeroing every trivial fate (collapse / freeze / blow-up /
white-noise) and reporting an edge-of-chaos Lyapunov. A hyperparameter search
(`train/morph_search.py`) maximizes it to pick the *constants* so the fixed rule stays
alive — it does **not** act during the simulation.

**Result.** Search moved aliveness **0.003 → 0.16** (rank 1.0 → 1.8, spread 1.45,
Lyapunov +0.005 — sustained, structured, edge-of-chaos). It also exposed that the
hand-tuned "sustained" config was really a near-1D limit cycle (~0). Currently *alive
but not richly structured* (a coupled oscillation, not full Turing patterns) — the
open next step is ES-training the weights against aliveness, or adding a conservation
law + drive + homeostatic gain (borrowed from the economy) so aliveness is structural.

**Run.** `serve --morph` (reuses the blob viewer). Score a config: `aliveness`.
Search: `morph_search --samples 60`.

**Key files.** `fold/morph.py`, `train/{aliveness,morph_search}.py`,
`configs/morph.yaml`.

**Status.** Built, tuned, watchable. Not an emergence claim — it's a dynamics gallery
with a measurable liveness target for heedless iteration.

---

## How separate are they, really?

- **Fold ↔ Morph** are close cousins: the morph lives in `fold/morph.py` and reuses
  `FoldWeights`, the contour geometry, the local attention, and `viewer.html`. It is
  "the fold's block, run as reaction–diffusion instead of docking."
- **Economy** is the most independent (its own state/ledger/reproduction) but imports
  the attention *operator* from `fold/hk.py`. Same operator, different everything else.

The common thread is the one idea. Fold aims the block at **matching**, economy at
**survival**, morph at **pattern** — same engine underneath, which is why they share
substrate without blending. Tests gate all three: `tests/test_*` — 90 total.
