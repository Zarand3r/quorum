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

---

## Pre-verdict observation, 2026-09-11 18:15 — the first hit is a LASSO, not a clean ring

`VESICLE_0_N56_sd904_s600000.npz` passes the gate cleanly on the numbers: dilation ladder
`[1,1,1,1]`, enclosing cluster 56/56, lumen ratio **0.196** (nearly twice the 0.10 threshold),
sustained across consecutive checkpoints.

**The render** (`docs/figures/h11_N56_sd904.png`) shows a **closed loop with a substantial tail** — a
lasso — not the clean ring that seed 509 produced. The enclosure is genuine, and it is clearly better
than the branched-net-with-a-pocket that `vesicle_call` correctly rejected at sd313. But it sits
between those two.

**Recorded before the verdict so the eventual count is read correctly.** If H11 passes its gate, the
honest statement is "N=56 produces enclosed structures at rate X", and how many of those are clean
rings is a separate question that requires looking at each one. A count of gate passes is not a count
of vesicles, and this project has conflated the two before.

## Second hit, 2026-09-11 19:15 — N = 112, and this one IS a clean ring

`VESICLE_0_N112_sd903_s850000.npz`: ladder `[1,1,1,1]`, enclosing cluster **35 of 112** lipids, lumen
ratio **0.454** — four and a half times the threshold, and more than double the N=56 lasso's 0.196.

**The render (`docs/figures/h11_N112.png`) is a clean closed ring** with a visible lumen and heads on
both faces, coexisting with several separate open ribbons. This is the third emergent vesicle on
record (after seed 509 at N=160 and the N=56 lasso) and the cleanest of the small ones.

Worth noting for the mechanism, separately from the rate: it is **35 lipids out of 112**, i.e. a small
vesicle that closed while the rest of the system stayed as unincorporated ribbons. That is the
"several small aggregates, one of which closes" picture the hypothesis was built on — the mechanism
looks right even where the rate has so far not moved.

Running tally, cells complete: N=56 **1/20**, N=80 **0/20**. Neither clears the registered 4/20.

---

## H11 — VERDICT: FAILS, 2026-09-11 21:13

80 runs, seeds 900-919, four cells at constant lipid density.

| N | vesicle | any-enclosure | mean largest |
|---|---|---|---|
| 56 | **1/20** | 6/20 | 55.2 |
| 80 | **0/20** | 5/20 | 69.8 |
| 112 | **2/20** | 11/20 | 89.8 |
| 160 | **1/20** | 13/20 | 104.0 |

    GATE: some cell N<=112 gives >=4/20 AND Fisher p<=0.05 vs this sweep's N=160
    N=56  1/20 vs 1/20  p=0.7564    N=80 0/20  p=1.0000    N=112 2/20  p=0.5000
    ==> FAILS

### Scoring the registered predictions

| # | prediction | outcome |
|---|---|---|
| 1 | rate highest at N=56, falling with N | **WRONG** — flat (1, 0, 2, 1) |
| 2 | N=160 reproduces its historical 0-2/20 | **RIGHT** — 1/20 |
| 3 | mean largest scales with N | **RIGHT** — 55.2 / 69.8 / 89.8 / 104.0 |

The manipulation worked and the rate did not follow. This is the registered second outcome verbatim:
*"aggregate size is not the limiter. The race model is wrong and the 85-vs-132 observation was a
coincidence of one seed."*

### The one thing that DID scale

**Any-enclosure rises with N: 6, 5, 11, 13 — while strict vesicles stay flat at 0-2.** Bigger systems
enclose *more often* under the loose criterion and no more often under the strict one. Read together
with the renders, that is bigger aggregates making more pockets, not more vesicles — and it is another
reason the loose criterion must not be used as an emergence endpoint.

---

# H12 — WITHDRAWN BEFORE RUNNING, 2026-09-11 21:15

`specs/2026-09-11_H12_density_at_fixed_N.md` was registered at 20:45, before H11's final cell
reported. H11's completed result makes it largely redundant, and it is withdrawn rather than run.

**Why.** H12 varies density at fixed N. Its mechanism is the merge rate, and the quantity it acts
through is **the size of the largest aggregate** — exactly the mediating variable H11 just swept over
a **1.9× range** (55.2 to 104.0) with **no movement in the rate**. Running H12 would test the same
mediator through a different knob, and H11 is already powered enough to say that mediator does not
move the endpoint.

Withdrawing costs nothing and running it would have cost ~3 hours. Recorded here rather than deleted,
because a registered experiment that is not run should leave a trace saying why.

**What this does not rule out:** density has effects beyond aggregate size — solvent-mediated
interactions, encounter statistics, the time to condense at all. If a later result makes density
interesting for a reason other than the merge race, this spec can be revived on that basis, not this
one.
