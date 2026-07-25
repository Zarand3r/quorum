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
demonstration, not a triumph: measured aliveness is modest (the packing droplet ~0.06; a
pure-attention variant reaches ~0.26–0.42 on [0,1]). By default the network weights are fixed (the
**state** is optimized, not the parameters), but an optional, transformer-faithful **plasticity**
— fast-weight Hebbian memory, i.e. the fast-weight form of linear attention — lets the *coupling*
weights learn while the sim runs, and is *load-bearing* when on. We report the built system,
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

Each agent is one token `xᵢ ∈ ℝ^d` (default `d=16`, `N=64`), split into **position** `pᵢ`
(`pos_dim` channels — 2 for a flat dish, 3 for a volumetric one), **shape** `Cᵢ` (the grounded
contour: `2K` channels of circular harmonics `{cos kθ, sin kθ}` in 2-D, `K(K+2)` channels of real
spherical harmonics `Y_lm`, `l=1..K`, in 3-D), a **k=0 radius** channel, and **hidden** (whatever
`d` leaves). The radius is the token's physical **size** and is deliberately *disjoint* from the
contour: the contour (`k≥1` / `l≥1`) carries only the charge *deviation*, so bulk and charge are
independent — a token can be bulky **and** neutral (a lipid tail) or small **and** strongly dipolar
(water). The dish is a **periodic (toroidal) domain** — a 2-torus in 2-D, a 3-torus in 3-D — so
there are no walls and nothing piles in corners.

Two grounded overlap sensors, both free from the attention math (Parseval):
- **direct clash** `⟨Cᵢ, Cⱼ⟩` — shapes occupying the same space (steric overlap);
- **complementary fit** `⟨Cᵢ, M·Cⱼ⟩` — bump-meets-pocket, `M` a fixed π-rotation.

One weight-tied block per tick, all **strictly transformer-only** (attention / MLP / LayerNorm;
see [`design/HARD_REQUIREMENT.md`](../design/HARD_REQUIREMENT.md)):

- **attract head (van der Waals)** — `g_ij = tanh(radᵢ·radⱼ/0.25)·exp(−λ‖Δp‖²)`; move toward
  neighbours you have contact area with. This is **London dispersion**: proportional to contact
  area / polarizability (the k=0 radius) and **charge-independent** — which is exactly why neutral
  alkanes and oils cohere. It is symmetric, bounded, and decaying, so `F_ij = −F_ji` and the force
  is conservative. It deliberately replaces the earlier `sigmoid(⟨Cᵢ,M·Cⱼ⟩/τ)·exp(−λ‖Δp‖²)`
  *complementary-fit* kernel, which modelled specific lock-and-key binding rather than dispersion
  (and, since `sigmoid(0)=0.5`, made featureless tokens sticky instead of hydrophobic).
- **complementary fit** — `A_fit = softmax_j(⟨Cᵢ,M·Cⱼ⟩ − λ‖Δp‖²)` survives as the **induced-fit
  morph** signal (below); it no longer supplies the attractive force.
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
↑ dispersion contact, ↑ complementary fit *of shape*), driven off-equilibrium by the non-gradient
**skew flux** `J`:

$$\dot x = -D\,\nabla\Phi(x) \;+\; J(x)$$

This is the **potential–flux form** of a living, dissipative system (see
[`design/potential_flux.md`](../design/potential_flux.md)): a landscape the state relaxes down,
plus a rotational flux that keeps it from settling. The *inference* relaxing `Φ` **is** the living.
So vivarium *does* embody a thermodynamic objective — it simply is not a *training* loss.

**Honest scope of "no separation."** *living = inference = optimization* holds at the **state**
level: the embeddings (the "fold") are what the forward pass optimizes. By default the network
weights are fixed. But *"weights that learn while alive"* is now available as an optional,
transformer-faithful mechanism (§3.1) — off by default, and it is **load-bearing** when on.

### 3.1 Optional plasticity: weights that learn while alive (fast-weight linear attention)

Biology adapts within a life not by changing the laws of physics but by changing **coupling
strengths** — synaptic plasticity, driven by activity. We implement the analog **without leaving
the transformer**, using a fact that is easy to miss: a Hebbian outer-product weight update **is**
the fast-weight form of linear attention [Schlag+2021; Schmidhuber1992]. Concretely, a plastic
memory `W_fast` accumulates `W_fast ← γ·W_fast + η·(kᵀv)` — a Hebbian write (= a linear-attention
memory write) with a decay `γ` that is a gated-linear-attention forget gate (homeostasis, the
brake our earlier attempt lacked). It is read as `z·W_fast` and added to the message, so the
interaction adapts with the history of activity. Crucially, **only these *fast* weights learn**;
the *slow* weights that encode the physics — grounding, complementarity `M`, the energy `Φ` —
stay **fixed**. So plasticity changes *couplings, not laws*: faithful to synaptic plasticity, not
to evolution.

This is behind a `plasticity` knob (default 0 → skipped, identical to the fixed-rule sim). When
on, it is **load-bearing** — the property the earlier predictive-plasticity attempt (§5) failed:
across three seeds, learning sustains aliveness ~0.038–0.045 while *freezing* the fast weights
(reading them but stopping the learning) drops it to ~0–0.017. The gain comes entirely from the
weights *actually learning*. The effect is modest and not yet rigorously characterized (one
config, three seeds), but it is a genuine, reproducible, transformer-only instance of "weights
that learn while alive."

**Future extension: from simple things following simple rules to complex things following
*learned, complex* rules.** The plasticity above is the smallest possible version of a much larger
research direction, and the most interesting one this work points to. Static-rule simulations —
Boids, Schelling, cellular automata, and vivarium's own fixed-rule substrate — produce a
*bounded, settling* repertoire of emergent patterns, and their macro behavior is often *reducible*
(analytically derivable, so you need not run the sim). Open-ended, novelty-generating collective
systems — ecologies, economies, **human markets**, cultures, institutions, language — are
different: their agents are *complex things following complex rules*, and, crucially, **the rules
of interaction are themselves learned and rewritten while the system runs** (norms, prices,
strategies, culture). We conjecture this is *why* such systems resist static-rule modelling: the
macro behavior depends on the accumulated *learning history*, making the emergence *irreducible*
— there is no shortcut but to run it. The plasticity here shows, at toy scale, the first step of
that ladder: learned couplings outperform fixed ones for sustained complexity. The open research
program is to climb it — replacing the Hebbian fast-weight rule with progressively richer *learned
interaction rules* (predictive, strategic, model-based; eventually agents that model each other),
and asking at each rung whether the emergence becomes measurably irreducible. Extending the engine
from *simple things following simple rules* toward *complex things following learned complex rules*
— e.g. a market of agents whose trading strategies adapt to each other — is, in our view, the most
promising and important direction beyond this paper.

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
goes 41% → **100%** (one cluster) and occupancy 0.21 → 0.05 (compact, empty space around it). The
droplet is *more alive* and continually rearranging — sustained aliveness **~0.06** with
deformation ~0.42 (measured with the periodicity-correct metric; see the note below). **Honest
limit:** cohesion has finite range, so in a 2× box the fragments — now farther apart than the
reach — re-fragment. Surface tension is local; the single droplet holds at the default density.

*(Measurement caveat, found in review: an earlier version of the aliveness metric used raw
Euclidean velocities on the periodic torus, so agent wrap-arounds registered as spurious huge
jumps and inflated the packing aliveness ~5× — early notes citing "~0.3" were this artifact. The
metric is now min-image (periodicity-aware); the corrected sustained figure is ~0.06. The
pure-transformer engine (§4.3) clips its domain rather than wrapping, so its numbers were never
affected.)*

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

- **Modest aliveness.** The packing droplet sustains ~0.06; the pure-attention variant reaches
  ~0.26–0.42 on [0,1]. Genuinely alive-looking motion, but faint in absolute terms.
- **Measuring aliveness is itself an open problem.** The metric is a *validated heuristic, not a
  proven measure* — a product of six hand-designed factors with hand-tuned thresholds that
  operationalizes "not-obviously-dead + non-trivially organized and morphing." It has already
  required two corrections (a rigid-rotation loophole; the periodicity bug above), which is
  evidence it closes *known* degenerate cases rather than defining life. Its real value is as a
  **bullshit detector and relative comparator** (it caught several illusory results), not as an
  absolute truth; the absolute number should be read as "all gates pass, each factor moderate,"
  not as a percentage of life. A principled, adversarially-hardened aliveness measure is left as
  open future work.
- **Weights learn only optionally, and only the fast ones.** By default the parameters are fixed
  (the *state* is optimized). The optional fast-weight plasticity (§3.1) makes *coupling* weights
  learn while alive — load-bearing, but modest and not yet rigorously characterized; and the *slow*
  physics weights deliberately never learn. "Full training = living" (all weights, a global
  objective) remains unrealized.
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
[Schlag+2021] Linear Transformers Are Secretly Fast Weight Programmers, ICML (arXiv:2102.11174);
[Schmidhuber1992] Learning to control fast-weight memories, Neural Computation 4(1).
[Rao&Ballard1999] Predictive coding in the visual cortex, Nature Neuroscience 2(1).
[Friston2010] The free-energy principle, Nature Rev. Neuroscience 11(2).
[Battle+2016] Broken detailed balance at mesoscopic scales in living systems, Science 352:604.
[Ao2004] / [Wang+2008] potential–flux decomposition (see `design/potential_flux.md`).
