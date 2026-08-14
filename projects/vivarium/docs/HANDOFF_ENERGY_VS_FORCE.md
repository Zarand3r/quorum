# Handoff: the oracle emerges vesicles in minutes; porting it into Vivarium keeps failing. Why?

**Date:** 2026-08-14. **Worktree:** `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
Self-contained. Background in `docs/RESULTS.md`; not required to answer §5.

**Standing instruction:** be adversarial. Seven results have been withdrawn in this project, four of
them measurement artefacts rather than physics. Assume any positive claim is weaker than it sounds.

---

## 1. The situation in one paragraph

Two reference models produce vesicles from a random start: stock LAMMPS `pair_style ylz` (~3 min) and
our own reimplementation `bilipid.py`, a two-species head/tail amphiphile (94-molecule shell, heads
outward 1.000, gradient-checked at 1.2e-8). Vivarium -- the actual transformer-style engine -- does
not, despite now containing the same angular term, correctly differentiated and verified against
numerical gradients at 2.2e-9. This document is about that gap.

## 2. The structural difference we think matters most

`SPEC.md` line 21 specifies an **energy model**: "transformer as a force field, dynamics =
`-grad_X E_theta + J`".

`pack.py` contains **zero** methods named `energy`. Forces are assembled by hand:

    force = attract*A + repel*R
    force = force + cohesion*C
    force = force + curvature_force
    force = force + _extra_force(...)

The oracle does the opposite: `ylz.py` and `bilipid.py` each define one scalar `energy()` and
differentiate it, so force and torque fall out of the same derivative and are automatically
consistent.

Three consequences, all of which bit us:

1. **Every term's gradient is hand-derived.** We derived one and made three errors -- a pair sum
   subtracting its own transpose, beads taking `g_c/2` where the centre is a mean over all `nb`
   beads, and a missing `1/nt` from the tail centroid. The numerical check caught them at 2.5
   against a target of 1e-9. In an energy model none of those errors are expressible.
2. **Orientation-dependent weights silently produce no torque.** Multiplying the attraction weight
   `g` by an orientation factor *looks* like applying orientation physics. It is not: Vivarium's
   `force_i = -sum_j g_ij * dirn_ij` treats `g` as a constant coefficient, so there is no tangential
   force and no couple. Measured in vacuum, switching such a weight on in EITHER sign degraded heads
   outward from 1.000 to 0.44-0.60 -- it scrambled an ordering the electrostatics had produced. The
   pre-existing `nematic` weight has the identical defect and has therefore never worked either
   (it has never been enabled in a shipped configuration, so this was never exposed).
3. **Nothing guarantees the total force is a gradient of anything.** "Conservative" in `pack.py`
   means `F_ij = -F_ji`, which is Newton's third law, not curl-free. That is fine while every weight
   depends only on distance, and silently wrong the moment one depends on orientation.

**So the oracle cannot be "ported"; it has to be re-derived into a different formalism, by hand, per
term.** Roughly twenty lines of physics have taken days for this reason.

## 3. What is verified working

* **The angular form.** `a = q + beta*p - beta^2` with `q = u_i.u_j - (u_i.r_hat)(u_j.r_hat)` and
  `p = (u_i - u_j).r_hat`. In the symmetric-splay geometry this is exactly `1 - (sin(theta)+beta)^2`
  (identity holds to 4e-16), so `max a = 1` for every beta while the optimum moves to
  `sin(theta*) = -beta`. Spontaneous curvature therefore shifts the preferred geometry without
  deepening the well. Locked by tests.
* **The differentiated force in Vivarium.** `_curvature_pot_and_force` computes
  `U = sum_{i<j} bend*env(r)*(1 - a)` over molecular centres and returns `-dU/dx` on the beads,
  including the tangential term and the couple. Verified at **2.2e-9**.
* **Sign of the penalty.** `a <= 1`, so misalignment must COST: `U = bend*env*(1-a) >= 0`, zero at
  the preferred splay. The first version had it inverted (`U <= 0` everywhere, so misaligned pairs
  gained attraction) and collapsed the aggregate.
* **Vivarium's baseline.** At `curvature = 0` the engine reproduces its pre-oracle behaviour exactly
  (tag `vivarium-pre-oracle`, commit `3a70fce`): micelles 35/63 lipids at `attract=1.0`, bilayer
  38/63 at `attract=1.5`, both from a clumped start.

## 4. What has been tried and has not produced a vesicle

| attempt | result |
|---|---|
| curvature as a multiplicative weight | no torque; heads outward degraded 1.00 -> 0.44-0.60 in either sign |
| weight evaluated bead-wise vs molecule-wise | no difference (0.51-0.60); hypothesis falsified |
| sign flip of `r_hat` | ring geometry says `p = +0.26` for heads-outward, so the sign was right; flipping did not help |
| hydration 4 / 10 / 20 waters per lipid | heads outward 0.42 / 0.65 / 0.12 -- NON-monotonic, so hydration is not a clean variable |
| vacuum (no solvent) | collapses at EVERY curvature including 0, so it cannot discriminate |
| differentiated force, penalty sign correct | heads outward 0.94-1.00 preserved, but still collapsed or filled |

Two facts constrain any explanation. Vivarium's solvent is clustered in every hydrated run
(homogeneity 1.5-4.3 against a random-point null of 0.38), so the lipids sit in an emulsion rather
than a continuous phase -- though we accept the earlier reviewer's point that a Poisson null is the
wrong comparison for an interacting liquid, and the matched pure-solvent control has **not** been
run. And in vacuum the aggregate collapses even with no curvature at all, so nothing but `repel`
maintains spacing there.

## 5. Questions

1. **Is the energy-model refactor the right next move, or is there a cheaper diagnostic?** Rewriting
   `pack.py`'s forces as `-grad E` where `E` is a sum of scalar terms would make the oracle port as a
   single term, and would make `nematic` functional as a side effect. It also breaks byte-identity
   (summation order) and touches every force path. Is there a way to answer "can Vivarium support a
   vesicle at all" without paying that first?
2. **Is a curvature term even the right mechanism here, given the engine already has electrostatics?**
   In vacuum at `curvature = 0`, head-head repulsion alone gives heads outward 1.000 and a clean
   micelle. Perhaps the missing ingredient for a HOLLOW structure is not spontaneous curvature but
   something that prevents the tail core from filling -- tail-tail excluded volume, or a chain length
   that cannot reach the centre. In the reference model the shell is one particle thick by
   construction, which sidesteps the question entirely.
3. **Should the solvent be fixed first?** We keep deferring the pure-solvent control. If Vivarium's
   water cannot form a continuous phase at any density this engine can afford, then no membrane
   result in solvent is interpretable, and the honest move is vacuum plus an explicit statement of
   that limitation.
4. **Is 63 lipids simply too few for a 2-D vesicle?** A closed ring needs enough molecules to
   surround a lumen larger than the molecular length. We have never computed that threshold for
   Vivarium's geometry the way we did for the reference (where it decided everything).

## 6. Reproduction

```bash
cd projects/vivarium
bazel run //projects/vivarium:_cgrad                       # curvature force vs numerical gradient
bazel run //projects/vivarium:_viv_vacuum -- 20000         # vacuum sweep, both signs
bazel run //projects/vivarium:_viv_hunt   -- 20000 10 0.15,0.30   # hydrated
bazel run //projects/vivarium:_viv_morph  -- 20000         # micelle + bilayer baselines
bazel test //projects/vivarium:test_suite
```

Engine `pack.py` (`curvature`, `bend`, `_axis_signed`, `_curvature_pot_and_force`); builder
`bicelle2d.build`; renderer `fig2d.render`; oracle `ylz.py`, `bilipid.py`, `attention_ylz.py`.
