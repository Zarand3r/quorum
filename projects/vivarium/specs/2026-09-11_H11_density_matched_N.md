# H11 — does a SMALLER system at the SAME density emerge vesicles more often?

**Registered 2026-09-11, before any run.** 2-D, production chemistry, nothing else changed.

## Why

Emergence is ~1 run in 32, too rare to gate anything. The one validated reaction coordinate is the
ribbon's **end-to-end gap** (5/5 closure at 3.4 sigma, 1/10 at 10.1). Closure is therefore a race
between a ribbon finding its own ends and the aggregate growing too large for its ends to meet.

The data hint at exactly that. Across 32 production runs at N = 160, the ONE success had largest
aggregate **85** (and closed at **56**); the 31 failures averaged **132**, median **142**.

**H10 already lowered N and it made things worse** (N=50 0/12, N=80 0/12, N=160 1/32). But H10 varied
N at FIXED L = 65, so it lowered the density too and starved the system -- at N = 50 the largest
aggregate only reached 17.8 lipids, far below a viable vesicle. That experiment could not separate
"too few lipids" from "too big an aggregate".

This one holds **density constant** and varies only the system size, so the aggregate a system can
possibly build scales with N while the encounter rate per lipid does not.

## Design

Lipid area density fixed at the production value, `N / L^2 = 160 / 65^2 = 0.03787`:

| N | L | total beads |
|---|---|---|
| 56 | 38.45 | ~1035 |
| 80 | 45.96 | ~1479 |
| 112 | 54.40 | ~2071 |
| **160** | **65.00** | **2959** (the production baseline) |

N = 56 is the size of the confirmed emergent vesicle (`emergent_vesicle_sd509_s500000.npz`), so at
that cell the whole system is exactly one vesicle's worth of lipid.

| | |
|---|---|
| chemistry | production, all six affinities, phi = 0.55, kT = 0.45 |
| start | `plant="random"`, dispersed, nothing planted |
| seeds | 20 per cell, fresh: 900-919 |
| steps | 1e6, checkpoint every 10,000 |
| endpoint | `vesicle_call` true at any checkpoint (the strict two-gate detector) |

## Gate, fixed before data

```
H11 PASSES iff  some cell with N <= 112 gives >= 4/20
           AND  Fisher one-sided vs the N=160 cell of this same sweep p <= 0.05
```

The comparator is the **N = 160 cell of this sweep**, not the historical 1/32 — a contemporaneous
control, because H7 was left uninterpretable by leaning on a historical one.

## Predictions, registered

1. The rate is highest at N = 56 and falls with N.
2. N = 160 reproduces roughly its historical rate (0-2 of 20).
3. Mean largest aggregate scales with N, and the cells that emerge are the ones whose largest
   aggregate stays near the ~56-85 range where the two confirmed vesicles closed.

## What each outcome means, written before running

- **PASS.** Emergence is limited by aggregate size relative to the capture radius, not by chemistry,
  and the rate is controllable by system size. That gives the project a usable emergence gate for the
  first time, which unblocks every downstream comparison.
- **FAIL, rate flat in N.** Aggregate size is not the limiter. The race model is wrong and the 85-vs-132
  observation was a coincidence of one seed.
- **FAIL, rate falls with smaller N (as H10 found).** Then H10's starvation reading was not about
  density after all, and small systems genuinely cannot sustain a vesicle -- which would put a hard
  floor under R_c and make N = 160 near-optimal already.
- **All cells 0/20.** The strict gate is too strict to serve as an emergence endpoint at any size,
  which promotes roadmap item 2 (deciding what counts as a vesicle) from second to first.

## Threat

Smaller boxes bring the aggregate closer to its own periodic image. At N = 56, L = 38.45, a closed
vesicle of radius 56/(2*pi) = 8.9 has diameter 17.8 against a box of 38.45 -- it fits with room, but a
ribbon extended before closure could span. `n_enclosed` is measured on the unwrapped cluster, so the
detector is unaffected; the physics may not be. Reported alongside, not worked around.
