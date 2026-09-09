# Reviewer handoff — the MLP as a many-body term, 2026-09-09

**Loop stopped at its 2-hour deadline with G4 still running.** Nothing here is a G4 verdict.

## What is established

**An emergent 2-D vesicle, transformer-only, render-confirmed.** Seed 509, step 500,000, production
chemistry (all six affinities, explicit solvent), dispersed random start, nothing planted.
`vesicle_call` True at dilations `[1,1,1,1]`, lumen 0.136, sustained 22 checkpoints, reproducible.
It closed at CONSTANT SIZE -- 56 lipids for 100,000 steps before and after -- i.e. two ends of a
ribbon meeting, the same signature as the historical vesicle at 116. Shipped as
`docs/controls/emergent_vesicle_sd509_s500000.npz` and served at `/vivarium`.

**A live MLP inside a conservative force law.** `manybody.py` + `field.py` + `transformer.py`.
Each token carries a smooth coordination number over lipid beads; an MLP maps it to an exposure
`f_i`; chemistry becomes `chi_ij = chi0_ij * f_i * f_j`, symmetric so the pair force stays
antisymmetric. The force carries the term both force paths would otherwise omit,
`-sum eps*well*chi0*[f_j df_i/dx + f_i df_j/dx]` -- the same embedding-density term EAM and many-body
DPD carry.

| gate | result |
|---|---|
| G1a off-state vs the pre-existing force | **0.000e+00** bit-identical |
| G1b F vs -grad U, MLP live (scale 0.5/1.0/2.0) | **1.5e-08 / 2.5e-08 / 2.8e-08** |
| G1c field vs transformer force, every scale | **0.000e+00** |
| G2 leaflet asymmetry, FLAT membrane (the null) | **0.0000 exactly** |
| G3 leaflet asymmetry, curved ring | **+0.1179** |

G2 is the honesty check: the term is identically zero on a flat membrane, so it **cannot manufacture
curvature** -- it can only respond to curvature already present.

## What is NOT established

**G4 -- does a planted flat ribbon curl?** Attempt 2 was still running when the deadline hit. Score it
with:

    python curl.py --score

```
G4 PASSES iff  on >= 6/12  AND  off <= 1/12  AND  Fisher one-sided p <= 0.05
```

The gate is mechanical; it needs no interpretation. **Render any curled state before believing the
count** -- `python gap_shot.py docs/states_curl/CURL_*.npz out.png`. Every scalar in this project has
at some point contradicted its own picture.

## The defect that nearly produced a false verdict

**G4 attempt 1 was VOID.** `max|X_off - X_mlp| = 0.000e+00` after 400 steps -- both arms were the same
simulation. `manybody` was wired into `field.forces`, but the production engine runs
`transformer.attention`, a SECOND implementation of the same force law that never consulted it.

Had it completed it would have reported *"G4 fails, the MLP does nothing"* -- the opposite of the
truth, backed by 24 runs and ~48 CPU-hours.

This is the duplication defect this session's audit measured: `def plant` in 18 files, `def build` in
15, `def step` in 12, `largest_cluster` in 5. Two force laws; one was patched. **G1 is amended to
require the two paths to AGREE at every MLP scale** -- both were internally consistent, with different
physics, and an off-state bit-identity check cannot catch that because with the MLP off they agree
trivially.

## Open items, in priority order

1. **Score G4** and render before believing it.
2. **Re-run the test suite on an idle machine.** It TIMED OUT at 900 s under 24-worker load having
   passed everything it reached (738 s idle). Not a code failure, but it is a hard prerequisite for
   pushing and has not been satisfied since `field.py` and `transformer.py` changed.
3. **`ManyBodyMLP.scale = 1.0` is a free parameter** (`n_ref = 6.0` is close-packed 2-D coordination,
   i.e. geometry). It must not be tuned to make G4 pass; report every value run.
4. **Unify the two force implementations.** The cross-path gate is a patch over the real problem.

## Retracted this session, all verified independently

- **The gel/fluid explanation.** `phase.py` hardcoded 6B chemistry, so all 63 map rows were one
  chemistry and production was never measured. Measured properly both read retention **0.776** -- both
  gel. At matched `T*`, production still beats the reduced chemistry (p = 0.0036): **chemistry, not
  phase, carries the gap.**
- **The ladder's "no loss" headline.** 6B is the only arm where the strict gate diverges from
  persistence: **11/20 against 2B's 18/20**, p = 0.0155.
- **The 3-D bending fix.** `bend_r0 = 4.0` does not stiffen, it **stretches every bond 67%**
  (`b* = (2 + 2 r0)/6`, verified analytically and against the shipped Field). Cooke gets away with it
  only because FENE bonds are inextensible. Consequence: the "103% of reference" thickness compared a
  3.33 sigma molecule against a yardstick for a 1.93 sigma one -- it is **54%**, not 103%.

## Operational notes worth keeping

- `pkill -f` matched this session's own shell **three times**. Kill by explicit PID.
- Killing a `ProcessPoolExecutor` PARENT leaves its workers orphaned. Attempt 1's 24 workers survived
  and ran alongside attempt 2 for 28 minutes, 49 processes on 32 cores, half producing void data.
  Kill the worker PIDs too.
- Four cost estimates in this project were wrong for the same reason: benchmarking a DISPERSED start
  and quoting it for the CONDENSED regime, or benchmarking solo and quoting it contended. Measured
  properly: 2-D production **3.40 ms/step** condensed, 3-D **97 ms/step** (9.9x its dispersed figure).
