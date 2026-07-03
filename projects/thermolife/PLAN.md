# thermolife — A Continuous Thermodynamic Neural Cellular Automaton

> **Status: design only, no implementation yet.** This document is the source of truth for scope, invariants (I1–I15), risks (R1–R14), architecture, components (§12), the vertical Slice 0 (§15), and the milestone roadmap M1–M7 (§16). Read it before proposing changes that cross layers.

---

## 1. Goal

Build a 2D artificial world in which a **shared local neural rule** drives cells that continuously sense, expose learned ligand/receptor interfaces, selectively bind and exchange resources, predict their local future, update a slow plastic state from prediction error, and pay explicit energetic costs to move, signal, divide, repair, and die. There is **no single target shape**. The system must remain *viable* under continually changing conditions.

The research question, stated narrowly enough to falsify:

> Do locally-learned, visually-interpretable binding interfaces plus online predictive plasticity produce **measurably better** long-horizon viability and recovery than matched systems without those mechanisms, in a physically-constrained changing world?

The strongest possible result is **not** "it made pretty blobs." It is: plastic interfaces + local prediction + resource-constrained interaction beat *matched ablations* (frozen plasticity, randomized interfaces, no costs, no prediction) on long-horizon survival and shock recovery. If we cannot beat those ablations, the mechanisms are decorative and the hypothesis is not supported.

This is a **resource-constrained neural cellular automaton (NCA)** with local attention-like interaction and online plasticity — Growing-NCA machinery, but the static target image is replaced with *persistent viability in a dynamic world*.

## 2. Success Metrics

### 2.1 v0 — Slice 0 (physical substrate, no learning; §15)

- **Conservation residual** `|Σ(nutrient) + Σ(energy·χ) + Σ(waste·χ) − ledger|` stays below a fixed float tolerance over a 10k-tick rollout (I1).
- **Non-negativity** holds every tick for every field and every energy reserve (I2).
- A **hand-coded forager** survives indefinitely near a *static* nutrient gradient, and **dies within a bounded window** when the gradient is removed. This is the whole point of Slice 0: the physics has real stakes.
- Determinism: same seed + same `state_0` ⇒ byte-identical trajectory (I8).

### 2.2 v1 — post-slice metrics (the actual research payoff)

Grouped by what they measure (full definitions in §10.4):

```text
Viability            mean lifespan; lineage persistence; population-collapse rate; viable biomass over time
Thermodynamics       conservation residual; nutrient-uptake efficiency; waste per unit useful work; heat-stress exposure
Adaptation           recovery time after shocks; adaptation speed after env change; performance on UNSEEN schedules;
                     Δviability of plastic vs frozen-control population
Organization         binding selectivity; cluster lifetime; repair-after-lesion; diversity of stable strategies;
                     information flow between neighbors
Prediction           local next-state error; calibration under shift; whether better prediction PREDICTS later survival
```

The headline v1 claim requires **all four essential ablations** (§18) to move the metric in the predicted direction with a matched-compute control.

### 2.3 Non-goals (explicit)

- **Not** molecular thermodynamics or a literal cell-biology model. "Thermodynamic" here means *abstract physics with conservation constraints and per-action cost* (§3), not Gibbs free energy of real molecules.
- **Not** rewarding "low entropy" / "more order" directly — that is vague and trivially gamed (I10). Order must *emerge* from viability + costs.
- **Not** open-ended AGI/"life-like intelligence." That is a hypothesis this platform *studies*, not a claim it makes.
- **Not** particles first. Grid first (§6 rationale). Particles are Phase 7, gated behind a working grid.
- **Not** evolution first. Within-lifetime plasticity (M4) must work before reproduction/selection (M6).
- **Not** a beauty contest. No metric is an "interesting pattern" judged by eye (§19, F-Aesthetic).

## 3. Constraints

### 3.1 Hard

- **Explicit abstract physics with conservation.** Fields evolve by declared PDE-stencil updates (diffusion + decay + accounted source/sink). No channel changes except through a defined transaction.
- **Every useful action costs energy.** Uptake, movement, signaling, computation/plasticity, repair, division each debit `e_i` *before* the effect applies (I12). No un-costed action exists.
- **No per-cell Python loop in the hot path.** Neighborhoods are shifted tensors / `unfold` / conv stencils. Vectorized over the whole grid (I6).
- **Plasticity ≠ training.** Within an episode, base weights `θ,φ` are frozen; only fast state `h` (every tick), interface expression (every `k` ticks), and slow plastic state `z` (continuous) change (I9). The outer optimizer only steps at *detached* TBPTT chunk boundaries.
- **Determinism / replay** (I8). `torch.use_deterministic_algorithms(True)`, pinned seeds, logged RNG state.
- **Interface groundedness** (I11). The rendered ligand/receptor contour is a pure function of the *same* code that drives the binding kernel. A hand that morphs visually ⟺ its interaction kernel changed.

### 3.2 Soft

- **64×64** grid for the first real experiment; batched to fill one GPU. Larger later.
- **Cognitive state higher-dim than the visualization**: render interfaces in 2D while keeping 4–8 latent interface dims and 16-D hidden state internally.
- Prefer isotropic / steerable stencils to reduce axis dependence (R5), but Slice 0 may start axis-aware and *measure* the dependence rather than assume it away.
- One shared cell program across all cells (a "genome"). Heterogeneity comes from state/plasticity/mutation, not from per-cell architectures.

## 4. Positioning — what this is and isn't

| Axis | thermolife | Contrast |
|---|---|---|
| Target | persistent *viability* in a changing world | Growing-NCA: reconstruct a **fixed** target image |
| Learning | base rule meta-trained offline **+** online plasticity `z` within a lifetime | pure inference NCA (frozen after training) |
| Interaction | learned ligand/receptor binding with **energetic consequences** in a physical world | transformer attention over tokens (no physics, no cost) |
| Objective | continuing **average-reward** viability, soft barriers | one-time terminal reconstruction loss |
| "Free energy" | explicit resource accounting; statistical FE is *not* treated as literal heat | active-inference systems that reify a statistical FE as energy |

Be precise about the "no inference/training boundary" claim (from the proposal §2). Three honesty tiers:

- **Practical (what we build first, M2–M5):** base rules `F_θ, G_φ` are meta-trained offline; cells keep learning through `z` during simulation. There *is* still an outer loop.
- **Radical (M6):** cells reproduce, copy a mutated genome, selection acts through survival. Then there is *only* simulation + evolution — no external gradient optimizer.
- **Not actually unified:** repeatedly running backprop through the world is still an outer training loop even if the task never ends. We will not claim otherwise. This honesty is the analogue of quorum's "computed, not retrieved."

## 5. Architecture Decomposition

```text
┌─────────────────────────── World tensor  [B, H, W, C] ───────────────────────────┐
│  Physical channels: nutrient n · waste w · heat τ · pheromone · biomass/occupancy │
│  Cell channels:     energy e · alive-prob · hidden h[16] · plastic z[8] · orient[2]│
└───────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼   per-tick pipeline (§10.1) — pure functions over the world tensor
  ┌───────────────────────────────────────────────────────────────────────────────┐
  │ env/     : diffuse_and_decay → local_perception → apply_conservative_transactions │
  │            → lifecycle(death/decomp/division) → invariants                        │
  │ sim/     : forager · tick(loop) · runner · controller · server (Slice-0 ops+web)  │
  │ model/   : interface_heads (ligand,receptor,value) → binding → predictor         │
  │            → cell_core (Δh, actions) → plasticity_rule (Δz)                        │
  │ train/   : rollout · truncated_bptt · objective (avg-reward) · curriculum         │
  │ eval/    : perturbations · ablations · metrics · long_horizon                     │
  │ viz/     : world_renderer · interface_shapes · binding_animation · trajectories   │
  └───────────────────────────────────────────────────────────────────────────────┘
```

Layer ownership:
- **env/** owns the physics and conservation. It is the only layer allowed to change physical channels. It knows nothing about neural nets.
- **model/** owns the learned rule. It reads observations/messages, emits *action intents* and *transfer requests*; it never mutates fields directly — it hands intents to `env/apply_conservative_transactions`, which enforces cost and conservation.
- **sim/** owns the *operational* Slice-0 loop (forager, tick pipeline, headless runner) and the web control surface (a thread-safe start/pause/restart state machine + a stdlib HTTP server, exposed over Tailscale). Distinct from `train/`: `sim/` runs the world, `train/` trains the rule.
- **train/** owns the outer loop (TBPTT, objective, curriculum). Frozen `θ,φ` inside a chunk (I9).
- **eval/** owns falsification: ablations, perturbations, metrics, matched controls.
- **viz/** is read-only over the world; its interface renderer must call the *same* code path as the binding kernel (I11).

## 6. Why grid, not particles (v0)

A grid gives: Game-of-Life legibility, cheap vectorized simulation, deterministic local neighborhoods, direct field diffusion via stencils, and trivial rendering. Particles (radius graph, learned motion/adhesion/collision, equivariant message passing) are strictly harder to stabilize and evaluate. Move to particles (Phase 7 / M7) **only after** the grid produces nontrivial adaptive behavior. Orientation dependence is a real design issue even on a grid (original NCAs can leak world-axis dependence) — we *measure* it (I13 test) rather than assume isotropy.

## 7. Architecture Options Considered

| Option | Verdict |
|---|---|
| Particles-first (radius graph, EGNN) | **Rejected for v0.** Highest capability ceiling, but motion/adhesion/collision + equivariance make debugging and conservation accounting far harder. Deferred to M7. |
| Reward "order"/low-entropy directly | **Rejected (I10).** Vague, trivially gamed; kills the research claim. Order must emerge from viability+cost. |
| No plasticity, pure meta-trained inference NCA | **Kept as the M4 frozen-control**, not as the product. It is the thing we must beat. |
| Backprop-through-full-world (no truncation) | **Rejected.** Intractable memory; unstable. Use TBPTT with detached chunks (I9, §9). |
| Per-cell Python loop for clarity | **Rejected (I6).** Kills throughput and makes 64×64×B infeasible. Shifted tensors / `unfold` only. |
| Reify statistical free energy as the physics | **Rejected (§4).** Keep resource accounting explicit; FE analogy stays an analogy. |
| Grid + shared NCA rule + explicit physics + online plasticity | **Chosen.** Legible, vectorizable, conservation-checkable, and directly tests the hypothesis. |

## 8. Invariants (I1–I15)

The gate. Each is a test, an assertion, or a metric. The two starred ones are the anti-gaming invariants — the difference between a real result and a fooled one.

- **I1 — Conservation.** `Σ nutrient + Σ (energy·χ_e) + Σ (waste·χ_w)` changes *only* through declared sources/sinks (injection `s`, cooling to ambient, decomposition). Per-tick residual < fixed tolerance; cumulative residual bounded over 10k ticks.
- **I2 — Non-negativity.** No field concentration and no `e_i` ever goes negative. Clamping that would hide a leak is a bug, not a fix — clamp *and* assert the clamp did nothing beyond float epsilon.
- **I3 — No free energy.** Binding, signaling, message aggregation, and plasticity never create energy or mass. Every transfer is a zero-sum move between two accounted stores.
- **I4 — Dead cells are inert.** `alive_prob < θ_dead` ⇒ no uptake, no action, no message emission, no division. Decomposition returns biomass to fields *exactly once*, then the cell channel is cleared.
- **I5 — Locality.** Every cell update reads only its fixed-radius neighborhood. No global broadcast. Enforced by construction (stencils); tested by a permutation/independence check.
- **I6 — Vectorization.** No Python loop over cells in the hot path. Guarded by a structural test (and a wall-clock budget on 64×64×B).
- **I7 — Synchrony.** Actions computed from `state_t`, applied atomically to form `state_{t+1}`. Diffusion and transactions never read half-updated state (double-buffer).
- **I8 — Determinism / replay.** Same seed + same `state_0` ⇒ identical trajectory. Deterministic CUDA, logged RNG.
- **I9 — Parameter/plasticity separation.** Within a rollout chunk, `θ,φ` are frozen. Only `h` (every tick), interface expression (every `k` ticks), `z` (continuous) change. Optimizer steps only at detached chunk boundaries. Asserted by a hook that fails if `θ.grad` is applied mid-chunk.
- **I10 ★ — Thermodynamic honesty.** The reward contains **no** direct "lower entropy / more order / more structure" term. Organization is only ever an *emergent consequence* of viability soft-barriers + action/plasticity costs. Any term that scores order directly is a constitutional violation.
- **I11 ★ — Interface groundedness.** The rendered ligand/receptor contour `R(φ)` is a pure function of the *same* code that parameterizes the binding kernel `κ`. Test: perturb the code, assert both the rendered shape *and* the kernel change consistently; assert the renderer reads nothing the kernel doesn't.
- **I12 — Cost coverage.** Every action (uptake, move, signal, compute/plasticity, repair, divide) debits `e_i` *before* its effect applies. No un-costed action path exists (enumerated + tested).
- **I13 — Symmetry accounting.** World-axis dependence is *measured*, not assumed. Rotating/reflecting the world and the rule together changes trajectories only within a declared tolerance, or the dependence is logged as a known quantity.
- **I14 — Bounded interfaces & updates.** Finite receptor capacity, finite outgoing binding capacity, bounded plastic-update magnitude, bounded messages/cell. Prevents the "bind to everything" and "z runs away" collapses (R1, R2).
- **I15 — Bounded population.** Biomass/occupancy and population are bounded above (division gated by energy + space) and the collapse-to-zero case is detected and logged, not silently continued.

## 9. Core Entities and Interfaces

Dense tensors, SoA over the grid. No per-cell objects.

### 9.1 `World` (the single mutable state)
```text
fields  : [B, H, W, F]  physical channels — F = {nutrient, waste, heat, pheromone, biomass}
cells   : [B, H, W, ...] cell channels:
            energy      [B,H,W,1]
            alive       [B,H,W,1]   alive-probability in [0,1]
            hidden  h   [B,H,W,16]
            plastic z   [B,H,W,8]
            orient      [B,H,W,2]
ledger  : running scalar accumulator per conserved quantity (for I1)
rng     : logged RNG state (for I8)
```

### 9.2 `Observation` (all a cell may read — locality I5)
```text
local_fields   : neighborhood stencil of physical channels
self_cell      : this cell's energy/hidden/plastic/orient
neighbor_codes : neighbor ligand/receptor codes per direction (for binding)
```

### 9.3 `Interfaces`
```text
ligand   ℓ_{i,d}  = f_ℓ(h_i, z_i, d)     [B,H,W,D_iface] per cardinal direction d
receptor ρ_{i,d}  = f_ρ(h_i, z_i, d)     [B,H,W,D_iface] per cardinal direction d
value    v_i      = W_v h_i               [B,H,W,D_val]  (what a bound neighbor receives)
```

### 9.4 `Binding` (directional compatibility → attention-like weights)
```text
κ_{i→j}^d = σ( (b − |ℓ_{i,d} − ρ_{j,−d}|²) / T_bind )     compatibility, gated by alive_j
α_{ij}    = softmax_j( κ_{i→j} )                          normalized, capacity-limited (I14)
m_i       = Σ_{j∈N(i)} α_{ij} v_j                          aggregated message
```
Binding controls: information exchange, nutrient/metabolite transfer, adhesion, signaling, competition, repair cooperation, reproduction permission.

### 9.5 `Actions` (intents — env enforces cost & conservation)
```text
uptake, secrete, move(Δorient/step), adhere, divide, repair, die
```
The cell core emits *intents*; `env/apply_conservative_transactions` debits energy first (I12), then applies effects while preserving I1/I3.

### 9.6 `TransactionLedger`
Owns the conserved-quantity bookkeeping. Every source/sink is a named, logged entry. This is what I1 checks against — not a re-derived sum, a *ledger*.

## 10. Data Flow / Control Flow

### 10.1 Per-tick pipeline (the hot path)
```text
1. diffuse_and_decay(fields)                     # nutrient/waste/heat/pheromone: D∇² + decay + source s
2. obs = local_perception(fields, cells)         # I5 stencils, no global view
3. ligand, receptor, value = interface_heads(cells, obs)
4. bind = local_binding(ligand, receptor, alive) # κ, α, capacity limits (I14)
   message = aggregate_neighbor_values(bind, value)
5. prediction = predict_next_observation(h, obs, message)
6. Δh, actions = cell_core(h, z, obs, message, energy)
7. world = apply_conservative_transactions(world, actions, bind)   # cost-first (I12), conserving (I1,I3)
                                                  # uptake, secrete, move, adhere, divide, repair, death+decomp
8. next_obs = local_perception(world.fields, world.cells)
   prediction_error = next_obs − prediction
   z += plasticity_rule(z, h, prediction_error, energy, bind)      # slow, bounded (I14), NOT θ (I9)
9. h += Δh
10. log_stats(world)                              # conservation residual, survival, structure, adaptation
return world
```
Steps 1–10 are pure tensor ops. Double-buffered for synchrony (I7). Reference skeleton mirrors proposal §7; env/model split per §5.

### 10.2 The two-timescale update (proposal §2)
```text
h_{i,t+1} = F_θ(h_i, o_i, m_i, z_i)                         # fast state, every tick
z_{i,t+1} = z_i + G_φ(h_i, o_i, ε_i, e_i)   (bounded, I14)  # slow plastic state, continuous
```
Time constants, fastest → slowest: hidden `h` (every tick) · interface expression (every `k` ticks) · plastic `z` (slow continuous) · genome/base weights `θ,φ` (fixed within an episode; mutated only at reproduction, M6).

### 10.3 Physics (explicit, conservation-constrained)
```text
n_{t+1} = n_t + D_n ∇²n_t + s_t − u_t                                  # nutrient / free-energy field
w_{t+1} = w_t + D_w ∇²w_t + α u_t − δ_w w_t                            # waste / toxin
τ_{t+1} = τ_t + D_τ ∇²τ_t + β c_t − δ_τ(τ_t − τ_ambient)              # heat / stress
e_{i,t+1} = e_i + η·uptake_i − c_move − c_signal − c_plasticity − c_repair   # cellular energy reserve
```
Nutrient uptake depletes the environment; spending energy emits heat/waste; death returns biomass. Organized behavior is therefore contingent on exploiting *external* gradients — you cannot get something for nothing (I3).

### 10.4 World objective (continuing average-reward, not terminal)
```text
max_{θ,φ}  liminf_{T→∞} (1/T) E[ Σ_t Σ_i ( r_viability,i + r_repro,i − c_action,i − c_plasticity,i − λ_pred ℓ_pred,i ) ]

r_viability,i = − B(e_i) − B(τ_i) − B(w_i)      # soft barriers B(·) rise sharply near lethal thresholds
```
Term jobs: **viability** keeps cells in a survivable regime · **reproduction/biomass** turns survival into lineage persistence · **action cost** bounds motion/signaling/compute · **plasticity cost** stops free reshaping of interfaces · **prediction loss** makes cells learn environmental regularities. Note (I10): none of these is an "order" term.

## 11. State Machines / Lifecycles

### 11.1 Cell lifecycle
```text
seed/born ──► alive ──► (energy < e_lethal | τ > τ_lethal | w > w_lethal) ──► dying ──► decomposed
                │                                                                          │
                ├─ divide (energy ≥ e_div ∧ free neighbor ∧ binding permission) ──► child  │
                └─ repair (spend energy to restore self/neighbor)          decomp returns biomass→fields (once, I4)
```

### 11.2 Interface expression lifecycle
Expressed from `(h,z,d)` every tick but *committed* (used for major transfers) only after a binding-duration hold (R1 mitigation): transient compatibility ≠ instant resource transfer.

### 11.3 Plastic-state lifecycle
`z` drifts continuously under `G_φ` from prediction error + energy state, bounded (I14), with slow decay so a cell can *forget* a stale adaptation after a distribution shift.

## 12. Component Specifications

- **env/diffusion.py** — stencil diffusion + decay for each field (§10.3). Isotropic stencil option (R5). Owns no cells.
- **env/fields.py** — field channel layout, source injection `s`, ambient constants.
- **env/transactions.py** — `apply_conservative_transactions`: the *only* mutator of physical channels. Cost-first (I12), zero-sum transfers (I3), ledger updates (I1).
- **env/lifecycle.py** — birth/division/death/decomposition; dead-cell inertness (I4); population bound (I15).
- **env/invariants.py** — runtime assertions for I1–I4, I12, I15; called every tick under a debug flag, sampled in production.
- **model/interfaces.py** — `f_ℓ, f_ρ`, value head; per-direction codes; expression cost + noise (Phase 3 constraints, R1).
- **model/binding.py** — `κ`, `α` softmax with receptor/outgoing capacity limits (I14); adhesion/transfer/signaling routing.
- **model/predictor.py** — local next-observation predictor; produces `ε` (informative targets to dodge R11).
- **model/cell_core.py** — `F_θ`: `(h,z,o,m,e) ↦ (Δh, actions)`. Shared across all cells.
- **model/plasticity.py** — `G_φ`: bounded slow update to `z` from `(h,o,ε,e,bind)`; differentiable-plasticity-style so updates are *useful*, not noise.
- **train/rollout.py** — chunked rollout, persistent world state across chunks.
- **train/truncated_bptt.py** — random-length chunks, carry state, **detach at boundaries** (I9), backprop within chunk.
- **train/objective.py** — average-reward viability objective (§10.4); soft barriers; no order term (I10).
- **train/curriculum.py** — the nonstationarity schedule (Phase 5 / M5); randomized speed/amplitude/direction/duration.
- **eval/perturbations.py** — moving gradient, source relocation, heat waves, toxic pulses, terrain damage, cell ablation, unseen shock timing.
- **eval/ablations.py** — the seven essential ablations (§18) with matched-compute controls.
- **eval/metrics.py** — the four metric families (§2.2, §10.4).
- **eval/long_horizon.py** — 10k+ tick viability & conservation-drift runs.
- **viz/world_renderer.py** — field & occupancy render.
- **viz/interface_shapes.py** — `R(φ)=r₀+a₁cosφ+b₁sinφ+a₂cos2φ+b₂sin2φ` from the *actual* ligand/receptor code (ligand → outward lobes, receptor → complementary indentations). Groundedness (I11).
- **viz/binding_animation.py** — animate binding events; morphing hand ⟺ changed kernel.
- **viz/trajectory_plots.py** — metric trajectories, ablation overlays.

## 13. Cost Model (compute)

- Slice 0 (no learning): pure tensor physics on 64×64×B — CPU-feasible, trivially GPU-batched.
- M2+ (meta-training): TBPTT dominates. Memory ∝ chunk_length × B × H × W × channels. Random short chunks (§9) keep it bounded; long-horizon viability is achieved by *carrying detached state across chunks*, not by long backprop windows.
- Rendering is off the hot path (eval/viz sampled every N ticks).
- Budget discipline: a wall-clock/tick gate on 64×64×B is part of I6's test so a "clever" but slow rule is caught early.

## 14. Infrastructure & Scaling

Single GPU for the first experiment. World tensor is `[B,H,W,C]`; batch fills the GPU. Scaling path (post-M6): larger grids, sharded batch, isotropic/steerable stencils. Python (uv) + PyTorch; numpy for pure-physics reference implementations used by conservation tests. No custom kernels until profiling on the real workload demands them (grid physics vectorizes well without them).

## 15. Vertical Slice Strategy

### 15.1 Slice 0 — *"the physical substrate has real stakes, with zero learning"*
Corresponds to proposal **Phase 0**. Build only:
- nutrient diffusion + replenishment; waste diffusion + removal; heat diffusion + cooling;
- conservative nutrient→energy conversion; action costs; death + decomposition;
- **one hand-coded forager** that climbs the nutrient gradient and pays movement cost.

Config is fixed in `configs/world.yaml` (64×64, static gradient, diffusion/decay constants).

### 15.2 What Slice 0 proves
- The physics conserves (I1), stays non-negative (I2), invents no energy (I3), and keeps dead cells inert (I4) over a 10k-tick run.
- Behavior has **stakes**: the forager survives on a static gradient and *dies* when the gradient is removed. If death doesn't happen on gradient removal, the cost model is wrong — fix it before any neural net obscures the cause.
- Determinism/replay (I8) works end-to-end.

### 15.3 What Slice 0 defers
Everything learned: no `interface_heads`, no `binding`, no `predictor`, no `cell_core`, no `plasticity`, no TBPTT, no curriculum, no evolution, no particles. Interfaces are *hand-assigned fixed types* only when Phase 1 (M1) begins.

## 16. Milestone Roadmap (post Slice 0)

Each milestone maps to a proposal phase and carries a **binary success condition**.

- **M1 — Hand-coded artificial-chemistry baseline** (Phase 1). Three fixed cell types: forager (climbs nutrient), producer/collector (converts efficiently, moves poorly), scavenger (eats waste/dead biomass). Fixed ligand/receptor types. *Success:* visible binding, resource/info transfer, and population shifts when the environment changes — with the renderer, accounting, and selection pressures all legible *before* neural nets enter.
- **M2 — Shared NCA rule replaces hand-coded control** (Phase 2). One shared `(h,z,o,m) ↦ (Δh, actions)`, **plasticity off**. Objectives: survival under moving nutrient, energy efficiency, recovery after random deletion, bounded biomass, no waste/heat collapse. *Success:* a genetically identical population survives conditions **not in its initial state**.
- **M3 — Learn hands & receptors** (Phase 3). Turn on learned ligand/receptor codes with the anti-trivial constraints (finite receptor + outgoing capacity, per-interface energetic cost, neighbor competition, expression noise, binding-duration-before-transfer — I14, R1). *Success:* cells use **different interfaces for different functional interactions**, and a receptor lesion causes a **specific** behavioral deficit (not global degradation).
- **M4 — Predictive learning + plasticity** (Phase 4). Prediction targets: local nutrient change, incoming-signal change, temperature/waste change, whether a neighbor stays bound, whether own energy rises/falls. Prediction error updates `z` (not `θ`, I9). Separate time constants (§10.2). *Success:* after a distribution shift, **plastic cells regain viability faster than an identical frozen-control** population. This is the core hypothesis test.
- **M5 — Permanently nonstationary environment** (Phase 5). Curriculum: static island → drifting source → seasonal schedule → heat waves → toxic pulses → terrain damage → density changes → rotating gradients → new nutrient chemistry → recurring-but-not-identical cycles. **Randomize** speed/amplitude/direction/duration/causal structure — never train on one periodic schedule. *Success:* adaptation **transfers to unseen schedules** rather than memorizing one cycle.
- **M6 — Reproduction + evolution** (Phase 6). Cells reproduce above an energy threshold; child inherits shared genotype + slightly mutated genome code + limited inherited state (no full memory copy). Selection replaces much reward engineering. *Success:* distinct persistent strategies arise and stay viable across change **without manually assigned roles**. (Hardest to stabilize/evaluate — R12.)
- **M7 — Grid → continuous particles** (Phase 7). Radius-graph neighborhood `N(i)={j:|p_i−p_j|<r}`; learned motion/adhesion/collision/binding in continuous space; rotation/translation-equivariant interactions (EGNN-style) so rotating the world doesn't change its laws. *Success:* the grid-era adaptive behaviors reappear in continuous space without axis artifacts.

## 17. Verification Strategy

### 17.1 Always-on (every test run)
Conservation (I1), non-negativity (I2), no-free-energy (I3), dead-inertness (I4), cost-coverage (I12), replay determinism (I8). These are `tests/test_conservation.py`, `tests/test_death_and_reproduction.py`, and the symmetry probe `tests/test_symmetry.py` (I13).

### 17.2 Per-milestone gates
Each M's binary success condition (§16) is a checked-in test/scenario, with a **matched-compute control** where a comparison is claimed (M4's frozen control, M3's lesion specificity, M5's unseen-schedule holdout).

### 17.3 The essential ablations are part of verification, not an afterthought
Run §18 from the beginning. A metric improvement that survives none of the ablations is not a result.

### 17.4 Honest reporting
Report what was **not** run and why (matched-compute caveats, seeds, schedule holdouts). "Adaptation improved" with no frozen control is not reportable. No aesthetic claims (§19).

## 18. Essential Ablations (run from day one)

| Ablation | What it tests | Predicted direction |
|---|---|---|
| Freeze plasticity | Is lifetime learning actually useful? | plastic > frozen on recovery |
| Randomize ligand/receptor codes | Do interfaces causally matter? | randomized worse; lesions non-specific |
| Remove energy costs | Is behavior driven by real tradeoffs? | costless → degenerate / unbounded action |
| Remove prediction loss | Does prediction improve adaptation? | no-pred adapts slower |
| Freeze environment | Are dynamic-world skills necessary? | static-trained fails on shifts |
| Delete random cells | Is organization regenerative or brittle? | organized recovers; brittle doesn't |
| Shuffle neighbor messages | Is local communication carrying real info? | shuffled degrades transfer/coordination |

## 19. Known Failure Modes

- **F-Trivial (R1):** every cell binds to everything → chemistry collapses. Guard: I14 capacity/cost/noise/competition/duration.
- **F-Runaway (R2):** `z` or `h` diverges. Guard: bounded updates (I14), decay, differentiable-plasticity base so updates are useful.
- **F-Leak (R3):** float / operation-order error accumulates in conservation over long horizons. Guard: ledger (not re-summed truth) + fixed transaction order + long_horizon drift test.
- **F-Goodhart (R4):** reproduction term degenerates to divide-and-die spam; or cells sit exactly at a soft-barrier knee. Guard: barrier shape review, lineage-persistence metric (not raw division count).
- **F-Axis (R5):** rule leaks world-axis dependence. Guard: I13 symmetry probe; isotropic stencils.
- **F-Shortcut (R11):** predictor emits a constant and still lowers loss. Guard: informative/normalized targets; predictive-competence-predicts-survival check.
- **F-Aesthetic:** "pretty blobs" reported as adaptation. Guard: I10 + mandatory matched ablations (§18). **This is the failure the whole verification strategy exists to prevent.**
- **F-Collapse/Explode (R9, R15):** population → 0 or saturates. Guard: I15 bound + collapse detection (logged, not silently continued).

## 20. Risks and Bottlenecks (R1–R14)

| # | Risk | Mitigation |
|---|---|---|
| R1 | Trivial "bind-everything" solution (Phase 3) | I14 finite capacity, per-interface cost, competition, expression noise, binding-duration-before-transfer |
| R2 | Plasticity instability (`z`/`h` diverge) | bounded updates (I14), slow decay, differentiable-plasticity base |
| R3 | Conservation leakage via float/op-order | ledger of record + fixed transaction order + long-horizon drift test |
| R4 | Reward gaming / Goodhart | soft-barrier shape review; lineage-persistence over raw counts; no order term (I10) |
| R5 | World-axis dependence | I13 symmetry probe; isotropic/steerable stencils |
| R6 | TBPTT truncation too short for slow-plasticity credit | random chunk lengths, carry detached state, tune window vs `z` time constant |
| R7 | Overfitting one nonstationary schedule (Phase 5) | randomize speed/amplitude/direction/duration; unseen-schedule holdout is the M5 gate |
| R8 | Emergence-faking ("pretty blobs") | matched ablations (§18) are mandatory; I10 |
| R9 | Population collapse or explosion | I15 bound + collapse detection; barrier tuning |
| R10 | Compute cost of long rollouts / meta-training | short random TBPTT chunks; state carry; sampled eval; I6 wall-clock gate |
| R11 | Predictor shortcut (constant prediction) | informative normalized targets; competence-predicts-survival check |
| R12 | Evolution instability / evaluability (Phase 6) | gate M6 behind working M4; lineage metrics; long-horizon holdouts |
| R13 | Interface renderer drifts from kernel | I11 groundedness test; renderer reads only kernel inputs |
| R14 | Determinism silently broken by CUDA | I8 replay test in CI; deterministic algorithms; logged RNG |

## 21. Implementation Standards

- env/ is the sole mutator of physical channels; model/ emits intents only. This boundary is what makes I1/I3/I12 checkable in one place.
- No per-cell Python loops; shifted tensors / `unfold` / conv stencils only (I6).
- Explicit expected failure: transaction and lifecycle functions return `(new_world, TransactionReport)` where the report carries typed error codes (over-budget action, blocked division, conservation-residual-exceeded) — never a silent neutral default.
- Every behavior change ships with a test; every performance claim ships with a benchmark; invariants are tests/assertions/metrics, not comments.
- Report verification truthfully, including what was not run.

## 22. Recommended Next Step

Land **Slice 0** (§15.1) and nothing else in the first batch:
1. `env/fields.py`, `env/diffusion.py`, `env/transactions.py`, `env/lifecycle.py`, `env/invariants.py` — the physics.
2. A hand-coded forager (not the NCA) that climbs the gradient and pays movement cost.
3. `tests/test_conservation.py` (I1–I3, I12), `tests/test_death_and_reproduction.py` (I4 death path), plus the I8 replay test.
4. `configs/world.yaml` with the 64×64 static-gradient setup.

Do **not** start M1+ (no learned interfaces, no NCA, no plasticity, no evolution, no particles) until Slice 0 is green on the always-on invariants and the forager demonstrably dies when the gradient is removed.

## 23. Deferred Complexity

Particles / radius graph / EGNN equivariance (M7) · reproduction & mutation genetics (M6) · multiple hand-coded chemistries beyond the three baselines · steerable/isotropic-NCA rework if I13 shows large axis dependence · multi-GPU sharding · custom CUDA neighborhood kernels (only if profiling demands) · richer nutrient "chemistry" species.

## 24. Open Questions / Decision Points

1. **Barrier shape.** Exact `B(·)` for energy/heat/waste — piecewise? logistic? — governs whether cells park at the knee (R4). Decide empirically at M2.
2. **TBPTT window vs plasticity time constant.** How short can chunks be before slow-`z` credit assignment breaks (R6)?
3. **Interface dimensionality.** 4-D ligand/receptor per direction (proposal §12) vs higher — tradeoff selectivity (M3) against expression cost.
4. **Isotropy now or later.** Start axis-aware and measure (I13), or pay for isotropic stencils up front? Default: measure first.
5. **How much inherited state at reproduction (M6).** "Limited internal state, no full memory copy" — what exactly transfers?
6. **Average-reward vs discounted objective** for the outer loop given TBPTT chunking (§10.4).
7. **Where reproduction reward stops and pure selection starts** (the M6 "collapse training into simulation" honesty boundary, §4).

## 25. Related Systems

- **Growing / Self-classifying NCA** — repeated local neural rule → global organization + regeneration. We swap the fixed target image for persistent viability.
- **Goal-conditioned NCA** — local systems driven to change behavior dynamically rather than converge once.
- **Differentiable plasticity / neuromodulated variants** — base parameters trained so within-lifetime plastic updates are *useful*, not noise. Our `G_φ`.
- **Active inference / allostatic control** — homeostasis + prediction; we keep resource accounting explicit rather than reifying statistical free energy as heat.
- **EGNN / equivariant message passing** — the M7 particle machinery.
- **Sibling project `quorum`** — same repo, same "emergence must be earned, not faked" methodology (their I6 "computed not retrieved" ≈ our I10 "thermodynamic honesty").

### One-paragraph summary
thermolife is a resource-constrained neural cellular automaton on a 2D grid: one shared local neural rule gives every cell a fast hidden state and a slow plastic state, learned ligand/receptor interfaces that bind and trade resources with energetic consequences, and a local predictor whose errors reshape the plastic state online. An explicit, conservation-checked abstract physics (nutrient/waste/heat fields, per-action energy cost, death→decomposition) makes organized behavior contingent on exploiting external gradients. The objective is continuing average-reward *viability* — never a target shape and never a direct reward for "order." The entire point of the design is falsifiability: a first experiment (moving nutrient, diffusing waste, heat cost, periodic shocks on 64×64) plus seven mandatory ablations tests one question — do learned interfaces + online predictive plasticity measurably improve long-horizon survival and recovery over matched controls, or are they decorative?
