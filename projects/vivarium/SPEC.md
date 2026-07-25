# vivarium — spec (for review; no code until approved)

> **A petri dish of living bacteria whose *interaction rule learns as they live*.**
> Free-moving grounded-shape agents interact locally with each other; the rule that
> governs the interaction adapts *every step* by a **local learning rule** (not a
> global loss). Emergent, interacting, never-settling collective life — a continuous,
> learnable **Game of Life** — with **aliveness measured, never optimized.** Working
> name: **vivarium**. Rename freely.

New standalone project (`projects/vivarium/`); vendors a small self-contained block
(no cross-project import of thermolife). Shares thermolife's *ideas* (block as an
interaction engine; grounded readouts; the aliveness metric) but not its code.

**Design rationale + the alternatives we rejected live in [`DECISIONS.md`](DECISIONS.md).
The open global-vs-local research question lives in
[`design/global_vs_local.md`](design/global_vs_local.md); its rigorous thermodynamic
foundation — the potential–flux structure `ẋ = −D∇Φ + J`, the single-scalar-vs-flux question,
and the deferred flux experiments — lives in [`design/potential_flux.md`](design/potential_flux.md).
Prior art, the training-route fork, and post-M2 architectural directions live in
[`design/related_work.md`](design/related_work.md). A parallel *molecular / energy* formulation
("do what molecules do" — transformer as a force field, dynamics = `−∇_X E_θ + J`) and the
two-scale comparison it enables are reasoned through in
[`design/two_tracks.md`](design/two_tracks.md) (reasoning only, undecided).**

---

## 1. The one idea

Not the fold (docking, converges) and not the Gray–Scott lattice (fixed cells). A
**petri dish of moving bacteria that interact with each other** — complexity comes
from agents affecting agents, like Conway's Game of Life / Boids / Lenia. The twist:
their shared interaction rule **learns while they live** (one clock, biological
plasticity), so **watching the simulation is watching it learn**, and it **never
converges** because the colony (gently perturbed by a drifting field) keeps adapting.

## 2. Substrate

- **Petri dish:** a bounded continuous space, **2-D or 3-D** (per-config `pos_dim ∈ {2,3}`;
  not a lattice). 2-D is the flat dish; `pos_dim=3` is a volumetric dish, in which the
  contour basis becomes real spherical harmonics (see DECISIONS D12).
- **Bacteria:** `N` free-moving agents, each an embedding `x_i ∈ ℝ^d`. Channels split
  into **position** (`pos_dim` channels — where it is), **shape** (its grounded contour
  readout `C = x·W_c`, drawn as a blob — `2K` coefficients in 2-D, `K(K+2)` in 3-D),
  a **k=0 radius** channel (its physical *size*, held disjoint from the contour so that
  bulk and charge are independent), and **hidden** (working memory for talking to
  neighbors). The contour carries only the `k≥1` / `l≥1` charge *deviation*.
- **Interaction = local attention.** Each bacterium attends over its *nearby* neighbors
  (distance-penalized). Locality is load-bearing: global/all-to-all coupling
  homogenizes (the thermolife HK result; see `global_vs_local.md`).
- **The transformer block is the shared local interaction rule**, applied every tick
  (weight-tied → "layers" and sim-time steps are the *same* axis).
- **Gentle drift:** a weak external field slowly changes (the "season"), so the colony
  is perpetually, mildly perturbed — the nested outer-(a) non-stationarity.

## 3. One clock: learn while living

Every tick does **both** the forward interaction **and** a weight update, from a
**local learning rule** — no global loss, no backprop, no separate training phase:

- **Local predictive plasticity (the pick):** each bacterium predicts its neighbors'
  next state; the local surprise `e_i = actual − predicted` drives `Δθ_i ∝ e_i · inputs`.
  Bacteria get better at anticipating each other → coordinated dynamics; the drift +
  ever-shifting neighbors mean they never fully predict → **never converge.**
- Alternatives (Hebbian, homeostatic) documented in DECISIONS/global_vs_local.

**There is no global objective being optimized.** Aliveness is a **measured readout**,
never a target (the project's measure-don't-reward discipline). Emergence, if it comes,
is earned by local rules — exactly Game of Life's spirit.

## 4. What is measured (not optimized): aliveness

The same ungameable idea as thermolife's `aliveness`, applied to the colony over a
window. The **live** score is `gate_finite · gate_spread · gate_motion · structure ·
coherence`, reported alongside the dish plus an edge-of-chaos Lyapunov diagnostic. It
scores the run; it never feeds back into the rule.

**Irreducibility (INTERACTION) is measured separately, not as a live factor.** Requiring
the life to be *irreducible* — ablate agent–agent coupling and the colony must be *less*
alive (many-body; the economy's shuffle test) — needs a *counterfactual coupling-off
rollout*, so it cannot be a term inside the per-tick score. It is a distinct **ablation
experiment**, owned by invariant P6 and gated at M2 (see
[`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) Step 4), not a multiplier in the live
gauge above.

## 5. Visualization — two clocks would give two views; one clock gives one

Because it's one clock, the petri dish **is** the learning. Each frame = one tick =
bacteria interacting *and* their rule adapting. Render: moving grounded-shape blobs +
local interaction edges + the live (measured) aliveness / Lyapunov readouts + a churn
indicator so it's visible that the *rule* is changing, not just the state.

## 6. Invariants (each gated by a test)

- **P1 Locality** — interaction + learning use only a bounded neighborhood (no global
  loss, no backprop, no all-to-all coupling).
- **P2 One clock** — a single step advances both state and weights; no separate phase.
- **P3 Measured-not-rewarded** — no code path lets aliveness (or any global objective)
  influence the update. Grep-able.
- **P4 Determinism** — `(seed, drift schedule)` → byte-identical run.
- **P5 Read-only render** — snapshotting never perturbs the dynamics.
- **P6 Interaction is load-bearing** — measured aliveness with coupling ablated < with
  coupling on (else it's not Game-of-Life, it's independent agents).
- **P7 Boundedness** — states/weights finite and bounded (no blow-up).
- **P8 Grounded render** — the drawn shape is a readout of the bacterium's embedding.

## 7. Milestones (vertical slices, each watchable + a binary gate)

> The rigorous, checklist-first execution of M0–M2 (organism track, Route A) lives in
> [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): Step 1 = M0, Step 2 = M1,
> Steps 3–4 = M2, with each invariant below tied to a specific test in a specific step.

- **M0 — Dish + agents + render + skeleton.** Moving grounded-shape bacteria under a
  *fixed random* interaction rule (no learning yet). *Gate:* P1/P4/P5/P7/P8.
- **M1 — Local learning rule (one clock).** Predictive plasticity on; weights change
  every tick. *Gate:* P2/P3 (one clock; nothing optimizes aliveness); still bounded.
- **M2 — Emergent interacting life.** Tune the substrate (scale, ranges, drift) until
  the *measured* aliveness clears collapse/freeze AND **P6** (interaction irreducible).
  *Gate:* P6 + sustained non-convergence over a long window. **This is the deliverable.**
- **M3 — Global-vs-local experiment.** Implement a global-rule variant (see
  `global_vs_local.md`) and compare measured aliveness/patterns to the local rule.
  *Gate:* a documented, honest verdict on the research question.
- **M4 (post-core research program) — The potential–flux experiments.** Instrument the
  non-conservative flux `J` (entropy production / broken detailed balance / probability
  current) and test the sharpened thermodynamic claims: aliveness ⟺ `‖J‖ > 0`, and
  `J → 0 ⇒ death`, vs a pure-gradient control. Full program (E-flux1–5) +
  the single-scalar-vs-flux foundation in [`design/potential_flux.md`](design/potential_flux.md).
  *Not first-pass — do not pull into M0–M2.*

## 8. Open decisions (see DECISIONS.md §Open)

Name · which local rule (predictive / Hebbian / homeostatic) · scale (N, d, ranges) ·
autodiff/impl (numpy local rules need no autograd; a global-energy variant might) ·
whether to keep a two-clock ES variant as a control · hosting.
