# vivarium — followups (reasoning-only backlog)

Open directions, reasoned through but **not implemented**. Each respects the hard requirements:

- **Strict transformer-only** — every dynamical op is attention / MLP / LayerNorm / structured
  linear (`design/HARD_REQUIREMENT.md`). No force kernels, energy ledgers, or global terms.
- **Fixed token count N** — no reproduction / variable-length tokens.
- **Measure, don't reward** — aliveness is observed, never fed into the update.
- **Fixed physics, plastic couplings** — the laws (grounding, `M`, energy `Φ`) stay fixed; only
  fast/coupling weights may learn.

---

## 0. A better aliveness measure (the current one is distrusted — for good reason)

### The problem (observed, not hypothetical)
The current score `gate_finite · gate_spread · gate_motion · coherence · structure · deformation`
is a **hand-tuned product** measuring one narrow thing: *coordinated morphing motion in a velocity
band, with rigid drift and rotation subtracted.* It **disagrees with informed visual judgment** —
genuinely interesting, alive-looking behaviour (split-and-chase pursuit, blobs forming and
splitting) scores ~0. The honest verdict: the metric is a decent **"definitely dead" filter**
(freeze / collapse / blow-up / drift-fakes-interaction) but a poor **"how alive / how interesting"
ruler**. A single hand-designed scalar is the *wrong shape* for aliveness, and it should not
overrule the eye on the non-degenerate regimes.

### The epistemic fix (the most important part)
**Flip the ground truth: informed human judgment is the *calibration target*, not the thing to be
overruled.** A better measure earns trust by *correlating* with "this looks alive/interesting" on a
labelled set of clips — it does not assert authority over the eye. Concretely: collect a small
labelled corpus from our own runs (alive / dead / interesting / boring), and **select and validate
measures by how well they match the labels.** Whatever correlates is kept; whatever doesn't is
discarded *even if it is "principled."* This inverts the whole session's stance ("trust the
ungameable metric over the eye"), which was wrong for the rich regimes.

### Design principles for the replacement
- **Principled**, grounded in a *theory* of life (thermodynamic / information / complexity) — not
  hand-set thresholds.
- **Multi-dimensional** — a **profile (vector)**, not one scalar. Life is off-equilibrium *and*
  responsive *and* complex *and* self-maintaining; a product collapses exactly the distinctions
  that matter (and is fragile — one low factor zeros it).
- **Parameter-light / self-calibrating** — few hand constants.
- **Validated against the eye** (above), and **read-only** (measure-don't-reward preserved).

### Candidate axes (ranked by: principled + matches-eye + computable)
1. **Off-equilibrium — entropy production / broken detailed balance.** *The* physics-of-life axis:
   living matter breaks detailed balance and sustains a probability current (Battle+2016); a
   gradient system settles (dead). Measure via broken-detailed-balance area loops in a
   coarse-grained phase space, or entropy production from forward-vs-time-reversed trajectory
   probabilities. Matches the eye (a chase *is* off-equilibrium); principled; connects directly to
   the "transformer = active matter" claim (§3.1 of the paper / `potential_flux.md`).
2. **Responsiveness / agency — inter-agent mutual information & transfer entropy.** Do agents carry
   information about each other (MI)? Does A's past predict B's future beyond B's own past
   (transfer entropy = *directed* influence — who drives whom)? This captures the "they're reacting
   to / chasing each other" that the eye reads, and is the *principled* form of "interaction is
   load-bearing" (replacing the ablation heuristic with an information measure).
3. **Complexity / edge-of-chaos — statistical complexity & trajectory compressibility.** Life sits
   between crystal (too ordered → trivially compressible) and gas (too random → incompressible);
   statistical complexity (Crutchfield) peaks in between, and a compression ratio (Lempel-Ziv) of
   the coarse trajectory is a cheap proxy. Captures "interesting." Lyapunov ≈ 0 (already computed)
   is the cheapest edge-of-chaos proxy.
4. **Self-maintenance / homeostasis — perturbation recovery.** Kick the system; does it *recover*
   its organization (cluster structure, spectral distribution)? Regeneration is a strong, distinct
   life signature (the headline of Growing-NCA). Cheap to run: perturb a fork, measure return.
5. **Open-endedness / novelty — non-saturating state-space exploration.** Does it keep visiting new
   regions of behaviour over long runs, or cycle/settle? Rate of novel-region discovery; does it
   plateau (settled) or persist (open-ended)?

### What to actually build
Report a **profile over these axes**, validate it against the labelled clip set, and only *then*
consider a scalar (a validated combination — or just keep the profile). **Prioritise #1 (entropy
production) and #2 (mutual information)**: both principled, both match the eye, both feed the deeper
scientific claims (off-equilibrium activity; agency/responsiveness). This replaces "trust the
hand-tuned gate product" with "measure the physics and the information flow, and confirm they match
what a human sees." The old gate product survives only as a fast *dead-regime filter*.

---

## 1. Variable / dynamic shape complexity (variable number of curves-spikes)

### Where we are
`n_harmonics = 3` → `shape_dim = 6` → up to ~3 lobes; the spike count is already emergent (0–3) and
dynamic, but **capped at 3** and identical budget for every agent.

### Faithful mechanisms
- **(a) Bigger harmonic budget** (raise `K`): blobs can express up to `K` spikes; the *effective*
  count emerges from the morph concentrating/spreading spectral power. Faithful. Constraint:
  embedding size stays **uniform** (variability in *expression*, not dimensionality — variable
  channel count would break uniform tokens, like reproduction breaks fixed-N).
- **(b) Spectral gating**: an attention/MLP head that modulates *which* harmonics are active → agents
  grow/shed spikes dynamically (the morph already does a weak version).

### Deeper: why this matters more than it looks
- **LayerNorm conserves total spectral power**, so raising `K` alone spreads power thin and the high
  harmonics wash out. The real lever is **adaptive concentration** — a per-harmonic scale (fixed or
  gated) that lets an agent *commit* power to specific frequencies. Without it, more `K` is cosmetic;
  with it, agents can specialise their surface.
- **Bounded shape space is a hidden ceiling on open-endedness.** `K=3` → a *bounded* vocabulary of
  shapes → a bounded space of possible bindings → **bounded novelty**. Open-ended ALife needs an
  unbounded (or growing) space of forms; capped harmonics quietly forecloses it. Variable complexity
  is a *prerequisite* for open-ended shape evolution, not a garnish.
- **It is the substrate for emergent *types*.** More harmonics → finer, more distinguishable keys →
  agents can differentiate. **Measurable prediction:** at higher `K`, the across-agent distribution
  of spectral complexity should become *multimodal* (distinct types) rather than unimodal — and
  emergent types are exactly what powers type-based fission / cell sorting (§2).
- **Finer binding specificity** (high-frequency complementarity = specific lock-and-key) → selective,
  specific bonds rather than the coarse 3-scale fit — the difference between "everything sticks to
  everything" and "specific recognition."

### Honest caveats
More dims → harder to tune; whether variable complexity yields *measurably* richer emergence (vs
prettier) must be tested — measure spectral diversity across agents and whether complexity
correlates with binding selectivity and with the aliveness *profile* (§0), not just eyeballed.

---

## 2. Blob fission (blobs that split apart)

### The distinction that resolves "does it need reproduction?"
- **Blob = aggregate of agents.** "A blob splits" = the fixed agents **redistribute** into two
  clusters. N fixed → transformer-only ✓, life-faithful (a colony / tissue / droplet dividing).
- **Agent/token splits** = replication → N grows → **not** transformer-only. Only needed if the
  *population/mass* must grow. **So blob fission does NOT require reproduction.**

### Faithful mechanisms (fixed-N)
1. **Finite-range cohesion instability — already latent** (we saw "re-fragments in a 2× box"): a blob
   larger than the cohesion range is intrinsically unstable to splitting (Rayleigh–Plateau-like).
2. **Type-based differential adhesion** (cell sorting; Steinberg): sub-populations complementary
   *within* but not *between* → demix and split.
3. **Morph-driven bond-breaking** (induced *misfit*): a subset morphs incompatible with the rest →
   fracture along the fault line.
4. **Oscillatory cohesion** (aggregation–fragmentation cycles; *Dictyostelium*): binding strength
   oscillates → merge/grow/split/repeat.
5. **Non-reciprocal chase splitting — already observed** (split-and-chase): asymmetric forces tear a
   blob along the pursuit axis; the fission *is* the flux `J`.

### Deeper: fission vs fragmentation, and heredity without new tokens
- **The crux is *viability*, not splitting.** Anything can fall apart (fragmentation = death). The
  interesting thing is fission into **viable daughters** — each self-maintaining (cohesive,
  persists), able to re-bind/grow, ideally carrying structure. A fission diagnostic must therefore
  check *daughter viability* (each daughter independently sustains the aliveness *profile*, §0), not
  just cluster-count 1→2.
- **The profound reframe — heredity is information, not token creation.** If daughters *inherit* the
  parent's learned state — its plastic couplings `W_fast`, its shape distribution — then **fission +
  inheritance = a primitive reproduction of *information* on a fixed token pool.** Heredity is about
  what is *transmitted and persists*, not about creating new tokens. This partially **dissolves the
  "reproduction needs dynamic N" boundary**: you *can* have **selection and heredity at fixed N** if
  what is selected is the *learned/shape state* rather than the token count — like a chemostat with
  constant cell number but evolving genotypes, or memes spreading through a fixed population. Fixed N
  caps *population* growth but **not informational evolution.** This is the faithful route to
  Darwinian dynamics inside the constraint, and it is genuinely novel.

### Promising next steps
- Exploit finite-range cohesion (#1) + a type/morph fault line (#2/#3) for viable division; **measure
  daughter viability** (each sustains the profile) and **conservation** (daughter areas ≈ parent).
- Add **inheritance** (daughters carry `W_fast` / shape distribution) and ask whether *selection*
  emerges (which daughter-types persist/spread) — the fixed-N Darwinian experiment.
- **Metaball / field rendering** to see merged/split blobs as single outlines (rendering only).

### Honest boundary
Fixed-N fission *conserves mass* (blobs split and can re-merge — an emulsion / closed population);
open-ended *mass-growing* reproduction needs dynamic N and is out of scope. But **informational**
heredity/selection is *in* scope (above) — the interesting part survives the constraint.

---

## 3. Per-pair (relationship-specific) plasticity — from chemistry to society

### Where we are
Current plasticity is a **shared, global** fast-weight (a self-morph modulation applied uniformly);
it stores the population's *aggregate* activity correlations, **not** "who I've bonded with." No
memory of specific relationships.

### The idea, deepened
A Hebbian memory on the **edge** (specific pair), not the node: augment the attention logit with a
learned per-pair term that strengthens with successful binding,
`score_ij += β · m_ij`, `m_ij ← γ·m_ij + η·(binding_ij)`. This is **linear-attention memory indexed
by pair** — transformer-native (attention *is* pairwise), O(N²) memory (fine at N=64), and
homeostatic via `γ`. Faithful.

**Why it's a phase change, not a tweak:** per-pair plasticity is the transition from **chemistry
(aggregate couplings) to society (specific, persistent relationships).** It gives the substrate for
*reciprocity, reputation, preferential attachment, and social networks* — none expressible with a
shared global memory. It is the concrete first step toward the "human markets / culture" direction:
markets and cultures are built on *specific, remembered, asymmetric relationships*, which require
per-pair memory. Measurable: does a persistent, structured interaction graph emerge (stable
partnerships, hubs) rather than a memoryless well-mixed soup?

---

## 4. Sustained (non-converging) learning — the Red Queen

### The observation
The fast-weight matrix **converges in ~50 ticks** (`τ = −1/ln γ`) because the activity statistics
become stationary. So the "learning" is a one-time adaptation, not life-long. This is the
learning-level version of "everything settles."

### The deep reason, and the fix
Hebbian *correlation* converges because correlations stabilise — it is chasing a **stationary
target.** Sustained learning requires a **moving target**, and there are two faithful ways:
- **External non-stationarity** — a drifting field so the statistics never settle (a band-aid: the
  system adapts to the drift and re-converges relative to it).
- **Co-adaptive complexity (the real answer) — Red Queen dynamics.** If agents *learn to
  predict/exploit each other*, any effective strategy gets countered → perpetual arms race → the
  target is never stationary because *my adaptation changes what you should model, which changes what
  I should model.* This is **why markets never settle.** It requires the learning rule to be
  **predictive/strategic**, not Hebbian-correlational — a correlational rule fixpoints; a predictive
  one against an adapting opponent does not.
- **Measurable signature of sustained learning:** `‖ΔW‖` does *not* decay to 0, and one agent's
  *prediction error about another* plateaus **above** zero (the challenge stays hard) rather than →0
  (solved/converged). This is a clean, principled "is it still learning?" test.

---

## 5. Simple → complex learned rules (the ladder — the most important direction)

The paper (§3.1) conjectures that learned rules make emergence *irreducible*. The concrete,
transformer-faithful **ladder of learning rules**, each a rung to climb and measure:

- **Rung 0 (have it):** Hebbian fast-weight (correlational, converges).
- **Rung 1:** predictive plasticity *done right* — the local rule reduces surprise about neighbours,
  now *with* the homeostasis/anti-collapse we understand (a variance floor / decorrelation), which
  the first attempt lacked.
- **Rung 2:** strategic — the update responds to a *local* proxy for success (e.g. acquiring binding
  partners). **Care:** the local objective must not secretly be the global aliveness reward
  (measure-don't-reward); "acquire local bonds" is a legitimate local objective, "increase global
  order" is not.
- **Rung 3:** model-based — agents maintain a predictive model of *specific* others (needs per-pair
  state, §3).
- **Rung 4:** recursive — agents model each other's *models* (theory of mind), expressible as
  attention over attention (meta-attention).

**The measured spine (this is the profound experiment):** operationalise **irreducibility** as *the
failure of any cheap surrogate to shortcut the macro-state* — train a fast predictor to skip ahead;
if it succeeds, reducible; if error stays high regardless of surrogate capacity, irreducible. Then
show a **measured transition** up the ladder: fixed rules → reducible; Hebbian → slightly less;
predictive/strategic/co-adaptive → irreducible. Same substrate, one axis (rule complexity), a
measured phase boundary. This is the "computed / irreducible emergence" result the parent programme
has always wanted, finally measurable — and it directly tests the simple→complex thesis, with
**markets** (perpetually co-adapting strategies) as the archetype at the top of the ladder.

---

## 6. A DNA analogue — a stable genotype layer (unifies shape + heredity + evolution)

### Is DNA "plasticity with more capacity"? Partly — but the essence is timescale, not size.
DNA and plasticity are **opposite ends** of biology's information hierarchy, not the same thing
scaled:
- **Plasticity (our fast weights):** fast, activity-driven, **decaying**, low-capacity, *within*-life,
  adapts *couplings*.
- **DNA:** **stable** (read-only within a life), high-capacity, **heritable**, changes only by mutation
  *across* generations, specifies *form* (genotype→phenotype).
So "DNA = plasticity + capacity" conflates two *complementary* layers. DNA's essence is
**persistence + heritability + specifying form**; they should **coexist** (fast plastic adaptation on
top of a stable heritable gene).

### The design (faithful): a stable, heritable gene sub-embedding
Give each token a **gene**: a stable, high-capacity sub-vector of its embedding that the block
*reads* (attention/MLP) to produce its shape/dynamics, but that the fast morph does **not**
overwrite (a read-only sub-embedding). It changes only on **inheritance** — at fission, daughters
**copy** the parent's gene (± mutation noise). Transformer-only (gene = embedding channels, read
natively); fixed N (copied within the fixed pool — informational heredity, §2); high-capacity (as
wide as you like).

### Why it unifies the followups
- **Variable/dynamic shape complexity (§1):** the gene specifies each agent's shape *program*
  (which harmonics, what complexity, morph tendencies) → shape complexity becomes **per-agent,
  heritable, selectable**, not a fixed global `K`; it expands the addressable *form space* (lifts
  §1's capped-harmonics ceiling on open-endedness).
- **Heredity & selection (§2):** the gene **is** what's inherited on fission → **fixed-N Darwinian
  evolution of form** (which genotypes persist/spread) — the concrete realisation of
  "heredity is information, not token creation."
- **The full biological hierarchy in one transformer:** **genotype** (gene, stable/heritable) →
  **development** (the forward pass *expresses* the gene into a phenotype) → **phenotype** (shape +
  behaviour) → **plasticity** (§3, fast weights adapt within life) → **selection** (§2, viable
  daughters spread their genes). The forward pass = *ontogeny*; fission + inheritance = *phylogeny*.

### The deep payoff — learning × evolution (Baldwin)
With both a heritable gene (slow) and plasticity (fast) in the *same* substrate, you can study their
interaction — the **Baldwin effect** (within-life learning guiding/being assimilated into
evolution), a classic question, here **measurable**: does a plastic adaptation that helps get
absorbed into the gene over generations? This is a genuinely profound experiment the DNA layer
enables, and it sits *inside* all the hard requirements.

### Honest caveats
- Keep the gene **stable** (read-only within life) — if the fast dynamics overwrite it, it is just
  more state, not a gene; the persistence/heritability is what *makes* it DNA.
- The genotype→phenotype map must be **non-trivial** (the gene *specifies* the shape program, not
  *equals* the shape), else it is a relabel.
- It needs the fission + viability machinery (§2) to actually *select*, and mutation-rate /
  selection-strength become the evolutionary knobs.

---

## 7. Cross-cutting: the profound scientific framing

The single most profound reframe these threads point at: **the transformer forward pass is active
(living) matter — softmax row-normalisation is generically non-reciprocal, producing a
non-conservative flux (broken detailed balance = the thermodynamic signature of life), and adding
learned couplings drives a measurable reducible→irreducible transition.** It connects transformers,
active-matter physics, non-equilibrium thermodynamics, and computational irreducibility. The
measurable results that would establish it: (1) **entropy production** of the attention dynamics
(§0.1) — attention is off-equilibrium *by construction*; (2) the **irreducibility transition** up
the learning ladder (§5). Everything else here (better metric §0, shape openness §1, fission+heredity
§2, per-pair society §3, Red Queen §4) supplies the ingredients and the measurements.

*See also:* [`paper/paper.md`](paper/paper.md), [`design/potential_flux.md`](design/potential_flux.md)
(the flux/entropy-production program), [`design/dynamics_zoo.md`](design/dynamics_zoo.md),
[`design/HARD_REQUIREMENT.md`](design/HARD_REQUIREMENT.md), [`RESEARCH_LOG.md`](RESEARCH_LOG.md).
