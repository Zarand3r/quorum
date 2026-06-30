# Quorum — Single-Pass LLM Population Simulator for Emergent Behavior

> Project lens: this is a *discovery* engine, not a *prediction* engine. The deliverable is irreducible, **computed** emergence — macro-structure absent from the local rule and absent from the LLM's prior — validated on Boids/Schelling baselines before any semantic target. We never care whether any single agent matches a real person; we care whether the population produces structure nobody designed.

---

## 1. Goal

Build a Game-of-Life–style emergence engine in which the local rule is an LLM, but the common-case update for the *entire population* is **one batched forward pass**. Expensive autoregressive generations are reserved for rare, decision-critical moments. The architecture is engineered for cheapness + surprise; per-agent realism is traded away to get them.

A run produces a trajectory of `(state_t, actions_t)` tuples plus emergence metrics that distinguish *computed* from *retrieved* emergence. The system is validated on known-emergent test problems (Boids, Schelling) before being pointed at semantic targets (norm formation, rumor spread, coalition formation) where no cheap baseline exists.

---

## 2. Success Metrics

### 2.1 v0 — Slice 0 (Boids on a grid, single GPU)

- 100 ticks complete end-to-end with **one batched forward pass per tick** for the Tier-1 population (Tier 0 and Tier 2 disabled in Slice 0).
- Flocking signal detectable: mean nearest-neighbor distance over the run is monotonically lower than under a uniform-random action baseline by a statistically significant margin (Mann-Whitney U, p < 0.01 over ≥10 seeds).
- Per-tick wall clock < 5 s at N=64 on a single consumer GPU (RTX-class).
- Replay determinism: same seed + same state → byte-identical trajectory (I8).
- 0 I3 violations: per-tick forward-pass count = 1 (one batched call, never N individual generations).
- 0 I11 violations: every agent's prompt contains state strictly within its neighborhood (asserted).

### 2.2 v1 — post-Slice metrics

- Population scales to N ≥ 1024 with sub-linear LLM cost vs N (the design promise of batching + memoization).
- Tier-0 memoization hit rate ≥ 70% after warmup on Boids; ≥ 40% on Schelling. (Below these, the abstraction function is broken — see R3.)
- Tier-2 reflection consumes ≤ 5% of total LLM compute per run.
- **Beats zero-intelligence (Gode-Sunder spirit) baseline** on the active test problem in an FM-as-judge evaluation.
- **Passes the irreducibility test**: asking the base LLM to predict the macro outcome directly (zero-shot, no rollout) underperforms the simulated outcome on the chosen target metric. If the LLM can guess the answer, it's retrieved, not computed.
- Decorrelation gate: cross-agent action correlation < 0.4 over a window (high values indicate herding, not emergence).

### 2.3 Non-goals

- **Not a behavior foundation model.** No fidelity validation against real humans; no interview grounding (cf. Simile / Stanford Generative Agents at the opposite pole — see §22).
- **Not a chat simulator.** No agent-to-agent free-form dialogue. Communication, if any, is a discretized symbol/message on the action vocabulary.
- **Not real-time.** Tick cadence is whatever the inference engine sustains; sub-second is a nice-to-have, not a requirement.
- **Not a single-monolithic-prompt simulator.** Each agent is a separate sequence in the batch; we never pack the population into one shared context (R5).
- **Not GPT-4-class APIs.** Hot path runs against open-weights models served locally / on a single rented GPU. Closed-API calls are limited to optional Tier-2 reflection and the FM-judge.

---

## 3. Constraints

### 3.1 Hard

- **Single batched forward pass per tick is the hot path.** No O(N) generations in the common case. Anything that requires N autoregressive rollouts per tick is a design failure.
- **Locality.** An agent's rule sees only its neighborhood. No global view in the common case (Tier 2 may peek; nothing else may).
- **Synchrony.** Actions computed from `state_t`, applied together to form `state_{t+1}`. No in-place updates during the LLM call.
- **Fixed-size per-agent memory.** Memory bytes per agent are constant tick-over-tick. Growing transcripts kill the single-pass economics.
- **Replay-deterministic with seeds.** Same seeds + same state ⇒ same trajectory. Required to debug emergence claims.
- **Local LLM serving.** Hot-path inference runs on open-weights models accessible via batched forward, with prefix-cache reuse, on hardware we own/rent. (vLLM-class engines: vLLM, SGLang, TensorRT-LLM.)

### 3.2 Soft

- Prefer one tool to many: a single inference engine for the hot path; a single substrate library; one batched-judge for evaluation.
- Prefer dense arrays / `numpy` / `torch.Tensor` over dict-of-dict for population state. Per-agent `__slots__` dataclasses if dataclasses are unavoidable.
- Prefer pure Python for the orchestration glue; drop into C++/CUDA only where measurement shows a hot path that Python can't sustain.

---

## 4. Positioning — what this system is and isn't

Two poles define the design space for LLM-driven social/population simulation:

| Pole | Where the LLM sits | Validation target | Optimizes for |
|---|---|---|---|
| **Convergent / fidelity** (Simile / Stanford Generative Agents) | Per-agent, interview-grounded; behavior FM | Replicate specific real individuals (~85%) | Prediction |
| **Divergent / emergence** (Sakana ASAL; classic Game of Life) | Local rule; population is the unit | Irreducibility, novelty, beats-baseline | Discovery |

**Quorum sits firmly at the divergent / emergence pole.** Every design choice trades per-agent realism for cheapness and surprise. Borrow Simile's *real-data grounding insight* as the strongest heterogeneity-injection technique (§12.9); do **not** borrow its fidelity-validation target — an FM trained for prediction is structurally a retrieval engine, and would manufacture *retrieved* emergence (the opposite of the goal).

---

## 5. Architecture Decomposition

```text
                       ┌──────────────────────────────────────────────┐
   OFFLINE (once)      │  Policy Compiler / Hypernetwork (M4+)         │
                       │   persona text → cheap per-agent policy/      │
                       │   adapter (Text-to-LoRA style, single fwd)    │
                       └───────────────┬──────────────────────────────┘
                                       │ diverse cheap policies
                                       ▼
   RUNTIME (per tick)  ┌───────────────────────────────────────────────┐
                       │  1. Environment / Substrate  (state_t)         │
                       │         │ local neighborhoods                  │
                       │         ▼                                      │
                       │  2. Prompt Renderer  (one seq per agent)       │
                       │         │ batch of N prompts                   │
                       │         ▼                                      │
                       │  3. Tier Router ──► Tier 0: Memoization Store  │
                       │         │            (cache hit → action)      │
                       │         ▼                                      │
                       │  4. Batched Inference Engine                   │
                       │       (ONE forward pass over the batch)        │
                       │         │ logits                               │
                       │         ▼                                      │
                       │  5. Action Readout (logit projection → token)  │
                       │         │ actions[]                            │
                       │         ▼                                      │
                       │  6. Environment.step(actions) → state_{t+1}    │
                       │         │                                      │
                       │         ├─► 7. Cheap Memory Update             │
                       │         └─► 8. Surprise Detector ──► Tier 2:   │
                       │                 Reflection (rare full gen)     │
                       └───────────────────────────────────────────────┘
                                       │ trajectories
                                       ▼
   ANALYSIS            ┌───────────────────────────────────────────────┐
                       │  9. Emergence Evaluator (FM-as-judge, ASAL    │
                       │     style) + baselines + irreducibility test  │
                       └───────────────────────────────────────────────┘
```

Stages 1–8 form the **hot path**. Stage 9 runs offline, after the trajectory is recorded.

---

## 6. Invariants

Each invariant maps to a test, assertion, metric, or alert (§17). Violations are blockers, not warnings.

| ID  | Invariant | Verification |
|-----|-----------|--------------|
| I1  | **Locality.** An agent's prompt contains only state within its declared neighborhood (cells / nodes / signals). | Assertion in `Environment.local_observation`; round-trip prompt-content check. |
| I2  | **Synchrony.** Actions are computed from `state_t` and applied atomically to form `state_{t+1}`. `Environment.step` reads no state mutated during the LLM call. | Property test on a stub environment; in-flight state-snapshot diff. |
| I3  | **Single-pass default.** Per tick, the Tier-1 population is served by **one** batched forward pass. Total forward passes per tick = 1 (Tier 1) + #Tier-2 reflections. | Per-tick forward-pass counter; CI gate at `≤ 1 + tier2_count`. |
| I4  | **Latent reasoning.** Tier 1 actions are read via logit projection onto `ACTION_VOCAB` — never via autoregressive decode. | Type-level assertion: `Tier1Result = LogitsAtActionPosition` (no `generate()` allowed). |
| I5  | **Heterogeneity at the rule level.** Diversity comes from persona / private info / per-agent adapter / per-agent seed-temperature — not just from initial conditions. | Decorrelation metric: cross-agent action correlation < threshold over a window. |
| I6  | **Computed (not retrieved) emergence.** The target macro outcome cannot be predicted by asking the base LLM directly (zero-shot, no rollout). | Irreducibility test (§17): single-shot LLM prediction vs simulated outcome; LLM must lose. |
| I7  | **Fixed-size memory.** Per-agent memory byte count is constant tick-over-tick. | Assertion in `Memory.update()` boundary; CI snapshot. |
| I8  | **Replay determinism.** Same seeds + same `state_0` ⇒ same trajectory, byte-identical. | Replay diff test on a frozen scenario. |
| I9  | **Tier-2 budget.** Tier-2 reflection calls account for ≤ 5% of total LLM compute over a run (or whatever budget the scenario configures). | Per-run counter; budget enforced by router. |
| I10 | **Shared prefix.** The system prompt + rules prefix is byte-identical across batch members in a tick. Per-agent suffix carries persona + observation + memory. | Assertion in `PromptRenderer`; prefix-cache hit ratio metric. |
| I11 | **No global-view leakage.** An agent's prompt never contains state outside its neighborhood, ever. | Assertion at prompt build time, comparing prompt text against `neighborhood(agent)`. |
| I12 | **Visible failure.** Reflection errors, cache misses interpreted as decisions, surprise misfires, and budget over-runs are logged with typed error codes — never silently substituted with neutral defaults. | Failure-count metric; zero rows with `state = "default-on-failure"` over a 100-tick run. |

---

## 7. Architecture Options Considered

For each major decision, two or three options. Pick the simplest that meets v0 metrics.

| Decision | Options | v0 pick | Reason |
|---|---|---|---|
| Substrate | 2D grid (custom); graph (NetworkX / cuGraph); continuous spatial (vmas / brax) | **2D grid, custom (numpy)** | Smallest API surface; trivial neighborhoods; reproducible; everything else is deferred to M6. |
| Base model | Closed API (Claude / OpenAI); open small (Qwen 2.5 0.5B–3B, Gemma 2 2B); open mid (Llama 3.1 8B) | **Qwen 2.5 1.5B-Instruct** | Open weights → local serving with batching and prefix cache. Small enough for 1024-batch on a single GPU; instruct-tuned for the action-vocab readout. |
| Inference engine | vLLM; SGLang; HF Transformers; TensorRT-LLM | **vLLM** | Batched serving + paged KV cache + prefix cache + logit-bias / logits-only forward path. Pythonic, fits the hot loop. |
| Action vocab | Single-letter tokens; emoji single-tokens; structured short decode | **Single-letter tokens** for Slice 0 (N/S/E/W/STAY) | Cleanest single-token readout. Move to richer vocab + short decode at M3+ if expressivity is the bottleneck (R4). |
| Memoization key | Exact-match hash of obs; learned coarse hash; semantic embedding cluster | **Exact-match hash of an abstraction function** | Start hand-tuned; iterate on hit rate vs emergence fidelity. Embedding-based clustering deferred to M1+. |
| Heterogeneity source | Initial conditions only; per-agent seed/temp; per-agent persona; per-agent adapter (hypernet) | **Per-agent seed/temp + persona prompt** for v0; hypernet at M4 | Cheap baseline; defer expensive amortization. |
| Surprise trigger | Fixed schedule; KL between predicted and observed; reward-gradient swing | **KL on action-distribution shift + hysteresis** | Self-tuning; avoids reflection spirals (R8). |
| Emergence judge | Same model as policy; separate small judge; closed-API judge (Claude) | **Separate model + closed-API judge for final score**, sweep with the local model | Conflict-of-interest hygiene (Q8). |

---

## 8. Risks and Bottlenecks

For each: cheapest experiment that reduces uncertainty, success criterion, fallback.

| ID  | Risk | Cheapest experiment | Success criterion | Fallback |
|-----|------|---------------------|-------------------|----------|
| R1  | **Retrieved (not computed) emergence** — LLM autocompletes "what an ant colony does". | Irreducibility test (§17) on Schelling and on the target task. | Direct-LLM-prediction loses to simulated outcome on target metric. | Keep LLM at *local rule only*; never let it see global state; tighten action vocab. |
| R2  | **Diversity inversion** — N agents = N samples of one model → herding artifact. | Decorrelation metric over a 100-tick window with persona variation off vs on. | Cross-agent action correlation < 0.4 with persona variation on. | Stronger heterogeneity injector (§12.9): persona widths, per-agent adapters, mixed base models. |
| R3  | **Cost blowup** — low Tier-0 hit rate, growing memory, over-triggered Tier-2. | Hit-rate measurement on Boids over 100 ticks with the v0 abstraction function. | ≥ 50% hit rate after warmup. | Iterate the abstraction function; tighten memory; raise the surprise threshold. |
| R4  | **Action-space too coarse** — single-token vocab can't express needed behavior. | Boids with vocab {N,S,E,W,STAY} vs vocab + "FOLLOW <neighbor_id>". | Slice 0 flocking signal achieved with the coarse vocab. | Short fixed-length decode at Tier 1; hierarchical actions. |
| R5  | **Context bleed** — packing agents into a single shared context leaks identities. | Sanity check: keep agents as separate sequences in the batch (never one shared prompt). | Per-agent prompts confirmed distinct at runtime. | Strict invariant I11 + per-agent prompt audit. |
| R6  | **Sophistication theater** — LLM adds nothing over Boids/Schelling for geometric phenomena. | Compare LLM Slice-0 vs hardcoded Boids rule on the same metric. | LLM ≥ hardcoded on emergence score; or LLM does something the rule doesn't (e.g. responds to messages). | Reserve LLMs for *semantic* emergence; use geometric tasks only as the test harness. |
| R7  | **KV-cache miss** — drifting prefixes destroy prefix-cache reuse. | Instrument prefix-cache hit ratio in vLLM. | ≥ 90% prefix-token cache hit ratio. | Force shared-prefix discipline; move per-agent context into the suffix. |
| R8  | **Tier-2 spiral** — one surprising tick triggers more reflection, which triggers more surprise. | Stress test: inject one anomaly and measure subsequent reflection rate over 50 ticks. | Reflection rate decays back to baseline within 10 ticks. | Hysteresis on surprise detector; budget cap (I9). |
| R9  | **Inference throughput cliff** — at certain batch sizes, throughput collapses. | Throughput vs batch-size sweep for the chosen model. | Identify a stable batch-size band; pick the middle. | Shard population across multiple engine instances at the cliff boundary. |
| R10 | **Heterogeneity injector tuning** — too narrow → herding; too wide → noise. | Sweep persona-distribution width; measure decorrelation and emergence quality. | Identify a width band where both decorrelate and emerge. | Anneal width over the run; use real-data grounding (Simile's insight) for personas. |
| R11 | **Substrate–LLM coupling** — environment modifies state during the LLM call. | Property test: snapshot state before forward; assert no diff during. | 0 diffs. | Strict I2 + state freezing + explicit copy-on-step. |
| R12 | **Replay non-determinism** — seeded but non-deterministic CUDA kernels mask bugs. | Replay diff test: same seed × 5 runs → byte-identical traces. | Identical traces. | `torch.use_deterministic_algorithms(True)`; pin CUDA versions; log all RNG state to disk. |

---

## 9. Core Entities and Interfaces

Python sketches. Final binding is decided at M0 along with the inference engine.

### 9.1 `AgentState`

```python
@dataclass(slots=True, frozen=True)
class AgentState:
    id: int
    persona: PersonaRef          # stable identity / strategy / biases (heterogeneity)
    policy: PolicyRef            # cheap compiled controller / adapter id
    memory: FixedVector          # COMPACT summary, NOT a transcript (I7)
    private_info: dict           # partial observability — agents see different things
    position: GridCell | NodeId  # location in substrate
```

### 9.2 `Neighborhood` (the only thing an agent observes by default)

```python
@dataclass(slots=True, frozen=True)
class Neighborhood:
    local_cells: list[CellState]    # or neighbor node states on a graph
    local_signals: dict             # pheromone, prices, broadcast messages
    # NEVER any global state. Invariant I1.
```

### 9.3 `ActionVocab`

```python
@dataclass(slots=True)
class ActionVocab:
    tokens: list[int]               # action ↔ one (or few) token(s) (I4)
    decode: Callable[[int], Action] # token → structured action
```

### 9.4 `MemoKey` (generalized GoL transition-table key)

```python
@dataclass(slots=True, frozen=True)
class MemoKey:
    context_hash: bytes              # hash of ABSTRACTED neighborhood
    persona_id: int                  # policy identity
    # value (stored separately): sampled action + logits + tick stamped
```

GoL is a lookup over 2⁹ neighborhood configs; this is a **learned, sparse** lookup over a far larger space, populated lazily by Tier 1.

### 9.5 `Tick` (recorded per tick for replay + analysis)

```python
@dataclass(slots=True)
class Tick:
    t: int
    state: SubstrateState
    actions: list[Action]
    metrics: TickMetrics            # decorrelation, entropy, novelty, fwd-pass count
    rng_state: bytes                # for replay (I8)
```

### 9.6 `Environment` (substrate contract)

```python
class Environment(Protocol):
    def local_observation(self, agent: AgentState, state: SubstrateState) -> Neighborhood: ...
    def step(self, state: SubstrateState, actions: list[Action]) -> SubstrateState: ...
```

The environment owns ground-truth state and enforces locality (I1) and synchrony (I2). It must be **cheap**, **deterministic given actions**, and **never call the LLM**.

### 9.7 `BatchedInferenceEngine`

```python
class BatchedInferenceEngine(Protocol):
    def forward(self, prompts: list[str]) -> Tensor:
        """One batched forward pass. Returns logits at the action position only.
        No autoregressive decode (I4). One call per tick (I3)."""
```

---

## 10. Data Flow / Control Flow

The hot path: one tick per one batched forward pass.

```python
def tick(t: int, state: SubstrateState) -> tuple[SubstrateState, TickMetrics]:
    # 1. Observe — locality enforced here (I1)
    obs = [environment.local_observation(a, state) for a in agents]

    # 2. Route by fidelity tier
    routes = tier_router.route(agents, obs)

    actions: list[Action | None] = [None] * len(agents)
    fwd_pass_count = 0

    # 3. Tier 0 — memoized, no forward pass
    for a in routes.tier0:
        actions[a.id] = memo_store.get(MemoKey(abstract(obs[a.id]), a.persona.id))

    # 4. Tier 1 — SINGLE batched forward pass over all Tier-1 agents (I3)
    if routes.tier1:
        prompts = [renderer.render(a.persona, obs[a.id], a.memory) for a in routes.tier1]
        assert all(prompts[i].startswith(SHARED_PREFIX) for i in range(len(prompts)))  # I10
        logits = inference_engine.forward(prompts)                # ONE pass, batched
        fwd_pass_count = 1
        for a, lg in zip(routes.tier1, logits):
            act = action_readout.sample(lg, ACTION_VOCAB)         # logit projection (I4)
            actions[a.id] = act
            memo_store.put(MemoKey(abstract(obs[a.id]), a.persona.id), act, lg)

    # 5. Tier 2 — reflection (rare full generation), budget-capped (I9)
    for a in routes.tier2:
        actions[a.id] = reflection.replan(a, obs[a.id])           # may update persona/memory
        fwd_pass_count += reflection.fwd_passes()                 # logged for I9 budget

    # 6. Apply synchronously — GoL semantics (I2)
    next_state = environment.step(state, actions)

    # 7. Cheap memory update — fixed-size (I7)
    for a in agents:
        a.memory = memory.cheap_update(a.memory, actions[a.id], obs[a.id])

    # 8. Surprise detection → schedule Tier-2 for next tick (with hysteresis)
    surprise_detector.flag(agents, obs, actions, next_state)

    metrics = collect_metrics(actions, fwd_pass_count, ...)
    assert metrics.tier1_fwd_passes <= 1                          # I3 gate
    return next_state, metrics
```

### 10.1 Cold path — analysis (after a run completes)

```python
def analyze(trajectory: list[Tick]) -> EvaluationReport:
    baselines = run_baselines(scenario)                         # zero-intelligence, random
    fm_judge_scores = fm_judge.score(trajectory, scenario)      # ASAL-style novelty + targets
    irreducibility = run_irreducibility_test(scenario, trajectory)
    decorrelation = compute_decorrelation(trajectory)
    return EvaluationReport(
        beats_baseline=fm_judge_scores > baselines + epsilon,
        decorrelated=decorrelation < THRESHOLD,
        irreducible=irreducibility.llm_prediction_loses,
        ...
    )
```

---

## 11. State Machines / Lifecycles

### 11.1 Agent lifecycle

```text
spawn(persona, position) → idle
  └── per tick:
        observe → route(Tier 0 | Tier 1 | Tier 2)
        Tier 0: cache hit  → act → memory_update → wait
        Tier 1: batched fwd → act → memo_store.put → memory_update → wait
        Tier 2: reflect    → act → persona/memory updated → wait
  └── on surprise flag: scheduled for Tier 2 next tick (with hysteresis)
  └── on optional persona mutation (M4+): policy re-compiled via hypernetwork
```

### 11.2 Memo entry lifecycle

```text
new entry: created by Tier 1 with (action, logits, tick_stamp)
  └── reads: increment hit count
  └── stale (no read for K ticks): evicted LRU-style
  └── confidence drift detected: invalidated, forces Tier 1 next time
```

### 11.3 Tick lifecycle (state machine for the loop)

```text
state_t  ─►  observe  ─►  route  ─►  inference (Tier 1 only)
                            │
                            ├─►  Tier 0 dispatch
                            ├─►  Tier 2 dispatch
                            ▼
                          actions[]  ─►  step  ─►  state_{t+1}
                                          │
                                          ▼
                                       memory.update,
                                       surprise.flag,
                                       metrics.emit
```

---

## 12. Component Specifications

### 12.1 Environment / Substrate

- Owns ground-truth state. Provides `local_observation` (enforces I1) and `step` (enforces I2).
- Cheap and deterministic given actions. **The LLM never imagines global state** — only proposes local actions.
- Slice 0: 2D toroidal grid, 32×32, `numpy` arrays for cell state.
- M6+: graph substrates (norm formation), spatial continuous (vmas-style).

### 12.2 Prompt Renderer

- Maps `(persona, neighborhood, memory) → sequence`. Deterministic, templated, byte-identical for the same inputs.
- **Shared prefix** (rules text + action-vocab description + format) identical across the batch (I10) → KV-cache prefix reuse.
- Per-agent suffix carries persona + local obs + memory.
- Renderer is hot but pure-Python should suffice (template format).

### 12.3 Batched Inference Engine

- Exposes `forward(prompts: List[str]) → List[Logits]` as **one batched forward pass**.
- Returns logits at the action position only — no autoregressive decode (I4).
- Backed by vLLM (default). Configuration: `enable_prefix_caching=True`, `enforce_eager=False`, max batch sized to the throughput plateau (R9).

### 12.4 Action Readout

- Projects logits onto `ACTION_VOCAB.tokens`, normalizes, samples (per-agent temperature/seed for decorrelation).
- Single-pass-classification pattern (SALSA-style): the model "reasons" latently in conditioning; only action-token logits are read.
- Optional: log per-agent logit vectors for audit (I12) — expensive, gated by config.

### 12.5 Tier Router (mixed-fidelity)

- Assigns each agent to Tier 0/1/2 per tick.
- Policy: Tier 0 if `MemoKey` hit and confidence high; Tier 2 if flagged surprising or scheduled (every K ticks); else Tier 1.
- Target steady state: most ticks Tier 0/1; Tier 2 ≤ 5% of total compute (I9).

### 12.6 Memoization Store (generalized GoL transition table)

- `MemoKey(abstract(neighborhood), persona_id) → (action, logits, tick_stamp, hit_count)`.
- The **abstraction function** is the most important hyperparameter:
  - Coarse → high hit rate, low decision fidelity.
  - Rich → low hit rate, high decision fidelity.
  - Tuned per scenario; monitored via hit rate vs emergence fidelity (R3).
- Eviction: LRU + confidence-based invalidation.

### 12.7 Reflection Module (Tier 2)

- The only place a full generation runs (and even then, batched if possible).
- Triggered sparingly (I9 budget; R8 hysteresis).
- Responsibilities: replan strategy, rewrite/compress memory, optionally mutate persona, seed new behaviors. Writes results back into memory and (optionally) the memo store, lowering future Tier-0 cost.

### 12.8 Policy Compiler / Hypernetwork (offline amortization, M4+)

- Generates a distinct cheap controller/adapter per persona from a natural-language description **in a single forward pass each** (Text-to-LoRA / Doc-to-LoRA pattern).
- Output: a population of genuinely different cheap policies. Solves cost *and* heterogeneity simultaneously.
- Alternative / complement: **logit-probe distillation** — probe the LLM once per distinct memory-state for its action logits, treat as a stochastic policy, run huge populations on the cheap surrogate. (Validated approach: Hamann et al., arXiv:2510.22422.)

### 12.9 Heterogeneity Injector

- Sources of rule-level diversity (apply several):
  1. Sampled persona traits / goals / biases.
  2. Private / partial information (each agent sees a slightly different slice).
  3. Per-agent adapters (M4+ via §12.8).
  4. Per-agent temperature / seed.
  5. Occasionally different base models.
- Emits a **decorrelation metric** (cross-agent action correlation) as a first-class output.
- The strongest heterogeneity insight from the convergent pole (Simile) — **real-data-grounded personas** — is borrowed here without borrowing its fidelity target.

### 12.10 Emergence Evaluator (analysis)

- **FM-as-judge (ASAL-style):** a vision/language FM scores (i) presence of target phenomena, (ii) open-ended novelty over time, (iii) diversity across a rule-space sweep — in a human-aligned way.
- **Baselines:** zero-intelligence and simple-rule agents (Gode-Sunder spirit). Does the LLM population do anything they don't?
- **Irreducibility test:** can the macro outcome be predicted *without running* the sim — by asking the LLM directly for the end-state? If yes → retrieval, not emergence. Genuine emergence should be **cheaper to run than to predict**.

---

## 13. Cost Model

| Reference | Order of magnitude | Verdict |
|---|---|---|
| GoL: 1000×1000 × 1000 steps ≈ 10⁹ cell-updates, ns each | trivial | baseline |
| Naive LLM-per-agent-per-step: N×T generations. 1000 agents × 1000 steps = 10⁶ generations | days, thousands of dollars per run | **rejected as the default** |
| **This design** (hot path): **O(T) batched forward passes**, each over ≤ N sequences, most agents served from Tier 0 | far below N effective LLM calls per tick; Tier-2 a small fraction | **target** |

The single hardest engineering variable is the **Tier-0 hit rate**, governed by the abstraction function (§12.6). High hit rate ⇒ GoL-like economics; low hit rate ⇒ back toward O(N×T) and the design fails (R3).

---

## 14. Infrastructure & Scaling

- **KV-cache prefix sharing.** Identical shared prefix across the batch → reuse KV for the shared portion (cf. Halo, arXiv:2509.02121). Large win since most of each prompt is common (I10).
- **Batch sizing.** ~64–128 agents per inference engine is a sane starting ratio; tune by CPU(env)-to-GPU(LLM) work ratio. Find the throughput plateau (R9).
- **Synchronous update.** Keeps GoL semantics and makes batching natural. If asynchrony is required, batch by *ready-set* rather than abandoning batching.
- **Determinism knobs.** Fixed per-agent seeds for reproducibility; log all logits at Tier 1 for replay/audit; `torch.use_deterministic_algorithms(True)`; pinned CUDA versions.
- **Sharding (post-Slice 0).** For large N, shard the population across multiple inference engines. Each shard runs its own batched forward; results stitched into a global `actions[]` before `Environment.step`.
- **Build system.** Bazel is the project's build tool (workspace at the repo root). Slice 0 is pure Python; later milestones expect CUDA kernels (for fast neighborhood extraction at large N) and possibly C++ substrate cores — exactly the polyglot territory bazel is good at.

---

## 15. Vertical Slice Strategy

> Build one end-to-end thread before adding breadth. The slice exercises every hot-path component; M1–M7 expand each component once the slice works.

### 15.1 Slice 0 — *"Boids on a grid, single GPU, single batched forward pass per tick"*

| Knob | Value |
|---|---|
| Substrate | 2D toroidal grid, 32×32 |
| Population | N = 64 |
| Persona | one ("swarm member"); per-agent seed/temp only |
| Action vocab | 5 actions: N, S, E, W, STAY — single token each |
| Base model | Qwen 2.5 1.5B-Instruct (open weights) |
| Inference engine | vLLM, batched forward, logit-only readout (I4) |
| Tier 0 | disabled (engine sanity first) |
| Tier 2 | disabled |
| Heterogeneity | per-agent seed only |
| Hypernetwork | n/a |
| Storage | per-tick `Tick` rows in a single Parquet file |
| Runtime | single GPU, single process |
| Tick cadence | as fast as the engine allows; no real-time requirement |
| Metrics | per-tick forward-pass count (must = 1), decorrelation, mean-nearest-neighbor distance, wall-clock |

**Success (slice 0):**

- 100 ticks complete with one batched forward pass per tick (I3 gate green).
- Mean nearest-neighbor distance under the LLM population is monotonically lower than under a uniform-random baseline by a statistically significant margin (Mann-Whitney U, p < 0.01 over ≥ 10 seeds).
- Replay determinism (I8): same seed + same `state_0` → byte-identical trajectory.
- 0 I3, I10, I11 violations over the run.

### 15.2 What Slice 0 proves

- The hot-path mechanics: batched forward, logit projection, synchronous update, per-tick metrics.
- Discipline invariants I1, I2, I3, I4, I7, I8, I10, I11 (everything except the ones that need Tier 0/2/hypernet).
- Baseline economics: cost-per-tick on the target hardware; throughput-vs-batch plateau (R9).

### 15.3 What Slice 0 defers

- Tier 0 memoization (M1).
- Tier 2 reflection (M2).
- Persona heterogeneity injection (M3).
- Policy compiler / hypernetwork (M4).
- FM-as-judge + irreducibility test (M5).
- Sugarscape / Schelling harness (M6).
- Semantic targets (M7).

---

## 16. Milestone Roadmap (post Slice 0)

Each milestone: goal, deliverable, scope, non-goals, dependencies, verification, definition of done.

### M1 — Tier 0 memoization + abstraction function

- **Goal:** establish the cache that makes the design economically viable (R3).
- **Deliverable:** `MemoStore` + an abstraction function for the Boids grid scenario.
- **Verification:** hit rate ≥ 50% after warmup on Boids; emergence quality not degraded vs Slice 0 (no false-positive cache hits).
- **Done when:** hit rate sustained over 1000 ticks; cost-per-tick drops linearly with hit rate.

### M2 — Surprise detector + Tier 2 reflection

- **Goal:** rare full-generation reflection that improves memory and writes back to the memo store.
- **Deliverable:** KL-based surprise detector with hysteresis; `Reflection.replan` running a bounded autoregressive generation.
- **Verification:** Tier-2 budget I9 respected over a 1000-tick run (≤ 5%); injected anomalies trigger reflection within 3 ticks; reflection rate decays back within 10 ticks (R8).
- **Done when:** Tier-2 reflection demonstrably improves Tier-0 hit rate and/or Tier-1 quality on a controlled scenario.

### M3 — Persona heterogeneity + decorrelation gate

- **Goal:** rule-level diversity that defeats herding (R2).
- **Deliverable:** persona sampler with measurable width; decorrelation metric as a CI gate.
- **Verification:** cross-agent action correlation < 0.4 over a window with persona variation on; correlation visibly higher with persona variation off.
- **Done when:** decorrelation gate is the second hard CI gate (after I3).

### M4 — Policy compiler / Text-to-LoRA hypernetwork

- **Goal:** amortize per-agent adapter generation into a single forward pass each (offline).
- **Deliverable:** hypernet trained on personas → cheap per-agent LoRAs loaded into the inference engine.
- **Verification:** N personas × hypernet inference cost ≪ N personas × LoRA fine-tuning cost; per-agent action distributions differ in measurable ways.
- **Done when:** v1 metric (R10 width band found) is achieved with hypernet-driven heterogeneity.

### M5 — FM-as-judge + irreducibility test

- **Goal:** validate emergence claims as *computed*, not *retrieved* (I6).
- **Deliverable:** FM-as-judge harness (separate model from the policy LLM); irreducibility-test harness; baseline comparison harness.
- **Verification:** Schelling segregation emergence is judged as such; irreducibility test detects the (deliberately) retrieved case.
- **Done when:** every claim of emergence in this project carries an FM-judge score and an irreducibility verdict.

### M6 — Schelling + Sugarscape harnesses

- **Goal:** prove the engine scales beyond Boids, on known-emergent test problems.
- **Deliverable:** scenario configs for Schelling segregation and Sugarscape; per-scenario metrics and baselines.
- **Verification:** known emergent patterns reproduced; FM-judge agrees; scaling to N ≥ 256 sustained.
- **Done when:** the three classical scenarios (Boids, Schelling, Sugarscape) all pass the gate criteria of §17.

### M7 — Semantic target (first one)

- **Goal:** point the engine at a problem with no cheap baseline.
- **Deliverable:** norm formation, rumor / meme spread, or coalition formation scenario (pick one).
- **Verification:** baselines (random / zero-intelligence) lose to the LLM population on the FM-judge target; irreducibility test holds.
- **Done when:** the project is doing something other systems cannot, on a target that nobody hand-coded a rule for.

Beyond M7: open-ended search over scenario space (ASAL-style); multi-GPU sharding; surrogate distillation (logit-probe) for huge populations. All deferred.

---

## 17. Verification Strategy

Per-invariant tests live alongside code; per-milestone gates block promotion.

### 17.1 Always-on (every test run)

- **I3 gate** (single-pass): per-tick forward-pass counter = 1 + Tier-2 count. Asserted in the runner.
- **I10 prefix discipline**: byte-equal prefix across all batch prompts.
- **I11 no-global-leak**: assertion in `PromptRenderer` that prompt text contains no state outside the agent's neighborhood.
- **I4 logits-only Tier 1**: type-level guarantee.
- **I8 replay determinism**: snapshot test on a frozen 10-tick scenario.

### 17.2 Per-scenario gates

- **Reproduces known emergence** (Boids, Schelling, Sugarscape on M6).
- **Beats zero-intelligence baseline** (Gode-Sunder spirit) on the active scenario.
- **Decorrelation check** passes (I5 metric below threshold).
- **Irreducibility test** passes (I6 — direct LLM prediction loses to simulated outcome).

### 17.3 Replay test

- Frozen 100-tick window for each scenario. Run twice with the same seed; bit-equal trajectories required. Catches R12.

### 17.4 Cost meter

- Per-run LLM cost (token-count × per-token cost) persisted to disk. Alert at 80% of run budget. Backs I9.

### 17.5 Honest reporting

- Verification results emitted as a single `EvaluationReport` JSON per run. **Not run** is a first-class status; partial verification is reported as partial, never as full.

---

## 18. Implementation Standards

These are the invariants restated as daily implementation rules.

- **Locality is enforced by the substrate** (I1, I11). Anything else is a bug.
- **Single-pass is enforced by the runner** (I3). If you find yourself writing a per-agent generation loop in the hot path, stop.
- **Latent reasoning** (I4). Tier 1 reads logits at the action position. Calling `generate()` in Tier 1 is a bug.
- **Fixed-size memory** (I7). If memory grows tick-over-tick, the design is broken — fix the memory update, don't widen the prompt.
- **Replay-determinism** (I8). Seeds, RNG state, deterministic CUDA. Logged to disk per tick.
- **Shared prefix** (I10). Build prompts as `PREFIX + suffix`; never let the prefix drift.
- **Visible failure** (I12). Typed errors; never silent neutral defaults.
- **Tier-2 budget** (I9). Capped by the router; never bypass.
- **Honest verification** (per principal-production-engineer): include what was not run, and why.

---

## 19. Known Failure Modes

| Failure mode | Cause | Mitigation |
|---|---|---|
| **Retrieved (not computed) emergence** | LLM autocompletes "what an ant colony does" | I6 irreducibility test; keep LLM at *local rule only*; FM-judge novelty over time |
| **Diversity inversion / herding** | N agents = N samples of one model → coupled | Rule-level heterogeneity (§12.9); decorrelation metric as gate |
| **Cost blowup** | Low Tier-0 hit rate; growing memory; over-triggered Tier 2 | Abstraction-function iteration; fixed-size memory (I7); conservative surprise threshold |
| **Action-space too coarse** | Single-token vocab can't express needed behavior | Short fixed decode; richer vocab; hierarchical actions |
| **Context bleed** | Packing agents into one shared context leaks identities | Keep agents as separate sequences in the batch, not one shared prompt (I11) |
| **Sophistication theater** | LLM adds nothing over Boids for geometric phenomena | Reserve LLMs for *semantic* emergence; use geometric tasks only as the test harness |
| **KV-cache miss** | Drifting prefixes | Shared-prefix discipline (I10); audit prefix bytes pre-batch |
| **Tier-2 spiral** | Surprise → reflection → more surprise | Hysteresis; budget cap (I9) |
| **Replay non-determinism** | Non-deterministic CUDA kernels | `use_deterministic_algorithms(True)`; pin CUDA; log RNG state |
| **Substrate-LLM coupling** | Environment mutates state during LLM call | Copy-on-step; assertion (I2) |

---

## 20. Recommended Next Step

Implement **Slice 0** (§15.1):

1. Decide the open questions in §22 that block coding (base model, inference engine, action-vocab tokenization, substrate library, base GPU).
2. Stand up the Bazel build graph for the Python orchestrator + a vendored small model. `rules_python` declared at the root `MODULE.bazel`.
3. Implement `Environment` (2D toroidal grid), `PromptRenderer` (with shared prefix), `BatchedInferenceEngine` (vLLM wrapper), `ActionReadout`, the tick loop.
4. Add the I3, I10, I11, I8 assertions; add the replay test.
5. Run 100 ticks. Generate the trajectory Parquet. Compute the baseline metric (mean nearest-neighbor distance under uniform-random actions).
6. Confirm Slice 0 success criteria (§15.1). Generate the static report.

Stop and review before starting any of M1–M7. Slice 0 is non-trivial; don't pre-build M1+ components.

---

## 21. Deferred Complexity

Explicit list of things *not* in v0 / Slice 0, and the milestone that re-evaluates them:

| Item | Re-evaluate at |
|---|---|
| Tier 0 memoization + abstraction function | M1 |
| Tier 2 reflection + surprise detector | M2 |
| Persona-driven heterogeneity injection | M3 |
| Policy compiler / Text-to-LoRA hypernetwork | M4 |
| FM-as-judge emergence evaluator | M5 |
| Irreducibility test harness | M5 |
| Sugarscape / Schelling scenarios | M6 |
| Graph / continuous substrates | M6 |
| Semantic targets (norm / rumor / coalition) | M7 |
| Multi-GPU sharding | Beyond M7 |
| Logit-probe surrogate distillation | Beyond M7 |
| Open-ended search over rule-space (ASAL-style) | Beyond M7 |
| C++ substrate cores / CUDA neighborhood kernels | When pure Python hurts |
| Real-time streaming of trajectories to a dashboard | When a dashboard exists |

---

## 22. Open Questions / Decision Points

Block Slice 0 until answered:

1. **Base model.** Qwen 2.5 1.5B vs Gemma 2 2B vs Llama 3.2 3B. Constraints: batched serving with prefix cache; size that fits 64-batch on the chosen GPU; instruct-tuned for action-vocab readout.
2. **Inference engine.** vLLM (default) vs SGLang vs HF Transformers. Driver: which gives the cleanest logit-only forward API + prefix caching control.
3. **Substrate library.** Custom numpy grid (recommended for Slice 0) vs Gymnasium / Mesa / pettingzoo. Cheap iteration vs ecosystem.
4. **Action-vocab tokenization.** Single ASCII tokens (e.g. `N`, `S`, …) vs structured short decode. Affects sampling fidelity and prompt format.
5. **Surprise trigger function.** KL between predicted and observed action distribution? Reward-gradient swing? Action-novelty against memo-store? Pick one default at M2.
6. **Memoization abstraction.** Hand-designed buckets vs feature hashing vs embedding clustering. Picked at M1.
7. **Determinism vs throughput.** Strict per-agent seeds reduce batch efficiency; quantify the cost at Slice 0.
8. **FM-as-judge model.** Same model as the policy LLM (cheap, conflict of interest) or a separate judge (cleaner, expensive). Default: separate, closed-API for the final score.
9. **Hardware target.** Single consumer GPU (RTX 4090-class) for Slice 0; later milestones may need an H100 for throughput.
10. **Logging granularity.** Per-agent logits every tick (audit) vs aggregated (cheap). Toggle by config.
11. **Reflection-mutates-persona policy.** Does Tier-2 reflection rewrite a persona, or only memory? Conservative default: memory only.
12. **Surrogate distillation policy.** When (if ever) do we replace the LLM hot path with a distilled stochastic policy (Hamann et al.)? Default: never in Slice 0; revisit at M3 if persona variation breaks the abstraction-function hit rate.

Defer to milestones, but worth noting now:

13. **Closed-source persona data.** Real-data-grounded personas (Simile insight) require permission for the source data. We will use synthetic personas in v0 and document this constraint.

---

## 23. Related Systems

| System | Pole | Where the LLM sits | Validation target |
|---|---|---|---|
| **Simile / Stanford Generative Agents** | Convergent / fidelity | Per-agent, interview-grounded; behavior FM | Replicate specific real individuals (~85%) |
| **Sakana ASAL** | Divergent / search | FM as evaluator / searcher over rule-space | Open-ended novelty; human-aligned "interestingness" |
| **Quorum (this system)** | Divergent / emergence | Local rule, amortized to single-pass | Irreducibility; beats zero-intelligence baseline |

Borrow Simile's real-data grounding as the strongest heterogeneity-injection insight (§12.9); do **not** borrow its fidelity-validation target or its behavior-FM amortization — an FM trained for prediction is structurally a retrieval engine and will manufacture *retrieved* emergence, the opposite of this system's goal.

---

## 24. References

**Sakana AI**

- ASAL — *Automating the Search for Artificial Life with Foundation Models* (arXiv:2412.17799). FM-as-evaluator; found CA more open-ended than Conway's GoL.
- Text-to-LoRA / Doc-to-LoRA — hypernetworks generating adapters in a single forward pass; cost amortization; history internalization.
- *World Models* (David Ha) — learned model rolling out dynamics internally (the global-simulator alternative; use only as a surrogate).

**Other frontier work**

- Hamann et al. — *Group size effects and collective misalignment in LLM multi-agent systems* (arXiv:2510.22422). Logit-probe → stochastic surrogate at population scale.
- Park et al. — *Generative Agents* (UIST '23) and *Generative Agent Simulations of 1,000 People* (arXiv:2411.10109) — the convergent / fidelity pole; ~85% individual replication. (Commercialized as Simile.)
- *LLM-Empowered Agent-Based Modeling: A Survey* (arXiv:2312.11970) — batch prompting (~5× savings), scaling bottlenecks.
- *LLM Economist* (arXiv:2507.15815), *MobileCity* (arXiv:2504.16946) — large-population batched simulation.
- Halo — *Batch Query Processing for Agentic Workflows* (arXiv:2509.02121) — KV-cache / prefix reuse.
- SALSA — *Single-pass Autoregressive LLM Structured Classification* (arXiv:2510.22691) — single-token action readout.
- Classics: Conway's Game of Life; Reynolds' Boids; Schelling segregation; Gode-Sunder zero-intelligence traders; Stanley / Lehman open-endedness & novelty search.

---

### One-paragraph summary

Each agent is one sequence in a batch; the whole population advances one tick per **single batched forward pass**, with the action read out as a single token so reasoning happens latently in conditioning. Most ticks are free via a memoized "generalized Game-of-Life transition table"; rare full generations (reflection) run only at surprising, decision-critical moments and write their results back to lower future cost. Diversity is injected at the *rule* level — personas, private information, hypernetwork-generated per-agent adapters — to defeat the shared-weights herding that otherwise fakes emergence. The system is validated on Boids/Schelling, baselined against zero-intelligence agents, and checked with an ASAL-style FM judge plus an irreducibility test, so that the emergence is confirmed *computed*, not *retrieved* — distinguishing it sharply from the convergent / fidelity systems (Simile) at the other end of the field.
