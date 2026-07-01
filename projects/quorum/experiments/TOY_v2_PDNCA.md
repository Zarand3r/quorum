# Toy v2 — Petri Dish Neural Cellular Automata (PD-NCA)

> **Status: spec only.** Implementation comes after [`TOY_v1_SCHELLING.md`](TOY_v1_SCHELLING.md) ships. The v1 toy validates quorum's hot path; this v2 toy implements the *other side of the architectural bet* — what a Sakana-style differentiable multi-agent NCA actually delivers on a comparable substrate, so quorum's "LLM-as-rule unlocks emergence NCAs can't access" claim is held against a real reference rather than a paper-citation.

---

## 1. Purpose

Three reasons this toy exists, in priority order:

1. **Establish the baseline quorum must beat or honestly admit losing to at PLAN.md §16 M6.** Quorum's whole cost story (PLAN.md §13) assumes the LLM rule is justified by problems NCAs can't access. A real, runnable PD-NCA baseline is the only way to know which problems those are.
2. **Internalize the Digital Ecosystems engineering refinements before applying them to the LLM substrate.** Sakana's follow-up paper documents six refinements that proved *necessary* (not optional) for stable multi-species PD-NCA: presence gating, emergency respawn, differentiable growth gate, spatial concentration, win-rate feedback, soft-min loss. We will hit the LLM-substrate analogues of each at PLAN.md M6+; better to first feel them on the simpler substrate.
3. **Sanity-check the "computed-not-retrieved" emergence claim (PLAN.md I6 / R1).** PD-NCA agents have *no* prior — the conv-nets are randomly initialized and learned online. Whatever they emerge into is provably computed, not retrieved. That makes PD-NCA a cleaner irreducibility-test platform than any LLM-based toy. Differences in emergence between v1 and v2 are diagnostic of how much of v1's "emergence" is retrieved.

This toy is **not** a step toward Slice 0. It is a sibling reference point. Slice 0 keeps the LLM-as-rule commitment regardless of what v2 shows.

---

## 2. What v2 keeps from v1

The architectural shape is identical to v1 (and to PLAN.md §5):

- 2D substrate, synchronous tick.
- Locality — each cell's update reads only its 3 × 3 neighborhood.
- Replay determinism with seeded RNG (now also conditional on optimizer state).
- Bounded substrate (no off-grid leakage).
- Single forward call per species per tick.

## 3. What v2 changes from v1

| Property | v1 (LLM Schelling) | v2 (PD-NCA) |
|---|---|---|
| Local rule | Frozen LLM forward pass on text | Trainable conv-net per species, randomly initialized |
| Cell representation | Sparse: agent or empty; discrete color | Dense: every cell is a continuous C-channel float vector |
| Update | One batched LLM call across all agents | Per-species conv pass over the whole grid (K calls, one per species) |
| Output | Single discrete action token | Continuous channel delta (residual update) |
| Trainable params | 0 | ~3 K – 50 K per species |
| Loss / objective | None | Per-species survival reward, backprop online |
| Update direction | Forward only | Forward + backward through differentiable substrate |
| Competition | None | Attack / defense cosine-similarity when two species contend for a cell |
| Substrate | numpy on CPU | torch on GPU, end-to-end differentiable |
| Replay determinism inputs | RNG seeds only | RNG seeds + initial conv-net weights + optimizer state |
| Population | ~30 agents | Every cell on the grid is a "cell of some species" (full density) |

---

## 4. Architecture (per tick)

```
┌──────────────────────────────────────────────────────────────────────┐
│ State at time t                                                      │
│   state_channels: torch.Tensor [H, W, C]   (continuous)              │
│   species_id:     torch.Tensor [H, W]      (int, 0 = empty)          │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
  per-species forward      per-species forward     per-species forward
   conv_net_1(state)        conv_net_2(state)       conv_net_3(state)
   → delta_1[H,W,C]         → delta_2[H,W,C]        → delta_3[H,W,C]
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
                                  ▼
              Masked residual update:
                state += sum_k (mask_k * delta_k * growth_gate(alive))
                                  │
                                  ▼
              Competition resolution (where cells contend):
                winner = argmax_k cos_sim(attack_k, defense_other_k)
                                  │
                                  ▼
              Presence gating:
                cells with alive_channel < threshold → species_id = 0
                                  │
                                  ▼
              state_{t+1}, species_{t+1}
                                  │
                                  ▼
              Every T_train ticks:
                reward_k = territory_held_by_species_k
                loss = -sum_k reward_k
                loss.backward() through rollout
                optimizer.step() for each conv_net_k
```

All operations are differentiable. Gradients flow through every tick of the rollout window, which is what enables the **continual online training** that distinguishes PD-NCA from classical (pre-trained, then frozen) NCAs.

---

## 5. Cell representation

Every cell is a length-C float vector. Default `C = 16` (configurable). Channel layout:

| Channels | Semantic | Notes |
|---|---|---|
| `0` | `alive` | Smooth alive mask in [0, 1]. Drives presence gating + growth gate. |
| `1 – 3` | RGB | For visualization only; no semantic effect on rule. |
| `4 – 7` | `attack` vector | Used in competition resolution. |
| `8 – 11` | `defense` vector | Used in competition resolution. |
| `12 – 15` | hidden state | Free channels the conv-net can shape during training. |

Plus a single int per cell: `species_id ∈ {0, 1, …, K}` where 0 = empty.

The split is configurable (`C` and the channel groupings live in `CellConfig`). The 4-4-4-4 default is taken from the PD-NCA paper.

---

## 6. Per-species conv-net architecture

Each species has its own small conv-net. Default architecture (small enough to fit ~3 species + a 64 × 64 grid on a consumer GPU):

```
Conv2d(C, 32, kernel=3, padding=1)   # 3×3 neighborhood, padding-zero borders
ReLU
Conv2d(32, 32, kernel=1)             # per-cell MLP
ReLU
Conv2d(32, C, kernel=1)              # emit channel delta
```

Params: ~5 K per species. Three species = ~15 K total trainable params. Tiny.

The kernel-3 first layer is the *only* place each cell sees its neighborhood. After that, everything is 1 × 1, so **locality is enforced by the architecture itself** (Invariant A1 below).

---

## 7. Update mechanics

### 7.1 Residual update

Cells update via residual delta from their species' conv-net:

```python
delta_k = conv_net_k(state)                   # [H, W, C]
mask_k  = (species_id == k).float()           # [H, W]
gate    = growth_gate(state[..., ALIVE_CH])   # [H, W], smooth
state   = state + (mask_k * gate)[..., None] * delta_k
```

Two of the Digital Ecosystems refinements show up here:

- **Differentiable growth gate.** `growth_gate` is a smooth (sigmoid-like) function of the alive channel rather than a hard threshold. Cells just below `alive ≈ 0` get *almost* no update, cells just above get *almost* full update. Smooth so gradients flow.
- **Per-species mask** prevents species *k*'s conv-net from updating cells owned by species *j*. The mask must be detached from the species-id gradient path so a species can't learn to "claim" cells indirectly through its own gate.

### 7.2 Competition resolution

When two adjacent cells of different species both try to influence the same target cell (because the conv kernel reaches across the species boundary), the competition mechanic decides which gets to write.

Per PD-NCA:

```python
score(attacker_k, defender_j) = cos_sim(attack_k_vec, defense_j_vec)
winner = argmax_k score(k, j)                  # differentiable via Gumbel-softmax
```

For training stability the argmax is approximated with a temperature-controlled softmax during the backward pass (Gumbel-softmax-style; temperature anneals over training).

### 7.3 Presence gating

The first Digital Ecosystems refinement: **cells with `alive` below a threshold die** — `species_id ← 0`, channels zeroed. This prevents ghost cells (slowly-dying populations whose existence is mathematically nonzero but visually invisible) from accumulating gradient signal forever.

---

## 8. Training loop

Continuous training during simulation is the PD-NCA-distinguishing property. The loop:

```python
for window_start in range(0, total_ticks, rollout_window):
    state = state.detach()                     # break the previous graph
    rewards = torch.zeros(K)
    for t in range(rollout_window):
        state = tick(state, species_id, conv_nets)
        rewards += per_species_reward(state, species_id)
    loss = -rewards.sum()                      # maximize total survival
    loss.backward()
    for opt in optimizers: opt.step(); opt.zero_grad()
```

Rollout window defaults to 32 ticks (truncated BPTT). The full forward graph for a 32-tick rollout on a 64×64×16 substrate is ~30 MB of activations — fits a single consumer GPU.

### 8.1 Reward function

`per_species_reward(state, species_id, k) = sum_cells((species_id == k) * alive_channel)`

That is, "territory held, weighted by aliveness." Other choices are possible (mean alive over the run, area-under-curve, terminal area); start with the simplest, document the bias, iterate.

### 8.2 Why truncated BPTT (not full)

A 1000-tick rollout would need ~1 GB of forward activations per species. Truncated BPTT at 32 ticks is the standard solution; it costs nothing in expressiveness because the substrate's dynamics are local and short-correlated.

---

## 9. Invariants

Lettered to distinguish from the LLM-toy / quorum invariants. Each maps to a test in `tests/test_pdnca_invariants.py` (file to be created when the implementation lands).

| ID | Invariant | Verification |
|---|---|---|
| **A1** | **Locality.** A cell's update reads only its 3 × 3 neighborhood. | Architectural — first conv layer is the only kernel-> 1 op; verified by counting `nn.Conv2d` layers with `kernel_size > 1`. |
| **A2** | **Synchrony.** `state_{t+1}` is computed from `state_t` only. | Snapshot diff assertion: clone `state` before `tick`, run, confirm input clone is untouched. |
| **A3** | **End-to-end differentiable.** Forward function is differentiable through the full rollout window. | `torch.autograd.gradcheck` on a 4×4 toy grid, 2-tick rollout. |
| **A4** | **Replay determinism.** Same seed + same initial conv-net weights + same optimizer state → byte-identical trajectory. | Two-run diff test, mirroring v1's I8. |
| **A5** | **Per-species update independence.** Species *k*'s conv-net does not see species *j*'s weights in the forward pass. | Code-structural: each `conv_net_k` is a separate `nn.Module` instance with its own `state_dict`; tested by parameter-graph inspection. |
| **A6** | **Bounded loss.** Per-species reward magnitudes stay within a fixed range, even under runaway growth. | Reward bounded above by grid area × C; assertion in training loop. |
| **A7** | **No spontaneous species creation.** Presence gating only removes; new live cells come only from explicit growth-gate flow out of existing live cells of the same species. | Test: place a single seed of species 1, run 100 ticks with conv-nets frozen at init, assert species 2 cells never appear. |
| **A8** | **Single-GPU runnable at the default config.** 64 × 64 × C=16 × K=3 fits on a 16 GB consumer GPU. | Memory measurement in the smoke run. |

---

## 10. Success criteria

For v2 to be considered "working" the following all hold on a clean run with the defaults below:

1. **Runs to completion.** 2000 ticks at H=W=32, C=16, K=2 in < 5 minutes on a single consumer GPU. (Larger grids are stretch.)
2. **Replay determinism (A4) passes.** Two seeded runs produce byte-identical trajectories.
3. **Architectural invariants A1, A2, A3, A5, A7 pass as automated tests.**
4. **Visible emergence.** Place two species on opposite halves of a 32 × 32 grid; after online training, the run exhibits one of:
   - Stable coexistence with maintained territorial boundary (the most common PD-NCA outcome).
   - Cyclic dynamics where each species periodically expands and contracts.
   - Clear winner — one species drives the other to extinction.
   The "fails-emergence" failure mode would be that both populations decay to zero (extinction) or that both species occupy every cell uniformly (collapse) within the first few hundred ticks. Either is diagnostic, not a build bug.
5. **Comparison metric vs v1.** On a Schelling-equivalent task — initialize a grid with two interleaved species and measure the same-color-neighbor fraction over time — record the trajectory. **This is the number quorum must beat to justify LLM cost on this kind of task at PLAN.md M6.**

---

## 11. Configuration (defaults)

| Knob | Value | Reason |
|---|---|---|
| `H = W` | 32 | Smallest substrate that produces visible territorial dynamics |
| `C` | 16 | PD-NCA paper default; clean 4-4-4-4 channel split |
| `K` (number of species) | 2 | Smallest interesting case; cooperation/competition is binary |
| Per-species conv-net | 3 layers (3×3, 1×1, 1×1), 32 hidden | ~5 K params/species, GPU-cheap |
| Rollout window | 32 ticks | Truncated BPTT; activations fit single GPU |
| Optimizer | Adam, lr=3e-4 | PD-NCA paper defaults |
| Total ticks | 2000 | Long enough to observe steady-state dynamics |
| Initial placement | Two species on opposite halves of the grid | Easiest emergence signal to measure |
| Cell type defaults (alive threshold, growth-gate temperature) | 0.1 alive threshold; growth gate is `sigmoid(8 * (alive - 0.5))` | PD-NCA paper |
| Random seed | 42 | A4 replay test reference |

---

## 12. Deliberate omissions (the v2 stretch list)

The full Digital Ecosystems system uses six engineering refinements. v2 should ship with **the first three (presence gating, differentiable growth gate, win-rate feedback)** and defer the others. In priority order for follow-up:

1. **Spatial concentration loss term** — penalizes a species for spreading too thin; produces clearer territorial shapes.
2. **Soft-minimum loss** — stabilizes multi-species training when one species is winning by a large margin.
3. **Emergency respawn** — re-seeds a species after extinction with a small random initialization, so the simulation can recover.
4. **More than 2 species** — 3 – 8 species is where the Digital Ecosystems demos get visually striking, but training stability gets harder.
5. **Multi-GPU via halo exchanges** — only relevant if we push past 256 × 256 grids.
6. **Population-based training** (Sakana's "Evolving Many Worlds" follow-up) — concurrent seeds, pick survivors. Out of scope for the toy.

---

## 13. Open questions / hyperparameters to tune

These are documented because they will dominate the first few days of iteration:

| # | Question | Default | What might change it |
|---|---|---|---|
| 1 | Channel count `C` | 16 | 8 if memory is tight; 32 if cells need richer state for cooperation dynamics |
| 2 | Number of species `K` | 2 | 3 only after K=2 is stable |
| 3 | Rollout window | 32 ticks | Drop to 16 if activations blow up; raise to 64 if long-range dynamics matter |
| 4 | Reward function | sum(alive × in_species_mask) | Try mean-over-window, or area-under-curve, or time-discounted variants |
| 5 | Competition temperature anneal | Linear from 1.0 → 0.1 over training | Cosine; constant; exponential |
| 6 | Optimizer per species vs single | One Adam per species | Single Adam over the joint param set is simpler but may bias toward whichever species converges first |
| 7 | Initial cell placement | Two halves | Random scatter; checkerboard; tight clusters; lattice |
| 8 | Alive-channel threshold for presence gating | 0.1 | Higher → more conservative culling; lower → ghost cells |
| 9 | Growth-gate function | `sigmoid(8(a - 0.5))` | Tanh; piecewise linear; learned |
| 10 | When to detach the rollout graph | Once per `rollout_window` | More often → cheaper but shorter horizon; less often → bigger memory |

---

## 14. Build plumbing (when v2 implementation lands)

Same uv structure as v1 — `projects/quorum/experiments/` is a standalone uv project, not part of the workspace. Adds torch (already present from v1's `[llm]` extra) and reuses the substrate / metrics scaffolding where applicable.

Suggested layout:

```
projects/quorum/experiments/
├── toy_v1/                  # ships in this PR (the LLM Schelling toy)
├── toy_v2/                  # ships in a follow-up PR
│   ├── __init__.py
│   ├── substrate.py         # cell state tensors + species mask
│   ├── conv_net.py          # per-species NCA module
│   ├── tick.py              # forward step (residual + competition + presence gating)
│   ├── train.py             # rollout window + backprop loop
│   ├── metrics.py           # territory + same-color-fraction for comparison vs v1
│   └── main.py              # CLI
└── tests/
    └── test_pdnca_invariants.py    # A1–A8 verification
```

---

## 15. References

- **Petri Dish NCA** (Zhang, Risi, Darlow; Sakana AI, Nov 2025). [Blog](https://sakana.ai/pd-nca/) · [PDF](https://pub.sakana.ai/pdnca/assets/pdf/pdnca.pdf)
- **Digital Ecosystems: Interactive Multi-Agent Neural Cellular Automata** (Darlow et al.; Sakana AI, Apr 2026). [Interactive page](https://pub.sakana.ai/digital-ecosystem/) · [Source](https://github.com/SakanaAI/digital-ecosystem)
- **Growing Neural Cellular Automata** (Mordvintsev et al., 2020) — the classical NCA precursor. [Distill](https://distill.pub/2020/growing-ca/)
- **PLAN.md §4 / §16 M6 / R6** — the quorum context this toy exists to support.

---

## 16. What we will and won't learn from v2

**Will learn:**

- Whether the competitive multi-agent training loop is stable enough to use as a baseline harness.
- How hard the geometric / spatial / morphogenetic emergence tasks are when the rule is small + trainable.
- The numerical value of "territory dynamics" or "same-color fraction" that quorum must beat at PLAN.md M6 to earn LLM cost.
- Which of the six Digital Ecosystems refinements are *load-bearing* vs *quality-of-life* — this informs which to port to the LLM substrate.

**Won't learn:**

- Anything about *semantic* emergence (norms, rumor spread, coalitions). PD-NCA's substrate is continuous-spatial; semantic tasks require an LLM-shaped rule. That's quorum's reserved territory.
- Whether quorum will actually beat PD-NCA on M6. That decision waits for the comparison.
- Whether LLM-as-rule is "worth it." This toy is one data point; the answer takes a full Slice 0 + M6 build.

The honest framing: v2 is the experiment that lets quorum's bet (LLM-as-rule unlocks emergence NCAs can't access) be testable. If we cannot articulate what v2 will produce, we cannot say what quorum needs to beat. Building v2 *before* claiming v1 generalizes is the principled move.
