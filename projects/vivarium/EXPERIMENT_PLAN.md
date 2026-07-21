# vivarium — experiment / implementation plan

The companion to [`FOLLOWUPS.md`](FOLLOWUPS.md) (what & why). This is **how, in what order, and
how we'll know it worked.** Every idea is checked against the four hard requirements, given a
minimal implementation sketch, and — most importantly — a **VISUAL success criterion you can judge
by eye** (primary), with measured signals as *secondary corroboration only*. Metrics do not declare
success; you do.

**Requirement legend** (each idea tagged ✓ / ⚠ / ✗ per axis):
- **TX** transformer-only (attention / MLP / LayerNorm / structured-linear; no force kernels,
  ledgers, or global terms).
- **N** fixed token count (no reproduction / variable-length tokens).
- **MDR** measure-don't-reward (nothing optimises the aliveness gauge or any global order metric).
- **LAW** fixed physics, plastic couplings (grounding / `M` / `Φ` never learn; only fast weights,
  genes, or state change, and only in the sanctioned way).

---

## The order (recommended)

1. **Species + differential adhesion (demixing)** — the first rung; high visual, clean, foundational.
2. **Richer / anisotropic shape** — cheap enhancer + prerequisite for membranes.
3. **Amphiphilic membranes (self-assembly)** — the big visual + scientific payoff.
4. **Clean blob fission + viable daughters** — dramatic, ties heredity together.
5. **Heritable gene evolution (Baldwin)** — the evolutionary layer.
6. **Per-pair plasticity (social structure)** — enables the strategic layer.
7. **Red Queen / the learning ladder (irreducibility)** — profound, subtle-visual, hardest.

*Parallel support track (not a visual step):* **B. Better aliveness profile** (entropy production +
mutual information), built and **validated against your eye** on the outputs of steps 1–4 — the way
to *rebuild trust in a metric* is to show it agrees with what you see.

Rationale: ordered by **visual payoff × faithfulness-confidence × foundation-for-later**, cheapest
solid win first. Steps 1–3 are the "different species → membrane" arc you asked about and build a
reusable gene/type + shape substrate; 4–5 add division and evolution on top; 6–7 are the deep,
harder, less-visual learning results.

---

## 1. Species + differential adhesion (demixing) — DO FIRST

**Refined mechanism.** Add a small, stable per-agent **type/gene channel** (a one-hot or
low-dim code in the embedding, set at init, never overwritten by the morph). Compute a
**species affinity** from the type channels via content attention, and add it to the existing
attract/repel scores: like-with-like (or a fixed/learned `K[s_i,s_j]` affinity matrix) so different
species prefer their own kind. Robust result in all particle systems: **phase separation** — the
species demix.

**Requirements:** TX ✓ (type = embedding channels; affinity = content attention on them — the same
op we already use for binding). N ✓ (partition the fixed pool into species). MDR ✓ (no reward; we
just set affinities and watch). LAW ✓ (`K` is a fixed/structured map or a slow gene, not a learned
physics law; the grounding stays fixed).

**Implementation sketch.** In `pack.py`: add `type` channels to the init (assign N agents to S
species); a `K` affinity matrix (S×S, fixed); fold `K[type_i,type_j]` into the attract/repel score.
Colour blobs by species in the viewer (a per-species hue, overriding/optioning the spikiness hue).
~50–80 lines, one new engine knob (`species_affinity` strength, default 0 → single species).

**VISUAL success (you judge):** turn on 2–3 species and watch them **visibly sort into distinct,
same-coloured regions/blobs** — oil-and-water demixing. Failure = they stay mixed (soup) or one
species is expelled to the walls.
*Secondary:* a phase-separation index (fraction of each agent's neighbours that share its type)
rising over time.

**Effort:** moderate. **Risk:** low (demixing is extremely robust). **Depends on:** nothing.

---

## 2. Richer / anisotropic shape — cheap enhancer, membrane prerequisite

**Refined mechanism.** Two independent sub-moves: (a) raise the harmonic budget `K` (more spikes)
with a **per-harmonic scale** so LayerNorm doesn't wash out high frequencies; (b) expose an agent's
**angular orientation** (the contour already has phase) so "which face points where" is readable —
the hook §3 needs for amphiphiles.

**Requirements:** TX ✓ (more shape channels + a per-harmonic scale = structured linear; still the
grounded contour). N ✓. MDR ✓. LAW ✓ (per-harmonic scale is a fixed structured map, not a learned
law).

**Implementation sketch.** `config.n_harmonics` already exists → raise it; add a fixed per-harmonic
weighting in the contour readout so high harmonics survive LN; verify the grounded-render test still
passes (contour = `z·W_c`). ~30–50 lines.

**VISUAL success:** blobs are **visibly more varied and more intricately shaped** (4–6+ lobes, not
capped at 3), and different agents look genuinely different. *Secondary:* across-agent spectral
diversity increases; distribution of spike-count is broader.

**Effort:** low. **Risk:** low (LN-washout is the only gotcha, addressed by per-harmonic scale).
**Depends on:** nothing (can even precede step 1).

---

## 3. Amphiphilic membranes (self-assembly) — the payoff

**Refined mechanism.** One species is **amphiphilic**: anisotropic affinity — a "head" arc that
likes water (species W) and a "tail" arc that repels water and likes other tails. Make the
interaction **orientation-dependent**: affinity between i and j depends on i's contour *in the
bearing toward j* and vice-versa (relative-orientation attention, à la rotary/relative position).
Amphiphiles then self-orient tails-in / heads-out → a **bilayer** (a double row in 2-D; a closed
loop = a **vesicle**).

**Requirements:** TX ✓ (orientation-dependent attention = keys modulated by relative bearing;
standard attention variant — an *extension*, but attention). N ✓. MDR ✓ (set up amphiphiles, watch;
never reward "make a membrane"). LAW ✓ (the anisotropic affinity is a fixed structured map).

**Implementation sketch.** Extend the affinity computation to read the contour *at the bearing to
the neighbour* (a directional dot product), and give the lipid species a head/tail contour prior.
This is the real work — the current forces are radial/isotropic. ~100–150 lines + a self-assembly
sweep (water:lipid ratio, affinity contrast). **Depends on:** step 1 (species) + step 2 (anisotropic
shape).

**VISUAL success:** lipids **spontaneously line up into a double-layered membrane** — a bilayer
ribbon, and ideally a **closed vesicle enclosing water**. This is unmistakable by eye and is *the*
demo. Failure = amphiphiles clump into a blob (micelle-ish) or stay disordered.
*Secondary:* nematic/orientational order parameter; bilayer detection (paired antiparallel rows).

**Effort:** high (the anisotropy). **Risk:** moderate (orientation-dependent attention must be got
right; the bilayer regime is a narrow "edge-of-assembly" band to find).

---

## 4. Clean blob fission + viable daughters

**Refined mechanism.** Sharpen the *already-observed* split-and-chase / finite-range-cohesion
splitting into **clean binary fission producing viable daughters** — each daughter is cohesive,
persists, and (with the gene from step 1/5) inherits the parent's type/gene. Distinguish fission
(viable division) from fragmentation (death) by daughter persistence.

**Requirements:** TX ✓ (forces/attention already present; no new machinery). N ✓ (redistribution,
not replication). MDR ✓ (measure cluster count / viability; don't reward splitting). LAW ✓.

**Implementation sketch.** Tune cohesion-vs-non-reciprocity so a grown blob divides cleanly; on the
division event, daughters keep their agents' genes; add a fission diagnostic (single-linkage cluster
count over time). Mostly tuning + measurement of existing dynamics. ~40–80 lines.

**VISUAL success:** you watch a single blob **grow, neck, and pinch cleanly into two persistent
blobs** (not just transiently scatter). Both daughters keep moving/morphing afterwards. *Secondary:*
cluster count 1→2 with both daughters sustaining motion; area roughly conserved.

**Effort:** moderate. **Risk:** moderate (clean binary vs messy fragmentation is a tuning band).
**Depends on:** step 1 (gene, for inheritance) — soft dependency.

---

## 5. Heritable gene evolution (Baldwin)

**Refined mechanism.** Make the gene (step 1) **heritable** on fission (copy ± mutation), and let
**selection** act (viable daughters spread their genes; non-viable lineages vanish) — Darwinian
dynamics at fixed N (informational heredity). With plasticity also on, test the **Baldwin effect**:
does a within-life plastic adaptation get assimilated into the gene over generations?

**Requirements:** TX ✓ (gene = channels; expression = the block reading them). N ✓ (fixed pool;
heredity is informational, not new tokens). MDR ✓ (selection is via *viability/persistence*, an
emergent survival, not a rewarded aliveness score — care: "survival" must be dynamical persistence,
not the aliveness gauge). LAW ✓ (genes are a slow heritable code, not the physics laws).

**Implementation sketch.** Gene copy+mutate on fission; track lineages; measure gene-distribution
drift and whether a plastic trait migrates into the gene. **Depends on:** steps 1 + 4.

**VISUAL success:** over a long run, the **population visibly shifts composition** — some
species/shapes take over, others die out; you can *see* selection happen (a colour/shape becomes
dominant). *Secondary:* gene-distribution entropy drops (selection); Baldwin assimilation measured.

**Effort:** moderate-high. **Risk:** moderate. **Note:** ⚠ keep "selection" grounded in dynamical
persistence, not in the aliveness metric, to respect MDR.

---

## 6. Per-pair plasticity (social structure)

**Refined mechanism.** A Hebbian fast-weight on the **edge** (specific pair), not the node: augment
the attention logit with a learned per-pair term `m_ij` that strengthens with successful binding and
decays (homeostasis). Gives persistent, specific relationships → reciprocity, preferential
attachment, social networks — the substrate for the strategic/market layer.

**Requirements:** TX ✓ (per-pair memory added to the attention logit = a linear-attention memory
indexed by pair — attention). N ✓ (O(N²) memory, fine at N=64). MDR ✓ (Hebbian on binding, not on a
reward). LAW ✓ (plastic couplings, not laws).

**Implementation sketch.** An N×N fast-weight `m`, updated `m ← γm + η·(binding)`, added to the
attention score. `plasticity_pair` knob (default 0). ~50 lines. **Depends on:** none hard.

**VISUAL success:** **persistent partnerships form** — the amber binding lines to specific partners
*stabilise* over time (the same pairs stay bonded) rather than the binding graph being memoryless
churn. *Secondary:* binding-graph stability / edge persistence; emergence of hubs (degree
heterogeneity).

**Effort:** moderate. **Risk:** low-moderate.

---

## 7. Red Queen / the learning ladder (irreducibility) — hardest, deepest

**Refined mechanism.** Climb the rule-complexity ladder (Hebbian → predictive → strategic →
model-based) and measure whether emergence becomes **irreducible** (a cheap surrogate can no longer
shortcut the macro-state). Sustained learning (non-decaying `‖ΔW‖`) requires **co-adaptation** (a
moving target), which needs a **local predictive/strategic** rule, not just Hebbian.

**Requirements:** TX ✓ (predictive plasticity via fast-weights / local rule, Hebbian-style, no
backprop needed). N ✓. **MDR ⚠ — the crux:** the local learning objective must be *genuinely local*
(predict a neighbour's next state; acquire local bonds) and **must not be the global aliveness gauge
or any global order metric.** This is a real risk and must be enforced (grep/test that the update
never reads the aliveness). LAW ✓ (couplings/fast-weights learn; laws fixed).

**Implementation sketch.** Rung 1: predictive plasticity done right (local surprise-reduction +
homeostasis/anti-collapse — the brake the first attempt lacked). Rung 2+: strategic local objective.
Plus the **irreducibility probe** (train a fast surrogate to predict the macro-state; measure its
error vs rule complexity). **Depends on:** step 6 (per-pair) for the model-based rungs.

**VISUAL success:** the system **keeps producing new behaviour indefinitely** — it does *not* settle
into a repeating pattern; you can watch it for minutes and it stays surprising. *Secondary (the
profound result):* the irreducibility metric rises as rule complexity climbs; `‖ΔW‖` stops decaying.

**Effort:** high. **Risk:** high (this is the frontier; the earlier predictive-plasticity attempt
collapsed — the homeostatic brake and the local-not-global objective are the make-or-break details).

---

## B. Parallel: a better aliveness profile (support track, not a visual step)

**Refined mechanism.** Replace the hand-tuned gate product's *authority* with a principled **profile**
— prioritise **entropy production / broken detailed balance** (is it genuinely off-equilibrium?) and
**inter-agent mutual information / transfer entropy** (are agents actually responding to / driving
each other?). **Validate against your eye:** on clips from steps 1–4, check that these measures rank
"looks alive/interesting" the way you do. Keep the gate product only as a fast dead-regime filter.

**Requirements:** TX n/a (read-only). N ✓. MDR ✓ (measurement only). LAW ✓.

**Implementation sketch.** Add `metrics_info.py` (entropy-production estimator via
forward-vs-reversed trajectory stats; pairwise mutual information over the state window). Report a
profile; correlate with a small hand-labelled clip set. ~120 lines.

**Success (calibration, not visual):** the profile **correlates with your judgment** on labelled
clips (the split-and-chase you find alive scores high on entropy-production + MI, even though the old
gauge scores it low). That is how the metric *earns* trust — by matching your eye.

**Effort:** moderate. **When:** alongside steps 1–4, once there are varied behaviours to calibrate on.

---

## Process note
Per your call: I implement one idea at a time; the **metric never declares success** — you try it in
the live viewer and judge. Each step above is scoped so its visual criterion is checkable in a
minute of watching. If a step's visual fails, its plan lists the tuning band / failure mode to
adjust before moving on.
