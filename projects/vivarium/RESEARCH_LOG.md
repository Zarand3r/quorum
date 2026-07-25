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
