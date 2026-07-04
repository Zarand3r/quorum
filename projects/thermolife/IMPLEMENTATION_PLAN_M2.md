# thermolife M2 — Implementation Plan (the "Transformer Game of Life")

> Turns PLAN.md §10.5 (reaction–diffusion–advection cell update) into an executable build. **Scope: M2a — the *mechanism*.** A conserved, attention-driven grid tick where one shared local rule (a "genome" `θ`) makes patterns **move** (attention advection), **morph** (pointwise reaction), and **merge** (compatibility gate), demonstrated with **fixed/random `θ` in pure numpy — no torch, no gradient training**. Gradient training (M2b) is deferred (§C) — it needs torch and is a separate, uncertain research slice.

## Pre-flight (Phase 1)

- **Build on the working substrate.** Slice 0 (`env/` physics + conservation ledger + `sim/`) is done and green (38 tests). M2 **adds** a `model/` numpy neural rule and a new engine that runs the RDA tick over a hidden-state grid coupled to the nutrient feed. It does **not** modify the Slice-0 forager (that stays as the M1-baseline and the conservation reference).
- **Why numpy, not torch (avoid unnecessary complexity).** The *mechanism* — windowed softmax attention, conserved flux transport, a small pointwise MLP — is all dense array math. numpy keeps the Bazel build light/fast and the conservation math auditable. Autodiff/TBPTT (M2b) is the only part that needs torch; deferring it removes an ~800 MB dependency and an uncertain training loop from this slice.
- **The hard part is conservation of *movement*.** Attention that moves mass must conserve it (source-side flux limiter, non-negativity) and book it in the existing `TransactionLedger`. This is the load-bearing invariant; most of the test budget goes here.

## The steps at a glance

- [ ] **M2.0 — `model/` foundation.** numpy cell-rule package, model config, `θ` genome (fixed/seeded), a hidden-state + occupancy world extension. Test infra.
- [ ] **M2.1 — Windowed neighbor attention.** Per-cell ligand/receptor/value over the neighborhood → `κ` compatibility → softmax `α` → aggregate `m`. Vectorized, local, deterministic.
- [ ] **M2.2 — Conserved attention advection (movement).** Route occupancy/mass along `α` with a source-side flux limiter. **Mass conserved exactly**; a blob translates under a directional field.
- [ ] **M2.3 — Diffusion + reaction (morphing).** Per-channel `D_c∇²h` + pointwise reaction `F_θ` (small numpy MLP). The full `h ← h + D∇²h − ∇·(𝐯h) + F_θ(h,m)` in one batched pass.
- [ ] **M2.4 — Engine + viewer + demo.** `NCAEngine` running the RDA tick coupled to the nutrient feed, booked in the ledger; a server scenario + hidden-channel viewer overlay; a demo showing emergent move/morph/merge with fixed `θ`.

**Dependency graph** (linear; each slice conserves + tests before the next):
```
M2.0 ──▶ M2.1 ──▶ M2.2 ──▶ M2.3 ──▶ M2.4
```

## Properties to preserve (Q1–Q6) — M2-specific, on top of P1–P8

### Q1 — Attention-flux conservation (extends I1/I3)
**Invariant:** occupancy/mass moved by attention advection is conserved exactly (total change = booked flux only); the `TransactionLedger` stays consistent.
**Proved by:** M2.2 `test_advection_conserves` (mass constant under pure transport) + M2.4 `test_rda_conservation` (full tick over N ticks, residual < tol).

### Q2 — Non-negativity under transport (extends I2/P2)
**Invariant:** the flux limiter guarantees no cell's mass/occupancy goes negative (outflow ≤ available).
**Proved by:** M2.2 `test_flux_limiter_nonneg`.

### Q3 — Locality (I5)
**Invariant:** the update reads only the fixed neighborhood; no global mixing.
**Proved by:** M2.1 `test_attention_locality` (perturbing a far cell can't change a cell's `m`).

### Q4 — Single batched pass / no per-cell loop (I6)
**Invariant:** the whole-grid RDA tick is vectorized; no Python loop over cells.
**Proved by:** M2.3 `test_no_cell_loop` (structural scan over `model/`) + a wall-clock budget.

### Q5 — Synchrony (I7)
**Invariant:** `state_{t+1}` computed from `state_t` only (double-buffered); order-independent.
**Proved by:** M2.3 `test_synchrony` (update reads no array it has already written this tick).

### Q6 — Determinism / emergent movement
**Invariant:** same seed+θ ⇒ identical trajectory; and a directional interface field makes a mass blob **translate** (movement is emergent from attention, not a hand-coded move).
**Proved by:** M2.4 `test_rda_determinism` + M2.2 `test_blob_translates`.

---

## M2.0 — `model/` foundation

**Goal:** the numpy neural-rule package + a hidden-state/occupancy world extension + a seeded genome `θ`, with nothing computed yet.
**Why now:** every later slice writes into `model/` and needs the state arrays + `θ` to exist.

### Tests first
- [ ] `tests/test_m2_genome.py`: `Genome.random(seed)` yields arrays of the documented shapes; same seed → identical `θ` (determinism); a `hidden` grid `[H,W,C]` and `mass` grid `[H,W]` allocate to the right shapes/dtype.

### Implementation
- [ ] `model/config.py`: `ModelConfig` (hidden_dim `C`, iface_dim, n_dirs, per-channel diffusivities `D_c`, MLP width) loaded from `configs/model.yaml`.
- [ ] `model/genome.py`: `Genome` — the fixed weight set (`W_ℓ, W_ρ, W_v`, MLP weights) as numpy arrays, `Genome.random(cfg, seed)`.
- [ ] `model/state.py`: helpers to allocate/seed a `hidden[H,W,C]` + `mass[H,W]` field on a `World` (or a small `NCAState` dataclass alongside it).

### Acceptance
- [ ] `bazel test //projects/thermolife:test_suite` green; `grep -rn "import torch" projects/thermolife` still empty.

**Depends on:** Slice 0.

---

## M2.1 — Windowed neighbor attention

**Goal:** the attention aggregate `m_i` over the local neighborhood from ligand/receptor/value codes.
**Why now:** it's the coupling operator all three RDA roles ride on.

### Tests first
- [ ] `tests/test_m2_attention.py`:
  - shapes: `ligand/receptor/value` heads produce `[H,W,dirs,·]`; `α` sums to 1 over the neighborhood per cell.
  - **Q3 locality**: perturbing a cell outside the window leaves `m` unchanged.
  - determinism: same inputs → same `m`.

### Implementation
- [ ] `model/attention.py`: `interface_heads(hidden, genome)` → `ℓ, ρ, v`; `neighbor_attention(ℓ, ρ, v, mask)` → `α, m` using shifted-tensor gather over the 4/8 neighborhood, `κ = σ((b−|ℓ−ρ|²)/T)`, softmax `α`, `m = Σ α·v`. Fully vectorized.

### Acceptance
- [ ] `test_m2_attention.py` green (softmax normalized, locality, determinism).

**Depends on:** M2.0.

---

## M2.2 — Conserved attention advection (movement)

**Goal:** move occupancy/mass along the attention field **conserving mass exactly** (source-side flux limiter, non-negativity).
**Why now:** this is movement — and the load-bearing conservation invariant (Q1/Q2). It must be right before diffusion/reaction pile on.

### Tests first
- [ ] `tests/test_m2_advection.py`:
  - **Q1 conserves**: `advect(mass, α)` preserves `mass.sum()` to float tol, for random fields and many steps.
  - **Q2 non-negative**: outflow per source cell ≤ its mass ⇒ `mass.min() ≥ 0` always.
  - **Q6 blob translates**: with an interface field biased in one direction, a Gaussian mass blob's centroid moves that way over K steps (emergent movement, no move-action).

### Implementation
- [ ] `model/advection.py`: `advect(mass, alpha_out)` — `alpha_out[i,d]` = fraction of cell i's mass sent to neighbor d; **source-side normalize** so `Σ_d alpha_out ≤ 1` (flux limiter, CFL-like); scatter-add to neighbors via shifted tensors. Returns `(new_mass, flux_report)` for the ledger.

### Integration check
- [ ] Full-grid conservation over 1k steps with random directional fields: `|mass.sum() − initial| < tol`.

### Acceptance
- [ ] `test_m2_advection.py` green (conserves, non-negative, blob translates).

**Depends on:** M2.1.

---

## M2.3 — Diffusion + reaction (the full RDA tick)

**Goal:** assemble `h ← h + D_c∇²h − ∇·(𝐯h) + F_θ(h,m)` in one batched, synchronous pass.
**Why now:** completes the §10.5 update; diffusion (reuse `env.diffusion.laplacian`) + a pointwise reaction MLP close the mechanism.

### Tests first
- [ ] `tests/test_m2_rda.py`:
  - **Q4 no-cell-loop**: structural scan of `model/*.py` finds no grid loop; wall-clock budget for 500 ticks on 64×64.
  - **Q5 synchrony**: the update is double-buffered (recomputing from a copy gives the identical result).
  - bounded: hidden state stays finite over 1k ticks (no blow-up with the reference `θ`).

### Implementation
- [ ] `model/reaction.py`: `reaction(hidden, m, genome)` — a per-cell MLP (numpy matmuls + nonlinearity), the difference-amplifying term.
- [ ] `model/rda.py`: `rda_step(state, genome, cfg)` — per-channel `D_c·laplacian(h)` + `advect` (M2.2) + `reaction`, double-buffered, one pass.

### Acceptance
- [ ] `test_m2_rda.py` green (no-loop, synchrony, bounded).

**Depends on:** M2.2.

---

## M2.4 — Engine + viewer + demo (the transformer Game of Life, live)

**Goal:** run the RDA tick as a simulation coupled to the nutrient feed, conserved and viewable; demonstrate emergent move/morph/merge with fixed `θ`.
**Why now:** it's the user-facing deliverable — the transformer Game of Life you can watch.

### Tests first
- [ ] `tests/test_m2_engine.py`:
  - **Q1 full conservation**: mass + coupling to nutrient feed conserved over N ticks (ledger residual < tol).
  - **Q6 determinism**: same seed+θ → identical per-tick hash.
  - runs end-to-end from `configs`.

### Implementation
- [ ] `sim/nca_engine.py`: `NCAEngine` — owns the `NCAState`, steps `rda_step`, couples mass birth/decay to the nutrient field via the `TransactionLedger` (feed/kill), snapshot for the viewer (mass + a hidden-channel projection).
- [ ] `sim/server.py`/`controller.py`: an `--engine nca` option so `SimController` can run the NCA engine; extend `/state` with a `mass` grid; viewer gains a "Cells" field button.
- [ ] `sim/host.sh`: `ENGINE=nca` knob.

### Integration check
- [ ] `bazel run //projects/thermolife:serve -- --engine nca` → the viewer shows a moving/morphing pattern; conservation residual stays bounded.

### Acceptance
- [ ] `test_m2_engine.py` green; full `bazel test //projects/thermolife:test_suite` green; endpoint shows the transformer Game of Life live.

**Depends on:** M2.3.

---

## §A — Golden path (M2 spine)

```
GIVEN  seed+θ fixed, a directional/attention interface field, a mass blob + nutrient feed
WHEN   NCAEngine runs the RDA tick for N steps
THEN   total mass (+ ledger-booked feed/kill) is conserved to tol       (Q1)
AND    mass stays non-negative every tick                               (Q2)
AND    the pattern's centroid moves (emergent advection)                (Q6)
AND    the per-tick state hash is reproducible across two runs          (Q6)
```

## §B — Iteration loop
Same as the Slice-0 plan: read the failing assertion; fix test or impl (minimum change or rewrite the file fresh against the test); re-run the failing test → run §A → green. Conservation bugs → print `mass.sum()` and the ledger delta before diagnosing. A single-file rewrite of `advection.py` is a valid escape.

## §C — Out of scope (deferred)
- **M2b — gradient training (torch).** TBPTT to meta-train `θ` for survival, the "population survives unseen conditions" success gate. Needs torch in the Bazel build (`thermolife_deps` + a `train/` loop) and is an uncertain research slice — separate plan.
- **M3 learned interfaces / M4 plasticity** — `ℓ,ρ` stay from fixed `θ` here (morphing over a *lifetime* is M4); **M5** nonstationarity, **M6** reproduction, **M7** particles.
- Learned per-channel diffusivities, equivariant/steerable stencils.

## §D — Design tensions
- **D1. Mass as a separate field vs reuse `energy`/`alive`.** Rec: a dedicated `mass`/occupancy channel — cleaner conservation accounting than overloading `energy`; couples to nutrient via the ledger.
- **D2. Attention over 4 vs 8 neighbors.** Rec: start 4 (von Neumann) — matches the diffusion stencil and the flux limiter is simpler; revisit for richer motion.
- **D3. Reaction MLP depth.** Rec: one hidden layer — enough for autocatalysis-like amplification, keeps the fixed-`θ` demo legible and fast.
- **D4. Couple to the existing forager substrate or run standalone.** Rec: standalone `NCAEngine` sharing the ledger + nutrient physics; leave the Slice-0 forager untouched as the baseline/reference.

## Definition of done (M2a)
- [ ] `bazel test //projects/thermolife:test_suite` green incl. Q1–Q6; no torch imported.
- [ ] `bazel run //projects/thermolife:serve -- --engine nca` shows a live pattern that **moves and morphs**, conserving mass.
- [ ] Modular commits `thermolife(M2.0..M2.4): …`, each green at commit.
- [ ] §C clearly records that gradient-trained survival (M2b) is deferred and why.
