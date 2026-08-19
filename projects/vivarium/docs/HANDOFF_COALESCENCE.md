# Reviewer prompt: two bilayer patches in contact will not reliably merge, at any temperature

**Date:** 2026-08-19. Worktree `/home/rbao/quorum-thermolife`, branch `autoresearch/bilayer-emergence`.
Self-contained. **One question, in §5.**

Raised under a stuck criterion agreed in advance: *the same target failing across many regimes, with
each proposed mechanism subsequently measured and found insufficient.*

---

## 1. The decisive measurement

Two flat two-leaflet patches of 30 lipids each, placed **in direct contact** (diffusion removed from
the question entirely), 15 seeds, 15000 steps. Fraction of trials ending as ONE connected aggregate:

| kT | 0.25 | 0.30 | 0.35 | **0.45** | 0.55 | 0.70 |
|---|---|---|---|---|---|---|
| merged | 0/15 | 1/15 | 3/15 | **7/15** | 5/15 | 4/15 |
| largest frac | 0.559 | 0.656 | 0.651 | 0.761 | 0.716 | 0.704 |

**The curve has a maximum at kT = 0.45 and that maximum is 47%.** Below it the membrane is a gel and
cannot rearrange; above it thermal disruption dominates. Separating the patches makes it worse:
at kT = 0.45, gap 1.0 sigma gives 3/15 and gap 2.5 sigma gives 2/15.

The initial condition is verified by render: two clean two-leaflet slabs, heads on both faces. At
gap 0 they are a single continuous slab, so that arm is a positive control -- and it fails 8 times in
15.

## 2. Why this is decisive rather than another failure

A 2-D ring in this model needs **>= 120 lipids in one aggregate** (measured: planted arcs unroll at
N = 70 and retain a lumen at 120/150/200/300, shell CV falling monotonically
0.370/0.353/0.312/0.218/0.194). Dispersed runs produce aggregates of **10-36 lipids**. Getting from 20
to 120 requires many successive merge events at <= 47% each. The dispersed route is closed by
arithmetic rather than by insufficient sampling.

## 3. The system

2-D coarse-grained amphiphile, explicit solvent, pair energy
`U_ij = eps [core(r/sigma) + well(r/sigma) * chi_ij]`: one energy scale, one length scale, symmetric
3x3 `chi` over (head, tail, water), **no orientation term anywhere**. Molecules are branched -- one
head, two chains -- i.e. phospholipid rather than detergent topology. Inertial Langevin at dt = 8e-3,
validated against the overdamped ensemble over 5 seeds per rung. Forces are `-dU/dX` to 1.2e-07;
`chi` factors as a query-key inner product to 3.3e-16.

Independently measured and holding: line tension **lambda = +40.7 +- 15.7 kT per end** (2.6 sigma), so
closure has ~81 kT to gain; **kappa ~ 90 eps*sigma** from the critical-size threshold; cluster
diffusion **D_M = D_1/N_beads exactly** (alpha = 1, confirmed to 0.98 at M = 64).

## 4. What has been tried and eliminated

* temperature, 0.17 to 0.70 -- gel below, disruption above, coalescence peaking at 47%;
* chain flexibility, `bend_frac` 1.0 to 0.0 -- freely jointed chains are still caged at kT = 0.17;
* tail length 2/4/6 -- P = v/(a0 l) is independent of tail length for a single chain, so this could
  not have worked and did not;
* linear vs branched topology at matched bead count -- morphology differs, closure does not;
* concentration, from spanning-stripe-favoured to very dilute -- gives a network at one end and ~20
  micelles of <= 23 lipids at the other;
* box geometry, stripe-affordable vs ring-affordable;
* run length -- coarsening arrested at 178/200 for 150000 consecutive steps.

## 5. The question

**Is a coarse-grained membrane model whose patches will not reliably coalesce in direct contact
repairable, and if so what is the usual cause?**

Specifically:

1. **Is ~47% coalescence at best diagnostic of a known defect?** Our suspicion is that cohesion strong
   enough to hold a patch is strong enough to freeze it, so no temperature satisfies both. Is that the
   standard reading, or does it more often indicate something else -- too-soft a core allowing
   interdigitation without true fusion, a missing angular term, an over-cohesive solvent competing for
   the heads?
2. **Should merging be reliable in a healthy CG membrane model at all?** We have assumed yes. If real
   patches also merge stochastically at these sizes, our criterion is wrong rather than our model.
3. **Does the absence of any orientation term make this inevitable?** It was omitted deliberately, so
   that spontaneous curvature could not be imported (the reference model produces 0 vesicles at
   beta = 0 and 3-4 at beta = 0.15). An EVEN term such as `(u_i . u_j)^2` would supply rigidity with
   C_0 = 0. Would that plausibly fix coalescence, or is coalescence unrelated to orientation coupling?
4. **Is 2-D the whole problem?** A 3-D shell closes at 40-54 molecules in the reference; our 2-D
   threshold is 120, which is above anything dispersed runs produce. If 2-D closure is simply not
   reachable at attainable aggregate sizes, we would rather retire it than keep instrumenting it.

## 6. Standing caveat

This project has withdrawn roughly twenty results, the large majority measurement or protocol
artefacts rather than physics: five false HOLLOW verdicts, a kappa that was both a bad fit and
dimensionally mislabelled, a 3-D solvent that was never a liquid, MSD contaminated by rigid-body
rotation, three geometry errors in harnesses that planted without rendering, and a 5-seed coalescence
run that over-reported by 2x. Treat every number here as provisional unless it has a control or a
render. The curve in §1 has 15 seeds per point and a rendered initial condition.
