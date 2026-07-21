# Vivarium: a transformer-only living dish — grounded shapes that move, morph, and bind

**vivarium — working paper v1 (2026-07).** *A watchable, hosted demonstration. All claims are at
toy scale and reported with their honest limits and negative results.*

---

## Abstract

We present **vivarium**, a live, browser-watchable artificial-life dish in which every agent is a
single token of one small transformer, and *the simulation is the transformer's forward pass*.
Each agent carries a 2-D position and a **grounded contour** — a drawn blob that, by Parseval, *is*
the token's attention query. Iterating one weight-tied block, agents **move** by neighbour
attention (attract toward complementary "lock-and-key" shapes, repel from clashing ones, cohere by
surface tension) and **morph** their contours to fit their binding partners (induced fit). The
whole update is **strictly transformer-only** — attention, MLP, LayerNorm — with *no external force
law, no energy ledger, and no variable token count*. We show that this produces a compact,
conserved, continually-rearranging **droplet of bound, morphing shapes**, watchable live and
instrumented with an *ungameable, measured-not-rewarded* aliveness gauge. The result is a
demonstration, not a triumph: measured aliveness is modest (~0.05–0.3 on [0,1]) and the network
*weights are fixed* (the **state** is optimized, not the parameters). We report the built system,
its visualizations, and — prominently — what the honest metric refused to certify.

---

## 1. What it is, and the one idea

Open the dish and you see ~64 coloured blobs on a bounded periodic plane. They drift, deform,
and connect to partners with amber "binding" lines. It is not a video and not a pre-trained net
playing back: **each animation frame is one application of a transformer block to the set of
agent-tokens.** Running it *is* computing it.

> **Living = inference = optimization, with no separation.** A tick is a forward pass; the forward
> pass relaxes a physical energy; the relaxing *is* the living. There is no separate train / infer
> / run phase.

The design lineage is deliberate. From the sibling **thermolife** project we inherit the
*grounded readout*: one linear map produces both the drawn contour and the attention query, so —
by Parseval — the attention dock score **equals** the overlap integral of the two drawn shapes.
The picture cannot lie about the computation. Vivarium's move is to make that grounded interaction
**a moving, morphing, binding population** rather than a settling docking task.

## 2. The substrate (dock-and-morph)

Each agent is one token `xᵢ ∈ ℝ^d` (default `d=16`, `N=64`), split into **position** `pᵢ` (2
channels), **shape** `Cᵢ` (the grounded contour, `2K=6` channels), and **hidden** (8 channels). The
dish is a **periodic (toroidal) plane** — no walls, so nothing piles in corners.

Two grounded overlap sensors, both free from the attention math (Parseval):
- **direct clash** `⟨Cᵢ, Cⱼ⟩` — shapes occupying the same space (steric overlap);
- **complementary fit** `⟨Cᵢ, M·Cⱼ⟩` — bump-meets-pocket, `M` a fixed π-rotation.

One weight-tied block per tick, all **strictly transformer-only** (attention / MLP / LayerNorm;
see [`design/HARD_REQUIREMENT.md`](../design/HARD_REQUIREMENT.md)):

- **attract head** — `A_fit = softmax_j(⟨Cᵢ,M·Cⱼ⟩ − λ‖Δp‖²)`; move toward complementary neighbours.
- **repel head** — `A_rep = softmax_j(⟨Cᵢ,Cⱼ⟩ − λ‖Δp‖²)`; move away from clashing neighbours. To
  keep the push finite as shapes touch (a bounded softmax weight of `Δp` vanishes at contact), the
  head aggregates **unit directions** — so repulsion is a genuine attention op, *soft* excluded
  volume, **not** a divergent `1/d²` kernel.
- **cohesion head** — a broad `A_coh = softmax_j(−λ_c‖Δp‖²)` over a larger neighbourhood; pull
  toward the neighbourhood centroid. This is **surface tension**: it merges fragments into one
  droplet (§4.2).
- **shape morph** — `z ← LN(z + morph·A_fit·zWᵥ + skew·zJ)`, then `z ← LN(z + MLP(z))`. The
  attention message deforms an agent's contour toward its binding partners (**induced fit**); the
  skew term `zJ` (`J=−Jᵀ`) keeps the shape rotating so the packing never freezes.
- Position integrates with momentum and a velocity cap, then wraps to the torus.

**Motion comes only from neighbour attention.** With no neighbours (the identity ablation) the
force is exactly zero — so **interaction is load-bearing for the dynamics by construction** (an
isolated agent cannot move). This is the property every earlier design failed (§5).

## 3. The physical law (and where it is baked in)

There is no trained loss and no gradient descent on weights — but there **is** a physical
objective, and it lives in the grounded attention. The dock score `⟨Cᵢ, M·Cⱼ⟩` *is* a binding
energy (Parseval). The dynamics descend a **packing / binding free energy** `Φ` (↓ steric clash,
↑ complementary fit), driven off-equilibrium by the non-gradient **skew flux** `J`:

$$\dot x = -D\,\nabla\Phi(x) \;+\; J(x)$$

This is the **potential–flux form** of a living, dissipative system (see
[`design/potential_flux.md`](../design/potential_flux.md)): a landscape the state relaxes down,
plus a rotational flux that keeps it from settling. The *inference* relaxing `Φ` **is** the living.
So vivarium *does* embody a thermodynamic objective — it simply is not a *training* loss.

**Honest scope of "no separation."** *living = inference = optimization* holds at the **state**
level: the embeddings (the "fold") are what the forward pass optimizes. It does **not** hold at
the **weight** level — the parameters are fixed. Full *"weights that learn while alive"* (training
= living, one clock) is the harder predictive-plasticity direction we built, measured, and set
aside (§5).

## 4. What it does (measured)

Aliveness is a single ungameable gauge, **measured over a window and never fed back** into the
update (measure-don't-reward):
`gate_finite · gate_spread · gate_motion · coherence · structure · deformation ∈ [0,1]`.
Hard-zero gates kill the degenerate regimes (freeze, collapse, blow-up, white noise). Two factors
were hardened after early self-deception: **structure** uses drift-removed velocities (a rigid
coherent *translation* scores ~0), and **deformation** measures change in the pairwise-distance
configuration (a rigid *rotation* scores ~0). Only genuinely reconfiguring, coordinated motion
scores.

### 4.1 It is matter, not gas
With cohesion off, a validated aggregation metric (occupancy, cluster fraction, radius of gyration
`Rg`; [`metrics_pack.py`](../metrics_pack.py)) reads the colony as **matter, not gas**: occupancy
0.24 (it does *not* fill the box), and `Rg` is **box-independent** (0.52 at both 1× and 2× box) —
the signature of a compact aggregate rather than a spreading gas. But it forms **~4–5 small
clusters**, not one droplet.

### 4.2 Cohesion merges fragments into one droplet
Turning on the cohesion head (surface tension) merges them: at strength 0.15 the largest cluster
goes 41% → **100%** (one cluster), occupancy 0.21 → 0.05 (compact, empty space around it), and the
droplet is *more alive* — aliveness ~0.3 with deformation ~1.0 (a continually morphing, rearranging
droplet, not a frozen clump). **Honest limit:** cohesion has finite range, so in a 2× box the
fragments — now farther apart than the reach — re-fragment. Surface tension is local; the single
droplet holds at the default density.

### 4.3 A pure-transformer variant moves *everything* by attention
A second engine ([`pure.py`](../pure.py)) drops the force framing entirely: position is just
channels of `X`, updated by the *same* block (attention + MLP + LayerNorm) with **non-reciprocal
attention** `A + β(A−Aᵀ)` — the antisymmetric part supplies circulation that defeats attention's
rank-collapse contraction. It sustains coordinated morphing motion at higher aliveness (~0.26 mean,
~0.42 best-seed) to 8000 ticks. Here P6 is **measured-positive** (identity ablation drops aliveness
by ~0.10) rather than by-construction, because the per-agent MLP produces a baseline of motion —
an honest weaker guarantee than the force-based substrate's.

## 5. What the honest metric refused to certify (and prior dead ends)

The measure-don't-reward discipline earned its keep by falsifying results that eyeballing would
have accepted:
- **Predictive plasticity** (weights learn online to reduce surprise about neighbours) **collapsed**
  — surprise is minimized the trivial way, by homogenizing; and a *frozen-weights control scored
  the same aliveness as the learned one*, so the learning was **not load-bearing**. This is the
  design that would have made "training = living" literal; we could not make it work at toy scale.
- **Strong external drift** produced high aliveness that **survived ablating interaction** —
  independent agents dragged by a field, not a colony (P6 fails).
- A **too-weak early metric** rewarded a rigid coherent *drift* as "alive"; a **rigid rotation**
  slipped past until the deformation gate was added; and a **short measurement window** mistook
  *dying transients* (peak aliveness 0.13–0.17 that froze by ~1500 ticks) for sustained life.

Each is recorded with its commit in [`RESEARCH_LOG.md`](../RESEARCH_LOG.md). The through-line: the
metric is a bullshit detector, and it fired repeatedly.

## 6. Visualization and hosting

Vivarium runs live in the browser (stdlib HTTP server + a self-contained canvas viewer), exposed
on a tailnet. Solid grounded-contour blobs show packing and boundaries; **amber lines draw the
real binding graph** — each agent's strongest complementary-fit attention partner, opacity ∝
attention weight (not a proximity heuristic — the actual `A_fit` the transformer computes). Live
sliders expose every coefficient (repel, attract, cohesion, skew, morph, momentum, speed) and an
in-page panel documents the architecture, the network geometry (real tensor shapes), and the
objective. Client-side interpolation and wrap-aware rendering keep the motion smooth over the
network.

## 7. Related work (honest positioning)

None of the ingredients is new; the contribution is the **combination + the strict
transformer-only constraint + the ungameable metric**. Neural Cellular Automata [Mordvintsev+2020]
iterate a learned local rule; **attention** as the CA rule is done [Tesfaldet+2022 (ViTCA)]. Lenia
and Flow Lenia [Chan2019] are the moving, mass-conserving ALife this resembles; Particle Life and
Boids [Reynolds1987] are the attract/repel lineage. The grounded readout, potential–flux law, and
predictive-plasticity direction connect to energy-based models [Ramsauer+2020], predictive coding
[Rao&Ballard1999], the Free Energy Principle [Friston2010], and measured broken-detailed-balance in
living matter [Battle+2016]. What is unusual here: *everything is one transformer's forward pass*
(no bolt-on force law), and *aliveness is a falsifiable measured observable*, where almost all ALife
is eyeballed.

## 8. Honest limitations

- **Modest aliveness.** ~0.05–0.3 on [0,1] — genuinely alive-looking motion, but faint; the sibling
  morph sim reached ~0.16, and absolute "aliveness" here is not high.
- **Weights are fixed.** The *state* is optimized, not the parameters. The full "learn while living"
  thesis is unrealized (§5).
- **Soft boundaries.** Bounded-attention excluded volume is strong-but-not-hard; shapes strongly
  avoid overlap but there is no guaranteed wall (the price of strict transformer-only).
- **Cohesion is finite-range.** One droplet holds at the default density; a larger box re-fragments.
- **P6 varies by engine.** Load-bearing *by construction* in the force-based substrate; only
  *measured-positive* in the pure-attention variant (per-agent MLP baseline).
- **No division or metabolism.** Both would require state beyond a fixed token set, breaking the
  transformer-only constraint; explicitly out of scope.

## 9. Conclusion

Vivarium is a small, honest demonstration that *a fixed set of grounded shapes, moved and morphed
purely by one transformer's attention, will pack, bind, and continually rearrange into a
conserved, watchable droplet of life* — with the physical law baked into the grounded attention
(`ẋ = −D∇Φ + J`) and aliveness measured rather than rewarded. It is not alive in any strong sense,
and its weights do not yet learn while it lives; those are the next milestones, not this paper's
claims. What we offer is the built thing, the discipline that kept us honest about it, and the
dish you can open and watch.

## References

*(informal.)*
[Mordvintsev+2020] Growing Neural Cellular Automata, distill.pub/2020/growing-ca.
[Tesfaldet+2022] Attention-based Neural Cellular Automata (ViTCA), NeurIPS.
[Chan2019] Lenia — Biology of Artificial Life, arXiv:1812.05433 (Flow Lenia, arXiv:2212.07906).
[Reynolds1987] Flocks, Herds and Schools, SIGGRAPH '87.
[Ramsauer+2020] Hopfield Networks is All You Need, arXiv:2008.02217.
[Rao&Ballard1999] Predictive coding in the visual cortex, Nature Neuroscience 2(1).
[Friston2010] The free-energy principle, Nature Rev. Neuroscience 11(2).
[Battle+2016] Broken detailed balance at mesoscopic scales in living systems, Science 352:604.
[Ao2004] / [Wang+2008] potential–flux decomposition (see `design/potential_flux.md`).
