# Reviewer prompt: Vivarium vesicle transfer — one gate passed, two experiments invalidated by their own instruments

**Date:** 2026-08-14. **Worktree:** `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
Self-contained. You do not need prior context to answer §5.

---

## 0. What you are being asked

Two reference systems already emerge vesicles: stock LAMMPS `pair_style ylz` (~3 min) and our own
`bilipid.py` (two-species head/tail, 94-molecule shell, heads outward 1.000, gradient check 1.2e-8).
Vivarium — the transformer-style engine, explicit water, strict 2-D — does not.

We ran the prioritised diagnostic programme. **Priority 1 passed cleanly. Priorities 2 and 4 each
produced a result that turned out to be an artefact of its own measurement, caught only by a control
or a render.** We want your judgement on what to run next and whether the architecture verdict can
yet be reached.

---

## 1. Priority 1 — pure-solvent gate: **PASS**

250 water alone, at exactly `bicelle2d.build`'s density, box, temperature, timestep, damping,
repulsion and water–water interaction. 40 000 steps.

| measure | result | pass? |
|---|---|---|
| `g(r)` first peak | stationary, 4.84% drift over 2nd half, peak at r = 0.95 | yes |
| MSD | still rising, +1.241 over 2nd half | yes |
| `S(q_min)` | 1.01× over 2nd half | yes — **no growing low-q demixing mode** |
| deep-overlap fraction (nn < 0.5·contact) | +0.040 | yes |
| largest connected water domain | +0.000 | yes |

**This retracts an earlier claim of ours that Vivarium's solvent was broken.** That came from
cell-occupancy variance ≈ 4 against a *Poisson* null of 0.38 — an invalid comparison for an
interacting liquid, since the first peak of `g(r)` *is* non-uniformity. Hydrated runs are
interpretable. The solvent is not the blocker.

One instrument was corrected mid-gate: "penetration" first returned the mean neighbour count within
contact (≈ 8.8 against an ideal-gas 1.6 — i.e. the first coordination shell) and was judged against
a fraction-sized threshold, failing the gate on ordinary liquid structure.

## 2. Priority 2 — planted bilayer rings at curvature 0: **INCONCLUSIVE**

Rings planted with correct two-leaflet geometry (outer heads out, inner heads in, shared tail core),
curvature = 0, 20 000 steps.

| N | inner leaflet | lumen water | largest cluster | render shows | metric said |
|---|---|---|---|---|---|
| 50 | 12 → 0 | 2 → 0 | intact | filled micelle | opened/lost ✔ |
| 65 | 20 → 17 | 12 → 0 | intact | **filled micelle** | HOLLOW ✘ |
| 80 | 27 → 38 | 26 → 64 | 57% | **two micelles** | HOLLOW ✘ |
| 100 | 37 → 34 | 49 → 30 | 25% | **fragmented** | HOLLOW ✘ |
| 120 | 47 → 40 | 93 → 44 | 22% | **fragmented** | HOLLOW ✘ |

**Four false HOLLOW verdicts, every one caught by looking at the render.** Two independent bugs:

* `lumen_r = tail_core_median − molecule_length` is positive for **any** aggregate whose tail median
  exceeds the molecular length, filled or not. That produced the N=65 false positive.
* When a ring fragments, the centroid lands **between** the pieces, so the water-filled gap reads as
  a lumen — N=80's "64 waters" is inter-fragment solvent.

Both now gated: a lumen requires ≥ 5 waters **and** ≥ 90% of lipids in one connected cluster.

**Also confounded by our own setup:** we held `bound = 16.0` fixed while N varied, so token density
ran **0.39–0.82** against the validated **0.907**, most dilute exactly where rings are largest. The
fragmentation at N ≥ 80 is therefore not attributable to ring physics.

What we think survives: N = 50 and N = 65 stayed connected and became filled micelles, so the
minimum stable ring is plausibly above 65 — consistent with a historical ~81 — but we are not
asserting it until the sweep is rerun at matched density.

Incidental: `fig2d`'s `align` reads **0.000** on a *correctly planted* bilayer ring (reference
"bilayer = 1.00"). That scalar is unusable for ring geometry.

## 3. Priority 4 — conservativeness audit: **RETRACTED IN FULL**

We measured `eta_curl = ||J − Jᵀ|| / ||J||` per deterministic term and got 0.33–0.91 for repel,
attract, polarity, cohesion and curvature — apparently "not a gradient field" almost everywhere.

**Every one of those numbers is withdrawn.** `curvature` was separately verified against its own
scalar at **2.2e-9**, so it must be conservative, yet the audit gave it 0.9111. Calibrating on that
same force:

| measurement of the *same* curvature force | eta_curl |
|---|---|
| read directly from its analytic form | **0.000000** |
| via one-step `step()` displacement (what the audit did) | **1.413797** |

The audit approximated force by the displacement of one `step()` from rest. That is not the force
field: it also contains momentum integration, the morph/contour update, bond forces that were never
disabled, and the per-particle speed cap. (`nematic` reading exactly 0.0000 was the other tell — with
`attract = 0` its weight multiplies nothing.)

**A valid audit requires `pack.py` to expose the assembled deterministic force without integrating.
`step()` computes `force` internally and returns nothing, so that accessor does not exist.** Whether
the `−∇E` refactor must touch every force family or only some is therefore **still open**.

## 4. What is established

* The solvent is a stationary liquid and is **not** the blocker. (measured)
* The curvature term is a genuine conservative force: `eta_curl = 0.000000`, gradient 2.2e-9. (measured)
* `bilipid.py` — same two-species representation Vivarium uses — **does** make vesicles. (measured)
* Vivarium at curvature 0 reproduces its pre-oracle phenotypes: micelles 35/63 at `attract=1.0`,
  bilayer 38/63 at `attract=1.5`. Tagged `vivarium-pre-oracle` (`3a70fce`). (measured)
* Small planted rings (50, 65) collapse to filled micelles. (measured, renders)
* Everything about rings ≥ 80, and every conservativeness verdict, is **not** established.

## 5. Questions

1. **Is the ring sweep worth rerunning at matched density, or is the planted-ring test the wrong
   assay entirely?** An alternative is Priority 3 — the "oracle force island": run `bilipid.py`'s
   complete scalar energy on Vivarium coordinates with native lipid–lipid forces disabled, which
   cleanly separates engine failure from force-field failure. We have not run it. Which first?
2. **Given four false positives from one lumen metric, do you trust the corrected version?** The gate
   is now ≥ 5 lumen waters plus ≥ 90% single-cluster. Is there a better assay — a radial `P(r,s)`
   two-population test, or something not centroid-based, since the centroid is what failed?
3. **Is there a way to audit conservativeness without adding a force accessor to `pack.py`?** Adding
   one is small but touches the hot path. If not, is the accessor worth it purely as instrumentation?
4. **Does the evidence yet justify the `−∇E` refactor?** We think **no** — the only term we can
   currently vouch for is conservative, and the audit that suggested otherwise was invalid. But the
   argument for the refactor was never really conservativeness; it was that hand-derived gradients
   are error-prone (we made three in one function). Is "the derivation is error-prone" sufficient
   justification on its own?
5. **Is 2-D closure even the right target?** No open-source 2-D reference we found closes a ring;
   LAMMPS's own 2-D example produces branched bilayer strips, exactly like ours. Should Vivarium's
   vesicle milestone move to 3-D, where both oracles work?

## 6. Reproduction

```bash
cd projects/vivarium
bazel run //projects/vivarium:_solvent_gate -- 40000        # Priority 1, passes
bazel run //projects/vivarium:_ring_sweep   -- 20000 "50,65,80,100,120" 0.0
bazel run //projects/vivarium:_curl_cal                     # shows the audit instrument is invalid
bazel run //projects/vivarium:_cgrad                        # curvature force vs numerical gradient
bazel test //projects/vivarium:test_suite
```

Engine `pack.py`; builder `bicelle2d.build`; renderer `fig2d.render`; oracles `ylz.py`, `bilipid.py`.

**Standing note:** eight results have now been withdrawn in this project, and **five** were
measurement artefacts rather than physics. Treat every positive number here as provisional unless it
has a control or a render behind it.
