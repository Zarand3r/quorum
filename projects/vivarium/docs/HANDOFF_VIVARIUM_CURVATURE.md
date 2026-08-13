# Handoff: Vivarium makes micelles and bilayers but not vesicles; the closure term collapses it

**Date:** 2026-08-13. **Worktree:** `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
Self-contained. Background in `docs/RESULTS.md` and `docs/ROADMAP_V2.md`, not required to answer §4.

**Standing instruction:** be adversarial about over-claiming. Six results have been withdrawn in this
project, three of them this session, and all three were MEASUREMENT artifacts rather than physics.

---

## 1. Where we are

Outside Vivarium, in reference models, this is solved. A solvent-free membrane potential (Yuan-Li-
Zhang, stock LAMMPS `pair_style ylz`) self-assembles vesicles in ~3 minutes; we reproduced that in
our own engine, proved its energy is EXACTLY one unnormalized distance-penalized attention layer
(relative error 1.6e-16), replaced its divergent `r^-4` core with a bounded one and still got
vesicles, and carried it to a two-species head/tail representation that closes with heads outward
1.000. Those results are locked by tests.

Inside Vivarium -- the actual transformer-style engine, with explicit water -- we do not have a
vesicle. This document is about that gap.

## 2. What Vivarium does now

`bicelle2d.build`, 63 lipids (1 head + 2 tails), 250 explicit waters, 2-D, clumped start, 20k steps.
The only new parameter is `curvature`, the spontaneous-curvature term described in §3.

| attract | curvature | largest cluster | solvent homogeneity | outcome |
|---|---|---|---|---|
| 1.0 | 0.00 | 35 / 63 | 4.29 | **micelles** |
| 1.5 | 0.00 | 38 / 63 | 3.69 | **bilayer** |
| 1.5 | 0.15 | **63 / 63** | 3.77 | **COLLAPSED** -- disqualified, nearest non-bonded neighbour at 0.18 of contact |

Random-null solvent homogeneity for 250 points on this grid is **0.38**.

Two things to notice. Curvature does something large and in the right direction -- it takes the
aggregate from 38 of 63 lipids to all 63, i.e. it unifies the membrane. And it then destroys it: the
harness's own disqualification criterion fires because non-bonded beads sit at 0.18 of contact
distance, which is interpenetration, not a membrane.

## 3. The term

Vivarium already had a `nematic` weight using `(u_i . u_j)^2`. That square is deliberately
director-free, so it can align leaflets but can never prefer one face of a membrane over the other,
which is why nothing here ever closed. Closure needs a term ODD under `u -> -u`. We added

    w_ij *= 1 + curvature * (u_i - u_j) . r_hat_ij

with `u` pointing from the tail centre toward the head, applied to the attraction weight, on
lipid-lipid pairs only. It is symmetric under i<->j (both the vector difference and r_hat flip), so
momentum is conserved. Verified live: `max|dX| = 4.83` between curvature 0 and 0.2, byte-identical
base case without molecules, cost 0.48 ms/step off and 0.55 ms/step on.

The same functional form, in the reference models, is what turns an open flat disc into a closed
vesicle at exactly these magnitudes (0 -> open disc, 0.1 -> vesicle).

## 4. The question

**Our hypothesis, which we would like challenged: the term as implemented raises NET cohesion rather
than redistributing it, so it collapses the aggregate instead of curving it.**

`(u_i - u_j) . r_hat` lies in [-2, 2], so the factor lies in [1 - 2c, 1 + 2c]. At curvature 0.15 that
is up to a 30% boost to an attraction already at 1.5. Nothing scales the repulsion to match, so the
membrane gains cohesion and interpenetrates. In the reference model the analogous angular factor
multiplies an attractive well that is balanced by a strong repulsive core; Vivarium's excluded volume
is a separate, unscaled head.

Specific questions:

1. **Should the curvature factor be made mean-zero over neighbours**, so it redistributes attraction
   by orientation without changing its total? Something like subtracting the neighbourhood mean of
   the projection before applying it. Does that preserve the closure physics, or is the net cohesion
   increase part of why closure works in the reference?
2. **Or should curvature not multiply the attraction at all**, and instead enter as its own additive
   force -- a couple on the molecular axis -- leaving the attraction magnitude untouched? That is
   closer to what the term physically is (a preferred splay), but it is no longer a single attention
   weight, which matters for the transformer constraint.
3. **Is there a curvature magnitude that curves without collapsing?** We have 0.15 (collapse) and 0.0
   (no closure) at attract 1.5; 0.30 is running. If the window is narrow, that itself is informative.
4. **Should the repulsion be scaled by the same factor** to keep the balance, i.e. apply the weight
   to the net pair interaction rather than to the attractive head alone?

## 5. The other blocker, which may be prior to all of this

**Vivarium's solvent is heavily clustered in every run, including the baseline**: homogeneity 3.69 to
4.29 against a random null of 0.38, an order of magnitude. This is NOT caused by curvature -- it is
identical at curvature 0.

This matters because an earlier phase of this project was invalidated wholesale for exactly this
reason: structural results measured while the solvent was condensing were later withdrawn, and the
standing rule since then is that no lipid result counts unless a matched pure-solvent control passes.
We have not run that control on the current configuration.

**Question 5: should the solvent be fixed before any curvature tuning?** Our instinct is yes -- a
membrane measured in a collapsing solvent is not evidence -- but that is a large detour and we would
like a second opinion on whether homogeneity ~4 is disqualifying or merely untidy for a 2-D system at
this density.

## 6. Reproduction

```bash
cd projects/vivarium
bazel run //projects/vivarium:_viv_morph -- 20000     # the table in section 2
bazel test //projects/vivarium:test_suite             # includes tests/test_curvature.py
bazel run //projects/vivarium:serve -- --polar --port 8899   # live viewer, curvature slider
```

Engine: `pack.py` (`curvature`, `_axis_signed`, `_curvature_weight`). Builder: `bicelle2d.build`.
Renderer: `fig2d.render`.

## 7. Three measurement artifacts from this session, listed because the pattern is the point

Each initially looked like a physics result:

* **M1 "cannot reproduce the vesicle"** -- diagnosed from a trajectory truncated at 450k steps, with
  a four-cause dynamical explanation written up. It closes at 1.05M. Nothing was wrong.
* **head orientation 0.51, "chemically ambivalent"** -- positions came from one clustering pass and
  orientations from another with a different ordering, so unrelated molecules were compared. True
  value 1.000.
* **"curvature collapses the solvent"** -- from renders. `fig2d.render` auto-scales on the lipid
  cluster and minimum-images the water, so a compact aggregate zooms in and makes uniform water look
  clumped. Measured, homogeneity was 2.71 vs 2.99 -- no difference. A fix was shipped on this false
  premise (it happens to be correct for independent reasons).

The collapse reported in §2 is NOT one of these: it is the harness's own disqualification criterion
firing on a measured interbead distance, not an impression from a picture.
