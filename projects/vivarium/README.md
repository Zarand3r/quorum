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
- **[RESEARCH_LOG.md](RESEARCH_LOG.md)** — every idea tried, with its commit and its (often
  negative) result.
- **[FOLLOWUPS.md](FOLLOWUPS.md)** — reasoned-through future directions (variable shape complexity,
  blob fission, per-pair plasticity, sustained/co-adaptive learning) — all kept faithful to the
  hard requirements.

## The engines
- **`pack.py`** — dock-and-morph packing: attract (complementary fit) + repel (soft excluded
  volume) + cohesion (surface tension) + induced-fit morph, on a periodic torus. Motion from
  neighbour attention → interaction load-bearing by construction (identity ablation → frozen).
  Optional **plasticity** (`plasticity` knob, default off): a Hebbian fast-weight memory — the
  fast-weight form of linear attention (no backprop) — so the *coupling* weights **learn while
  alive**, while the *physics* weights stay fixed. Load-bearing when on (paper §3.1).
- **`pure.py`** — everything (move + morph) by one block with non-reciprocal attention
  `A+β(A−Aᵀ)`; higher aliveness, P6 measured-positive (not by-construction).
- **`engine.py`** — legacy force-based engine (NOT transformer-only; kept for history).

## Run it
```bash
bazel test //projects/vivarium:test_suite          # gates (P1–P9, transformer-only, metrics)
bazel run  //projects/vivarium:pack -- --probe     # numeric probe of the packing engine
bazel run  //projects/vivarium:pack -- --measure   # matter-vs-gas / droplet metrics
bazel run  //projects/vivarium:serve -- --pack --port 8788   # live viewer
#   then:  tailscale serve --bg 8788
```

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
