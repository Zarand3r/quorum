> **SUPERSEDED (2026-07-25)** — by the three-fundamental-forces approach in
> [`docs/BILAYER_REVIEW.md`](docs/BILAYER_REVIEW.md): everything must emerge from **Pauli exclusion
> + van der Waals + electrostatics** only, with the **k=0 radius channel** (bulk separated from
> charge) and **contact-area, charge-independent vdW**. The explicit per-species lipid force laws
> (`k_hydro` / `k_tail`, the `LIPID` rod) are **retracted**. Kept for the record.

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

**Risk calibration (fresh review):** step 1 low-risk / moderate-effort (demixing is robust); step 2
low/low; **step 3 HIGH-risk** (a true bilayer is finicky — micelles are the likely first outcome);
step 4 moderate; step 5 moderate-high (needs the Moran fixed-N process below); step 6 low-moderate;
**step 7 highest-risk** (the earlier predictive-plasticity attempt *collapsed* — it may not work
without the homeostatic brake + strictly-local objective).

**Optional swap:** if you want the *safest, quickest* first trust-builder over the foundational one,
do **step 2 (richer shape)** first — it is the lowest-effort, lowest-risk guaranteed visual change
(more varied blobs). I recommend species (step 1) first anyway because it directly answers your
species/membrane interest and lays the gene substrate — but the swap is a legitimate lower-risk
opening.

**Two MDR ⚠ flags (the only requirement tensions):** step 5 (fixed-N selection) and step 7 (Red
Queen) must keep their *fitness / learning objective* a **local dynamical quantity** and must
**never read the aliveness gauge** — this will be grep/test-enforced. A blanket rule applies to all
steps: **hand-tuning a physical knob to find a regime is allowed; feeding any reward signal into the
per-tick update is not.**

---

## 1. Species + differential adhesion (demixing) — DO FIRST

**Refined mechanism.** Add a small, stable per-agent **type/gene channel** (a one-hot or
low-dim code in the embedding, set at init, never overwritten by the morph). Compute a
**species affinity** from the type channels via content attention, and add it to the existing
attract/repel scores: like-with-like (or a fixed/learned `K[s_i,s_j]` affinity matrix) so different
species prefer their own kind. Robust result in all particle systems: **phase separation** — the
species demix.

**Requirements:** TX ✓ (the affinity is an **attention-logit bias** `+ K[s_i,s_j]` on the existing
attract/repel scores — a learned/relative attention bias, exactly the transformer's own mechanism,
*not* a separate force). N ✓ (partition the fixed pool). MDR ✓ (we *set* affinities and watch;
hand-tuning a physical knob to find a regime is allowed — it is not feeding a reward into the loop).
LAW ✓ (`K` is a fixed structured map; the grounding / `M` / `Φ` stay fixed).

**Implementation sketch — note the shared foundation.** This step actually builds the **minimal
gene layer** (§6) that steps 5/7 reuse: a **protected, read-only sub-embedding** holding the type
code. *Key implementation detail:* the morph currently updates all of `z`; the type channels must be
**carved out and NOT overwritten by the morph** (else "species" is transient state, not identity).
So: reserve K_type channels, init them per species, exclude them from the `z ← LN(z + …)` update,
fold `K[type_i,type_j]` into the attract/repel logits, and colour blobs by species in the viewer.
~60–100 lines, one knob (`species_affinity`, default 0 → single species, current behaviour intact).

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

**Effort:** high (the anisotropy). **Risk: HIGH** (revised up on review) — a *genuine bilayer* is the
narrowest regime in soft matter; the likely first outcome is **micelles** (tails-in balls) or
disorder, and a true 2-D bilayer/vesicle may need several attempts and a careful head/tail contrast.
Treat "micelles form" as a real partial win and "closed vesicle" as the stretch goal. This is the
plan's highest-risk visual step; do it *after* the cheaper wins so momentum is banked first.

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

**Refined mechanism — the fixed-N subtlety made explicit.** Simple fission (step 4) does *not*
create selection on its own: the daughters are the *same* agents keeping their *same* genes, so
nothing evolves. Real Darwinian dynamics at fixed N need a **Moran-style birth–death / conversion**
process: when an agent "dies" (loses cohesion / fails to bind for long enough — a **dynamical**
failure, not a low aliveness score), its slot is **reborn carrying a *successful neighbour's* gene
± mutation.** N is constant; what "reproduces" is the gene, spreading through the fixed pool
(a chemostat / meme dynamic). *That* is where variation + differential success + heredity → evolution.
With plasticity also on, test the **Baldwin effect**: does a within-life plastic adaptation get
assimilated into the gene over generations?

**Requirements:** TX ✓ (gene = channels; a gene-copy is an attention/gather op over neighbours). N ✓
(Moran keeps N *exactly* fixed — a death is immediately a birth). **MDR ⚠ (the crux):** the "fitness"
that decides who copies whom **must be a local dynamical quantity** (persistence, local binding
success), and **must never read the aliveness gauge or any global order metric** — enforce with a
grep/test. This is the one place the fixed-N-selection design can accidentally smuggle in a reward.
LAW ✓ (genes are a slow heritable code; the physics laws stay fixed).

**Implementation sketch.** A local death rule (no bonds / lost cluster for T ticks) → gene overwrite
from a live neighbour + mutation noise; lineage tracking; measure gene-distribution drift and Baldwin
assimilation. **Depends on:** steps 1 + 4. ~80–120 lines.

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
