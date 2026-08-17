# Reviewer prompt: a physics audit found four defects; the negative results may be sampling artefacts

**Date:** 2026-08-17. Worktree `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
Self-contained. Questions in §6.

---

## 0. One paragraph

Vivarium is a strictly transformer-only 2-D/3-D molecular simulator. Its goal is an EMERGENT vesicle.
The force field was rebuilt this week as a single scalar energy whose forces are its exact gradient,
with no orientation term, so that spontaneous curvature cannot be imported. A planted 2-D bilayer ring
is now stable. No vesicle has ever emerged from a dispersed start. A physics audit against both the
old engine and the reference model then found four defects in the new field, three of which are now
fixed, and a fifth problem that calls the negative emergence results into question entirely.

## 1. The force field

Every non-bonded pair contributes

    U_ij = eps * [ core(r/sigma) + well(r/sigma) * chi_ij ]

one energy scale, one length scale, and a symmetric dimensionless 3x3 matrix `chi` over
(head, tail, water). `core` is quadratic in overlap and bounded (DPD form); `well` is a cosine tail
from contact to `rc = 2.5 sigma`. `chi` factors through its eigendecomposition as `chi_ij = q_i . k_j`,
so the content term is a query-key inner product and the whole energy is one unnormalized
distance-penalized attention layer. Molecules are bead chains with 1-2 and 1-3 harmonic bonds.

Gated in CI: forces vs numerical `dU/dx` **1.2e-07**; `chi` as an inner product **3.3e-16**; neighbour
list vs dense reference **exactly 0.0**; isolated pair settles at contact within 0.02 sigma; rotation,
translation, zero-net-force; bending costs energy; bonded pairs excluded; water most cohesive.

## 2. The audit -- four defects, found by reading the three force fields side by side

| | pre-oracle `pack.py` | new `field.py` | oracle YLZ |
|---|---|---|---|
| defined by | forces, by hand | **scalar energy**, F = -dU/dX | scalar energy |
| core | orientation-dependent (contour) | isotropic | isotropic |
| orientation term | `nematic` | **none, deliberate** | full, with `beta` |
| chain stiffness | **1-3 bonds** (`bend_frac`) | **was missing** | 1-2 only |

1. **No chain bending stiffness.** `field.py` had 1-2 bonds only, so its tail was a freely jointed
   chain with zero persistence length. Membrane bending rigidity comes from chain stiffness or
   orientation coupling; this model deliberately has no orientation term, so it had **essentially no
   bending rigidity**. Fixing it changed the lipid a lot -- a 4-tail bilayer went from d = 5.72 to
   **8.00 sigma** because the tails were coiled and are now extended, with area per lipid 1.364 ->
   1.150. Every previously computed sizing is superseded.
2. **Bonded pairs were not excluded** from the non-bonded term, double-counting 1-2 interactions.
3. **`chi` inverted the hydrophobic effect**: tail-tail 1.00 above water-water 0.40. Real CG force
   fields put water highest (MARTINI water-water above alkane-alkane) because the effect is water's
   self-attraction squeezing oil out. Now water 1.00, tail 0.70, demixing condition still satisfied.
   This project's own `pack.py` documents that inversion as the reason its membrane cores stayed wet;
   the new field reintroduced it in a new form.
4. **We ran twice as hot as the reference.** Core/kT matches (171 vs 174) but well-depth/kT was
   2.86 against the oracle's 5.80.

1-3 are fixed and gated. 4 is a run parameter.

## 3. The fifth problem, which may invalidate every negative result

| | dt | steps | reduced time | free-diffusion rms | box crossings |
|---|---|---|---|---|---|
| ours | 2e-4 | 400 000 | **80** | 7.4 sigma | **0.26** |
| oracle | 5e-3 | 1 500 000 | **7 500** | 88.1 sigma | **3.52** |

Our longest run covers a quarter of one box crossing of free diffusion. Coarsening requires aggregates
to MEET. Every emergence run shows the same shape -- lipids condense quickly into many small
aggregates, then the largest cluster stops changing -- which is what under-sampled coarsening looks
like. **The claim that closure does not occur by nucleation is withdrawn.**

The bottleneck is the overdamped driver's timestep. dt = 2e-4 is very conservative: peak force is
about 2 * CORE_HEIGHT = 120, so F*dt = 0.024, far below a bead diameter.

## 4. What is established

* A planted 2-D bilayer ring is stable: 200 000 steps, lumen holding, **shell CV tightening
  monotonically 0.284 -> 0.204**, renders show heads on both surfaces and water inside. Every planted
  ring before the rebuild collapsed to a filled micelle.
* Micelles EMERGE from a dispersed start with genuine head/tail segregation, with no polarity knob and
  no orientation term.
* Excluded volume is real: beads at 0.95-0.99 of contact, against 0.15-0.36 in the old engine. The
  historical "bilayers" were interpenetrating piles scoring 0.837 on shape metrics, and the
  admissibility floor `MIN_PACKING = 0.35` was admitting them by construction. Both retracted and
  fixed.
* The oracle's vesicle is BOUGHT: same N, box, seed, 1.5M steps, `beta = 0` gives 0 vesicles and flat
  sheets, `beta = 0.15` gives 3-4 sustained. `beta` is the spontaneous curvature. So porting the
  angular term would import the answer, which is why this field has no orientation term.
* Measured area per lipid 1.15-1.40 sigma^2 against the oracle's 1.50, so the lipid is dimensionally
  sane.

## 5. What is NOT established

* No vesicle has emerged in 2-D or 3-D -- but see §3.
* Nothing in 3-D at all. A planted 3-D vesicle collapsed, but three planting artefacts were found
  while chasing it (leaflet split by AREA rather than volume; an unfilled lumen; a solvent too dilute
  to pressurise one), so that collapse is uninterpretable.
* None of this is in the served frontend, which still runs the old engine.

## 6. Questions

1. **Is the sampling deficit the whole story?** If we raise dt and run to a comparable reduced time,
   is there reason to expect nucleation to proceed, or is there a separate barrier we are missing?
   What is the right diagnostic to distinguish "too short" from "kinetically blocked" -- a cluster-size
   distribution over time, a nucleation-rate measurement, something else?
2. **How far can dt go for overdamped Brownian dynamics with a bounded quadratic core?** We are at
   F*dt = 0.024. Is there a standard stability criterion for this integrator and core, and does
   raising dt bias the sampled ensemble rather than merely coarsening it?
3. **Is a solvent-free model the honest move?** Explicit water dominates the O(N^2) cost and forced the
   dilute boxes that made 3-D unaffordable. Cooke-Deserno and the oracle are both implicit-solvent.
   The project wants explicit water for its own reasons, but is there a defensible middle -- e.g.
   implicit solvent for phase-behaviour questions, explicit for the final demonstration?
4. **Is chain stiffness enough to give a membrane bending rigidity without an orientation term?** We
   removed the orientation term on principle, since its `beta` IS the spontaneous curvature. Is that
   principled distinction real, or does any model that closes need orientation coupling somewhere --
   in which case our "emergent vs imported" framing is confused and we would like to be told so?
5. **Have we REGRESSED against our own starting point, and how would we tell?** The pre-oracle engine
   (tag `vivarium-pre-oracle`, commit `3a70fce`) produced clean-looking micelles and bilayers -- 35/63
   and 38/63, alignment 0.837. Those are now known to be interpenetrating piles: `packing` 0.36 on a
   planted sheet and 0.13-0.15 condensed, against this project's own scorecard bands of bilayer
   0.71-1.00 and **collapse below 0.35**. Alignment stayed high because it is computed from
   DIRECTIONS, which remain well defined at any density. The new field is at 0.95-0.99 -- correct
   packing -- but its emergent morphology is a percolating tail network rather than clean micelles or
   bilayers. We cannot presently say whether that is a regression, because the new runs differ from
   the old in sampling (0.26 box crossings), lipid (stiff 2-tail vs floppy 3-bead) and temperature all
   at once. What is the right matched comparison, and is "correct packing, messier morphology" the
   expected trade when a too-soft core is fixed?

6. **Is a stable PLANTED vesicle the right target at all?** Simulated vesicles are long-lived
   metastable states, and we have been treating planted-stability as a requirement. Would a
   defensible criterion be emergence plus persistence over a stated window, and if so what window?

## 7. Standing caveat

This project has now withdrawn ten results, and seven were measurement or protocol artefacts rather
than physics: four false HOLLOW verdicts from one centroid lumen detector, a whole family of "working
bilayers" that were interpenetrating piles, a conservativity audit that measured step displacement
instead of force, a degenerate closure metric that scored any blob as closed, a render slab so thick it
turned a hollow shell into a filled ball, and now an under-sampled set of emergence runs. Treat every
number here as provisional unless it has a control or a rendered image behind it. The ones in §1, §2
and §4 do.

## 8. Reproduction

```bash
cd projects/vivarium
bazel run  //projects/vivarium:_field                       # all gates
bazel test //projects/vivarium:test_suite
bazel run  //projects/vivarium:_sizing3d -- 30000 4 3.0     # lipid geometry + sizing prediction
bazel run  //projects/vivarium:_mixture  -- 200000 2 70 0.0 40.0 0.35 0.55 ring   # the stable ring
bazel run  //projects/vivarium:_emerge2d -- 400000 70 28.0 0.17 2                 # emergence, under-sampled
```

Force field `field.py`; audit `docs/PHYSICS_AUDIT.md`; transfer diagnosis
`docs/WHY_THE_ORACLE_DOES_NOT_TRANSFER.md`; oracles `ylz.py`, `bilipid.py`.
