# Handoff: vesicle emergence in the DPD reference — state, evidence, open questions

**Date:** 2026-08-11. **Branch:** `quorum-asal-boids-reproduction`, worktree `/home/rbao/quorum-thermolife`.
**Audience:** an AI agent or reviewer auditing this work. Read `docs/DECISIONS.md` D1–D9 alongside.

---

## 0. What you are reviewing, and the one instruction that matters

We are trying to make a **vesicle** emerge in a plain Groot–Warren DPD reference model. This is
*deliberately outside* the project's transformer-only constraint. The ladder (`docs/ROADMAP_RESET.md`)
is: reproduce emergence with known-good methods (stage D) → port into Vivarium's engine (E) →
transformerise the forces one at a time (F). We are still on **D**. Nothing here should be read as a
Vivarium result.

**Please be adversarial about over-claiming.** This project has a documented history of it, including
by the author of this document. Two results have already been withdrawn (F48/F49 self-assembly; D8's
bilayer ranking). The prior should be that any positive claim below is weaker than it sounds.

---

## 1. Bottom line

**No vesicle. Not close.** Two distinct partial structures exist, and a measurement that ranks them
fairly says the *older 2-D* one is better:

| state | dim | n_amph | `bilayer_frac` (local, calibrated) | lumen | failure mode |
|---|---|---|---|---|---|
| `big_phi20_nb3_da15_s1` (2-D ribbons) | 2 | 400 | **0.310** | 0 | has edges, but **branches** instead of closing |
| `sl_f28_N12000_s1` (3-D SL slab) | 3 | 305 | 0.184 | 0 | proper leaflets, but **spans the box** so has no edges |

Target is >0.5 within a finite (non-box-spanning) aggregate with a non-zero lumen. Nothing measured
to date exceeds 0.32.

---

## 2. The model (stage D reference)

`dpd_reference.py` — Groot–Warren DPD, plain numpy, dimension-generic cell list.

    F_C = a_ij (1 - r/rc) r_hat
    F_D = -gamma w^2 (r_hat . v) r_hat
    F_R = sigma w theta / sqrt(dt) r_hat,   sigma^2 = 2 gamma kT

`_sl_model.py` — Shillcock–Lipowsky amphiphile **H₃(C₄)₂** (3 head beads, two 4-bead tails, 11 total),
`a_WW=a_TT=25, a_HH=35, a_HT=a_WT=80, a_HW=15`, bonds `k=128, l0=0.5`, three-body bending `k₃=15`.

**Engine validation, done before trusting any physics:** measured pressure against the published
Groot–Warren equation of state `p = rho kT + alpha a rho^2` (alpha ≈ 0.101) at `p/p_pred = 0.92–0.99`;
temperature holds across an 8× timestep range.

**One integrator bug worth knowing about.** A two-evaluation velocity-Verlet draws the DPD random
force twice per step and measured `T = 0.51` against a target of 1.0 — an exact factor of two.
*Reusing the draw does not fix it*, because the pair list changes when positions move between the two
evaluations. The fix is to carry the force across steps (one evaluation per step), which also halves
the cost. If you are auditing any DPD code, check this first.

---

## 3. Measurement work (the part most likely to contain the next error)

### 3.1 The comparison metric had to be rebuilt, and failed three times

`harness.bilayer_fraction` is **2-D only** (defect #26): a planted *3-D* bilayer scores 0.000 there,
identical to a 3-D gas, so every 3-D reading from it is void. Comparing a 2-D ribbon network against a
3-D slab therefore needed a dimension-generic rebuild (`_pairing.py`). Three versions failed, each
caught by planted controls rather than by inspection:

1. Gating tail proximity on **centroids** read **0.000 on a planted bilayer** in both dimensions. The
   two leaflets' tail centroids sit ~1.8 apart because each is pulled back toward its own head; the
   beads that actually touch at the midplane are the *terminal* tail beads.
2. Pairing alone (anti-aligned axes + touching tips + splayed heads) then read **1.000 on a planted
   bilayer AND 1.000 on a planted micelle**. A micelle's antipodal molecules are anti-aligned with
   tips meeting at the centre, so they satisfy every pair criterion. This independently reproduced a
   collision already documented in `harness.bilayer_fraction`'s docstring.
3. The micelle control was planted at an arbitrary 40 molecules, which over-packs it and makes it
   spuriously flat. Sizing it **physically** (tips meet at the centre → radius = one molecule length →
   M = 13 in 2-D, 56 in 3-D) fixed this.

Only the **paired AND locally-flat** conjunction separates the poles:

| pole | bilayer_frac | paired | flat |
|---|---|---|---|
| 2-D planted bilayer | 0.967 | 1.000 | 0.967 |
| 2-D planted micelle (M=13) | **0.000** | 1.000 | 0.000 |
| 3-D planted bilayer | 1.000 | 1.000 | 1.000 |
| 3-D planted micelle (M=56) | **0.000** | 1.000 | 0.000 |

### 3.2 Dimensional-bias control

`flat` thresholds a mean dot product, and a 3-D leaflet tilts in two transverse directions where a 2-D
one tilts in one, so the threshold could penalise 3-D and manufacture the 2-D "win". Measured by
perturbing planted bilayers at matched angular sigma: the bias runs the **other** way, 3-D scoring
1.03–1.39× *higher* across sigma 0.0–0.5 rad. The 2-D result therefore stands and is if anything
understated.

### 3.3 A measurement I got wrong, and how

I initially ranked the 3-D slab above the 2-D ribbons using a **transverse density profile** (tail
core vs head peaks along the membrane normal). That profile requires *one* global normal. A branched
network has none, so projecting it onto a single axis smears every leaflet orientation together and
scored the ribbons at −0.15 tail excess. That number is a geometry artifact, not a structural finding.
**Any ranking built on a global-normal measure applied to a branched morphology is invalid.**

---

## 4. Geometry: why the vesicle runs were mis-sized

Measured on the box-spanning slab, where geometry is unambiguous (`_geom.py`):

- membrane thickness (head-peak to head-peak) **d = 5.03 rc**
- tail-core FWHM 3.44 rc
- area per amphiphile **a = 1.65 rc²**

A vesicle needs outer radius **R > d**, or there is no lumen and the object is a solid micelle.
Amphiphile count is `4π(R² + (R−d)²)/a`:

| R | lumen radius | n_amph needed | box L ≥ 3.5R | N particles |
|---|---|---|---|---|
| 6.0 | 1.0 | 284 | 21.1 | 28 200 |
| 7.5 | 2.5 | 480 | 26.4 | 55 100 |
| 9.0 | 4.0 | 746 | 31.7 | 95 300 |

The `L ≥ 3.5R` rule matters: a box-spanning lamella costs `2L²/a` amphiphiles, so if the box is too
small the flat phase is *cheaper* than the vesicle and there is no thermodynamic reason to close.

**Three vesicle runs launched before this measurement were mis-sized.** They had 174, 261 and 290
amphiphiles against a 284 minimum, at L = 20.0, 20.0, 23.7. The original sizing targeted R = 5, which
is *below* d = 5.03 — i.e. a solid micelle with no lumen at all. Two were killed; the third is
marginal.

---

## 5. Literature: the branched→vesicle route (this is the useful part)

Searched because the 2-D result is a *branched* network and that is a recognised phase with a known
route to closure.

**Cryo-electron tomography** of surfactant systems reports the sequence
`linear wormlike micelles → branched WLMs → saturated multiconnected network → perforated vesicles
(stomatosomes)`, proceeding by increasing branch count at the expense of cylindrical subchains and
endcaps. So branching is **on the path**, not a dead end.
([Cryo-ET study](https://www.sciencedirect.com/science/article/abs/pii/S0021979724012517))

**The controlling competition** is edge line tension Γ against bending rigidity κ, with a critical
disk radius `R_c = 2κ/Γ` (equivalently `πκ/2Γ_end` in the 2-D ribbon form). Simulations show "a smooth
transition from branched shapes to flat disks as line tension increases, followed by a **sharp**
transition from flat disk to closed vesicle at higher line tension."
([Elastic properties and line tension of bilayer membranes](https://arxiv.org/pdf/1307.0410),
[shapes of fluid membranes with chiral edges](https://arxiv.org/pdf/1912.08172))

**Headgroup area sets the packing parameter** `P = v/(a₀ l)`: spheres `P ≤ 1/3`, cylinders
`1/3–1/2`, bilayers `1/2–1`. Varying headgroup interaction moves the morphology directly.
([packing factor for micelles/vesicles](https://www.sciencedirect.com/science/article/abs/pii/S0927775712002269))

**Self-assembly pathway in DPD** is micelle → cylindrical → open disk → closure, and is
concentration-dependent.
([Yamamoto/Hyodo 2002](https://ui.adsabs.harvard.edu/abs/2002JChPh.116.5842Y/abstract),
[diblock copolymer vesicle dynamics](https://pubs.acs.org/doi/10.1021/ma052536g))

This maps cleanly onto both failures: the 2-D ribbons have **Γ too low** (they used `a_TW = 40` and
*no* bending term), and the 3-D slab is **stiff and edgeless** (`k₃ = 15`, box-spanning), so `R_c` is
large and there is no rim to pay for closure.

---

## 6. An external reviewer's hypothesis, and the first test of it

A reviewer proposed the failure is **membrane fluidity**: a bilayer can have perfect head-tail order
and still be a 2-D *solid*, in which case Y/T junctions can never anneal and branched networks are the
expected frozen end state. Their recommended first measurement was lateral diffusion `D_∥`.

**Measured (`_fluidity.py`), planted box-spanning SL slab, 128 amphiphiles:**

| step | MSD_∥ | √MSD / neighbour spacing |
|---|---|---|
| 2 000 | 4.50 | 1.65 |
| 6 000 | 10.38 | 2.51 |
| 12 000 | 23.71 | 3.79 |

MSD grows **linearly** in t (the diffusive signature) and lipids traverse ~4 neighbour spacings. By
this measure the SL membrane is **fluid, not a solid** — so for *this* chemistry the frozen-membrane
hypothesis is not supported.

**Caveats you should press on:**
1. A membrane that **dissolved** produces the same rising MSD. An intactness control (largest
   connected aggregate ≥ 0.8 of all amphiphiles at every snapshot) was added *after* the numbers
   above and is re-running. **Treat the "fluid" reading as provisional until that lands.**
2. This tests the **3-D SL chemistry**. The reviewer's hypothesis was about the **2-D ribbon**
   chemistry (`nb=3`, `da=15`, `k_ang=0`), which is a different model and is **not yet tested**.
3. Bulk slab drift is subtracted, but the box is small (L = 10.28); finite-size effects on `D_∥` are
   not characterised.

---

## 7. Running now

- **Planted-disk closure scan** (`_disk_closure.py`): a flat bilayer disk holding exactly the
  amphiphiles a R=6 vesicle needs (281 amphiphiles, R_disk = 8.57, L = 21.5, N = 29 800), scanned over
  `k_ang ∈ {0, 3, 8, 15}` for 12 000 steps. This tests `R_c = 2κ/Γ` **directly** by moving κ at fixed
  chemistry, and removes aggregation kinetics entirely — if a disk with `R > R_c` exists, closure is
  downhill and fast. Readouts: gyration asphericity (0 = flat disk, 1 = sphere) and flood-fill lumen.

  **Defect found and fixed mid-run.** The first version flood-filled merely-*unoccupied* cells and
  reported `lumen = 51–68` on disks that were still provably flat (asphericity 0.08). It was counting
  voids inside the bilayer's own tail core — the same false positive that retired the old `enclosed`
  metric. A lumen now only counts if the enclosed pocket **actually contains water**, which reads 0 on
  a flat disk as it must. Any lumen number produced by this project before 2026-08-11 should be
  checked for this.
- **Fluidity re-run** with the intactness control.
- One marginal legacy vesicle run (290 amphiphiles, L = 23.7).

---

## 8. Questions I would most like a reviewer to attack

1. **Is `bilayer_frac`'s flat threshold (mean dot > 0.90) too strict for a membrane at kT = 1?** If
   so both absolute numbers are depressed and only the ratio means anything. My bound: a planted
   bilayer perturbed at sigma = 0.2 rad still reads 0.93–0.97, so a well-ordered fluctuating membrane
   should clear 0.5 and reading 0.18 is a real deficit. Is that bound sound?
2. **Is the `L ≥ 3.5R` box rule right?** It comes from comparing `4π(R²+(R−d)²)/a` against `2L²/a`.
   If a spanning lamella is still cheaper at that ratio, every self-assembly run here is mis-sized.
3. **Does the planted-disk experiment actually isolate κ?** `k_ang` changes tail stiffness, which may
   also change area per lipid and hence Γ. If κ and Γ move together the scan does not cleanly test
   `R_c = 2κ/Γ`. How would you separate them?
4. **Is measuring `D_∥` on a box-spanning slab the right fluidity test?** Annealing a Y/T junction may
   require a different mode (junction sliding, leaflet rotation) that lateral diffusion does not
   report on. The reviewer's direct T-junction planting test is not yet built.
5. **Should the 2-D or 3-D line be pursued?** 2-D is Vivarium's actual geometry and currently scores
   better, but a 2-D "vesicle" is a closed *ring* — a far less studied object, and planted 2-D rings
   dissolved at 8 of 9 parameter sets (D7). 3-D is where all the published vesicle work lives. This is
   the main open strategic question.

---

## 9. Reproduction

```bash
cd /home/rbao/quorum-thermolife
bazel run //projects/vivarium:_pairing -- --calibrate sl_f28_N12000_s1 big_phi20_nb3_da15_s1
bazel run //projects/vivarium:_geom    -- sl_f28_N12000_s1
bazel run //projects/vivarium:_fluidity -- 12000
bazel run //projects/vivarium:_disk_closure -- 6 29800 12000 0,3,8,15
```

Saved states are in `docs/runs/states/*.npz` (`x`, `species`, `L`, `n_amph`, `nb`, `nh`). Decisions
with metrics and falsification criteria are in `docs/DECISIONS.md`; the ladder is in
`docs/ROADMAP_RESET.md`.
