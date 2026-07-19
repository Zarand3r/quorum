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

---

*Sweep harness:* [`research.py`](research.py) · *substrate:* [`design/dock_and_morph.md`](design/dock_and_morph.md)
· *why crystallisation:* [`design/potential_flux.md`](design/potential_flux.md)
· *idea lineage:* [`design/m2_collapse.md`](design/m2_collapse.md), [`design/signalling.md`](design/signalling.md)
