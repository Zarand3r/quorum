# H5 — does removing chi_HT increase transient enclosure? (2-D replication)

**Registered 2026-09-02, before any fresh-seed run.** All 2-D; the 3-D track is parked behind
`docs/REVIEWER_HANDOFF_2026-08-31.md`.

## The observation being replicated

From the 1e6-step knob-1 run (seeds 1-6, both arms), counting **seeds with at least one checkpoint at
`n_enclosed >= 1`**:

    chi_HT = -0.25 (knob IN)      0 / 6
    chi_HT =  0.00 (knob REMOVED) 4 / 6      Fisher one-sided p = 0.0303

Direction: removing the knob made transient enclosure MORE common — the opposite of the failure this
knob removal was guarding against.

**Why it is not yet a result.** It was not the registered endpoint of that run (vesicle_call was), it is
post-hoc, and n = 6. This project has watched three n<=5 effects evaporate on replication, one by a
factor of six. A post-hoc p = 0.03 at n = 6 is a lead.

## H5

Removing `chi_HT` raises the rate of transient enclosure in the 2-D system.

## Design

| | |
|---|---|
| arms | `chi_HT` = -0.25 (baseline) vs 0.00 (removed) |
| seeds | **7-18, fresh** — no reuse of 1-6, which generated the hypothesis |
| n | 12 per arm |
| system | 2-D, N=160, L=65, kT=0.45, phi=0.55, all other chemistry unchanged |
| steps | 1e6 |
| engine | transformer |

## Endpoint, fixed before data

Primary: **fraction of seeds with >= 1 checkpoint at `n_enclosed >= 1`**, counted per seed, not per
checkpoint (11 of the original 18 checkpoints came from a single seed; per-checkpoint counting is
pseudo-replication).

```
PASS iff  removed >= 6/12  AND  baseline <= 2/12  AND  Fisher one-sided p <= 0.05
```

Secondary, reported but not gating: `vesicle_call` passes, and largest-aggregate size.

## What each outcome means — written before the data

- **PASS.** Removing chi_HT does not merely do no harm, it helps: enclosure becomes more frequent. That
  is a positive argument for the knob reduction rather than an absence of harm, and it makes chi_HH the
  natural next removal.
- **FAIL, baseline also encloses.** The original 0/6 baseline was a fluctuation. The knob is neutral;
  report and move on to chi_HH.
- **FAIL, neither arm encloses.** Enclosure at 1e6 steps is rarer than the first run suggested; the
  endpoint is too weak at n = 12 and the comparison needs either far more seeds or a different
  observable.
- **Reversed (baseline > removed).** The first run was noise in the other direction. Report it as such;
  it would be the fourth small-sample effect to evaporate in this project and worth recording as a
  pattern.

## Threat

`n_enclosed` is the 2-D detector, validated in 2-D (planted ring reads 1,1,1,1; nves 1; call True) and
known broken in 3-D. This experiment is 2-D only, so it is inside its validated domain.
