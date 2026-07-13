# vivarium — spec (for review; no code until approved)

> **A toy transformer whose *training loop is the simulation*.** It is the local
> update rule of a Gray–Scott reaction–diffusion world, and it is trained *online*
> to track that world as the world drifts. Because the world never stops changing,
> **the training never converges** — you watch a transformer perpetually learning,
> its cells rendered as shapes that move and morph. Working name: **vivarium**
> (a living enclosure you observe). Rename freely.

This is a **new standalone project** (`projects/vivarium/`), not part of thermolife.
Per the monorepo rule (no cross-project imports) it **vendors** a ~150-line
self-contained transformer block rather than importing `thermolife`. It shares
thermolife's *ideas* (a block as an interaction engine; grounded readouts; an
ungameable aliveness metric) but none of its code.

---

## 1. The one idea

Three prior thermolife sims iterate a transformer's **forward** pass and watch
embeddings move. vivarium is different: **each rendered frame is one optimizer
step.** The thing you watch morph is the network *learning*. We engineer the task
so learning never finishes — the honest, "earned" version of "never converges."

The substrate is **Gray–Scott** because it is the canonical reaction–diffusion
pattern generator, it is continuous and differentiable (a gradient-trained
transformer slots straight in), its patterns are legible (spots → stripes → worms →
self-replicating → chaos), and "a changing environment" is a single clean knob:
drift the feed/kill rates `(F, k)`.

## 2. Non-goals

- Not a benchmark or a task-accuracy result. The deliverable is a *watchable,
  measurable* never-converging training process, plus the honest finding of what it
  took to sustain it.
- Not photorealism, not a large model. Toy scale by design (small grid, tiny block).
- Not thermolife. No import of `fold/`, `eco/`, or `sim/`; concepts may echo, code
  does not.
- Not RL / agents (that is the ant-colony variant, explicitly deferred — see §9).

## 3. Substrate & mechanism

**The world (reference).** A standard Gray–Scott PDE on a 2-D grid with two
chemicals `U, V`:

```
∂U/∂t = Du∇²U − U V² + F(1−U)
∂V/∂t = Dv∇²V + U V² − (F+k)V
```

`(F, k)` select the pattern regime. A reference integrator produces the **target**
field `Y_t` — the "world as it currently is."

**The learner (transformer-NCA).** A single small **transformer block is the local
update rule** of a *learned* cellular automaton over a grid of cell states
`X ∈ ℝ^{H×W×d}` (decision **(ii)** from our discussion — the rule is weight-shared
and applied everywhere; it is *cellular*, not a whole-field sequence model):

- **Perception:** each cell attends over its **local neighborhood** (a k×k window /
  masked local attention) — this is the diffusion term, and locality is load-bearing
  (global attention = infinite diffusion = homogenization; the thermolife HK result).
- **Update:** attention output + a pointwise **MLP** (the reaction term) produce the
  cell's state increment; a bounded activation / norm keeps it stable.
- **Readout:** a linear map turns each cell state into (a) its `V` concentration for
  the world-match loss and (b) — optionally — a grounded contour **shape** for the
  thermolife-style render.

One **CA rollout** = apply this rule `R` times across the grid (a short forward
unroll). This is the "forward pass"; it is *not* where the watching happens.

## 4. The training loop = the simulator (nested a-outer / b-inner)

State carried across frames: block weights `θ`, the persistent field `X`, the
environment `(F, k)`, and the reference state that produces `Y`. **Each frame:**

1. **Drift the environment** — the nested non-convergence:
   - **Outer, (a) — exogenous:** a slow scripted schedule moves `(F, k)` along a path
     through the pattern phase diagram (spots→stripes→worms→…). Controllable, legible.
   - **Inner, (b) — endogenous (staged in at M4):** let `(F, k)` (or a local feed
     field) **respond to X itself** — the pattern consumes/reshapes its own feed — so
     part of the drift is self-generated (Red Queen in miniature). In nature both
     happen, nested; so does this (see §8).
2. **Target:** advance the reference PDE under the new `(F, k)` → `Y`.
3. **Roll the learner:** apply the transformer rule to `X` for `R` steps → `X'`.
4. **Loss:** `L = ‖ readout_V(X') − Y ‖²` (+ small regularizers, §5).
5. **One optimizer step** on `θ` (backprop through the R-step rollout).
6. **Persist & render:** `X ← X'`; draw `X'` (and optionally `Y`) and the live loss.

Because `Y` keeps drifting, `L` never reaches 0 and `θ` never settles — **the
training loop is a perpetual chase, and that chase is the animation.**

## 5. The exact objective, and "is there data?"

**Per-frame training loss** (differentiable, minimized by SGD/Adam):

```
L(θ) = ‖ readout_V(rollout_R(X; θ)) − Y(F_t,k_t) ‖²
        + β · smoothness/norm regularizer on the update (anti-blowup)
```

**Is there training data?** No fixed dataset. The target `Y` is **generated
on-the-fly** by the reference Gray–Scott integrator at the current drifting
`(F, k)` — a procedurally-generated, non-stationary stream. The "data distribution"
is *initial-condition seeds × (F,k) trajectories*; **held-out (F,k) paths** (and
unseen seeds) validate that the learner generalizes rather than memorizes one basin.
This is self-supervised tracking of a moving simulator, not supervised learning.

## 6. The measurable objective for heedless iteration — *aliveness of training*

We do not tune "never converges" by eye. Reusing thermolife's ungameable-metric
discipline, but applied to the **training trajectory** `{L_t, θ_t}` on the
asymptotic window:

```
TrainAliveness = gate_bounded          (L finite, not diverging)
               · gate_nonzero_loss     (L stays > ε: it never fully catches up)
               · gate_progress         (it DOES track: L below a naive no-learning baseline)
               · churn                  (‖Δθ_t‖ sustained: weights keep moving)
               · non_periodic          (θ / L path is not a short limit cycle)
```

Hard-zeros the trivial fates: **diverged** (blow-up), **converged** (L→const,
churn→0), **not-learning** (never beats the frozen-θ baseline), **trivial cycle**.
Rewards a learner that perpetually tracks-but-never-catches a drifting world. This
scalar is what any later search / hyperparameter loop maximizes.

## 7. Invariants (properties, each gated by a test)

- **P1 Locality.** The cell rule reads only a bounded neighborhood (no global mixing).
- **P2 Weight-sharing.** One block is applied at every cell (it is a CA, not H·W
  distinct nets).
- **P3 Determinism.** `(seed, F/k schedule)` → byte-identical run.
- **P4 Read-only render.** Snapshotting never perturbs training (state hash invariant).
- **P5 Non-convergence under drift.** With drift on, `L` never flatlines and `‖Δθ‖`
  stays above a floor over a long window (the core claim, measured).
- **P6 Convergence without drift (control).** With drift **off**, training *does*
  converge (L→low, churn→0) — proving the non-convergence is caused by the drift,
  not by broken optimization. (The freeze test from our (a)/(b) discussion.)
- **P7 Boundedness.** States/weights/loss stay finite and bounded (no NaN/blow-up).
- **P8 Grounded render (if shapes on).** The drawn shape is a readout of the cell
  state — the picture *is* the state, not a decoration.

## 8. Milestones (vertical slices, each ends watchable + a binary gate)

- **M0 — World + render.** Reference Gray–Scott integrator + grid render + project
  skeleton (bazel, tests, config). *Gate:* reproduces a known Gray–Scott pattern;
  deterministic.
- **M1 — Learner rule, forward only.** The transformer-NCA rule; untrained rollout.
  *Gate:* P1/P2 (locality, weight-sharing) hold; bounded (P7); deterministic (P3).
- **M2 — Train to a STATIC target (the control).** Fixed `(F,k)`; train the NCA to
  grow/hold one Gray–Scott pattern. *Gate:* **P6** — it converges (L→low, churn→0).
  This proves the pipeline and is the honest baseline.
- **M3 — Drift → never converge (the payoff).** Turn on the outer **(a)** `(F,k)`
  schedule; online training. *Gate:* **P5** — L never flatlines, churn sustained,
  and it beats the frozen-θ baseline (it *is* tracking). Ship the **TrainAliveness**
  metric + the watchable viewer. This is the deliverable.
- **M4 — Close the inner loop → (b).** Make `(F,k)`/feed respond to `X`. *Gate:*
  non-convergence persists **with the outer schedule frozen** (endogenous drift);
  compare TrainAliveness (a) vs (a+b).

Critical path M0→M1→M2→M3; M4 is the payoff extension.

## 9. Out of scope / later

- **Ant-colony / agent variant.** Same "environment-driven adaptation" spirit but
  discrete, stigmergic, multi-agent — a different substrate (closer to thermolife's
  economy). Deferred; vivarium is the continuous/differentiable one.
- **Grounded contour shapes as the primary render.** Optional overlay (P8); the
  primary render is the `V` field (classic RD look) because it makes "is it tracking
  the target?" legible. Shapes can be switched on later.
- Population growth / division (that was the morph's flourish, not needed here).

## 10. Open decisions (need your call before M0)

1. **Name.** `vivarium`? alternatives: `redqueen`, `perpetua`, `morphogen`.
2. **Autodiff.** Backprop through the R-step rollout. **(a)** `autograd` (pure-python,
   consistent with thermolife, no new heavy dep, but slow — keep grid ≈ 32×32, d ≈ 8,
   R ≈ 4–8); **(b)** add `torch`/`jax` (fast, GPU, but a new dependency and a
   departure from the repo's numpy-only norm). *Rec:* start **autograd** at tiny scale;
   escalate to torch only if M2 is too slow to iterate.
3. **Loss target.** **World-tracking** (match the reference PDE's `V` field — proposed,
   most legible) vs **homeostatic** (hold a target statistic, no reference integrator —
   simpler but less "chasing a world"). *Rec:* world-tracking.
4. **Render primary.** `V`-field heatmap (proposed) vs grounded shapes vs both.
5. **Hosting.** Reuse a thermolife-style stdlib server/viewer (vendored) so it's
   watchable on the tailnet like the others? *Rec:* yes, vendor a minimal one.

---

### What I'm most unsure of (flagging honestly)

- **M3 is the real risk.** Online SGD tracking a fast-drifting target can (i) lag so
  far it's effectively random, or (ii) the drift can be slow enough that it quasi-
  converges between steps. There's a **drift-rate sweet spot** (the analog of the
  economy's v\* gate) we'll have to find — likely the first real experiment. The
  TrainAliveness metric exists precisely to locate it.
- **Legibility of "learning."** We must make it visually obvious that *weights* are
  changing (the rule is adapting), not just that the field is moving. Plan: show the
  loss curve + a churn indicator alongside the field, and a frozen-θ ghost for
  contrast.
