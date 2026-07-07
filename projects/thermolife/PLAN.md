# thermolife — Embedding Folding as Ligand–Receptor Docking

> **Status: design.** Source of truth for scope, the mechanism (§4), invariants (J1–J6),
> the visualization contract (§5), and milestones S0–M3 (§8). This **replaces** the earlier
> thermodynamic-grid-NCA design — see §9 "What changed" for what was dropped and what survives.

## 1. Goal (one line)

Visualize how a token's embedding **morphs** as it passes through the attention blocks of a
*toy* transformer — Hinton's "embeddings fold like proteins" — and extend it so each embedding
is rendered as a **2D contour blob** whose shape is a *grounded* readout of the embedding, so
that complementary blobs **fold into each other like ligands into receptors**. Minimal,
mechanism-first: small embedding dim, random init, **no training, no grid.**

## 2. The claim we are making visual

- A transformer block refines each token conditioned on all the others. **Iterating** the block
  traces a **trajectory** for each embedding — a fold.
- Attention is a **compatibility** operation: token *i* attends to *j* when *i*'s query aligns
  with *j*'s key. Rendered as shapes, the query is a **ligand** surface and the key a **receptor**
  surface; high attention ⇔ the surfaces **fit**.
- So **fold = the embedding trajectory; binding = query/key overlap emerging along it.** The whole
  process is docking *in embedding space*, with no spatial grid.

## 3. Non-goals (explicit)

- **No spatial grid, no reaction–diffusion field, no nutrient/energy/waste, no forager.** The
  *space* is the embedding/visualization plane itself.
- **Not trained first.** S0 is random-init, mechanism only. Learned (meaningful) docking is M2.
- **No aesthetic claim.** "It looks like it docks" is not a result; report trajectory/attention
  metrics and what was *not* run (failure mode F-Aesthetic carries over).
- **"2D" is the visualization commitment, not `d_model = 2`.** The embedding dim is small and
  configurable; every embedding is rendered as **one 2D morphing object** (a contour blob).

## 4. Core mechanism (precise)

State: `N` tokens, embeddings `X ∈ R^{N×d}` (`d` small, default 4). Weights are fixed and seeded
(random init at S0).

**(a) Grounded interface readout (the old I11 → J1).** One linear decoder produces *both* the
drawn shape and the attention query/key, so they can never disagree:
```
C          = X · W_c                 ∈ R^{N×2K}     # K angular harmonics per token
contour_i(θ) = ρ0 + Σ_{k=1..K} ( C[i,2k-1]·cos kθ + C[i,2k]·sin kθ )   # a closed 2D blob
Q          = C                       # ligand: the surface token i offers
Kmat       = C · M                   # receptor: M is a fixed complementarity metric (bump@θ ↔ notch@θ)
V          = X · W_v                 # separate value channel
```
The query/key attention uses **are** the harmonic coefficients of the rendered contour.

**(b) Attention = contour overlap.** `S_ij = ⟨Q_i, K_j⟩/√d ∝ ∮ contour^L_i(θ)·contour^R_j(θ) dθ`.
The number drawn as "fit" is the number attention uses (J6).

**(c) The fold (weight-tied iteration).** For `t = 1..T`:
```
A = softmax_row(S)                   # receiver-side normalization
X ← LayerNorm( X + A · V )           # residual + norm keeps it bounded (J5)
X ← LayerNorm( X + MLP(X) )          # optional pointwise block
```
Record `X^(t), C^(t), A^(t)`. **Weight-tied** ⇒ one repeated map ⇒ a clean folding *flow* (matches
"over many iterations"); distinct-per-layer weights are a config toggle.

**(d) 2D placement.** `p_i = X_i · P ∈ R²` (`P` a fixed 2D projection; identity when `d = 2`), so
blobs drift as embeddings fold.

All of `S, A, X, C` are **batched matmuls over the N tokens — no per-token Python loop (J3)** — and
**synchronous**: `X^(t+1)` is computed from `X^(t)` only, double-buffered (J4).

## 5. Visualization contract

Each iteration `t` the snapshot renders:
- every token as its **filled contour blob** (from `C^(t)`) at position `p_i^(t)`;
- **attention edges** `i→j` with opacity ∝ `A_ij` — the docking bonds;
- a **step control** (play / pause / step / restart) driving `t`;
- readouts: iteration `t`, mean fold-step `‖X^t − X^{t-1}‖` (convergence), max attention.

Groundedness is *visible*: the same `C` that draws a blob sets its bonds.

## 6. Invariants (J1–J6) — the merge gates

- **J1 Groundedness.** `contour_i` is a pure function of `C_i = X_i W_c`, the same `C` forming `Q/K`.
  *Test:* perturb an embedding → its blob **and** its attention row change together; the renderer
  reads nothing but `C`.
- **J2 Determinism.** seed + weights ⇒ byte-identical trajectory hash.
- **J3 Vectorized.** no per-token loop; batched matmuls. Structural scan + wall-clock budget.
- **J4 Synchrony.** `X^{t+1}` from `X^{t}` only (double-buffered).
- **J5 Bounded.** LayerNorm + residual keep `‖X‖` finite over `T`; blobs stay renderable.
- **J6 Overlap identity.** the value drawn as "fit" equals the attention score used (groundedness at
  the bond level).

## 7. Architecture / modules

**New `fold/` package (replaces `env/`, `model/`, and the grid `sim/` pieces):**
- `fold/config.py` — `FoldConfig` (N, d, K harmonics, T, tie-weights, mlp on/off, seed).
- `fold/interface.py` — grounded contour decoder (`C` → closed polyline), complementarity metric `M`.
- `fold/transformer.py` — weight-tied attention block (grounded `Q/K`, `V`, softmax, residual,
  LayerNorm, optional MLP); pure + vectorized.
- `fold/engine.py` — `FoldEngine`: owns `X` + weights; `step()` = one iteration, `snapshot()` =
  blobs + edges + stats, `residual()` = fold-step norm. Implements the existing engine protocol.

**Reused unchanged:** `sim/controller.py` (run/pause/step/restart state machine), `sim/server.py`
(HTTP), `sim/host.sh` (tailnet hosting).

**Rewritten:** `sim/viewer.html` — draws morphing blobs + docking edges instead of field grids.

**Removed:** `env/*`, `model/*`, `sim/forager.py`, `sim/tick.py`, `sim/nca_engine.py`, and their
tests; `configs/world.yaml` (→ `configs/fold.yaml`).

## 8. Milestones

- **S0 — mechanism (numpy, random init).** §4 fold + §5 viewer; invariants J1–J6 green. Watch random
  embeddings fold and incidentally form bonds. **← first; this is what replaces the current code.**
- **M1 — designed docking.** Hand-set `W_c` / `M` so chosen token pairs are complementary; they fold
  into *deliberate* docking. Proves the ligand/receptor readout is real, not coincidental.
- **M2 — learned docking (torch).** Train the tiny transformer on a matching/assembly task so the
  fold is *meaningful*, not incidental. First real optimization.
- **M3 — objective-driven non-settling.** Re-introduce a viability / free-energy objective (the old
  thermodynamic idea, now as a docking energy over a *drifting* target) so folding keeps **adapting**
  instead of freezing — the "earned, not pretty" payoff.

## 9. What changed (from the thermodynamic-grid design)

**Dropped:** the 2D physical grid, reaction–diffusion of nutrient/heat/waste, energy/metabolism/death,
the conservation ledger, the hand-coded forager, and average-reward viability *as the starting point*.

**Kept — thermolife's soul:** **interface groundedness** (the rendered hands *are* the binding code,
J1/J6), **determinism** (J2), **vectorization** (J3), **synchrony** (J4), and the **honest-emergence
discipline** — no term rewards "order," no result is an eyeballed pattern. The thermodynamic objective
returns at **M3** as the force that keeps embeddings folding rather than settling.

## 10. Design tensions (for review)

- **D1. `d_model` size vs shape richness.** `d=2` gives the literal position-trajectory but only a
  2-parameter shape family; `d=4–6` gives richer blobs at the cost of a 2D projection for position.
  *Rec:* `d` configurable, default 4, position via fixed `P`; keep a `d=2` mode.
- **D2. Weight-tied vs per-layer.** Tied = a dynamical-systems fold (matches "over many iterations");
  per-layer = a standard stack. *Rec:* tied default, toggle for per-layer.
- **D3. Convergence is not a bug.** Mechanism-only tied iteration *settles* (a protein folds to its
  native state) — expected and fine at S0. Non-settling is M3's job, driven by a drifting objective,
  not by fighting the mechanism.
