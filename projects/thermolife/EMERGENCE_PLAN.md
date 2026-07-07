# thermolife — Route 2: Emergence in the Attention Graph

> **Status: design.** The research plan for open-ended, *computed* emergence on the
> set-based transformer substrate: sustained many-agent interaction that arises as the
> **solution to a viability pressure**, never as a rewarded target. This is the hard,
> unbounded direction (§9 risks: it may produce nothing). It reuses the S0/M2 substrate
> and deliberately re-fuses the thermodynamic ideas the grid design had — grid-free.

## 1. The one question

> Under a conserved resource economy with a **drifting** source, competition, and
> reproduction — and **no reward for order** — does a population of transformer-folded
> tokens develop **sustained, many-body, irreducible** interaction (the attention-graph
> analogue of Game-of-Life structure), or does it collapse / trivially forage?

The answer is allowed to be "no." A negative result, honestly measured, is a result.
The failure we refuse is a *false* yes — order claimed by eye, or smuggled in via the reward.

## 2. Throughline — what carries, what returns, what's new

- **Carries from S0/M2:** the token embedding as state; the **grounded blob** (a token's
  drawn contour *is* its attention query/key, J1/J6); a **real, trained transformer block**
  as the update; determinism, vectorization, no-per-token-loop.
- **Returns from the (deleted) grid design, now grid-free:** a **conserved resource/energy
  ledger** (I1/I3), per-action **cost** (I12), **death + reproduction**, a **drifting
  source**, and — decisively — the **anti-gaming invariant I10** (no direct order reward).
- **New:** there is **no grid**. "Space" is the embedding space `ℝ^d`; "neighborhood" is
  proximity realized *through attention*; "structure" is a persistent **attention-graph
  motif**, not a lattice pattern. And life/physics are **separated**: the transformer block
  is fixed *chemistry*; each token carries a small **evolvable interface gene** that is what
  selection acts on.

This is not a pivot away from M2 — it's M2's substrate placed inside an economy.

## 3. Substrate — a grid-free thermodynamic economy

**State (dense arrays over a bounded population `N ≤ N_max`):**
- `x_i ∈ ℝ^d` — embedding = position in abstract space.
- `e_i ≥ 0` — energy (the conserved currency).
- `g_i ∈ ℝ^{d_g}` — the **interface gene**: a short evolvable code that biases the token's
  query/key (its ligand/receptor surface). This is the unit of heredity.
- `alive_i` — mask.

**Environment:**
- Resource source `μ_t ∈ ℝ^d`, **drifting** (slow walk / orbit). Injection `S` per tick.
- Resource field harvestable only *near* `μ_t` in embedding space, and **finite/depletable**
  (local competition is real, not cosmetic).

**Per-tick pipeline (the transformer is the physics; pure tensor ops, double-buffered):**
1. **Observe** — each token reads its own `(x,e,g)` + the resource it can sense locally.
2. **Interact (attention)** — `A = softmax(QKᵀ/√d)` where `Q,K` are the grounded readout
   **modulated by the gene `g`**. `A` *is* the interaction graph — who trades/senses whom.
3. **Decode actions (MLP head)** from the folded embedding:
   - `move`: `Δx_i` — advect the embedding. **Cost ∝ ‖Δx‖²** (kinetic).
   - `harvest`: uptake from the local resource field (η converted to energy; `1−η`
     dissipated and booked). Depletes the field (conserved).
   - `transfer`: send energy along attention edges — enables trade **and predation**.
4. **Metabolism** — `e_i −= c_base + costs`. Existing and attending are not free (bounds A).
5. **Lifecycle** — `e_i ≤ 0 → die` (energy → pool/dissipation); `e_i ≥ e_div → reproduce`
   (offspring near parent; energy split; **gene `g` copied with mutation**).
6. **Ledger** — `injected == Δpool + Δ(Σeᵢ) + dissipated`, asserted every tick (~1e-9).

**Fixed chemistry, evolving life.** The transformer weights θ are the shared, fixed *laws*.
Reproduction never touches θ — it mutates `g_i`. Evolution is cheap (perturb a short vector,
not a network) and maps exactly to the ligand/receptor vision: **selection shapes binding
surfaces.** The drawn blob morphs across generations ⟺ the lineage's interaction changed.

## 4. Why non-settling and many-body are *forced*, not rewarded (the honesty core)

Two properties we want, neither of which may appear in the reward (I10):

- **Non-settling ← drift.** If the population finds any static configuration, `μ_t` moves
  away, local resource → 0, and it starves. The *only* survivable strategy is continual
  re-organization. Non-settling is therefore a **consequence of viability**, not an
  objective (an objective would be gameable and aesthetic). This is the single most
  important design decision.
- **Many-body ← competition + predation.** Depletable local resource makes crowding
  self-defeating (pressure to partition/spread); energy-transfer edges make *other tokens*
  an exploitable resource (food webs). The substrate **permits** rich interaction; whether
  it **emerges** is the empirical question §7 answers. We never score "coalitions."

If the honest outcome is "tokens forage independently and never interact," the irreducibility
test (§7) will say so, and that is the finding.

## 5. Optimization / evolution — two loops, staged

- **Stage A — meta-learned physics baseline (controllable).** Optimize the shared θ so the
  population survives longest under drift, via **Evolution Strategies** (fitness = a
  population-viability functional; birth/death and discrete actions are non-differentiable,
  so ES treats a rollout as a black box). Result: a *meta-learned forager* — verifiable,
  ablatable, but **not** open-ended. This exists to prove the substrate has real stakes and
  a learnable structure, and to be the matched-compute control for Stage B.
- **Stage B — per-token selection (the dream).** θ frozen; only genes `g_i` evolve, by
  **reproduction-with-mutation under differential survival**. No outer objective, no
  train/test split — *inference does not exist*, there is only ongoing dynamics. Open-ended
  by construction; controllable by nothing. This is where genuine emergence would live.

Average-reward viability (continuing, not terminal) is the honest objective shape for Stage A —
`liminf (1/T) Σ_t (alive count − costs)`, **no order term**.

## 6. Invariants (E-invariants)

- **E1 — Conservation.** Energy/resource is a closed ledger; every source/sink is booked;
  residual < tol over long horizons. *(Test: long-run ledger drift.)*
- **E2 ★ — No order reward (the anti-gaming invariant, = old I10).** The fitness / reward
  contains **no** term scoring order, complexity, structure, clustering, or "interesting-ness."
  Organization is only ever a consequence of viability + cost. *(Test: static scan of the
  fitness function for forbidden terms; code review gate.)*
- **E3 — Grid-freeness.** No lattice, no positional encoding; neighborhood is embedding-space
  proximity via attention. *(Test: structural.)*
- **E4 — Fixed chemistry / evolving genes (Stage B).** θ is byte-identical across a Stage-B
  run; only `g` changes. *(Test: θ hash invariant over a rollout.)*
- **E5 — Groundedness carried.** The rendered blob is a pure function of the gene-modulated
  Q/K. No decorative morphology. *(J1/J6 extended.)*
- **E6 — Determinism / replay, vectorization, bounded population.** Same seed → identical
  history; no per-token Python loop; `N ≤ N_max`.

## 7. How we know it's real — the measurement suite (as important as the mechanism)

Emergence is **claimed only** via observables that are *measured, never rewarded*. Every claim
is one of these numbers moving, on a held-out drift schedule — never a screenshot.

- **Non-settling:** time-entropy of the attention graph `A_t` and of the configuration stays
  high indefinitely (no convergence); population survives ≫ any static config's starvation time.
- **Many-body interaction:** a token's fate depends on ≥3 others — measured by **interaction
  information / ablation** (remove one neighbor's influence; if pairwise removals are additive,
  it's not many-body). Reducible-to-pairwise ⇒ *not* GoL-like.
- **Irreducibility (method borrowed from the sibling `quorum`, kept separate):** fit the best
  **independent-token** policy (each token blind to the others). If full-system behavior is not
  reproducible by independent tokens, interaction does real work ⇒ *computed* emergence.
- **Population/evolution dynamics:** lineage diversity > 1 and sustained; birth/death balance;
  niche count; predator-prey signatures in the transfer graph.
- **Open-endedness (contested — reported honestly):** evolutionary-activity statistics
  (Bedau–Packard), novelty of persisting motifs over time. Cited as exploratory, not proof.

**Ablations (a result must survive these):** freeze attention (no interaction), shuffle edges,
remove transfer, remove drift, remove costs, freeze genes. Each must degrade the observable in
the predicted direction, with a matched-compute control (the Stage-A baseline).

## 8. Milestones (E0 → E4), each a vertical slice with a binary gate

- **E0 — Grid-free viability substrate (no learning).** The economy of §3 + conservation
  ledger + drifting source + a **hand-coded** forager token policy. **Gate:** conservation
  residual < 1e-9 over 10k ticks; a hand-forager survives a slow source and **dies when the
  source drifts faster than a static config can track** (real stakes, zero emergence claim).
  *This is the honesty foundation — the grid Slice-0 gate, reborn grid-free.*
- **E1 — Attention as the interaction operator.** Replace hand-coded sensing/transfer with the
  (fixed-random, then gene-modulated) attention block decoding move/harvest/transfer. **Gate:**
  still conserves; energy provably routes along attention edges; no per-token loop.
- **E2 — Meta-learned viability (Stage A, ES).** Evolve θ for survival under drift. **Gate:**
  trained θ beats random-θ and hand-forager on survival-ticks (held-out drift), and the freeze-
  attention / shuffle-edges ablations hurt. Controllable, not yet open-ended.
- **E3 — Reproduction + evolving genes (Stage B).** θ frozen; genes mutate; selection = survival.
  **Gate:** population persists with lineage diversity > 1 **and** the emergence trio fires —
  **irreducibility** (not reproducible by independent tokens), **many-body** (≥3-body
  interaction information > 0), **non-settling** (graph-entropy stays high). Any one failing =
  honest negative result, reported.
- **E4 — Open-endedness pressure.** Finite resource + predation + coevolution; track open-
  endedness statistics over long runs. **Gate:** none binary — this is exploration; deliverable
  is the measured trajectory of the §7 observables + an honest verdict, positive or negative.

**Critical path:** E0 → E1 → E2 → E3; E4 is open-ended exploration gated behind E3.

## 9. Risks (honest)

- **R-Goldilocks.** The economy has a narrow band between mass death (too harsh) and trivial
  immortality (too easy); finding it is itself a research task. Mitigate: sweep the injection/
  cost/drift ratios; the E0 gate defines the band.
- **R-No-emergence.** E3 may yield only independent foraging — no interaction. This is a *valid
  outcome*, caught by the irreducibility test, not hidden.
- **R-Gaming.** Any leak of an order term into fitness (E2) invalidates the claim. The E2
  invariant scan is a hard gate.
- **R-Aesthetic (the project's named failure).** "It looks alive" is not a result. Only §7
  observables + ablations count.
- **R-Tractability.** ES is sample-hungry; population rollouts with birth/death are the compute
  cost. Mitigate: small `N_max`, short genes, vectorized rollouts, cheap chemistry (θ fixed).
- **R-Non-differentiability.** Reproduction/death are discrete. Stage A uses ES (gradient-free);
  a differentiable soft-mass relaxation is a fallback, flagged as a leaky abstraction.

## 10. First step

**Build E0.** It is fully specified, fully testable, makes **no** emergence claim, and reuses
everything we understand from the deleted grid Slice-0 — grid-free. It answers the only question
that must be true before any emergence work is meaningful: *does the economy have real stakes?*
Nothing above E0 is worth writing until its conservation + starvation gate is green.
