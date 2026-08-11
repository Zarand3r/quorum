# Handoff 2: the success metric was wrong. Request for advice.

**Date:** 2026-08-11. **Worktree:** `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
**Supersedes** `HANDOFF_VESICLE.md` on every point below. Read `docs/DECISIONS.md` D1–D9 alongside.

Your previous review (leaflet asymmetry, the exact `L/R` crossover, `κ̄` in the closure criterion,
`C_nn(t)` over `D_∥`, 3-D-for-validation / 2-D-for-science) was acted on in full. Acting on point 1 —
"calibrate `bilayer_frac` on planted, thermalized vesicles of the target radii" — is what produced the
result below, and it is worse than a mis-set threshold.

---

## 1. Headline: `bilayer_frac`'s success target is unreachable, and every comparison I have published is inside the noise band

A planted **flat** bilayer — a phase we independently believe is stable for this chemistry (it exists
as a box-spanning slab, holds T = 1.00, and is laterally fluid) — was thermalized for 6000 steps with
the same readout used everywhere else:

| step | bilayer_frac | paired | flat | intact | T |
|---|---|---|---|---|---|
| 0 | 1.000 | 1.000 | 1.000 | 0.12\* | 0.98 |
| 750 | 0.242 | 0.891 | 0.258 | 1.00 | 1.01 |
| 1500 | **0.117** | 0.875 | 0.125 | 1.00 | 1.04 |
| 3000 | 0.164 | 0.938 | 0.164 | 1.00 | 1.00 |
| 3750 | **0.312** | 0.930 | 0.320 | 1.00 | 0.99 |
| 6000 | 0.125 | 0.922 | 0.125 | 1.00 | 1.00 |

\* the t=0 intactness is a lattice artifact: planted spacing 1.285 exceeds the 1.2 contact cutoff
until the first relaxation. It resolves to 1.00 and stays there.

**A perfectly healthy, fully intact, laterally fluid flat bilayer reads 0.117–0.312 at kT = 1.**

Now place every structure this project has measured on that same axis:

| structure | bilayer_frac | inside the healthy band? |
|---|---|---|
| planted flat bilayer, thermalized (**the reference**) | 0.117–0.312 | — |
| 2-D emergent ribbons `big_phi20_nb3_da15_s1` | 0.310 | yes |
| 3-D SL slab `sl_f28_N12000_s1` | 0.184 | yes |
| planted R=9 vesicle, thermalized | 0.307 | yes |
| planted R=7.5 vesicle, thermalized | 0.179 | yes |

Consequences, stated plainly:

1. **The ">0.5 within a finite aggregate" success criterion is void.** It was calibrated against
   t=0 lattices (planted flat bilayer 0.967, planted R=9 vesicle 0.878) at effectively zero
   orientational noise. No thermalized membrane of any morphology reaches it.
2. **D9's ranking is retracted.** "2-D ribbons (0.310) beat the SL slab (0.184) by 1.7×" compares two
   points inside a band whose own reference oscillates 0.117 → 0.312 → 0.125 between consecutive
   snapshots of an unchanging, intact membrane. That is not a difference; it is sampling noise.
3. **"Planted vesicles are unstable" is NOT established.** I said this last message and I was wrong to.
   The R=7.5 decay 0.541 → 0.179 and R=9 0.878 → 0.307 are what a *healthy flat bilayer* does over the
   same interval. The decay is thermalization, not necessarily decomposition.

This is the fourth metric failure in this project, and the first one that invalidated a comparison I
had already reported to a reviewer.

---

## 2. Which half of the metric broke, and the proposed fix

The failure is entirely in `flat`, not `paired`:

| | flat bilayer (therm.) | R=9 vesicle (therm.) | R=7.5 (therm.) | R=6 (therm.) |
|---|---|---|---|---|
| `paired` | **0.875–0.938** | 0.701–0.756 | 0.411–0.528 | 0.196–0.676 |
| `flat` | 0.125–0.320 | 0.418–0.464 | 0.457–0.522 | 0.302–0.975 |

`paired` is robust under thermalization and orders the structures sensibly (flat slab > R=9 > R=7.5 >
R=6, which is exactly the leaflet-population ordering). `flat` collapses from 1.000 to ~0.15 on a
membrane that has not changed.

**Why.** `flat` thresholds the mean dot product between a molecule's own axis and its same-leaflet
neighbours' axes at 0.90, i.e. 25.8°. That is a *per-molecule* comparison, so it measures single-molecule
thermal tilt, which at kT = 1 is comparable to the threshold. It was never a curvature measure at kT > 0.

Note this is **not** the curvature concern you raised — your `s < 0.451R` bound is satisfied at every
radius (my neighbour window is 1.6 rc; the bound is 2.7 rc even at R=6), and indeed `flat` reads 0.975
on the planted R=6 vesicle at t=0. Thermal noise, not curvature, is what destroys it.

**Proposed fix, on which I want your opinion.** Compute a *smoothed* local normal by averaging axes
over a molecule's neighbourhood first, then measure how that smoothed normal varies between adjacent
patches. Averaging over `z` neighbours suppresses uncorrelated thermal tilt as `1/sqrt(z)` while
leaving genuine systematic curvature (a micelle, a tight vesicle) intact. The micelle pole should stay
near 0 because its normal genuinely rotates by `2π/M` per neighbour, which no amount of averaging
removes.

**Open question A:** is patch-averaged-normal variation the right robust flatness estimator, or would
you prefer something else entirely — a structure factor, a nematic order parameter computed on
leaflet-assigned subsets, a direct local mean-curvature estimate from the fitted surface?

**Open question B:** should `flat` be recalibrated against the *thermalized* poles (flat bilayer ≈ 0.19,
micelle ≈ ?) rather than the t=0 poles? I have not yet measured a thermalized micelle, so I do not know
whether the paired+flat conjunction retains any micelle discrimination at kT = 1. **I consider this the
single most important missing measurement** and it is queued next.

---

## 3. What survives from the previous handoff

These are unaffected by the metric failure because they are geometric or thermodynamic, not
`bilayer_frac`-derived:

- **Membrane geometry**, measured on the spanning slab: thickness `d = 5.03 rc`, area per amphiphile
  `a = 1.65 rc²`.
- **Leaflet asymmetry** (your catch): a vesicle needs `4πR²/a : 4π(R−d)²/a`, which is 274:7 at R=6 and
  616:121 at R=9. The R=6 disk-closure experiment was retired because closure would have required 48%
  of the lipids to migrate leaflets. Planted vesicles now build the asymmetry in from the start.
- **Exact box rule**, adopted: `L/R > sqrt(2π[1+(1−d/R)²])` — 2.54 at R=6, 3.545 asymptotically —
  described as mass balance plus periodic clearance, not as a free-energy argument.
- **Engine validation**: Groot–Warren EOS `p/p_pred = 0.92–0.99`; T stable across an 8× timestep range;
  the one-force-evaluation-per-step DPD integrator fix (a two-evaluation Verlet measures T = 0.51).
- **Lateral fluidity**: MSD linear, ~4 neighbour spacings over 12k steps, with intactness 1.00
  throughout. I accept your caveat that this does not establish *topological* fluidity; `C_nn(t)` and
  the T-junction test remain unbuilt.

---

## 4. The signals that still discriminate, and what they say

Since `bilayer_frac` is currently non-discriminating, the readouts I would actually rely on now are
`paired`, sealed lumen, intactness, and shell radius. On those:

| planted vesicle | paired (therm.) | lumen 0 → therm. | intact | ⟨r⟩ 0 → therm. |
|---|---|---|---|---|
| R=6.0 (274:7) | 0.196 → 0.676 | 131 → 5 | — | 4.19 → 5.39 (+29%) |
| R=7.5 (428:47) | 0.640 → 0.411 | 333 → 19 | 0.69 | 5.58 → 6.63 (+19%) |
| R=9.0 (616:121) | 0.878 → 0.756 | 537 → 52 | 0.87 | 6.99 → 7.94 (+14%) |

Reading: **R=9 is the only one behaving like a vesicle** — it keeps a sealed lumen (52 water cells),
stays 87% one aggregate, and holds `paired` at 0.756. R=6 collapses to a filled blob (rendered; heads
scattered through the interior). R=7.5 stays visibly hollow in cross-section but its inner face is bare
tail, because 47 inner lipids cannot line a sphere of radius 2.47, and its lumen unseals.

**Every vesicle swells**, monotonically with decreasing R (+14%, +19%, +29%). I suspect an osmotic
artifact of my planting: water is placed uniformly at random over the whole box, so the lumen is filled
at bulk density and then cannot equilibrate through the membrane. The smaller the vesicle, the larger
the surface-to-volume error.

**Open question C:** what is the standard way to plant a vesicle at osmotic balance in DPD? Options I
see are (a) explicitly count and adjust lumen water to match the exterior chemical potential rather
than bulk density, (b) plant, then run with a permeable membrane / lower `a_HW` for an equilibration
phase, (c) accept the swelling and measure area per lipid *after* relaxation instead of imposing it.
Is the swelling large enough to be the actual cause of the R=6 and R=7.5 failures, or is it second-order
next to the leaflet-population problem?

---

## 5. Where I think this leaves the program, and what I want advice on

Your recommendation was: 3-D as the reference/control line, reproducing one published spontaneous-vesicle
DPD result essentially verbatim; 2-D as the actual Vivarium science line. I accept that split.

But there is a hard constraint I should have surfaced earlier. This engine is **plain numpy on CPU**.
With the measured `d = 5.03`, a *physically ordinary* vesicle (R/d ≳ 3, giving an out:in ratio ≈ 2.25)
needs R ≈ 15, hence `L ≈ 45`, hence `N ≈ 2.7×10⁵` particles — roughly 6× the largest run completed here
(R=9 at N = 45 138 takes ~30 min for 6000 steps). Published spontaneous-vesicle DPD work runs at that
scale or larger, often on GPUs.

So the honest position is that the SL H₃(C₄)₂ amphiphile is **too thick** for this engine to reach a
non-extreme vesicle. Everything tested so far is in the R/d = 1.2–1.8 nanovesicle regime, which you
correctly identified as an extreme object rather than a clean test.

**Open question D — the one I most want your answer to.** Which of these is the best use of the next
block of compute?

1. **Shorten the amphiphile** (e.g. H₂(C₃)₂, 8 beads) to halve `d`, so R/d ≈ 3 becomes reachable at
   N ≈ 40 000. Cost: it is no longer a published parameter set, so a failure is ambiguous again —
   exactly the trap the reset roadmap was written to escape.
2. **Reproduce a published spontaneous-vesicle DPD system verbatim** at whatever N it demands, accept
   multi-hour runs, and treat it as the Stage-D exit criterion. Cleanest logic, worst wall-clock.
3. **Fix the metric first** (§2) and re-measure everything already on disk before running anything new.
   Cheapest, and given four metric failures arguably mandatory, but produces no new physics.
4. **Drop to 2-D** for the science line now, where boxes are small enough that R/d ≈ 3 rings are cheap,
   and accept that 2-D closure physics differs.

My instinct is 3 → 1 → 2, deferring the verbatim reproduction until the metric can actually adjudicate
its outcome. I would rather be told that is wrong now than after another day of compute.

---

## 6. Reproduction

```bash
cd /home/rbao/quorum-thermolife
bazel run //projects/vivarium:_thermal_ref   -- 6000            # the baseline that broke the target
bazel run //projects/vivarium:_vesicle_calib -- 6000 6,7.5,9    # planted vesicles, correct asymmetry
bazel run //projects/vivarium:_geom          -- sl_f28_N12000_s1
bazel run //projects/vivarium:_pairing       -- --calibrate <tags>
bazel run //projects/vivarium:_shot          -- "<tag>~<title>~<subtitle>~<slab>"
```

States: `docs/runs/states/*.npz` (`x`, `species`, `L`, `n_amph`, `nb`, `nh`). Images:
`docs/images/*.png`. Logs: `docs/runs/*.log`.

**Standing request:** assume any positive claim here is weaker than stated. Two results were withdrawn
before this document and two more are withdrawn inside it.
