# The knob ladder — replace every hand-set affinity in the 2-D vesicle model, one at a time

**Registered 2026-09-02, before any rung is run.** 2-D only. The 3-D track stays parked behind
`docs/REVIEWER_HANDOFF_2026-08-31.md`.

## Objective

The 2-D model emerges a vesicle. Its chemistry is six hand-set pair affinities — numbers a person
chose. The claim we want is that vesicles follow from **physics and geometry**, so every one of those
six must either be **replaced by a geometric or thermodynamic mechanism** or **shown to be
irreducible**. Replace, not delete: deleting a term and watching the system still clump proves
nothing, because clumping is not the target behaviour.

## Why the endpoint changes

Every knob test so far was scored on **self-assembly vesicle rate**, which is 2/18 ~ 11%. At six seeds
per arm that design cannot resolve anything: the previous rung returned 0/6 vs 0/6, and 0/6 is the
*expected* result for both arms. Roughly 300 seeds per arm would be needed to detect even a doubling.
Two full-length runs were spent learning this.

The project already has a far better endpoint. Closure is controlled by the ribbon's **end-to-end
gap** — the one reaction coordinate here that has ever been validated — and it gives a steep,
well-powered dose-response (`docs/RESULTS.md`):

| end-gap | closed |
|---|---|
| 3.4 sigma | 5/5 |
| 6.7 sigma | 4/5 |
| 10.1 sigma | 1/10 |

Fisher on the two extremes is p = 0.0016. Closure is also *fast* — 4/5 seeds closed by step 10,000
against a 300,000 budget — so each run is ~30x cheaper than a self-assembly run. This converts a rare
event into a graded measurement, which is the only way to test six knobs in one session.

**Geometry of the assay, re-derived and checked.** `_mixture._plant_ring(span=s)` puts `n` lipids on
an arc at `R_mid = n*lat/(4*pi*s)`, `lat = 2` for a branched 4-tail lipid, so the missing sector's arc
length is

    gap = 2*pi*R_mid*(1 - s) = (n*lat/2) * (1 - s)/s

Checked against the two radii published with the table: N=70 at gap 10.1 gives R_mid 12.75 (published
12.8); N=300 at gap 10.1 gives 49.35 (published 49.3). The harness inverts this to place a requested
gap.

## Instrument gate — runs BEFORE any rung, and can fail

The assay is only usable if it reproduces the published dose-response **under production chemistry**.

    GATE I: closure at 3.4 sigma  >=  4/5      AND
            closure at 10.1 sigma <=  3/10     AND
            Fisher one-sided p    <=  0.05

`closed` is fixed here as **`n_enclosed >= 1` at any checkpoint** — the detector the published table
names. `vesicle_call` is recorded alongside but is NOT the gate; choosing between them after seeing
data is exactly the yardstick failure this project has already committed once.

If GATE I fails, no rung is run and the session's finding is that the reaction coordinate does not
reproduce — which is itself a result worth having, since two documents depend on it.

## The ladder

`chi_TT = 0.70` is **kept and declared irreducible**: it is dispersion between alkane-like tails, the
one cohesive interaction, and there is no geometry that can stand in for "matter attracts". A model
with zero attractions has no condensed phase. Removing it is not a knob reduction, it is deleting the
physics. This is stated now so it cannot later look like the one term we happened not to test.

| rung | knob | current | replaced by | mechanism |
|---|---|---|---|---|
| 1 | `chi_HT` | -0.25 | 0.00, with `sigma_head` < `sigma_tail` | amphiphilicity as **geometry** — a head that is a different size, not a head that dislikes tails |
| 2 | `chi_HH` | +0.20 | 0.00 | heads keep excluded volume only |
| 3 | `chi_HW` | +0.75 | solvent-averaged | Flory-Huggins |
| 4 | `chi_TW` | 0.00 | solvent-averaged | Flory-Huggins |
| 5 | `chi_WW` | +0.50 | solvent-averaged | Flory-Huggins |
| 6 | explicit water | phi = 0.55 | removed | the hydrophobic effect becomes an **effective** tail-tail attraction |

Rungs 3-6 are one physical idea applied stepwise. `field.solvent_averaged_chi` already implements it:
`eff[i,j] = chi[i,j] + chi[WW] - chi[i,W] - chi[j,W]`. That is the standard reduction of a solvent to
an effective interaction, not a deletion — the water terms reappear inside `chi_TT_eff`. Rungs 3-5
zero each water term singly (so a single-variable A/B exists for each), rung 6 does the full
substitution and removes the solvent.

## Per-rung protocol

Each rung is a single-variable A/B against the rung below it, **not** against production, so the
ladder composes:

- arms: `previous rung's chemistry` vs `previous + this replacement`
- gaps: 3.4 and 10.1 sigma, 10 seeds per gap per arm (40 runs per rung)
- steps: 300,000, checkpoint every 10,000
- fresh seeds per rung, never reused across rungs

```
RUNG PASSES iff   closure(3.4) is not degraded:  arm >= 6/10  AND  Fisher vs baseline p > 0.05
            AND   the coordinate still discriminates: closure(3.4) > closure(10.1), Fisher p <= 0.05
```

The second clause is the criterion **we can fail by winning**. A replacement that made everything
close at every gap would pass the first clause and fail this one, and it would deserve to: it would
have destroyed the reaction coordinate rather than preserved the physics. A knob replacement must keep
the *shape* of the dose-response, not merely keep the numbers high.

## Secondary, reported but never gating

Self-assembly aggregation quality at the end of each rung, so a replacement that preserves closure but
destroys assembly is visible. Not gating, because it is the low-power endpoint this spec exists to
stop relying on.

## What each outcome means, written before the data

- **All six rungs pass.** The 2-D vesicle needs one attraction (tail-tail) plus geometry. That is a
  real claim and the strongest available from this project.
- **A rung fails.** That knob is load-bearing and we have located *which* physics is not being
  captured by geometry. More informative than a pass; the ladder stops there and the failure is
  characterised.
- **GATE I fails.** The reaction coordinate does not reproduce. Everything resting on the gap result
  needs re-examination before any knob work continues.
- **Rungs pass but assembly collapses.** Closure and assembly need different chemistry; the
  reduction is real for one and not the other, and must be reported that way.

## Threat register

- `n_enclosed` is a **2-D** detector and is broken in 3-D. This spec is 2-D only, inside its
  validated domain.
- The arc assay tests **closure given a membrane**, not assembly-then-closure. Stated as a scope
  limit, not worked around; the secondary endpoint is the partial cover.
- The assay hands the system its curvature. It therefore cannot show that curvature *emerges* — only
  that a knob replacement preserves closure once curvature exists. Both this and the point above mean
  a full pass supports "the chemistry reduces", NOT "vesicles emerge from geometry alone".
