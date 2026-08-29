# vivarium — signs-of-life research log

Every idea we've discussed for giving the sim measured signs of life, each **tried** and
**scored** against a fixed harness, with the commit that tested it. Append-only.

## The fixed harness (never edited mid-run)

- **Metric:** measured `aliveness` of the real run (`ablate=none`), higher is better
  (`gate_finite·gate_spread·gate_motion·coherence·structure·deformation`, `∈[0,1]`).
- **Constraint (P6):** `p6_margin = aliveness(none) − aliveness(identity)` must be **> 0** — an
  aliveness that survives ablating interaction is drift/independent motion, not life.
- **Eval:** run `T=1000` ticks, then `aliveness.evaluate` over a 40-tick window; mean over
  seeds 0–4. Measured, never rewarded.
- **Run it:** `bazel run //projects/vivarium:research` (sweeps all runnable ideas, prints the table).

The metric itself was hardened twice (review R2): `structure` removes rigid translation,
`deformation` removes rigid rotation — so a coherent drift or a spinning rigid blob score ~0.
Only genuine, coordinated, *morphing* motion counts.

## Idea catalog + results

### A. Runnable on the dock-and-morph substrate (swept — see table below)

Latest sweep (seeds 0–4, T=1000) at commit `64aef91`, best aliveness first:

| idea | alive(mean) | alive(best) | P6 margin | deform | note |
|---|---:|---:|---:|---:|---|
| **chase+mom-c** | **0.018** | **0.029** | +0.018 | 0.200 | chase 0.6 + momentum 0.6 (the lead) |
| chase+mom-a | 0.009 | 0.010 | +0.009 | 0.098 | chase 0.5 + momentum 0.7 |
| chase+mom+spin | 0.008 | 0.010 | +0.008 | 0.094 | + shape drive |
| momentum-only | 0.001 | 0.002 | +0.001 | 0.008 | inertia, no chase |
| chase-strong | 0.000 | 0.000 | 0.000 | 0.076 | strong non-reciprocal, no inertia (turbulent) |
| chase / chase-only / chase+weak-attract | 0.000 | — | 0.000 | 0.008–0.020 | non-reciprocal alone |
| baseline-symmetric | 0.000 | 0.000 | 0.000 | 0.003 | attract+repel only (crystallises) |
| morph-spin / -strong | 0.000 | 0.000 | 0.000 | 0.002 | skew on shape alone |
| weak-attract / strong-repel / low-locality / more-neighbors / bigger-pop | 0.000 | — | 0.000 | ~0.002 | force/graph tuning |

**Read:** every single-mechanism idea **crystallises** (settles → dead). Non-reciprocal **chase**
breaks the crystal (sustained deformation) but is **turbulent** (coherence 0). Adding **momentum**
smooths it back toward coherent motion. The **chase + momentum** combination is the only family
with positive P6 margin and sustained deformation — but the alive band is narrow and absolute
aliveness is still low (~0.02; none clear 0.05). This is the current frontier.

### B. Already tried on earlier substrates (documented results, not re-run)

| idea | result | why it failed | commit |
|---|---|---|---|
| **Predictive plasticity** (predict neighbours' next state; local delta rule) | collapses (dark room); learning **not load-bearing** (frozen ≈ learned) | minimising surprise homogenises the colony | `b62d926` |
| **Relative-neighbour signalling** (predict `(A−I)·obs`) | drift-invariant + load-bearing target (proven), but colony **freezes** with no drive; learning irrelevant | right objective, no drive → settles | `53d9e1e` |
| **Anti-collapse regularizer** (local VICReg-style diversity `β`) | seed-fragile; one seed ~0.26 under the weak metric; P6 not robust | patched collapse but not drift-dragging | `5268f33` |
| **Morph-spin / intrinsic skew on position** | fakeable coherence — a shared rotation moves identity too | any drive shared across agents is drift-dragged | `53d9e1e` |
| **Strong external drift** | high aliveness but **P6 fails** (drift drags independent agents) | motion from the field, not interaction | `73dd123` |

### C. Discussed but not built (candidate next builds)

| idea | why it might work | cost |
|---|---|---|
| **E–I / Dale's-principle agent types** (attractor vs repulsor *types*, asymmetric coupling) | the canonical non-settling oscillator; sharpens the chase mechanism into distinct types | medium (per-agent type + typed force matrix) |
| **Macro survival selection** (slow clock: evolve rules for persistence) | random rules crystallise ~always; *select* the rare alive ones — base rate ~0 → crisp target | large (environment + ES loop) |
| **Contrastive signalling** (tell real neighbours from impostors) | forces learning to be load-bearing; anti-collapse by construction | medium; but "doing more" than biology (user pushback) |
| **Route B backprop world-model** (+ anti-collapse regularizer) | native credit assignment; documented fallback | large |
| **Self-propulsion** (persistent per-agent heading) | active matter sustains motion | small, but risks P6 (interaction-independent motion) |

## Exhaustive search (grid.py) — the SUSTAINED solution

Ran `grid.py` over ~250 configs across chase × momentum × spin × attract × repel × typed × n_types.

**Two decisive findings:**

1. **Transient vs sustained.** Early grids measured at T=800 and rewarded a *dying transient*:
   the best configs peak at aliveness **0.13–0.17** near t=0 but **decay and freeze by ~t=1500**
   (motion→0, Lyapunov→−0.58). Fixing the harness to measure at **T=2000** (post-transient)
   corrected this — sustained aliveness is much lower than the transient peak.
2. **Typed forces (Particle-Life / E–I) did NOT help** — pure `force_chase` (antisymmetric part
   of A) + momentum beats typed-K forces at every setting.

**The sustained solution (confirmed steady to T=8000, both seeds):**

```
force_chase=1.0  momentum=0.6  morph_spin=0.4  force_attract=0.02  force_repel=0.02
→ sustained aliveness ≈ 0.05  (deform ~0.42, motion ~0.19, coherence ~0.42, structure ~0.28)
```

Mechanism: **non-reciprocal chase breaks crystallisation; momentum smooths turbulence into
coherent motion; morph-spin keeps the shape (and thus the interaction graph) shifting.**
Momentum = 0.6 is the sweet spot — higher (0.75+) overshoots and **dies** by t=1500; lower is
weaker. It is interaction-driven **by construction** (identity ablation freezes to 0).

**Honest read:** these are **real, sustained, morphing, interaction-driven signs of life** — but
**faint** (~0.05 on [0,1]; the morph sim reached 0.16). The force-mechanism family plateaus at
~0.05 sustained. Getting past it likely needs the untried builds: E–I *typed* structure done
properly, or **macro selection** (select the rare rules that clear a higher bar) — the point at
which hand-tuning should stop.

## PURE TRANSFORMER — the transformer does everything (the strongest result)

The force-based substrate used a bolt-on force law for motion. Question: can the *transformer
itself* move positions AND resist collapse, with no external rules? Yes — and it beats the force
law by ~5–9×. `pure.py`: position is just channels of `X`; the whole embedding is updated by one
block (grounded attention + MLP + LayerNorm) with two **internal architecture changes**:

- **Non-reciprocal attention** `A ← A + β(A − Aᵀ)` — injects the antisymmetric/circulating part,
  which **defeats attention's contraction** (the rank-collapse the whole paper fights). This is
  the key unlock; plain attention just clumps everyone.
- **Skew term** `X·J` (fixed skew-symmetric) — non-gradient ⇒ no fixed point.
- **Don't LayerNorm the position channels** — lets the dish spread instead of normalising to a
  point; a **residual scale** on (message + skew) tames over-energetic seeds into the motion band.

**Best config** (`dist_lambda=0.5, morph_spin=0.3, nonrecip=1.0, ln_pos=False, scale=0.5`):

```
sustained aliveness ~0.26 mean / ~0.42 best-seed   (force-based substrate: ~0.05)
identity ablation ~0.17   →  P6 margin +0.10   (interaction is load-bearing, measured)
motion in-band, coherence ~0.95, structure ~0.97, deformation ~0.44, steady to 3000+ ticks
```

**Honest nuance.** Unlike the force substrate (P6 by construction, identity→0), here the per-agent
MLP produces a real *baseline* of motion (identity ~0.17), so P6 is **measured-positive (+0.10),
not by-construction**. But the *interaction-driven increment* alone (~0.10) is already ~2× the
force substrate's entire aliveness, and total aliveness is ~5× — a genuinely stronger, and
*architecturally pure*, result. Non-reciprocal attention is the mechanism that lets a transformer
move things without collapsing. (Branch: `vivarium-pure-transformer`.)

## Conclusions (this run)

1. **Crystallization is the wall**, exactly as `potential_flux.md` predicts: symmetric gradient
   forces settle to a minimum → dead.
2. **Non-reciprocity (chase) is necessary** to break it — it's the only thing that sustains
   deformation — and **momentum** is necessary to keep the resulting motion coherent rather than
   turbulent. Together (chase+momentum) they give the only positive-P6, non-crystallising family.
3. **But it is not yet alive** in absolute terms (~0.02). The edge-of-chaos band (coherent *and*
   deforming) is narrow; coherence and deformation trade off against each other.

## Next ideas (if the loop resumes)

- Fine sweep the chase+momentum edge (chase 0.4–0.8 × momentum 0.5–0.75) at higher resolution;
  track Lyapunov ≈ 0 as the edge indicator.
- Build the **E–I typed** force (Idea C-1) — asymmetric *between types* is a stronger, more
  structured non-reciprocity than the antisymmetric-part-of-A used here.
- If tuning plateaus low, this is exactly the case for **macro selection** (C-2): stop tuning by
  hand, select rules that clear the aliveness bar.

## 2026-07-25 — auto-research: bulk-vs-charge, 3-D, and a conservative-force bug

A separate auto-research run, on its own harness: **does membrane-like structure emerge from
Pauli + van der Waals + electrostatics alone?** Primary metric `emergence_score` (amphiphile
assembly excess), secondary `demix_excess`. Two frozen benchmarks —
[`bench_emergence.py`](bench_emergence.py) (2-D) and [`bench_emergence3d.py`](bench_emergence3d.py)
(3-D) — logging to `docs/autoresearch_results.tsv` and `docs/autoresearch_results_3d.tsv`. Scores
are **not** comparable between them. Root-cause review: [`docs/BILAYER_REVIEW.md`](docs/BILAYER_REVIEW.md).

**Representation fix — the k=0 radius channel + contact-area vdW** (`cff597f`, `4284567`). The
contour had no `k=0` coefficient, so charge *was* extent: `C=0` meant neutral **and** a point,
`C≠0` meant bulky **and** charged. The model could not express *bulky but neutral* — which is what
a lipid tail is. Fix: a dedicated k=0 **radius** channel at `rad_idx = pos_dim + shape_dim`,
disjoint from the contour (which keeps `shape_dim = 2K`, so `pure`/`block`/`engine` are untouched).
van der Waals was rewritten from `sigmoid(⟨C_i,M·C_j⟩/τ)·exp(−λd²)` — complementary *fit*, i.e.
specific lock-and-key binding, with `sigmoid(0)=0.5` making featureless tokens half-sticky to
everything — to `tanh(rad_i·rad_j/0.25)·exp(−λd²)`: contact-area / polarizability based and
**charge-independent**, as London dispersion actually is. `A_fit` survives but now drives only the
induced-fit morph. `attract_gated` (an earlier partial fix) was **deleted**.

**3-D** (`ac0a1eb`, `7546ba7`). Per-config `pos_dim ∈ {2,3}`. The grounded readout
`⟨C, basis(bearing)⟩` is unchanged in form; the basis goes from circular harmonics `{cos kθ, sin kθ}`
(`2K`) to **real spherical harmonics** `Y_lm`, `l=1..K` (`K(K+2)`; `K ≤ 2` validated). Motivation:
2-D dipolar water forms H-bond *chains*, not a network, which structurally caps the hydrophobic
effect. Hosted via `serve --polar --dim3` with a depth-cued projection in the viewer. Also
introduced **AMPHI**, an *emergent* amphiphile — an ordinary token with a fixed polar-head /
neutral-tail contour that reorients in the local field like water, with **no per-species force
law**. The legacy explicit `LIPID` rod (`k_hydro`/`k_tail`) is retracted and is now 2-D only.

**Demix progression (3-D).** `demix_excess` 0.018 (baseline) → 0.167 (radius 0.8→0.4) → 0.253
(radius 0.22; `emergence_score` briefly positive at 0.024) → 0.468 (bulky neutral tails, 0.22/0.60)
→ **0.512** (size contrast 0.15/0.85). Raising the amphiphile head charge 0.8→2.0 recovered
emergence −0.062→−0.018 for free; 4.0 was worse. So the hydrophobic effect **did** emerge from the
three forces alone — but the 0.512 state is a *bulk* demixed phase with `emergence_score` still
negative. **Assembly has not been achieved.** In 2-D the same channel change moved demix 0.061 →
0.101 with emergence flat.

**Then: the conservative-force bug** (`3538e89`). The electrostatic near-face `nf_j` was reading
token j's **far** face, making `prod = nf_i·nf_j` asymmetric — so the force advertised as
"conservative" was not (net force ≠ 0). It is now `nf_j = nf_i.T`. Consequence, stated plainly:
**every number above was measured on a subtly non-physical system and is invalid.** The tuned
configs **collapse** under the fixed force (gates fail). Both benchmarks must be re-baselined from
scratch; the demix progression should be read as a hypothesis about the mechanism, not as a result.

---

*Sweep harness:* [`research.py`](research.py) · *substrate:* [`design/dock_and_morph.md`](design/dock_and_morph.md)
· *why crystallisation:* [`design/potential_flux.md`](design/potential_flux.md)
· *idea lineage:* [`design/m2_collapse.md`](design/m2_collapse.md), [`design/signalling.md`](design/signalling.md)

## 2026-08-28 — head-area geometry: NEGATIVE (screen)

**Question.** Every energetic lever on closure is a measured null, and `WHY_THE_ORACLE_DOES_NOT_TRANSFER`
refuses YLZ's `beta` because supplying spontaneous curvature imports the answer. The bottom-up origin
of the same quantity is the packing parameter P = v/(a0*l). `chain_bonds` already records that the
TAIL axis cannot move it, leaving head area a0 — which had no knob, because `field.Field` carried one
scalar sigma for every bead. `sigma_species` (exact no-op at default, transformer identity re-verified
at 1e-13) made a0 reachable.

**Result: FAIL. 0 of 15 runs formed, every arm 0/3, at L = 22, 100k steps, sigma_head 1.0–1.8.**
A parallel sweep at L = 25 (phi = 0.034) adds 0 of 12. Twenty-seven runs, no closure.
Mean `largest` across arms: 38.3, 39.3, 43.3, 40.0, 36.7 — not monotone, so the §6 escalation rule
does not fire and the 1M-step decision run is not authorised.

**Not a falsification.** 100k steps against a 2-D formation time of 6e5–1e6. The screen shows head
area gives no FAST route to closure; it cannot rule out a slow one. Pre-registered in
`specs/2026-08-28_head_area_geometry.md` before any treatment run existed, with two dated amendments
(box density) and the outcome appended.

**Process errors this run, both caught and recorded.** (1) The registered box L = 25 was phi = 0.034,
a gas; the first correction to L = 13 was jammed (largest = 199/200 at step 0); L = 22 was chosen by
measuring the dispersed-start window across L = 13..25. (2) `setsid nohup ... &` returns the wrapper
PID, not python's, so a sweep reported as killed ran for another hour alongside its replacement,
inflating wall-clock and interleaving two schemas into one results file. The `L` column added in
Amendment 2 is what kept the two separable and the gate correct.

## 2026-08-28 — head area, the other direction (H2): NEGATIVE

**FAIL on both registered endpoints. 0 of 12 formed; S1 (largest >= 150) fired in no arm, against a
maximum observed value of 78.** largest_max by arm: 1.0 -> [45,47,48]; 0.9 -> [38,61,63];
0.75 -> [39,51,62]; 0.6 -> [58,70,78].

With H1, head area is now swept 0.6-1.8 — spanning both sides of the Cooke-Deserno 0.95 reference —
for **zero vesicles in 39 runs**. Head area is not the closure lever in either direction.

**Lead, explicitly not a result.** At sigma_head = 0.6 all 3 seeds beat the baseline maximum (exact
one-sided p = 0.050) and mean burial rises (71.3 vs 58.3). It is not the registered endpoint (S1 was
150), n = 3, p exactly on the line, and burial is NOT monotone across arms, so the motivating
mechanism is not cleanly supported. Needs its own pre-registration at n >= 10 before it means
anything.

**The finding that is actually solid.** Across 39 runs, three densities, two lipid counts, two box
sizes and a threefold head-size range, the largest aggregate has never left 13-78; at N = 400 the
baseline reproduces at 45, 47, 48 — spread of 3 with 400 lipids available. That is a stable preferred
aggregation number, i.e. a micelle phase, and it is better measured than anything the closure endpoint
has produced.

**Next lever, per the spec.** Branch count. `chain_bonds` hardcodes two chains per head; a third
raises v at fixed l, the largest term in P = v/(a0*l), and no experiment here has touched it.

## 2026-08-29 — ERRATUM: the 3-D closure endpoint was an instrument artifact

`n_enclosed` / `count_vesicles` / `vesicle_call` are **2-D detectors**: `_interior_mask` builds
`np.zeros((n, n))` and floods with 4-connectivity. On 3-D input they project onto a plane, fill the
disc, and find no interior.

Known-answer test: a planted 3-D sphere (verified hollow, lipid beads at r = 2.66-6.66 with the
five-band bilayer profile) reads **nenc [0,0,0,0], nves 0, vesicle_call False**. The 2-D planted ring
reads 1,1,1,1 / 1 / True correctly.

**So `formed` could never fire in 3-D, and "0 vesicles in 39 runs" measures the instrument.** The
closure claims of H1 and H2 are withdrawn.

Surviving, because they never touch the grid: S1 (`largest >= 150`, never fired), the aggregation
number invariant (13-78; 45/47/48 at N=400), and the burial-vs-head-size trend (rho = -1.000). The
conclusion "head area does not move this model out of the micelle phase" stands on those; "head area
does not produce vesicles" does not.

Cause: a 2-D-validated endpoint carried into 3-D and scored 39 runs without a 3-D known-answer check.
Sixteenth instrument defect in this project (docs/MEASUREMENT_DISCIPLINE.md records fifteen). Found
only because fixing sweep efficiency made the planted-structure probe cheap enough to run -- which is
the check that should have come first.

**Blocked until fixed:** any 3-D closure experiment, including the Cooke-Deserno chi collapse
(implemented: `field.cooke_chi`, `VIVARIUM_CHI_MODE=cooke`, `VIVARIUM_RC` as the w_c analogue).

## 2026-08-29 — 3-D phase map: the bilayer does not stay open ANYWHERE, and the cause is interpenetration

**Reproduced Cooke-Deserno's phase diagram qualitatively.** 72 cells, w_c in {0.6,1.0,1.4,1.8} x
kT/eps in {0.3..1.3}, planted vesicle, CD chemistry (one tail-tail attraction, heads purely steric),
CD architecture (linear 3-bead), k_bond 30. Gel at low kT, breakup in the narrow-attraction/hot
corner, fluid between, and the fluid band broadens with w_c -- which is the paper's own title claim.
MSD monotone in temperature at every width. This is the first time this engine has been validated
against a published phase diagram.

**My gel hypothesis is REFUTED.** Our production point (w_c 1.5, kT/eps 0.64) sits in the fluid band,
not the gel: interpolated MSD ~0.29 against a frozen reference of 0.06. What survives is quantitative
only -- we are 3-4x less mobile than the CD-like fluid region, sluggish rather than frozen.

**THE DECISIVE RESULT: 0 of 72 cells hollow.** core_frac (share of lipid beads inside half the outer
radius; 0.00 for a shell, 0.125 for a uniform solid ball) reads **0.26 to 0.93 in every cell** -- 2 to
7x MORE centre-dense than a solid ball. The planted vesicle collapses into a dense core across the
entire (w_c, kT) plane. Temperature, attraction width and head area have now all been swept, and none
of them holds a bilayer open.

**Cause, measured: excluded volume is too weak and beads interpenetrate.** At the production
core_height 37.8 the minimum non-bonded separation is **0.366 of contact** -- reproducing exactly the
0.36 that docs/WHY_THE_ORACLE_DOES_NOT_TRANSFER section 2 records as "roughly 4x too weak", and whose
consequence it already stated: "every planted ring collapsing to a filled blob at every size". That
was diagnosed in 2-D; it holds in 3-D too, and it explains every null in this project better than
chemistry or geometry ever did.

    core_height   nn/contact   core_frac
          37.8        0.366       0.387
         100.0        0.784       0.892
         300.0        0.881       0.482
        1000.0        0.943       0.170     (uniform ball 0.125, shell 0.00)

Raising the core repairs packing monotonically but did NOT restore a hollow shell in this probe.
PRELIMINARY: one seed, 3000 steps, and integrator stability at high core_height is unverified (a
stiffer core needs a smaller dt than the 8e-3 used). Not a result yet.

**Two instrument corrections were needed to get here, both caught by rendering before claiming.**
`frac_largest` reads 1.000 for a collapsed globule, so an earlier claim that "a 3-D vesicle is stable
in this engine" was wrong and is withdrawn -- the render showed a filled blob. `core_fraction`
replaces it, validated on a known-answer shell (0.000) AND a null uniform ball (0.1253 against a
theory value of 0.125) before use.

**Next:** core_height with a stability-checked timestep, measured by core_frac, is the one lever with
a measured mechanism behind it. Chemistry and geometry are both excluded by this map.

## 2026-08-29 — interpenetration is NOT the cause either (hypothesis 2 refuted)

core_height x dt, 12 cells, 20000 steps, planted vesicle, CD chemistry. **All 12 stable** (thermostat
holds 0.57-0.64 against a 0.6 target), so the timestep concern is resolved: dt = 8e-3 is fine even at
core_height 1000.

     core      dt   nn/contact   core_frac
     37.8   0.008        0.302      0.388
    100.0   0.008        0.735      0.840
    300.0   0.008        0.884      0.295
   1000.0   0.002        0.952      0.193      (shell 0.000 | uniform ball 0.125)

**Excluded volume repairs monotonically (nn/contact 0.30 -> 0.95) and the shell still collapses.**
core_frac never approaches zero; the best cell is 0.193, still denser at the centre than a uniform
ball. So the 0.36 interpenetration is a real defect but is NOT the cause of the collapse.

Caveat: n = 1 per cell and the spread across dt at fixed core_height is large (300: 0.295/0.693/0.447;
1000: 0.528/0.257/0.193), so these are noisy. But no cell in the grid is near a shell.

**Four independent levers now swept, none holds a 3-D lumen open:** head area (0.6-1.8), temperature
(0.3-1.3), attraction width (0.6-1.8), excluded-volume stiffness (37.8-1000).

**Untested structural differences from Cooke-Deserno**, in the order they are worth trying:
1. Chain stiffness. CD's 1-3 spring has rest length 4 sigma against a straight-chain geometric length
   of ~2 sigma, i.e. permanently stretched and strongly straightening. Ours sits at 2.0 * r_bond, so a
   straight chain is merely the minimum, not actively enforced. Floppy lipids do not tile a bilayer.
2. Bond form: FENE (CD) vs harmonic (ours).
3. Core form: divergent WCA (CD) vs bounded quadratic (ours). Raising the height does not make a
   bounded core divergent, and the residual softness near contact may be what matters.

**Next: run the vendored oracle itself.** `cooke_deserno.py` is a working CD implementation in this
repo. If it produces a hollow vesicle under `core_fraction` and our engine does not, the difference is
localised to our engine and can be bisected against a control that works. That is the M0 rung of
ROADMAP_V2, and it is the cheapest decisive test available.
