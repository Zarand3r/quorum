# thermolife — Route 2 Emergence: Implementation Plan

> Executes [`EMERGENCE_PLAN.md`](EMERGENCE_PLAN.md). This plan is **fully specified through
> E1** (Steps 0–8, the critical path). **E2–E4** (ES meta-learning, per-token evolution,
> open-endedness) are a research phase whose engineering spec firms up *after* E1's numbers
> are in — sketched in §E, not step-locked, on purpose (you cannot lock a spec for a result
> you haven't measured).
>
> **Pre-flight verdict: build fresh in a new `eco/` package.** The `fold/` transformer stays
> untouched and is *imported* at Step 7 (E1) as the interaction operator. E0 is a new
> substrate (energy economy, drift, lifecycle) with no counterpart in the current code —
> migration has nothing to migrate. Reused as-is: `sim/controller.py`, `sim/server.py`,
> `sim/host.sh` (run/pause/step + hosting), and `fold/transformer.py` (at E1).

## Steps at a glance

- [x] **Step 0 — Foundation.** `eco/` skeleton, config, Bazel targets, test harness, ledger helper. *Infra only.*
- [x] **Step 1 — Lock state + ledger contract.** `EcoState` dense arrays; no-op tick conserves trivially. *(P1, P3, P4, P5, P6)*
- [x] **Step 2 — Slice: resource in.** Drifting source + field + harvest (η, dissipation booked). *(P1)*
- [x] **Step 3 — Slice: energy out.** Move (kinetic cost) + metabolism + death. *(P1)*
- [x] **Step 4 — Slice: reproduction.** Split on `e≥e_div`, gene mutation, `N` grows to `N_max`. *(P1, P6)*
- [x] **Step 5 — Hand-forager + THE E0 GATE.** Greedy policy; conserves 10k ticks; **starves when drift outpaces any static config**. *(P1, P8)*
- [ ] **Step 6 — Viewer.** Render population + field + source in the 2D projection; reuse `sim/`. *(P4)*
- [x] **Step 7 — E1: attention as interaction operator.** Swap hand-policy for `fold` block (fixed θ, gene-modulated Q/K) decoding move/harvest/transfer. *(P1, P2, P5, P7)*
- [x] **Step 8 — E1 gate: energy routes along edges.** Transfer provably follows attention; ablations wired. *(P1, P2)*

```
0 ──▶ 1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5 ──▶ 7 ──▶ 8
                         └──▶ 6 (viewer; parallel after Step 4)
```
**Critical path:** 0→1→2→3→4→5→7→8. Step 6 is parallel once state exists through Step 4.

---

## Properties to preserve (P1–P8)

### P1 — Conservation
**Invariant:** every tick, `injected == Δpool + Δ(Σ eᵢ over alive) + dissipated`, residual `< 1e-9`.
**Forbids:** energy created/destroyed off-ledger; harvest/move/death/reproduction that don't book their source and sink.
**Allowed:** dissipation (η<1, metabolic drain) — as long as it's booked to the `dissipated` accumulator.
**Proved by:** Step 1 (no-op), extended each of Steps 2/3/4; long-run in Step 5.

### P2 — No order reward (anti-gaming; = EMERGENCE_PLAN E2/old I10)
**Invariant:** no code that drives dynamics or (later) fitness contains a term scoring order, complexity, clustering, structure, or "interesting-ness."
**Forbids:** rewarding low entropy, high mutual information, cluster count, symmetry, edge-count, etc.
**Allowed:** *measuring* those as read-only observables (§7 of the design) that never feed back into dynamics/fitness.
**Proved by:** Step 7/8 (grep-gate over `eco/` action + reward paths); re-checked at E2.

### P3 — Grid-freeness
**Invariant:** positions are continuous `x_i ∈ ℝ^d`; no lattice, no positional encoding, no integer cell indices as space.
**Forbids:** a grid array, `x,y` integer cell coords, neighbor lookup by lattice adjacency.
**Allowed:** a fixed `P: ℝ^d→ℝ²` projection *for rendering only*.
**Proved by:** Step 1 (structural test) + code-review gate.

### P4 — Determinism / replay
**Invariant:** same seed + config ⇒ byte-identical state-history hash (including birth/death order).
**Forbids:** unseeded RNG; set/dict iteration order affecting state; wall-clock in dynamics.
**Proved by:** Step 1 (hash test), held across every subsequent step; viewer (Step 6) must not perturb it.

### P5 — Vectorization
**Invariant:** a tick is dense array ops over the population — no per-token Python loop.
**Forbids:** `for i in range(N)` mutating per-token state in the tick path.
**Allowed:** vectorized masked ops; compaction on death/birth is a bounded array rebuild, not a per-token loop.
**Proved by:** Step 1 (structural scan) + a wall-clock budget test at Step 5.

### P6 — Bounded population
**Invariant:** `N ≤ N_max` always; reproduction past the cap is refused (energy stays with parent), not silently dropped.
**Forbids:** unbounded growth; offspring overwriting live tokens.
**Proved by:** Step 4 (cap test — fill to `N_max`, assert no overflow, ledger still closes).

### P7 — Groundedness (carried from J1/J6, active at E1)
**Invariant:** once blobs render, a token's drawn contour is a pure function of its **gene-modulated** Q/K — the same coefficients attention uses.
**Forbids:** decorative morphology; a renderer reading anything but the interface coefficients.
**Proved by:** Step 7 (perturb a gene → blob *and* its attention row move together).

### P8 — Real stakes (the E0 thesis)
**Invariant:** there exists a drift rate `v*` such that a static configuration starves — survival *requires* motion.
**Forbids:** an economy where standing still survives forever (trivial), or where everything dies regardless (no viable band).
**Proved by:** Step 5 (the E0 gate: forager survives `v < v*`, dies at `v > v*`; a frozen-policy control starves at `v*`).

---

## How to execute

- **Vertical slices.** Each of Steps 2–4 adds one energy pathway *end-to-end* and leaves the
  ledger closed. No "build all actions, wire later."
- **Tests first, binary acceptance.** The "Tests first" block precedes "Implementation." Every
  acceptance check is a grep that returns empty, a test that passes, or a number under a bound.
- **Delete-after-verify.** Deletions (none until Step 7 swaps the hand-policy) live in Acceptance,
  gated by the replacement's tests passing.
- **Rewrite a stuck file from scratch** against its acceptance test rather than untangling it.
- **The ledger test (§A) is the spine** — it runs after every step; if it goes red, the last
  step broke conservation.

---

## Step 0 — Foundation

**Goal:** an `eco/` package that imports, builds under Bazel, and has a test harness + a ledger helper — no dynamics yet.
**Why now:** everything downstream asserts against the ledger helper and runs under one test target.

### Tests first
- [ ] `tests/test_eco_smoke.py`: `import eco`; `eco.__version__`/config loads; Bazel test target runs green.

### Implementation
- [ ] `eco/__init__.py`, `eco/config.py` (`EcoConfig`: `d`, `n_init`, `n_max`, injection `S`, costs `c_base`/`c_move`, efficiency `η`, `e_div`, drift `v`, mutation `σ_g`, `d_g`, seed) + `load_eco_config`.
- [ ] `eco/ledger.py`: `ledger_residual(before, after, injected, dissipated) -> float` (pure).
- [ ] `configs/eco.yaml`; Bazel `py_library(eco)` + `py_test` targets.

### Integration check
- [ ] `bazel test //projects/thermolife:eco_smoke` green.

### Acceptance
- [ ] `grep -rn "import torch" eco/` empty (autograd/numpy only, per the project's no-torch rule).
- [ ] package imports with zero dynamics code.

**Depends on:** —

## Step 1 — Lock state + ledger contract

**Goal:** the dense `EcoState` layout + a no-op `tick` that conserves trivially and is deterministic.
**Why now:** locks the data layout every slice mutates; the first ledger/determinism/vectorization gates land here.

### Tests first
- [ ] `test_conservation_noop`: 1000 no-op ticks, `ledger_residual < 1e-9` each.
- [ ] `test_determinism`: two runs, same seed ⇒ identical `state_hash()`.
- [ ] `test_grid_free` (structural): no integer cell coords / grid array in `eco/`; positions are `float ℝ^d`.
- [ ] `test_vectorized` (structural): no `for`-loop mutating per-token state in `tick`.
- [ ] `test_pop_bound`: `N ≤ n_max` after any tick.

### Implementation
- [ ] `eco/state.py`: `EcoState` (SoA, `__slots__`/dataclass of arrays): `x[N,d] f64`, `e[N] f64`, `g[N,d_g] f64`, `alive[N] bool`, plus `pool: float`, `dissipated: float`, `mu[d]` (source), `rng`. `state_hash()`.
- [ ] `eco/engine.py`: `EcoEngine(cfg, seed)`, `tick()` = no-op that only advances `mu` by drift and books nothing; `snapshot()`.

### Integration check
- [ ] §A ledger spine green on the no-op engine.

### Acceptance
- [ ] all five tests green; `state_hash` stable across a process restart (determinism).

**Depends on:** 0

## Step 2 — Slice: resource in (drifting source + harvest)

**Goal:** energy *enters* the ledger via harvest near the drifting source; dissipation booked.
**Why now:** the first real pathway; establishes the "energy in" half before any "out."

### Tests first
- [ ] `test_harvest_conserves`: field uptake with `η<1` — `Δ(Σe) + Δdissipated == harvested_from_field`, residual `<1e-9`.
- [ ] `test_source_drifts`: `‖mu_t − mu_0‖` grows at rate `v`; deterministic.
- [ ] `test_harvest_is_local`: a token far from `mu` harvests ≈0; near `mu` harvests >0.

### Implementation
- [ ] `eco/resource.py`: field `R(x; mu)` (e.g. Gaussian well), finite/**depletable** local stock, injection `S` per tick into the pool.
- [ ] harvest action in `tick`: `uptake = min(stock_local, demand)`; `e += η·uptake`; `dissipated += (1−η)·uptake`.

### Integration check
- [ ] §A spine green (now with injection + harvest terms).

### Acceptance
- [ ] harvest test residual `<1e-9`; locality test passes.

**Depends on:** 1

## Step 3 — Slice: energy out (move + metabolism + death)

**Goal:** energy *leaves* via motion cost + metabolic drain; tokens die at `e≤0` with energy booked back.
**Why now:** completes the in/out loop so viability is possible-or-not (stakes become real next step).

### Tests first
- [ ] `test_move_costs`: `Δx` debits `c_move·‖Δx‖²` from `e`, booked to `dissipated`; ledger closes.
- [ ] `test_metabolism`: every alive token pays `c_base`/tick.
- [ ] `test_death_conserves`: `e≤0 ⇒ alive=False`, remaining `e` (≈0, plus any residual) booked; `state_hash` deterministic through a death.
- [ ] `test_death_compaction_vectorized`: dead-token removal is an array rebuild, not a per-token loop; survivors' order deterministic.

### Implementation
- [ ] move action (writes `x`, debits kinetic cost), metabolism debit, death mask + booked return, array compaction.

### Integration check
- [ ] §A spine green across a run where some tokens die.

### Acceptance
- [ ] all four tests green; ledger residual `<1e-9` over a 1000-tick run with deaths.

**Depends on:** 2

## Step 4 — Slice: reproduction (population dynamics + heredity)

**Goal:** `e≥e_div ⇒ split`; offspring near parent, energy split, **gene mutated**; `N` grows, capped at `n_max`.
**Why now:** closes the lifecycle; introduces heredity (the substrate E3 needs) while still hand-driven.

### Tests first
- [ ] `test_reproduce_conserves`: parent energy split parent/child, none created; residual `<1e-9`.
- [ ] `test_gene_mutation`: child `g == parent g + σ_g·noise`; deterministic given seed.
- [ ] `test_pop_cap`: fill to `n_max`; further repro refused (energy stays with parent); no overflow; ledger closes.
- [ ] `test_birth_vectorized_deterministic`: births are a batched append; ordering + hash deterministic.

### Implementation
- [ ] reproduction in `tick`: eligible mask → batched offspring append (bounded by `n_max`), energy split, `g` mutation.

### Integration check
- [ ] §A spine green across births + deaths in one run.

### Acceptance
- [ ] all four tests green; `N ≤ n_max` invariant test green.

**Depends on:** 3

## Step 5 — Hand-forager + THE E0 GATE

**Goal:** a hand-coded greedy policy (move toward `mu`, harvest) and the binary **real-stakes** gate.
**Why now:** proves the economy has stakes *before* any learning/attention — the honesty foundation. Nothing above E0 is worth building until this is green.

### Tests first
- [ ] `test_conservation_longrun`: 10k ticks under the forager, residual `<1e-9` throughout.
- [ ] `test_e0_gate_survives_slow` (P8): at drift `v < v*`, population persists past `T_starve` (the time a frozen config would starve).
- [ ] `test_e0_gate_starves_fast` (P8): at drift `v > v*`, the population dies — survival *requires* tracking.
- [ ] `test_frozen_control_starves`: a no-move control starves at `v*` (isolates that motion, not luck, is what survives).
- [ ] `test_tick_perf` (P5): 10k ticks at `n_max` under a wall-clock budget (vectorization guard).

### Implementation
- [ ] `eco/policies.py`: `hand_forager(state) -> actions` (greedy, vectorized).
- [ ] a headless `run(cfg, ticks)` returning the observable trajectory (population, ledger residual, survival time).
- [ ] Bazel `eco_run` binary.

### Integration check
- [ ] §A spine green over the full 10k-tick forager run.

### Acceptance
- [ ] **E0 GATE:** `test_e0_gate_survives_slow` ∧ `test_e0_gate_starves_fast` ∧ `test_frozen_control_starves` all green.
- [ ] long-run residual `<1e-9`; perf budget met.

**Depends on:** 4

## Step 6 — Viewer (parallel)

**Goal:** watch the population fold/forage in the 2D projection with the drifting source + field.
**Why now:** makes E0 legible and de-risks the E1 visualization; independent of Steps 5/7 logic.

### Tests first
- [ ] `test_snapshot_schema`: `snapshot()` yields tokens (`p=x·P`, `e`, alive), source `mu·P`, field summary, tick, ledger residual.
- [ ] `test_viewer_readonly` (P4): stepping via the viewer path produces the same `state_hash` as headless (rendering never perturbs dynamics).

### Implementation
- [ ] `eco/engine.py.snapshot()` → viewer JSON; reuse `sim/controller.py` + `sim/server.py`.
- [ ] `sim/eco_viewer.html`: blobs at `p_i`, radius/opacity ∝ `e_i`, source marker, field heat, ledger-residual readout.
- [ ] `sim/host.sh` mode `ECO=default`.

### Integration check
- [ ] served locally; step/pause/restart drive ticks; residual readout ~0.

### Acceptance
- [ ] both tests green; deterministic replay identical headless-vs-viewer.

**Depends on:** 4

## Step 7 — E1: attention as the interaction operator

**Goal:** replace the hand-forager with the transformer interaction block — **fixed random θ**, Q/K **modulated by gene `g`** — decoding `move`/`harvest`/`transfer` actions.
**Operator (decided by the HK study, RESEARCH_HK.md — revised):** **distance-penalized dock attention** `A = softmax(dock − λ‖Δx‖²)` (`fold/hk.py`, λ from config). The study found the decisive axis is *smooth vs. hard*, not local vs. global: distance-penalty resists collapse (Exp A: 8–47× spread) **and** trains under gradients (Exp B), where the hard-HK threshold has dead gradients. **hk** and **global softmax** are kept as permanent ablation arms, not the default.
**Why now:** interaction now flows through attention (the mechanism the whole thesis rides on); genes make binding surfaces heritable and *drawable* (P7).

### Tests first
- [ ] `test_transfer_follows_attention` (P1): energy sent on edge `i→j` matches the decoded transfer gated by `A_ij`; ledger closes.
- [ ] `test_groundedness` (P7): perturb `g_i` ⇒ token `i`'s contour **and** its attention row change together; renderer reads only interface coefficients.
- [ ] `test_no_order_reward` (P2): grep — no order/complexity/cluster term in `eco/` action or (future) reward paths.
- [ ] `test_still_conserves`: E0 gate config with the attention policy still closes the ledger and still starves at `v>v*`.

### Implementation
- [ ] `eco/interaction.py`: adapt `fold/transformer.py` to consume `(x, e, g)` → `A` + action head; `Q,K = grounded_readout(x, g)`.
- [ ] wire actions into the Step 2–4 pathways (harvest/move/transfer); transfer routes energy along `A`.

### Integration check
- [ ] §A spine green with the attention policy driving a full run.

### Acceptance
- [ ] the four tests green.
- [ ] **DELETE-AFTER-VERIFY:** hand-forager demoted to a test-only baseline (kept for the E2 control), removed from the default run path.

**Depends on:** 5 (and 6 for the renderer that P7 asserts against)

## Step 8 — E1 gate: interaction does real work

**Goal:** demonstrate energy transport rides the attention graph and wire the ablation harness §7 will need.
**Why now:** closes E1 with a measured claim and leaves the observable/ablation scaffolding E2–E4 depend on.

### Tests first
- [ ] `test_edge_routing`: total transferred energy correlates with `A` mass on transfer edges above a threshold; zeroing `A` zeroes transfer.
- [ ] `test_ablation_harness`: `freeze_attention`, `shuffle_edges`, `remove_transfer`, `global_softmax` modes exist, are deterministic, and each changes the transport observable in the predicted direction (softmax arm per RESEARCH_HK.md §5.3).

### Implementation
- [ ] `eco/observables.py`: attention-graph entropy, transfer-on-edge mass, survival time (read-only — P2: never fed back).
- [ ] `eco/ablations.py`: the four ablation modes + a matched-compute harness.

### Integration check
- [ ] §A spine green under each ablation mode (they change dynamics, not conservation).

### Acceptance
- [ ] both tests green; observables are import-only (grep proves no feedback into `tick`/reward).

**Depends on:** 7

---

## Definition of done (E0 + E1)

- [ ] Steps 0–8 acceptance blocks green.
- [ ] **E0 gate** (Step 5) and **E1 conservation-under-attention** (Step 7) both green.
- [ ] P1–P7 each have a passing test at their named step; P8 proven by the E0 gate.
- [ ] Ledger spine (§A) green end-to-end; deterministic replay; no torch; no per-token loop; grid-free.
- [ ] Viewer serves a deterministic, ledger-honest E1 run.
- [ ] Observables + ablations exist and are provably read-only — the scaffolding E2–E4 build on.

## §A — Golden-path integration test (the spine)

```
GIVEN  eco.yaml + fixed seed
WHEN   run(cfg, ticks=N) executes the current tick path
THEN   ledger_residual < 1e-9 at EVERY tick   (conservation)
AND    state_hash(final) == stamped golden hash   (determinism; restamped only on
                                                   steps that intentionally change dynamics)
AND    N ≤ n_max at every tick   (bounded population)
```
Runs after every step. Red ⇒ the last step broke conservation, determinism, or the bound.

## §B — Iteration loop

Read the failing assertion verbatim → is the invariant correct? → fix test or fix impl
(minimum change *or* rewrite the file fresh against its acceptance test) → re-run the
failing test → run §A spine → green ⇒ done. Stuck >30 min: stop, write expected-vs-observed,
print actual values, re-read the step's Acceptance; a from-scratch rewrite of one `eco/`
module is a valid escape, not scope creep. Never start the next step on a red spine.

## §C — Out of scope (E0 + E1)

- **No learning/optimization.** θ is fixed random through E1. ES is E2.
- **No selection/evolution loop.** Genes mutate on reproduction but nothing selects on them
  yet; differential-survival evolution is E3.
- **No emergence claim.** E0/E1 build and instrument the substrate; the irreducibility /
  many-body / non-settling verdicts are E3's deliverable.
- **No spatial grid, no reaction–diffusion field, no positional encoding** (P3).
- **No order/complexity term anywhere in dynamics** (P2).

## §D — Design tensions surfaced for review

**D1. Genome location.** The gene `g` modulates Q/K only (cheap, ligand/receptor-faithful) vs.
genes that also parameterize the action head or a few θ rows (more expressive, heavier
mutation). *Rec:* Q/K-only for E0–E3; revisit at E4 if evolution plateaus.

**D2. Death/birth vs. determinism + vectorization.** Compaction on a changing `N` risks
per-token loops or nondeterministic ordering. *Rec:* fixed `n_max` capacity arrays with an
`alive` mask + deterministic stable compaction; never resize per token. (Gated by
`test_*_vectorized_deterministic`.)

**D3. `v*` calibration.** The E0 gate needs a drift `v*` where a static config starves. Too
low ⇒ trivial survival; too high ⇒ nothing lives (R-Goldilocks). *Rec:* a Step-5 sweep script
that reports the survival-vs-`v` curve and picks `v*` at the static-starvation knee; commit the
curve as evidence, not just the chosen number.

**D4. Stage-A optimizer (forward pointer).** ES (gradient-free, matches discrete
birth/death) vs. a differentiable soft-mass relaxation (backprop, but a leaky abstraction).
*Rec:* ES for E2; keep the tick differentiable-friendly so a gradient variant stays possible.
Decide with data after E1.

## §E — Beyond E1 (E2–E4, research phase — not step-locked)

Specced lightly on purpose; each firms into full steps once the prior milestone's numbers exist.

- **E2 — Stage A (ES meta-learning).** Evolve shared θ for a population-viability functional
  (average-reward survival under drift; **no order term** — P2 re-gated). Gate: trained θ beats
  random-θ and the hand-forager on held-out drift, and freeze-attention/shuffle-edges ablations
  hurt. Deliverable: a controllable meta-forager + the matched-compute control for E3.
- **E3 — Stage B (per-token selection).** θ frozen; genes mutate on reproduction; selection =
  differential survival; no outer objective. Gate: population persists with lineage diversity
  >1 **and** the emergence trio fires — irreducibility (not reproducible by independent-token
  policies), many-body (≥3-body interaction-information >0), non-settling (graph-entropy stays
  high). Any one failing = honest negative result.
- **E4 — Open-endedness.** Finite resource + predation + coevolution; track evolutionary-activity
  / novelty statistics (contested — reported as exploratory). No binary gate; deliverable is the
  measured trajectory + an honest verdict.
