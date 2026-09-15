# Measurement discipline

Lessons paid for in this project, written down so they are not paid for twice. Nineteen rules, each
bought with a defect, several of them introduced by fixes to earlier defects. In every case the
physics was fine and the instrument was wrong.

## The core failure mode

**A metric that cannot fail is not evidence.** Every retracted claim in `RESEARCH_LOG.md` came from a
number that looked reasonable, produced by code that could not have reported otherwise.

Concrete instances:
* `outward` correlated with itself, so its null was +0.669 where 0 was assumed. Three micelle claims
  rested on it.
* `lamellar` ANTI-discriminates: it scores a micelle (0.967) above a bilayer (0.889).
* `py_test(test_suite)` was deleted from BUILD.bazel by a scripted edit. Two "85 tests pass" claims
  were vacuous because an empty grep result was read as success.

## Rules

1. **Validate against BOTH controls.** A planted structure must score high AND a random configuration
   must score at the null. A positive control alone cannot catch a self-correlated statistic.
2. **Require DISCRIMINATION, not a value.** "Plant a bilayer, check it reads success" passes for a
   metric that returns success for everything. Plant every candidate and require each to read as
   ITSELF: bilayer vs micelle is separated only by `align`, micelle vs vesicle only by `hollow`.
3. **Verify the test can fail.** Reintroduce the bug and watch the test trip. Three successive
   versions of the aggregate-separation test passed with the known-bad cutoff still in place, because
   the geometry never actually straddled it.
4. **Derive constants, do not choose them.** The cluster cutoff was wrong in BOTH directions within
   hours: 2.2 merged distinct micelles, 1.4 split a bilayer's leaflets. It is now `1.6 x contact
   distance`, computed from the per-species radii.
5. **Look at the structure whenever a claim matters.** Every time an image or radial profile was
   consulted here it CONTRADICTED the scalar: a "SLAB" that was a droplet, an "aspect 0.189" that was
   a 23-lipid fragment, a "VESICLE" that was four separate micelles.
6. **Check the molecule before any order parameter.** Order parameters are computed from head/tail
   positions, so a deformed molecule makes all of them meaningless. Print bond length beside every
   structural claim.
7. **Disqualify, do not interpret.** If the molecule is deformed, the integrator is overshooting, or
   the aggregate is fragmented, refuse to report structure rather than reporting it with a caveat.
8. **Report the ROOT CAUSE, not its consequence.** A torn molecule also fragments its cluster; saying
   "fragmented" hides the tear.
9. **Periodic geometry goes through ONE chokepoint.** Raw coordinate arithmetic on a periodic system
   silently produces garbage: bond lengths of 13.3 in a box of 10 sent three diagnoses down the wrong
   path. Unwrap by BFS over the connectivity graph; a single reference only works within L/2.
10. **A reference structure must fit its box.** A spanning bilayer needs half-width above the membrane
    thickness or minimum image folds the leaflets together; a finite structure needs diameter < L/2 or
    the far side wraps onto the near side. Both silently invalidated calibrations here.
11. **Know each metric's domain.** `hollow` is a RADIAL decomposition and is meaningless on a slab
    (it read 22.27 on a planted bilayer). `edge` needs explicit solvent and scales with water density,
    so it is only readable RELATIVE to a control.
12. **State the limits you cannot tune away.** Unwrapping is ill-defined for a structure that
    percolates the box. Contact-graph clustering cannot separate aggregates closer than ~1.5 units.
    Record these rather than picking parameters that hide them.

## The loop that works

    derive the metric from the mechanism  ->  plant every candidate structure  ->  require
    discrimination between them  ->  verify each test fails when the bug returns  ->  run  ->
    render an image before believing the number  ->  disqualify anything inadmissible

A mechanism-derived single-axis test outperformed multi-parameter search badly here: a 60-config and
a 120-config search produced one usable number between them, while a four-point sweep chosen from the
stage-1 driver produced the first real signal.

## Rule 13 — calibrate a threshold against EVERY structure it will judge, not one

`MIN_PACKING` was fitted to a planted bilayer (1.000) and then applied to micelles. A micelle cannot
reach a bilayer's packing BY GEOMETRY: its lipids converge radially, so the inner tail beads sit
closer than contact by construction. The gate therefore rejected real micelles as "collapsed", and a
correct result was called a failure twice before the reference was built that exposed it.

    spanning bilayer, planted at contact   1.000
    spanning bilayer, relaxed              0.713
    MICELLE, planted                       0.683
    MICELLE, relaxed                       0.436   <- tightest LEGITIMATE structure
    genuine collapse                       0.150

The same error repeated with `MIN_CLUSTER_FRAC`, which demands one aggregate hold 60% of the lipids:
correct for a bilayer or vesicle, WRONG for a micelle phase, where many small aggregates IS the
answer. Both guards were bilayer-shaped. Before trusting any threshold, measure it on every phase it
might see, and expect the phases to disagree.

## Rule 14 — render at TRUE bead radius

A fixed pixel radius makes an interpenetrating pile look cleanly resolved. That is precisely how a
collapse passed for a structure: the published micelle figure drew beads at 3.6-4.5 px regardless of
scale, so overlap was invisible either way. Draw circles at sigma scaled by the view, and overlap
shows as overlap.

## Rule 15 — the numbers can be ambiguous in BOTH directions; the image resolves it

The finite-ribbon result could not have been established from metrics: `align` 0.73 is consistent
with a bilayer ribbon AND with a dense pile, and `packing` 0.452 sits a hair above the micelle floor
of 0.436. Two numbers, both ambiguous. The head-tail-tail-head layering in the render is not. This is
the case the image-plus-metrics-plus-reference protocol exists for.

## Rule 16 — check the STRUCTURE is physically possible for the molecule before blaming the run

A planted bilayer that dissolves into micelles is not a tuning failure. In nature bilayers do not do
that; DETERGENTS dissolve bilayers into micelles, and that is the standard way membranes are
solubilised in the laboratory. So the observation identifies the MOLECULE, not the parameters: an
amphiphile with packing parameter P = v/(a0*l) < 1/3 forms micelles and solubilises membranes, and no
annealing schedule or run length will make it build one. Every kinetic intervention tried against
this plateaued, which is what a thermodynamic constraint looks like from inside a parameter search.

Ask first whether the target phase is REACHABLE for this molecule's geometry. If it is not, the
search is over before it starts.

---

*Rules 17–19 added 2026-09-13, from the MLP many-body work. **Rule 16 was confirmed in the same
session and is worth re-reading first**: G5 raised head area and the bilayer became micelles, exactly
as Rule 16 predicts for `P = v/(a0*l) < 1/3`. The result was already written down here three weeks
before it was measured.*

## Rule 17 — a free parameter must be calibrated against the descriptor it divides

`ShapeMLP` used `n_ref = 6.0`, registered as "the close-packed 2-D coordination number — geometry, not
a fit". The descriptor it divides is a sum of smooth kernel weights, not a neighbour count: at the real
head spacing the kernel returns 0.107, so two neighbours score **0.21, not 2**. And a 2-D leaflet is a
*line*, so the count is 2, not 6. Measured coordination: **0.207 against an `n_ref` of 6.0**.

The whole term therefore evaluated to `1.2414` for every bead in every state, with **0.4 % spread** — a
uniform inflation, not a modulation. **Two registered experiments reported a physics null for a term
that was a constant**, and the descriptor had been changed from all-lipid to head-only in between
without anyone re-deriving the reference.

The guard: `manybody.assert_calibrated` raises when the descriptor's mean sits more than 4× from
`n_ref`, and the harness calls it at step 0, before spending CPU-hours on a constant. Neither modulator
has a default `n_ref` any more — a default is how the stale value survived the change of descriptor.

## Rule 18 — register a second criterion the experiment can fail BY WINNING

The curl experiment scored a single number, `aspect` — validated, separating flat (0.002) from a ring
(1.000). One run returned **0.5997 against a 0.45 threshold**: a clean pass.

The state was **three micelles**. Four aggregates of 110/100/60/10 beads, roundness 0.478, where one
intact ribbon is ~280 beads in a single cluster reading 0.002. A scattered set of blobs is isotropic,
so the metric rose for the opposite of the reason it was built to detect.

It was caught because an `intact` clause — largest aggregate ≥ 90 % of the lipids — had been registered
**before any data existed**, explicitly as the criterion the experiment could fail by winning. Without
it, that row enters the record as the project's first membrane curl on a protocol carrying five nulls.

A validated metric is not enough. The question to ask at registration time is: *what else could make
this number move, and what second check would separate it?*

## Rule 19 — measure throughput at the concurrency you intend to use

The sweep ran 24 workers because `nproc` reports 32. The box has **16 physical cores** with 2 threads
each. Measured on identical 300 000-step runs: **11 662 s/run at 24-way, ~3 720 s at 12-way — 1.53×
the throughput on half the workers.** Three hours ran at ~65 % of achievable speed.

This is the fourth cost-model error recorded here. The rule is the same every time: measure ONE run at
the concurrency you intend to use, before planning around it.
