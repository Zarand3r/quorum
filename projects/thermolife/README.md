# thermolife

> **A transformer block as a programmable interaction engine.** There are now
> **three simulations** on one substrate — **fold** (docking, trained), **economy**
> (survival, evolved), and **morph** (reaction–diffusion, untrained). Each is a
> separate engine sharing the same grounded-contour readout, local attention, and
> web viewer. **Full map: [`docs/SIMULATIONS.md`](docs/SIMULATIONS.md).**

Hinton's observation is that a token's embedding **morphs** as it passes through the
attention blocks of a transformer — a trajectory, like a protein folding. thermolife
makes that visible and extends it: each embedding is rendered as a **2D contour blob**
whose shape is a *grounded* readout of the embedding, so complementary blobs **fold
into each other like ligands into receptors**.

The grounding is the whole point. One linear readout `C = X·W_c` turns an embedding
into the **Fourier coefficients of a closed contour** — and those same coefficients
are the attention **query** (ligand); a fixed complementarity metric `M` turns them
into the **key** (receptor). By Parseval, the dot product `Q_i·K_j` (the attention
score) **equals** the overlap of the two drawn contours. So the shape you see *is* the
binding math — a blob that morphs on screen ⟺ its interaction changed (invariants
J1/J6). No spatial grid; the embedding space itself is the space.

## What to read

- **[`PLAN.md`](PLAN.md)** — the design: the mechanism (§4), the visualization
  contract (§5), invariants **J1–J6** (§6), the `fold/` module map (§7), milestones
  **S0–M3** (§8), and what changed from the earlier thermodynamic-grid design (§9).
  **Read this first.**
- **[`CLAUDE.md`](CLAUDE.md)** — project-specific anchors for Claude Code sessions.

## Current state — S0 (numpy, random init, no torch)

- `fold/` — the mechanism: `weights` (grounded `W_c` + complementarity `M`),
  `interface` (contour coeffs → blob polyline), `transformer` (weight-tied attention
  block = one fold iteration), `engine` (`FoldEngine` + the *fold gallery*: a settled
  fold reseeds a fresh one so the viewer keeps showing new folds).
- `sim/` — web control: `controller` (state machine), `server`, `viewer.html`
  (morphing blobs + docking edges). See [`sim/README.md`](sim/README.md).
- 12 tests gate J1–J6 (groundedness, `overlap == attention` via Parseval,
  no-token-loop, synchrony, bounded, determinism) + the fold gallery + the controller.

Run it: `bazel run //projects/thermolife:serve -- --port 8787`, then
`tailscale serve --bg 8787` (or `sim/host.sh`).

## What's next

- **M1** — hand-designed complementary weights so chosen tokens dock deliberately.
- **M2** — train the toy transformer (torch) so the fold is *meaningful*, not incidental.
- **M3** — reintroduce a viability / free-energy objective over a *drifting* target so
  folding keeps **adapting** instead of settling — the "earned, not pretty" payoff.

## Build + test

Built with Bazel `rules_python`. All bazel commands work from anywhere.

```bash
bazel test //projects/thermolife:test_suite   # J1-J6 + gallery + controller gate
bazel run  //projects/thermolife:serve -- --port 8787
```

## Repo context

One project in a bazel-only monorepo, kept conceptually separate from its siblings
(`market`, `quorum`). No cross-project imports.
