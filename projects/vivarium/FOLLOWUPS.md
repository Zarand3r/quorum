# vivarium — followups (reasoning-only backlog)

Open directions to explore, reasoned through but **not implemented**. Every one is constrained to
respect the project's hard requirements:

- **Strict transformer-only** — every dynamical op is attention / MLP / LayerNorm / structured
  linear (see `design/HARD_REQUIREMENT.md`). No force kernels, no energy ledgers, no global terms.
- **Fixed token count N** — no reproduction / variable-length tokens.
- **Measure, don't reward** — aliveness is observed, never fed into the update.
- **Fixed physics, plastic couplings** — the laws (grounding, complementarity `M`, energy `Φ`)
  stay fixed; only fast/coupling weights may learn.

---

## 1. Variable / dynamic shape complexity (variable number of curves-spikes)

### Where we are
`n_harmonics = 3` → `shape_dim = 6`, contour `r(θ) = R₀ + Σ_{k=1}^{3} c_k cos kθ + s_k sin kθ` →
up to ~3 lobes/spikes. The spike **count is already emergent** (0–3, from which coefficients
dominate) and **already dynamic** (it's what the spikiness colouring shows) — but the **maximum is
capped at 3**, and every agent has the same budget.

### The question
Can blobs have a **variable, dynamic** number of curves/spikes — some smooth, some highly
featured, changing over time and differing across agents?

### Faithful mechanisms
- **(a) Bigger harmonic budget — simplest.** Raise `K` (e.g. 6–10). Blobs can then express up to
  `K` spikes; the *effective* number active per agent **emerges** from the morph concentrating or
  spreading spectral power. So "variable spike count" is emergent, not hard-coded. Fully faithful
  (still the grounded contour, still attention/MLP). **Constraint:** the embedding size stays
  *uniform* across agents (same as fixed-N) — variability is in *expression*, not channel count.
- **(b) Spectral gating.** An attention/MLP head that modulates *which* harmonics are active
  (gates the shape channels) from the agent's state / neighbourhood → agents can "grow" or "shed"
  spikes dynamically. This is (a) + a learned concentration mechanism; the existing morph already
  does a weak version.
- **(c) NOT faithful:** literally different channel counts per agent (variable-size tokens) —
  breaks the uniform-token structure, exactly as reproduction breaks fixed-N. Avoid. Make the
  count variable in *expression*, never in *dimensionality*.

### Why it might be genuinely interesting (not just prettier)
- **Finer binding specificity.** More harmonics → finer lock-and-key complementarity → more
  *selective, specific* bonds (richer molecular recognition) vs the coarse 3-scale fit now.
- **Agent differentiation / specialization.** If agents settle into different spectral
  complexities (spiky specialists vs smooth generalists), emergent **types** appear — which feeds
  cell-sorting / demixing / fission (§2).
- **Higher-dimensional, harder-to-settle morph.** More shape DOF → richer conformational dynamics
  → possibly *more sustained* morphing (more room to avoid settling — directly relevant to the
  perpetual-aliveness problem).
- **Biologically faithful:** real surfaces have variable, dynamically exposed/hidden binding-site
  multiplicity (folding, allostery).

### Honest caveats
- **LayerNorm normalizes total shape power**, so high harmonics can wash out — likely need
  per-harmonic scaling / a k-weighting so high-frequency features aren't suppressed.
- More dims → harder to tune (small compute cost at N=64).
- Whether variable complexity yields *measurably* richer emergence (vs. cosmetic) is empirical —
  **measure it**: spectral diversity across agents, and whether spectral complexity correlates
  with binding selectivity or with sustained aliveness.

---

## 2. Blob fission (blobs that split apart)

### The key distinction (resolves "does it need reproduction?")
- **Blob = aggregate of many agents.** "A blob splits" = the fixed set of agents **redistributes**
  into two clusters. N stays fixed → transformer-only ✓, life-faithful (a colony / tissue /
  droplet dividing).
- **Agent/token splits into two** = literal replication → N **grows** → requires dynamic N →
  **NOT transformer-only.** Only needed if the population/mass must grow.
- **So blob fission does NOT require reproduction.** Reproduction is a different, out-of-scope
  thing (a growing lineage).

### Faithful, life-faithful mechanisms (all fixed-N)
1. **Finite-range cohesion instability — already latent.** Cohesion is a broad but *finite-range*
   attention; we observed "at 2× box the fragments re-fragment." A blob **larger than the cohesion
   range is intrinsically unstable to splitting** (the ends stop feeling each other). Let blobs
   grow past that range → they *want* to divide. Rayleigh–Plateau-like; pure attention.
2. **Type-based differential adhesion (cell sorting).** Types = embedding channels; adhesion =
   content attention on shape complementarity. Two sub-populations complementary *within* but not
   *between* → the blob **demixes and splits by type** (Steinberg's differential adhesion). Pure
   attention; deeply faithful.
3. **Morph-driven bond-breaking (induced *misfit*).** Shapes morph (skew + MLP); if a subset
   morphs to become mutually complementary but *incompatible* with the rest, the blob **fractures
   along that fault line** — the flip side of induced fit.
4. **Oscillatory cohesion (aggregation–fragmentation cycles).** If binding strength oscillates
   (skew already cycles the shape → binding), blobs merge / grow / split / repeat — *Dictyostelium*
   streaming. The most dynamically alive.
5. **Non-reciprocal chase splitting — we already OBSERVE this.** The split-and-chase default:
   row-softmax + k-NN asymmetry → non-reciprocal forces tear a blob along the pursuit axis, and
   momentum keeps the pieces chasing. Already present — fission driven by the non-conservative
   flux `J`.

### Promising next steps (faithful)
- **Cleanest / most latent:** exploit the finite-range cohesion — arrange for blobs to grow past
  the cohesion range so they **intrinsically split**, and add a mild type/morph fault line so
  daughters are **viable** (they reconfigure and persist), not mere fragmentation. Most elegant
  because we already have the seed (#1 + #3).
- **Sharpen the chase-fission** we already see into clean **binary** fission (tune
  non-reciprocity / momentum / cohesion).
- **Metaball / field rendering** so merged vs split blobs read as single outlines — *rendering
  only*, doesn't touch the dynamics, doesn't count against transformer-only.
- **Measure it, don't eyeball:** a fission diagnostic — cluster count over time (single-linkage,
  which `metrics_pack.py` already computes) + **conservation** (daughter areas ≈ parent area).
  Fission = count 1→2 with area conserved; distinguish from *fragmentation* (death) by daughter
  **viability** (each daughter sustains aliveness).

### Honest boundary
- Fixed-N fission **conserves total mass** — blobs split *and* can re-merge (an emulsion / a
  closed cell population). Life-faithful for a *closed* system.
- Open-ended **Darwinian reproduction** (a growing lineage) needs dynamic N → out of scope under
  transformer-only. That is the one thing "division that adds mass" requires and that we cannot do
  faithfully.

---

## 3. Other open threads (brief)

- **Per-pair (relationship-specific) plasticity.** Current plasticity is a *shared, global*
  fast-weight (a self-morph modulation applied uniformly), **not per-neighbour** — it stores the
  population's aggregate activity correlations, not "who I've bonded with." A Hebbian on the
  *actual binding between specific agents* (strengthen the bond between two that bind) would be
  per-neighbour, closer to classic synaptic plasticity, and still faithful (an attention memory
  indexed by pair).
- **Sustained (non-converging) learning.** The fast-weight matrix converges in ~50 ticks
  (`τ = −1/ln γ`) because the activity statistics become stationary — so the "learning" is a
  one-time adaptation, not life-long. Sustained learning needs **non-stationarity**: a drifting
  drive, or genuine **co-adaptive complexity** (Red Queen / markets). See paper §3.1.
- **Simple → complex learned rules (the big one).** Replace the Hebbian rule with progressively
  richer *learned* interaction rules (predictive → strategic → model-based → agents that model
  each other), toward markets/cultures where the rules perpetually co-adapt → *irreducible*
  emergence. Paper §3.1.
- **Aliveness metric is an open problem.** A validated heuristic, not a proven measure; corrected
  twice already. Needs adversarial hardening (construct known-non-living flows, confirm rejection).
  Paper §8.

*See also:* [`paper/paper.md`](paper/paper.md), [`design/dynamics_zoo.md`](design/dynamics_zoo.md)
(drives + what stays transformer-only), [`design/HARD_REQUIREMENT.md`](design/HARD_REQUIREMENT.md),
[`RESEARCH_LOG.md`](RESEARCH_LOG.md).
