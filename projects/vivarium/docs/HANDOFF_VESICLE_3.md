# Handoff 3: state of the vesicle work, self-contained

**Date:** 2026-08-11. **Worktree:** `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
Supersedes handoffs 1 and 2; readable without them. Decisions with falsification criteria: `docs/DECISIONS.md`
D1–D10.

**Standing instruction to the reviewer:** be adversarial about over-claiming. Four results have been
withdrawn in this project, two of them after being reported to a reviewer as findings. Assume any
positive claim below is weaker than it sounds.

---

## 1. What this is

A **plain Groot–Warren DPD reference model** — deliberately *outside* the project's transformer-only
constraint. The ladder (`docs/ROADMAP_RESET.md`) is: reproduce vesicle emergence with a known-good
conventional model (stage D) → port into Vivarium's engine (E) → transformerise the forces one at a
time (F). Still on **D**. Nothing here is a Vivarium result.

Model: Shillcock–Lipowsky **H₃(C₄)₂** (3 head beads, two 4-bead tails), `a_WW=a_TT=25, a_HH=35,
a_HT=a_WT=80, a_HW=15`, bonds `k=128, l0=0.5`, three-body bending `k₃=15`, ρ=3, kT=1, dt=0.02.
Engine validated against the published Groot–Warren EOS at `p/p_pred = 0.92–0.99`, T stable across an
8× timestep range.

---

## 2. Current status in one table

| claim | status |
|---|---|
| stable flat bilayer (planted, thermalized) | **yes**, intact 1.00 over 6000 steps, rendered edge-on |
| stable vesicle (planted, R=9, thermalized) | **yes**, plateaus; caveat in §5 |
| emergent bilayer, 2-D | **yes**, branched ribbons |
| emergent bilayer, 3-D | partial — patchy thick blobs, visibly worse than planted |
| **emergent vesicle** | **no** — runs launched, ETA 17–20 h |

---

## 3. Measured geometry, which now determines every run size

From the box-spanning slab, where geometry is unambiguous:

- membrane thickness (head-peak to head-peak) **d = 5.03 rc**
- area per amphiphile **a = 1.65 rc²**

A vesicle's leaflets sit at R and R−d, so it needs `4πR²/a : 4π(R−d)²/a` amphiphiles. This killed an
earlier experiment: at R=6 that ratio is **274:7**, while a flat disk of the same 281 amphiphiles
starts 141:141, so "closure" would have required 48% of the lipids to migrate leaflets. That
experiment was measuring rim transport, not bending-versus-edge competition.

Box rule, exact rather than asymptotic: `L/R > sqrt(2π[1+(1−d/R)²])` — 2.54 at R=6, 3.545 as R≫d.
Stated as mass balance plus periodic clearance, **not** as a free-energy argument.

---

## 4. The metric history — the most error-prone part of this project

`bilayer_frac` = *paired* AND *locally flat*. Both halves are needed: pairing alone scores a planted
micelle 1.000, and flatness alone cannot separate a bilayer from a nematic droplet.

**D10 (the big one).** A planted **flat bilayer** — intact, laterally fluid, T=1.00 — reads
**0.117–0.312** once thermalized, oscillating between those values on consecutive snapshots of an
unchanging membrane. Every structure ever measured here sits inside that band: 2-D ribbons 0.310,
3-D slab 0.184, R=9 vesicle 0.307, R=7.5 vesicle 0.179. Consequences: the ">0.5" success target was
**void**, and a previously reported ranking ("2-D ribbons beat the 3-D slab 1.7×") was **retracted** as
sampling noise.

Cause: `flat` thresholded a **per-molecule** dot product at 0.90 (25.8°), and single-molecule thermal
tilt at kT=1 is comparable. It measured thermal noise, not shape. Note this is *not* a curvature
artifact — `flat` reads 0.975 on a planted R=6 vesicle at t=0.

**Fixes now in place:**

1. *Smoothed-normal flatness* — average axes over the same-leaflet neighbourhood, then compare
   smoothed normals. Thermalized flat bilayer recovers 0.824 → **0.964**; micelle poles stay at
   0.824–0.885. **But it saturates at 0.951–0.982 on every real structure**, so it is a micelle guard,
   not a quality measure. Reported honestly rather than presented as a fix.
2. *Hydrophobic burial* — fraction of tail beads with no water within 1.0 rc. A density measure, so
   angular noise cannot touch it, and physically it **is** the edge energy (a line-tension proxy).
   This is the one that reproduces what the renders show:

   | structure | tail buried | paired | flat_smooth |
   |---|---|---|---|
   | planted flat bilayer, thermalized | **0.712** | 0.922 | 0.964 |
   | planted R=9 vesicle, thermalized | 0.638 | 0.752 | 0.972 |
   | emergent 3-D slab | 0.611 | 0.787 | 0.977 |
   | emergent 3-D, not a clean bilayer | 0.456 | 0.829 | 0.951 |
   | emergent 2-D ribbons | 0.402 | 0.950 | 0.967 |

   Head burial is 0.000 everywhere, confirming correct amphiphile orientation.
3. *Thermalized micelle pole* — a spherical micelle of the two-tailed lipid is physically impossible
   (packing parameter is in the bilayer regime), so the pole keeps the chemistry and **removes one
   tail**, then lets the model assemble its own. Running: largest aggregate 47–70 against a
   self-consistency prediction of M ≈ 45 (`R = 3v_tail/a ≈ 2.4`).

**Other corrected defects:** `lumen` counted voids inside the bilayer's own tail core and read 51–68
on provably flat disks; it now requires the enclosed pocket to contain water. `bilayer_fraction` in
`harness.py` is 2-D only (a planted 3-D bilayer scores 0.000 there). A transverse density profile was
used to rank a *branched* morphology, which is invalid because a branched network has no global normal.

---

## 5. Planted-vesicle results (the stability question)

Vesicles planted with the correct leaflet asymmetry, thermalized 6000 steps:

| R | out:in | paired 0→therm | sealed lumen 0→therm | intact | ⟨r⟩ 0→therm |
|---|---|---|---|---|---|
| 6.0 | 274:7 | 0.196 → 0.676 | 131 → 5 | — | 4.19 → 5.39 (+29%) |
| 7.5 | 428:47 | 0.640 → 0.411 | 333 → 19 | 0.69 | 5.58 → 6.63 (+19%) |
| 9.0 | 616:121 | 0.878 → **0.757** | 537 → **43** | 0.70 | 6.99 → 7.80 (+14%) |

**R=9 holds.** Over steps 1500→6000 paired runs 0.701→0.756→0.745→0.757 and radius 7.72→7.80: a
plateau, not decay. The render shows a hollow shell with heads on both outer and inner faces.

Caveats: `intact` falls to 0.70, so ~30% of amphiphiles have left the shell, and the lumen is slowly
shrinking (58→43). Longer runs are needed before calling it equilibrated rather than slowly bleeding.
R=6 collapses to a filled blob. **All three swell**, monotonically with decreasing R — I suspect an
osmotic artifact of planting lumen water at bulk density.

---

## 6. Running now: the emergent-vesicle attempt

Sized from the measurements for the first time. R=9 needs 737 amphiphiles; at L=3R a box-spanning
lamella needs 884, so the vesicle is favoured by 20%. That margin is why earlier runs (174–305
amphiphiles, boxes too small) could not have worked.

- **vesA**: N=59 049, L=27.0, 737 amphiphiles, φ=0.137, lamella margin 1.20
- **vesB**: N=75 076, L=29.2, 737 amphiphiles, φ=0.108, lamella margin 1.41

Benchmarked at **1.4–1.6 steps/s**, so 100k steps ≈ **17–20 h**. Checkpoints every 5000 steps so
trajectories can be measured with the corrected metrics without waiting. The signal to watch is
whether the largest aggregate climbs toward ~737 or stalls at 100–300, where every previous run died.

---

## 7. Open questions for the reviewer

1. **Is hydrophobic burial confounded by aggregate size?** A larger aggregate has a lower
   surface-to-volume ratio and so buries more regardless of quality. The 2-D-vs-3-D comparison in §4 is
   almost certainly not meaningful for this reason. What is the right normalisation — burial per unit
   perimeter, or an explicit surface-area model?
2. **Is a saturating flatness estimator acceptable as a micelle guard**, with burial carrying the
   quality signal? Or should flatness be replaced entirely by a direct local mean-curvature estimate
   from a fitted surface?
3. **Is the swelling an osmotic planting artifact or real?** All planted vesicles expand 14–29%. If it
   is osmotic, what is the standard way to plant a DPD vesicle at balance — adjust lumen water to match
   exterior chemical potential, equilibrate through a temporarily permeable membrane, or measure area
   per lipid after relaxation instead of imposing it?
4. **Is 737 amphiphiles at φ=0.137 the right self-assembly target**, or does the mass-balance margin of
   1.20 leave too many competing morphologies (cylinders, perforated lamellae, multiple small vesicles)
   accessible? Would you push to L=3.5R and accept ~30 h?
5. **Untested from your previous review:** the planted T/Y-junction healing test (whether branched
   networks are a kinetic intermediate or a competing equilibrium), the neighbour-persistence
   correlator `C_nn(t)` as opposed to bare MSD, and direct measurement of κ from the height-fluctuation
   spectrum and Γ from a free-edge geometry. All still queued. Also unaddressed: `2κ/Γ` neglects the
   Gaussian term, and the correct sphere criterion is `(2κ+κ̄)/Γ`.
6. **Scale ceiling.** This engine is plain numpy on CPU. With d=5.03, a *physically ordinary* vesicle
   (R/d ≳ 3) needs R≈15, L≈45, **N≈2.7×10⁵** — roughly 6× the largest run here. Everything tested is in
   the R/d = 1.2–1.8 nanovesicle regime. Options: shorten the amphiphile (loses the published parameter
   set), reproduce a published system verbatim and accept multi-day runs, or accept the nanovesicle
   regime and say so explicitly. **Which would you choose?**

---

## 8. Reproduction

```bash
cd /home/rbao/quorum-thermolife
bazel run //projects/vivarium:_thermal_ref   -- 6000                 # the baseline that broke the target
bazel run //projects/vivarium:_vesicle_calib -- 6000 6,7.5,9         # planted vesicles, correct asymmetry
bazel run //projects/vivarium:_flat2                                 # metric comparison table
bazel run //projects/vivarium:_micelle_pole  -- 0.10 15000 12000 1   # thermalized negative pole
bazel run //projects/vivarium:_geom          -- sl_f28_N12000_s1     # d and a
bazel run //projects/vivarium:_shot -- "<tag>~<title>~<sub>~<slab>~xz"   # edge-on render
```

States `docs/runs/states/*.npz`; images `docs/images/*.png`; logs `docs/runs/*.log`.

**Rendering note:** a membrane sliced along its own normal renders face-on and looks like a uniform
sheet whether or not a bilayer exists underneath. Always render edge-on (`xz` for a z-normal slab).
