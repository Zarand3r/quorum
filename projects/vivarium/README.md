# vivarium

A **transformer-only living dish**: every agent is one token of a small transformer, and *the
simulation is the forward pass*. Grounded-shape agents **move, morph, and bind** by attention —
purely attention / MLP / LayerNorm, no external force law, no energy ledger, no variable token
count. Watchable live in the browser.

> **living = inference = optimization, no separation** — a tick is a forward pass; the forward pass
> relaxes a physical binding energy; the relaxing *is* the living. `ẋ = −D∇Φ + J`.

## Read this first
- **[paper/paper.md](paper/paper.md)** — the v1 demonstration paper (what it is, what it does,
  honest limits).
- **[SPEC.md](SPEC.md)** — the spec. **[DECISIONS.md](DECISIONS.md)** — the design log.
- **[design/HARD_REQUIREMENT.md](design/HARD_REQUIREMENT.md)** — the strict transformer-only rule.
- **[docs/BILAYER_REVIEW.md](docs/BILAYER_REVIEW.md)** — why bilayers have not emerged, and the
  three-fundamental-forces discipline (Pauli + vdW + electrostatics only) the current work follows.
  It retracts the explicit per-species lipid force laws and supersedes `MEMBRANE_PLAN.md`,
  `EXPERIMENT_PLAN.md`, and `IMPLEMENTATION_PLAN.md` where they conflict.
- **[RESEARCH_LOG.md](RESEARCH_LOG.md)** — every idea tried, with its commit and its (often
  negative) result.
- **[FOLLOWUPS.md](FOLLOWUPS.md)** — reasoned-through future directions (variable shape complexity,
  blob fission, per-pair plasticity, sustained/co-adaptive learning, DNA/genes, species &
  membranes) — all kept faithful to the hard requirements.
- **[EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md)** — the ordered plan: each idea refined,
  requirement-checked, with an implementation sketch and a **visual** success criterion, plus the
  recommended order to try them.

## The engines
- **`pack.py`** — dock-and-morph packing: attract (van der Waals) + repel (soft excluded volume) +
  cohesion (surface tension) + induced-fit morph, on a periodic torus (2-D or 3-D, per
  `cfg.pos_dim`). The conservative attract head is **contact-area / dispersion**:
  `tanh(rad_i·rad_j/0.25)·exp(−λ‖Δp‖²)` off the **k=0 RADIUS channel** (a token's physical *size*,
  held at `rad_idx = pos_dim + shape_dim`, disjoint from the contour) — symmetric, bounded, and
  **charge-independent**, which is why neutral tokens cohere. The complementary-fit attention
  `A_fit = softmax(⟨Cᵢ,M·Cⱼ⟩ − λ‖Δp‖²)` still exists but now drives only the induced-fit **morph**,
  not the attractive force. Motion from neighbour attention → interaction load-bearing by
  construction (identity ablation → frozen). Optional **plasticity** (`plasticity` knob, default
  off): a Hebbian fast-weight memory — the fast-weight form of linear attention (no backprop) — so
  the *coupling* weights **learn while alive**, while the *physics* weights stay fixed.
  Load-bearing when on (paper §3.1).
- **`polar_pack.py`** — the ELECTROSTATIC head on top of `pack.py`: a bounded, bearing-aware
  attention on the near-face charges `nfᵢ(j)=⟨Cᵢ, basis(θ_{i→j})⟩` (no `1/d²` kernel). Carries the
  species — `WATER, ACTIVE, OIL, LIPID, AMPHI` — each with a fixed k=0 radius. **AMPHI** is the
  *emergent amphiphile*: an ordinary token with a fixed polar-head / neutral-tail contour that
  reorients in the local field like water, with **no per-species force law**. **LIPID** is the
  legacy explicit lipid rod (`k_hydro`/`k_tail`) and is **2-D only** — its force is a no-op when
  `pos_dim == 3`, and it is retracted by [`docs/BILAYER_REVIEW.md`](docs/BILAYER_REVIEW.md).
- **`pure.py`** — everything (move + morph) by one block with non-reciprocal attention
  `A+β(A−Aᵀ)`; higher aliveness, P6 measured-positive (not by-construction).
- **`engine.py`** — legacy force-based engine (NOT transformer-only; kept for history).

## The frozen benchmarks
Two harnesses, never edited mid-run (editing them invalidates every row of their log). Primary
metric `emergence_score` = amphiphile assembly excess (heads facing water + tails buried, against
the local-composition baseline); secondary `demix_excess` = the hydrophobic effect that must
precede assembly. Scores are **not** comparable across the two — different dimensionality.
- **`bench_emergence.py`** (2-D) → [`docs/autoresearch_results.tsv`](docs/autoresearch_results.tsv)
- **`bench_emergence3d.py`** (3-D) → [`docs/autoresearch_results_3d.tsv`](docs/autoresearch_results_3d.tsv)

> **Caveat on every recorded number.** A bug where the electrostatic near-face `nf_j` read token
> j's *far* face (fixed at `3538e89`: `nf_j = nf_i.T`) made the "conservative" electrostatic force
> non-conservative. Every row logged before that fix was measured on a subtly non-physical system,
> the tuned configs now **collapse** (gates fail), and both benchmarks need re-baselining.
> Assembly (`emergence_score`) has **not** been achieved; only demixing improved.

## Run it
```bash
bazel test //projects/vivarium:test_suite          # gates (P1–P9, transformer-only, metrics)
bazel run  //projects/vivarium:pack -- --probe     # numeric probe of the packing engine
bazel run  //projects/vivarium:pack -- --measure   # matter-vs-gas / droplet metrics
bazel run  //projects/vivarium:bench_emergence     # frozen 2-D emergence benchmark
bazel run  //projects/vivarium:bench_emergence3d   # frozen 3-D emergence benchmark
bazel run  //projects/vivarium:serve -- --pack --port 8788   # live viewer
bazel run  //projects/vivarium:serve -- --polar --dim3 --port 8788  # 3-D dish (depth-cued)
#   then:  tailscale serve --bg 8788
```
The `--dim3` dish sets `pos_dim=3, n_harmonics=2` — the contour becomes **real spherical harmonics**
(`shape_dim = K(K+2)`) — and swaps the UI's "lipid" fraction knob for **"amphi"**; the viewer draws
it through a depth-cued 2-D projection.

## Design docs (`design/`)
`HARD_REQUIREMENT.md` (transformer-only) · `dock_and_morph.md` (substrate) ·
`potential_flux.md` (`ẋ=−D∇Φ+J` thermodynamics) · `dynamics_zoo.md` (drives + what stays
transformer-only) · `signalling.md`, `m2_collapse.md` (the honest negative results) ·
`related_work.md`, `two_tracks.md`, `global_vs_local.md`.

## Honest status
Measured aliveness is modest (packing droplet ~0.06; pure-attention variant ~0.26–0.42 on [0,1]).
By default the network weights are fixed (the *state* is optimized); the optional fast-weight
**plasticity** makes *coupling* weights learn while alive — load-bearing but modest, and the *slow*
physics weights never learn. It is a demonstration and a discipline (measured-not-rewarded aliveness
that repeatedly caught illusory emergence — and has itself needed correction), not a claim of strong
artificial life. Aliveness measurement is left as an open problem.
