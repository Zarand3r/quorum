# vivarium — Implementation Plan

Checklist-first execution plan for the **organism / predictive track**, built on a **shared
substrate** that the molecular track will later fork from. Derived from
[`SPEC.md`](SPEC.md) (invariants + milestones), [`DECISIONS.md`](DECISIONS.md) (the *why*), and
`design/` (theory). **Design is locked; this is the *how*.**

**Pre-flight (Phase 1).** *Greenfield build, not a migration.* `projects/vivarium/` currently
holds design docs only — **no code**. Nothing is aligned-and-reusable; nothing violates
doctrine yet. So this is a pure build sequence. Build system follows the repo convention
(Bazel `rules_python`, per-project `pip.parse` hub + `requirements_lock.txt`), using
`projects/thermolife/` as the template; **dependencies are `numpy` + `pytest` only** (plain
numpy, per D9 Route A — no autograd, no torch).

**First-pass target (locked).** Organism track, **Route A** (local predictive plasticity, one
clock — D9), **M0–M2**. Route B (backprop world-model) and the molecular/energy track are
**out of scope here** (§C) — each gets its own plan when chosen.

---

## The steps at a glance

- [ ] **Step 0 — Foundation.** Package skeleton, Bazel target, test harness, seeding/determinism helpers, render stub. *Test infra only.*
- [ ] **Step 1 — Shared substrate (M0).** Dish + agents (tokens) + grounded contour render + **local** attention **forward pass**, fixed random weights. *← the fork point for both tracks.* Gates **P1, P4, P5, P7, P8**.
- [ ] **Step 2 — One clock, local learning (M1).** Predictive plasticity + gentle drift: each tick advances state **and** weights, from local one-step prediction error. Gates **P2, P9, P3(partial)**.
- [ ] **Step 3 — Aliveness harness (measured, read-only).** Gate product + Lyapunov, one-way (irreducibility is *not* a live factor — it's P6's ablation). Completes **P3**; supplies the metric for **P6**.
- [ ] **Step 4 — Emergent interacting life (M2, the deliverable).** Tune scale/ranges/drift until *measured* aliveness clears collapse/freeze **and** interaction is irreducible. Gate **P6** + sustained non-convergence.
- [ ] **Step 5 — CI guards + failure injection.** Grep guards (P3), determinism CI, NaN/blow-up injection (P7). *After* violations can't occur.
- [ ] **Step 6 — Viewer/host (parallel, optional).** Vendor a minimal thermolife-style server + viewer to watch on the tailnet.

**Dependency graph**
```
0 ──▶ 1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5
      │                 ▲
      └────▶ 6 (parallel)
      └────▶ (molecular track — separate future plan, forks here)
```
Critical path: **0 → 1 → 2 → 3 → 4 → 5**. Step 6 is parallel (needs only Step 1's snapshot).

---

## Properties to preserve (each gated by a test)

| # | Invariant | Forbids | Proved by |
|---|---|---|---|
| **P1** | **Locality** — interaction *and* learning use only a bounded neighborhood | all-to-all coupling; a global loss; backprop-through-time | Step 1 (attention neighborhood test) + Step 2 (update uses only local signals) |
| **P2** | **One clock** — a single `step()` advances both state and weights | a separate train phase; weights frozen during a "sim" call | Step 2 (`θ` before ≠ after one step; no other entry point mutates `θ`) |
| **P3** | **Measured-not-rewarded** — no path lets aliveness (or any global objective) influence the update | aliveness/`step` coupling; a reward term in the loss | Step 3 (aliveness exists ⇒ prove it's read-only) + Step 5 (grep guard) |
| **P4** | **Determinism** — `(seed, drift schedule)` → byte-identical run | wall-clock/`Random()` seeding; unordered set iteration; **unstable tie-breaking** (equal-distance k-NN via unstable `argsort`) | Step 1 (two runs byte-identical; k-NN ties broken by index) |
| **P5** | **Read-only render** — snapshotting never perturbs dynamics | a `snapshot()` that advances RNG or mutates state | Step 1 (snapshot-doesn't-change-next-state test) |
| **P6** | **Interaction is load-bearing** — measured aliveness with coupling ablated < with coupling on | "life" that survives ablating agent–agent coupling (independent agents) | Step 4 (ablation arm scores lower over ≥5 seeds by a stated margin) |
| **P7** | **Boundedness** — states and weights stay finite and bounded | NaN/Inf; unbounded growth of `‖x‖` or `‖θ‖` | Step 1 (bounded over long run) + Step 5 (injection) |
| **P8** | **Grounded render** — the drawn shape is a readout of the embedding, via the *same* `W_c` the attention query uses | a renderer with its own decorative map (a `W_c` distinct from the attention's) | Step 1 (rendered contour ≡ `X·W_c` with the block's own `W_c`; perturbing `x_i` moves blob *and* attention row) |
| **P9** | **Single transformer, no extra modules** — the only learnable module is the one weight-tied block; the "prediction" is a readout of the block's own output, not an auxiliary network | a separate predictor/decoder MLP; any second set of trained weights; per-agent networks | Step 2 (grep: no learnable module outside the block; prediction reads block output) |

Calibration note: P1/P7/P8/P9(substrate half) are *substrate/faithfulness* properties; P2/P3/P9
are *learning* properties (Steps 2–3); P6 is the *deliverable* property (Step 4). No property
test forward-references an abstraction that doesn't exist at its step. **P9 encodes your
"single transformer, no extra modules" constraint as a merge gate** — see §D-b for why Route A
strains it and Route B would satisfy it natively.

---

## How to execute

1. **Vertical slices.** Each step ships one capability end-to-end and leaves the sim runnable.
2. **Tests first.** The "Tests first" block is written and red before "Implementation."
3. **Binary acceptance.** Every acceptance box is a grep that returns empty, a test that passes,
   or a stamped artifact that matches. No "looks alive."
4. **Rewrite-from-scratch is allowed.** If a file fights you >30 min, rewrite it against its
   acceptance test rather than untangle it (see §B).
5. **Measured-not-rewarded is sacred.** No step may wire aliveness into the update, ever, to
   "help it along." That is the one unforgivable scope violation.

---

## Step 0 — Foundation

**Goal:** a runnable, testable, deterministic package skeleton — no dynamics yet.
**Why now:** everything downstream needs the harness, the config object, and reproducible
seeding before any behavior can be gated.

### Tests first
- [ ] `test_determinism_helpers.py` — the RNG factory returns identical streams for identical
  `(seed, tick)`; a `PCG64`-based `rng_for(seed, tick)` is a pure function.
- [ ] `test_config.py` — `VivariumConfig` (a frozen `@dataclass(slots=True)`) round-trips
  to/from YAML; fail-fast validation rejects `d < channels_used`, `n_neighbors ≥ N`, negative
  drift/rates.

### Implementation
- [ ] `projects/vivarium/` package: `BUILD.bazel`, `requirements_lock.txt` (`numpy`, `pytest`),
  wire the `pip.parse` hub in root `MODULE.bazel` (mirror `projects/thermolife/`).
- [ ] `config.py` (`VivariumConfig`: `N`, `d`, channel split `pos=2 / shape=2K / hidden`,
  `n_neighbors`/`radius`, `drift_rate`, `lr`, `seed`), `rng.py` (deterministic RNG factory),
  `render.py` **stub** returning an empty neutral snapshot.

### Integration check
- [ ] `bazel test //projects/vivarium/...` green (harness runs; trivial tests pass).

### Acceptance
- [ ] `bazel test //projects/vivarium/...` passes.
- [ ] Nondeterministic seeding is absent: `grep -rEn "default_rng\(\s*\)|random\.random|random\.seed|time\(|datetime\.now|perf_counter" projects/vivarium/` returns empty. (Targets only the *unseeded/wall-clock* forms — seeded `default_rng(seed)` / `PCG64(seed)` in `rng.py` are allowed; the real guarantee is the P4 test.)

**Depends on:** —

---

## Step 1 — Shared substrate (M0)

**Goal:** moving grounded-shape agents under a **fixed random** local-attention rule — the
forward pass only, no learning. This is the substrate **both tracks** fork from.
**Why now:** you cannot test locality, determinism, boundedness, or grounding without the
forward dynamics; and M1's learning has nothing to update until the block exists.

### Tests first
- [ ] `test_locality.py` (**P1**) — with `n_neighbors=k`, each agent's attention row has ≤ k
  nonzero entries, all among its k nearest neighbors; no entry to a non-neighbor.
- [ ] `test_determinism.py` (**P4**) — two runs at the same `(seed, drift schedule)` produce
  byte-identical state trajectories (hash of the stacked `X` per tick); **includes an
  equal-distance case** to prove k-NN ties are broken by index, not by unstable sort.
- [ ] `test_render_readonly.py` (**P5**) — `snapshot()` then `step()` yields the same next state
  as `step()` alone (snapshot advances no RNG, mutates nothing).
- [ ] `test_bounded.py` (**P7**) — over `T=5000` fixed-weight ticks, `‖X‖∞` and every value stay
  finite and below a stated bound (LayerNorm-backed).
- [ ] `test_grounded.py` (**P8**) — the rendered contour equals `X·W_c` computed with the block's
  **own** `W_c` (same matrix object/values the attention query uses — assert identity, not just
  correlation); and perturbing `x_i` moves both the blob and agent `i`'s attention row.

### Implementation
- [ ] `substrate.py` — state `X ∈ ℝ^{N×d}`; channel views (`pos`, `shape=C=X·W_c`, `hidden`).
- [ ] `block.py` — one weight-tied block as a **pure function** `forward(X, θ) → X` (no weight
  mutation): **local** attention `s_ij = ⟨C_i, C_j·M⟩/√2K − λ‖p_i−p_j‖²` over the k-NN set with
  **index-stable tie-breaking** (P4), `A = softmax` (local), `X ← LN(X + A·V)`,
  `X ← LN(X + MLP(X))`; positions move with `X`. `W_c` is shared with the renderer (P8). Fixed
  random `θ`. (Locality via k-NN mask now; **learned positional locality is §D-a** to revisit.)
- [ ] `engine.py` — `Engine(cfg, seed)` with `step()` (advance state), `snapshot()`
  (read-only), `drift` field carried but static at M0.
- [ ] `render.py` — grounded contour readout (blobs + local edges) using the block's `W_c`.

### Integration check
- [ ] Golden-path test (§A) green at M0 scope (fixed seed → stamped snapshot; render mounts).

### Acceptance
- [ ] P1, P4, P5, P7, P8 tests green.
- [ ] `block.forward` is pure — **primary gate:** a test asserting the weight arrays are
  **byte-identical before and after** a `step()` at M0. **Secondary heuristic grep** (mutation
  only, so constructor `=` init is not flagged):
  `grep -rEn "(self\.)?(W|M|mlp|theta)[a-z_]*\s*[-+*/]=|\.fill\(|\bnp\.(add|subtract|multiply)\([^)]*out=" projects/vivarium/block.py`
  returns empty (no in-place weight update).

**Depends on:** Step 0.

---

## Step 2 — One clock, local learning (M1)

**Goal:** turn on **predictive plasticity** — every `step()` advances state **and** nudges the
shared `θ` from each agent's **local one-step prediction error**, under a gentle drift.
**Why now:** this is the project's thesis (learn while living); it needs the M0 forward pass to
have something to update, and it must exist before aliveness can be measured on a learning run.

### Tests first
- [ ] `test_one_clock.py` (**P2**) — `θ` after one `step()` differs from before; there is **no**
  other public method that mutates `θ`; there is **no** separate `train()`/`fit()` entry point.
- [ ] `test_local_update.py` (**P1**, learning half) — an agent's `Δθ` contribution depends only
  on its neighborhood: zeroing a non-neighbor's state leaves that agent's local error unchanged.
- [ ] `test_nondegenerate_target.py` — with partial observation (hidden channels + drift), the
  one-step prediction target is **not** trivially recoverable: a null "predict-identity" baseline
  has strictly higher error than the learned predictor after `K` ticks (guards the ground-truth
  degeneracy called out in the design).
- [ ] `test_bounded_learning.py` (**P7**) — `‖θ‖` and `‖X‖` stay bounded over a long learning run.
- [ ] `test_single_module.py` (**P9**) — the prediction is a **readout of the block's own output**
  (e.g. `X·W_read` / a slice of the post-block state), not a separate trained network; there is
  exactly **one** learnable weight bundle (the block's `θ`) and no per-agent parameters.

### Implementation
- [ ] `predict.py` — a **readout** (not a network): each agent's prediction of its local world is a
  linear/thin readout of its post-block state (partial observation ⇒ non-degenerate target). No
  new trained weights beyond the block (P9); if a readout matrix is needed it is part of `θ`.
- [ ] `plasticity.py` — Route A local delta rule `Δθ ∝ Σ_i e_i · input_i` (`e_i` = local one-step
  prediction error); applied inside `step()` (one clock). **Deterministic accumulation order**
  over agents/neighbors (fixed index order) so P4/§A stay byte-identical.
- [ ] `drift.py` — a slow deterministic external field `s(t)` (the "season"); schedule is part of
  the determinism contract (P4).

### Integration check
- [ ] Golden path (§A) green with learning on (byte-identical stamped run at fixed seed/drift).

### Acceptance
- [ ] P2, P1-learning, P9, non-degeneracy, P7-learning tests green.
- [ ] No separate phase / BPTT / autograd:
  `grep -rEn "def train|def fit|for epoch|\.backward\(|autograd|import torch" projects/vivarium/`
  returns empty (Route A).
- [ ] Single learnable module: no second parameter set outside the block —
  `grep -rEn "nn\.|Linear\(|Sequential\(|class .*Net|class .*MLP" projects/vivarium/predict.py`
  returns empty (the predictor is a readout, not a network).

**Depends on:** Step 1.

---

## Step 3 — Aliveness harness (measured, read-only)

**Goal:** the ungameable **aliveness** scoreboard — gate product + Lyapunov + the irreducibility
measurement — wired **one-way** (reads state, never writes it or `θ`).
**Why now:** M2 can't be gated without the metric; and P3 can only be *proved* once aliveness
exists to show it's not fed back.

### Tests first
- [ ] `test_aliveness_gates.py` — hard-zeros fire correctly: a frozen run, a blown-up run, a
  collapsed run, and a white-noise run each score ~0; a moving+structured synthetic run scores >0.
- [ ] `test_aliveness_readonly.py` (**P3**) — computing aliveness during a run does not change the
  next state or `θ` (diff a run with and without the metric attached).
- [ ] `test_measure_not_rewarded.py` (**P3**) — static check: `plasticity.py`/`predict.py` do not
  import or reference the aliveness module (grep-level + import-graph assertion).

### Implementation
- [ ] `aliveness.py` — the **live score** is `gate_finite · gate_spread · gate_motion · structure
  · coherence` over a window (ported in spirit from thermolife's metric, re-derived — no
  cross-project import) + `lyapunov()` via twin-rollout. **Irreducibility is NOT a live factor
  here** — it requires a counterfactual coupling-off rollout, so it is a *separate ablation
  experiment* owned by P6 (Step 4), not a term inside the per-tick score. (This resolves the
  SPEC §4 wording, which is corrected to match.)
- [ ] wire aliveness as an **observer** on the engine (pull-only; never passed into `step`).

### Integration check
- [ ] Golden path (§A) now also asserts aliveness returns a **finite** number at the stamped tick.

### Acceptance
- [ ] All Step 3 tests green.
- [ ] `grep -rn "aliveness" projects/vivarium/{plasticity,predict,block,engine}.py` returns empty
  (the update path is blind to the scoreboard).

**Depends on:** Step 2.

---

## Step 4 — Emergent interacting life (M2 — the deliverable)

**Goal:** tune scale / neighborhood / drift until **measured** aliveness clears collapse *and*
freeze over a long window, **and** interaction is irreducible (**P6**).
**Why now:** this is the milestone the project exists to reach; it needs both the learning loop
and the metric in place.

### Tests first
- [ ] `test_interaction_load_bearing.py` (**P6**) — over **≥5 seeds**, mean measured aliveness with
  agent–agent coupling **ablated** (attention → identity, and separately **shuffled partners** =
  same interaction mass, wrong structure) is lower than with coupling on **by a stated margin
  `Δ` that exceeds the across-seed std** (not a single-seed "strictly lower", which noise can
  fake). This is the economy's shuffle test promoted to a gate, and it is the **sole owner** of
  irreducibility (aliveness has no live irreducibility factor — see Step 3).
- [ ] `test_sustained_nonconvergence.py` — over a long window the tuned run stays above the
  freeze/collapse gates (aliveness does not decay to ~0); a *no-drift* control **does** decay
  (shows the drive is load-bearing — the `J→0` prediction).

### Implementation
- [ ] `sweep.py` — a small search over `(N, d, n_neighbors, drift_rate, lr)` maximizing *measured*
  aliveness subject to P6 (record every config; **log any config dropped** — no silent caps).
- [ ] commit the winning config to `configs/vivarium.yaml`.

### Integration check
- [ ] Golden path (§A) re-stamped at the tuned config; render shows moving blobs + live aliveness.

### Acceptance
- [ ] P6 test green (ablation strictly lower) **and** sustained-non-convergence test green.
- [ ] `configs/vivarium.yaml` committed; a one-command rollout reproduces the reported aliveness
  within tolerance (fixed val seeds).
- [ ] **Honest report** (even if negative): the achieved aliveness number, the ablation gap, and
  whether the drift prevents the dark-room collapse — stated plainly (§B honesty rule).

**Depends on:** Step 3.

---

## Step 5 — CI guards + failure injection

**Goal:** make the invariants *merge gates*, not aspirations; prove failure is visible.
**Why now:** *after* Steps 2–4, so guards don't red-flag legitimate in-progress states.

### Tests first
- [ ] `test_ci_guards.py` — the grep guards from Steps 0–3 as executable assertions: no
  autograd/BPTT/train-phase (Step 2), no aliveness in the update path (Step 3), deterministic
  seeding only (Step 0), block `forward` is pure (Step 1), and **single learnable module / no
  auxiliary network** (P9, Step 2).
- [ ] `test_failure_injection.py` (**P7**) — inject a NaN into `X` and an overflow into `θ`;
  assert a **named fail-fast** path (loud error / marked-invalid tick), never a silent clamp.

### Implementation
- [ ] a `ci_guards` test target run in `bazel test //projects/vivarium/...`.
- [ ] fail-fast assertions on finiteness/bounds inside `step()` (visible, not swallowed).

### Integration check
- [ ] Full suite green; golden path green.

### Acceptance
- [ ] All guards green and wired into the default `bazel test` target.

**Depends on:** Steps 2, 3, 4.

---

## Step 6 — Viewer / host (parallel, optional)

**Goal:** watch it live on the tailnet (blobs + local edges + live measured aliveness + a churn
indicator showing `θ` is changing).
**Why now:** independent of the learning work; needs only Step 1's snapshot schema.

### Tests first
- [ ] `test_snapshot_schema.py` — `snapshot()` matches the viewer's expected JSON (tokens, edges,
  aliveness, churn); read-only (**P5** reaffirmed).

### Implementation
- [ ] vendor a minimal stdlib HTTP server + `viewer.html` (thermolife-style, self-contained).

### Acceptance
- [ ] Server serves a live run; snapshot-schema test green.

**Depends on:** Step 1 (Step 3 for the aliveness field).

---

## Definition of done (whole plan)

- [ ] Steps 0–5 acceptance boxes all checked (Step 6 optional).
- [ ] P1–P9 each green in CI.
- [ ] `bazel test //projects/vivarium/...` green; golden path (§A) green.
- [ ] `configs/vivarium.yaml` reproduces the reported aliveness within tolerance from one command.
- [ ] An honest M2 report exists — the achieved number, the ablation gap, and any negative result
  (dark-room collapse, low plateau) stated without spin.

---

## §A — Golden-path integration test (the spine)

```
GIVEN  a fixed (seed, drift schedule) and the current committed config
WHEN   the engine runs T ticks with learning on
THEN   the stacked-state hash at tick T matches a stamped golden value (byte-identical)
AND    snapshot() at tick T matches a stamped JSON snapshot (canonicalized floats)
AND    the renderer mounts and draws N blobs in-bounds
AND    aliveness at tick T is finite
```
Runs after **every** step. Golden values are re-stamped **only** at the end of Steps that
intentionally change dynamics (1, 2, 4) — never mid-step.

## §B — Iteration loop

```
Read the failing assertion verbatim
   → Is the test's invariant correct?
       no  → fix the test (+ note why in the PR)
       yes → fix impl (minimum change OR rewrite the file against its acceptance test)
   → re-run the failing test → run golden path → green ⇒ done
```
Stuck > 30 min: stop, print expected-vs-observed, re-read the step's Acceptance, consider a
from-scratch rewrite of the one file. **Report truthfully** — if aliveness is low, say so with
the number; never wire aliveness into the update to "rescue" a run.

## §C — Out of scope (this plan)

- **Route B** (backprop world-model + anti-collapse regularizer) — `related_work.md` §3; its own
  plan if/when chosen.
- **The molecular / energy track** (transformer as `E_θ`, `−∇_X E_θ + J`, dynamic environment) —
  `two_tracks.md`; forks off **Step 1** as a separate plan.
- **Post-core research** — M3 global-vs-local and the E-flux1–5 flux experiments
  (`potential_flux.md` §5); M4 in SPEC.
- **Architectural variants** F1–F5 (`related_work.md` §4) — post-M2.
- **Birth/death population dynamics, selection/genes** — start with fixed `N` (see §D).

## §D — Design tensions surfaced for review

**D-a. Learned vs hard-coded locality.** Step 1 uses a k-NN attention mask. Purer ("just a
transformer") is to let locality be *learned* via positional encoding.
*Recommendation:* ship the k-NN mask first (testable, guaranteed local for P1), then A/B it
against learned locality in Step 4; adopt learned if it holds locality without the mask.

**D-b. Route A vs B — and the faithfulness cost (P9).** Plan builds A (local delta rule, plain
numpy). Be honest that **A is *less* faithful to "single transformer, no extra modules"** than
B: the hand delta rule is not the transformer's native backward pass, and A is most tempted to
grow a separate predictor head. **P9 exists to hold that line** — the predictor must stay a
*readout of the block*, and there must be exactly one learnable weight bundle. B (native
backprop of the same one-step loss) would satisfy P9 more naturally but needs autograd + an
anti-collapse term. *Recommendation:* commit to A through Step 4 *with P9 enforced*; treat a
persistent dark-room collapse (or P9 becoming impossible to satisfy without a real predictor
network) as the trigger to open the Route-B plan — not as a reason to hand-tune or to quietly
add a module.

**D-c. Drift source: external vs internal.** M1 uses an external drift field as `J`. An internal
skew/rotational term (morph's) is the alternative.
*Recommendation:* external drift first (it doubles as the ground-truth renewal); keep the
internal-skew option as an E-flux5 experiment, not a first-pass knob.

**D-d. Fixed N vs population.** Birth/death makes it more life-like but complicates determinism
and the tensor shapes. *Recommendation:* fixed `N` for M0–M2; population dynamics is a post-M2
extension with its own determinism test.

**D-e. The dark-room risk is a real acceptance risk, not just a caveat.** If minimizing surprise
collapses the colony into trivial predictability, M2's aliveness gate will *correctly* score it
low. *Recommendation:* treat that as a **valid negative result** to report (§B), and the trigger
for Route B's anti-collapse term — do **not** patch it by rewarding aliveness (P3).
