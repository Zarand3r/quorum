# Related work — what's different, and where we could go later

Honest positioning. Every *ingredient* below exists in the literature; the contribution is
the **combination + the measurement discipline + one falsifiable question**, not a new
mechanism. This doc has two parts: (§1–2) how vivarium differs from prior art, and (§3) the
architectural changes we deliberately keep **out of the first pass** and log as future
directions.

---

## 1. The neighbours (prior art)

| Work | What it is | Nearest to us on… |
|---|---|---|
| **Growing NCA** (Mordvintsev 2020) | learned *local* rule (fixed Sobel perception + tiny MLP), grows a target image from a seed | local rule, hidden channels, seed-growth |
| **Attention-based NCA / ViTCA** (Tesfaldet 2022) | replaces perception+MLP with *localized self-attention*, recurrent, weight-shared; denoising | attention *is* the local interaction rule |
| **Graph NCA** (Grattarola 2021) | NCA on arbitrary graphs, not grids | agents-on-a-graph, not a lattice |
| **Lenia / Flow Lenia** (Chan 2019+) | continuous, moving, mass-conserving artificial life; emergent "creatures" | moving agents, never-settling, ALife target |
| **Particle Life / Boids** (Reynolds 1987) | local pairwise interaction → emergent collective motion | interaction-driven emergence |
| **Predictive coding** (Rao & Ballard 1999) | local prediction-error message passing | our exact local learning rule |
| **Free-Energy Principle** (Friston 2010) | global variational free energy = surprise + complexity | the global shadow of our local rule (`global_vs_local.md`) |
| **Hopfield / Boltzmann / Ising** | energy ↔ local-rule duality; local learning (`Δw ∝ ⟨··⟩`) | the duality we lean on in M3 |
| **Conway's Game of Life** | local rule → open-ended emergence | the spirit (local → emergence, no global goal) |

## 2. What is actually different about vivarium

Three axes, in decreasing order of how defensible the novelty is:

**(1) One clock — online local learning *is* the simulation.**
Every NCA above (including attention-NCA) is **two-clock**: minimize a global
reconstruction/target loss by **backprop-through-time offline**, then run the *frozen* rule
forward as the "simulation." Vivarium updates the shared block's weights **every tick, by a
local rule, with no global loss and no backprop-through-time** — so watching the sim *is*
watching it learn, literally, not metaphorically. (D8/D9.) This is the sharpest departure.

**(2) Aliveness is a *measured, ungameable observable* — never the objective.**
Lenia/Particle-Life/NCA emergence is **eyeballed** ("look, gliders"). We score the colony with
a gate product (`gate_finite · gate_spread · gate_motion · structure · coherence ·
**irreducibility**`, hard-zeros for collapse/freeze/blowup/noise, plus an edge-of-chaos
Lyapunov diagnostic) that **forbids gaming**, and we **forbid it from feeding back** into the
rule (P3). Falsifiable emergence, not a demo reel. This discipline is rare in ALife and is the
project's real backbone.

**(3) The binary global≡local experiment (M3).**
Most "global vs local rules" talk is philosophy. We reduce it to a matched-harness A/B — a
finite-range *global energy* rule vs the *local predictive-plasticity* rule over the *same*
substrate and *same* aliveness metric — with a stated prediction (`global_vs_local.md`): equal
under matched finite-range + drive; global converges (dies) if the drive is stripped; both
collapse if made mean-field. A refutable claim, not an admired one.

**Carried, not new:** the **grounded readout** (the drawn contour *is* `C = x·W_c`, so the
picture cannot lie about the interaction — thermolife §2) and **distance-penalized locality**
(thermolife's HK study picked smooth-local over hard-local). These are inherited strengths, not
vivarium inventions.

**The honest caveat.** "Learn while living, no global objective, and it's *alive*" is
ambitious: local predictive plasticity alone tends to converge (perfect prediction ⇒ frozen) or
collapse, and the sibling morph sim plateaued at aliveness ≈ 0.16 after search. Plan for a
*measured negative* as the likely first outcome — worth reporting **because** the metric can't
be gamed, but not the triumphant result the framing invites.

---

## 3. Two training routes for the first pass — an OPEN fork (undecided)

Two ways to make the weights learn *while the colony lives*. **Both are one clock, both keep
aliveness measured-only** (P2, P3 hold either way). We have **not committed** — likely resolved
empirically (build M1 with the simpler Route A; switch to B if the local rule is too weak or
collapses). *Status: undecided as of 2026-07 — may switch.*

**Route A — hand-written local plasticity rule (the current D9 default).**
Each tick, update `θ` by a local delta rule `Δθ ∝ Σ_i e_i · input_i`, where `e_i` is agent `i`'s
one-step prediction error about its neighbours. No autodiff. **Strictly neighbour-only:** only an
agent's neighbourhood ever influences `θ`.
- *Pros:* maximal locality (P1 in its strongest form); plain numpy, no autograd; biologically
  faithful (plasticity *during* activity); "nothing global ever touches `θ`" is literally true
  and grep-checkable.
- *Cons:* the delta rule is a hand-derived *approximation* of the prediction gradient; limited to
  shallow predictors; we own its correctness.

**Route B — native transformer backward pass (a world-model of its own rollout).**
Replace the hand rule with **autodiff backprop of the same one-step self-supervised loss** — the
plasticity rule *is* an approximation of this gradient, so compute it exactly. Nothing lives
outside the transformer's forward + backward pass.
- *The loss:* `L = ‖predict − next_state‖²  +  anti-collapse regularizer`.
- *The drift moves into the loss.* Pure prediction **freezes** (perfect prediction ⇒ nothing
  changes ⇒ dead — the same attractor Route A hits). So bake anti-collapse into the objective,
  **JEPA / VICReg-style**: a variance floor + channel-decorrelation term make a frozen/collapsed
  colony *high-loss*. This is the free-energy shape (`surprise + complexity`) and it **replaces
  the externally-injected "season."** (Alternative: keep the drift as non-stationarity *in the
  predicted world/data* — still just forward+backward.)
- *The one-clock loop:* each tick — forward step, compute `L`, backward, `θ ← θ − η∇L`, continue
  (or an outer loop over rollouts).
- *The deep unification:* transformers learn **in-context** — a single forward pass ≈ gradient
  descent (mesa-optimization; von Oswald+2022). So "learn while living" can live *inside* the
  forward rollout, and backprop only shapes `θ` to make that in-context learning good — the most
  literal "the simulation **is** the training iterations."
- *Pros:* native machinery, exact gradients, expressive (deep predictors); the in-context story;
  standard and well-understood.
- *Cons:* the loss is summed over agents ⇒ **more global than Route A** — the backward pass
  distributes credit across the attention graph within a step, so "only neighbours influence `θ`"
  softens to "a sum of local loss terms, backprop'd" (you can restrict each prediction term to a
  neighbourhood to stay as local as possible, but not *strictly* neighbour-only); wants autograd
  (numpy-autodiff or torch).

**Invariant across both routes (non-negotiable either way):**
- **One clock (P2):** weights change during the sim; no separate training phase.
- **Aliveness measured-only (P3):** the optimized objective is *self-supervised prediction
  (+ anti-collapse)*, **never** aliveness. Choosing Route B does **not** mean training for
  aliveness — the scoreboard still never enters the loss.
- **The freeze attractor exists in both:** pure prediction settles; something off-equilibrium
  (external drift in A; an anti-collapse loss term or non-stationary data in B) must counter it.
  Same physics, different bookkeeping.

**Note the bridge:** F1 (Equilibrium Propagation, §4) is essentially a *third* route — Route B's
expressiveness with Route A's strict locality (local dynamics compute the global gradient). If
the A-vs-B trade (locality vs exactness) becomes the binding constraint, F1 is where to look.

---

## 4. Future architectural directions (post-M2 — NOT the first pass)

**Scope guard.** M0–M2 are **plain numpy**, **local predictive plasticity**, **no autograd, no
architecture surgery.** The prototype must earn (or honestly fail to earn) measured aliveness
with the simplest possible mechanism first. Everything below is **exploratory**, reached for
*only* if the local-rule first pass plateaus, or to answer a specific question M3 raises — never
as scope creep to escape a stuck step.

These matter because architecture is the lever that decides **whether a global objective is even
reachable by local-only, one-clock updates** — i.e. whether we can ever bridge "optimize a
global target" with "keep one clock + locality" without regressing to two-clock backprop.

**F1 — Energy-based / equilibrium-prop block (Equilibrium Propagation, Scellier & Bengio 2017).**
Cast the block as an energy-based net whose *local* relaxation dynamics compute the *same
gradients* a global loss would (via a nudged second phase), using only locally available
signals. *Buys:* a principled way to descend a **global** objective with a **local** rule, one
clock intact. *Costs:* a second (nudged) phase per step, careful energy design, likely
autograd/torch. *Reach for it when:* M3 wants a global-objective variant that is still local, or
the pure predictive rule underperforms and we want global credit without breaking locality.

**F2 — Forward-Forward (Hinton 2022).**
Drop backprop entirely; each layer/agent optimizes its own **local "goodness"** objective on
positive vs negative data. *Buys:* fully local, one-clock learning with a crisper objective than
raw prediction-error. *Costs:* need a sensible positive/negative-data notion for a petri dish
(what is a "negative" colony state?). *Reach for it when:* predictive plasticity's surprise
signal is too weak/degenerate and we want a stronger local target that's still not global.

**F3 — Deep-equilibrium / iterative-inference block (DEQ; predictive-coding nets).**
Make the forward pass *itself* an iterative optimization, so "run the sim" and "descend the
objective" are the **same iteration** — the most literal "sim = training." *Buys:* the
cleanest identification of dynamics with learning. *Costs:* fixed-point solves, stability, cost
per tick. *Reach for it when:* we want the tightest possible "training iterations = simulation
frames" story and are willing to pay for it.

**F4 — Skew / rotational non-gradient term (already proven in morph).**
Add an intrinsic term that is *not* the gradient of any energy (Helmholtz: `f = −∇E + rot`), so
the dynamics **cannot settle** even with no external drive. *Buys:* intrinsic non-convergence
without leaning entirely on the drift — answers `global_vs_local.md` open-question 7 (can a
purely internal term sustain aliveness with no environment?). *Costs:* a hyperparameter that can
tip into blow-up; must stay inside the boundedness gate (P7). *Reach for it when:* the drift
alone is insufficient, or we want to test intrinsic vs external non-equilibrium cleanly. **This
is the smallest, cheapest of the four** — closest to first-pass-adjacent, but still deferred so
M0–M2 isolate the local rule's own behaviour first.

**F5 — Global energy-based control arm (this is M3, cross-referenced).**
The finite-range non-equilibrium *global* rule from `global_vs_local.md` §6 — kept here so the
architectural options are all in one list. Unlike F1–F4 it is *already planned* (as the
experiment's other arm), not speculative.

**Common thread.** F1–F3 are all routes to "global credit via local dynamics"; F4 is "intrinsic
non-convergence"; F5 is "the global control." None belong in M0–M2. If aliveness is earned by
the plain local rule, we may never need them — which would itself be the strongest result.

---

*See also:* [`DECISIONS.md`](../DECISIONS.md) (why we chose one clock + local rule),
[`global_vs_local.md`](global_vs_local.md) (the global≡local question + M3 experiment),
[`potential_flux.md`](potential_flux.md) (the thermodynamic foundation: `ẋ = −D∇Φ + J`, the
single-scalar-vs-flux question, and why Routes A/B are two ways to supply the flux `J`),
[`two_tracks.md`](two_tracks.md) (the parallel molecular/energy track — transformer as a force
field — and the two-scale comparison), [`../SPEC.md`](../SPEC.md) (milestones + invariants).
