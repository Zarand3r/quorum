# vivarium — decision log

What we've decided, what we rejected, and why. Newest context at the bottom of each
entry. This is the "why"; [`SPEC.md`](SPEC.md) is the "what".

Legend: **Decision** · *Alternatives* · *Rationale* · *Status*.

---

### D1 — A new standalone project, not part of thermolife
**Decision:** vivarium lives in `projects/vivarium/` and **vendors** a small
self-contained transformer block. *Alternatives:* extend thermolife's `fold/`.
*Rationale:* the monorepo forbids cross-project imports; and the concept (learn-while-
living) is distinct enough to deserve its own clean surface. *Status:* firm.

### D2 — The simulator IS the learning
**Decision:** you watch the network **learn**, not a pre-trained net run.
*Alternatives:* the thermolife pattern (train offline, watch inference).
*Rationale:* the user's north star from the start — "the simulator is the training
iterations." *Status:* firm.

### D3 — Petri dish of MOVING bacteria, not a fixed Gray–Scott lattice
**Decision:** free-moving agents in continuous 2-D (the fold/morph/economy lineage).
*Alternatives (rejected):* a Gray–Scott reaction–diffusion **lattice** where cells
never move — this was an earlier spec draft. *Rationale:* the user wants the **fold's
soul** (shapes that move and interact), a "petri dish of moving bacteria," not a frozen
grid. The Gray–Scott version made the *environment* the star; here the *interaction* is
the star. *Status:* firm — **explicitly reverses the earlier Gray–Scott decision.**

### D4 — The core is agent–agent INTERACTION → emergence
**Decision:** complexity comes from bacteria affecting each other (Conway's Game of
Life / Boids / Lenia), **not** from individuals chasing food. *Alternatives (rejected):*
a foraging/coverage objective where interaction is incidental. *Rationale:* user:
"they aren't just chasing food, they interact with each other like in Conway's Game of
Life." Interaction must be *load-bearing* (invariant P6). *Status:* firm.

### D5 — Bacteria are grounded-shape embeddings
**Decision:** each agent is an embedding `x_i∈ℝ^d`, rendered as its grounded contour
blob `C=x·W_c`; channels split position / shape / hidden. *Rationale:* carries
thermolife's grounding (the drawn shape *is* the interaction readout). *Status:* firm.

### D6 — Interaction is LOCAL (distance attention)
**Decision:** each bacterium attends only to nearby neighbors. *Alternatives:* global
softmax. *Rationale:* the thermolife HK study + the deeper physics (see
`global_vs_local.md`): finite-range coupling is necessary for moving spatial structure;
global/all-to-all homogenizes (collapse). *Status:* firm.

### D7 — Non-convergence = intrinsic + a gentle drift (nested a/b)
**Decision:** intrinsic interaction dynamics **plus** a slowly drifting external field.
*Alternatives:* pure intrinsic (like Game of Life, no environment) OR pure external
drift. *Rationale:* nature does both, nested — intrinsic rhythms entrained by slow
external change. User chose "intrinsic + gentle drifting environment." *Status:* firm.

### D8 — One clock, not two
**Decision:** a single tick advances **both** the forward interaction **and** a weight
update — the system learns *while* it lives. *Alternatives (rejected):* two clocks
(train a rule by ES on a slow loop, watch it run forward on a fast loop). *Rationale:*
the user challenged the two-clock framing; biology has one clock (plasticity happens
during activity, not in a separate phase), and it makes "sim = training" literally true.
*Status:* firm — **reverses the earlier two-clock ES framing.**

### D9 — Learning is a LOCAL rule, aliveness is MEASURED
**Decision:** the "loss" is replaced by a **local learning rule** (leading pick:
**predictive plasticity** — each bacterium reduces its own surprise about its
neighbors). Aliveness is a **measured readout**, never optimized. *Alternatives:*
global aliveness loss + backprop/ES (that forces two clocks; see D8). Other local rules:
Hebbian, homeostatic. *Rationale:* one clock (D8) can't use a whole-rollout objective, so
learning must run on locally-available signals each step; and measuring (not rewarding)
aliveness is the project's anti-gaming discipline + Game of Life's spirit (local rules →
emergence). *Status:* firm on "local + measured"; **open** on *which* local rule.

### D10 — No global objective is optimized
**Decision:** consequence of D8/D9 — nothing in the running system optimizes a global
quantity; global aliveness is observed only. *Status:* firm (invariant P3).

### D11 — The thermodynamic justification is potential + flux, not a single scalar
**Decision:** the design is grounded in `ẋ = −D∇Φ + J` — a relaxation/landscape part **plus**
an irreducible non-conservative flux `J`; **no single global scalar governs the living
dynamics** (a gradient system provably cannot oscillate/sustain, and living matter has
measured broken detailed balance). *Consequences:* non-convergence (D7) is `J ≠ 0` made
concrete; Route A's drift and Route B's anti-collapse term are two ways to *supply* `J`;
`J → 0` predicts death (a falsifiable claim). *Rationale + full treatment:*
[`design/potential_flux.md`](design/potential_flux.md). *Status:* firm as framing;
the flux experiments (E-flux1–5) are **post-core**.

---

## Open decisions

- **Name.** `vivarium` (working) vs `redqueen` / `perpetua` / `lenia-t` / `morphogen`.
- **Which local rule** (D9): predictive coding (rec) vs Hebbian vs homeostatic — the
  first real experiment; `global_vs_local.md` argues predictive is a local shadow of a
  global thermodynamic principle, which is a feature.
- **Scale:** `N` bacteria, dim `d`, interaction range, drift rate. A drift-rate sweet
  spot (the economy's `v*` analog) is expected and must be found.
- **Global-rule control (M3):** whether/how to build a global-thermodynamics variant to
  answer the research question (`global_vs_local.md`).
- **Impl:** local rules are plain numpy (no autograd needed); a global energy-based
  variant may want autograd/torch. Decide per-milestone.
- **Hosting:** vendor a minimal thermolife-style server/viewer so it's watchable on the
  tailnet like the others.
- **Training route — hand local rule (A) vs native backprop world-model (B):** OPEN,
  may switch. Both are one-clock and keep aliveness measured-only; A maximizes strict
  locality (D9 default, plain numpy), B replaces the hand delta rule with autodiff backprop
  of the same one-step self-supervised loss + an anti-collapse (JEPA/VICReg) term that stands
  in for the external drift — nothing outside the transformer's forward/backward pass. Full
  trade-off in [`design/related_work.md`](design/related_work.md) §3. Likely resolved
  empirically at M1 (start with A; switch to B if the local rule is too weak/collapses).
- **Architectural variants** (equilibrium-prop, forward-forward, DEQ, skew term):
  deliberately **out of the first pass** — logged as post-M2 future directions in
  [`design/related_work.md`](design/related_work.md) §4, reached for only if the plain
  local rule plateaus or M3 needs them. M0–M2 stay plain numpy + local plasticity.

## Superseded (kept for the record)

- **Gray–Scott fixed-lattice NCA** (reversed by D3): cells that don't move, trained to
  track a drifting Gray–Scott target. Good substrate, wrong *soul* — the environment
  was the star, not the interaction.
- **Two-clock ES-for-aliveness** (reversed by D8/D9): train a reusable rule by ES against
  the global aliveness metric, watch it run forward. May return **only** as an M3
  control to compare against the one-clock local rule.
