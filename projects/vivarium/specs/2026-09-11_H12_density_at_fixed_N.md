# H12 — does DENSITY move the emergence rate, at fixed system size?

**Registered 2026-09-11 20:45, before any H12 run and before H11's final cell reported.**
H11's N=160 cell stood at 12/20 with 0 vesicles at the time of writing; nothing here depends on how it
finishes.

## Why, and how it differs from H10 and H11

Three experiments, three different things held fixed:

| | varied | held fixed | result |
|---|---|---|---|
| H10 | N | box L = 65 (so density fell with N) | FAIL — small systems starved, largest aggregate 17.8 at N=50 |
| H11 | N **and** L together | **density** | 1/20, 0/20, 2/20 — no cell cleared 4/20 |
| **H12** | **L** | **N = 112** | this spec |

H11 removed density as a variable and found system size does not move the rate. H12 removes system
size and varies density — the one axis neither previous experiment moved on its own.

**The lead it tests.** Across all four confirmed vesicles, the cleanest rings are built from a
MINORITY of the system's lipids (#3: 35 of 112, ratio 0.454; #1: 56 of 160) while the one built from
nearly the whole system (#2: 56 of 56) renders as a lasso. Closure is a race between a ribbon finding
its own ends and aggregates merging into something too big to close. **Density sets the merge rate;
system size does not.** So density, not N, is the predicted lever — and H11 is exactly the experiment
that could not have seen it.

## Design

`N = 112` throughout (the best-performing H11 cell, 2/20 and 11/20 any-enclosure). Only the box moves:

| arm | L | beads | density vs production | note |
|---|---|---|---|---|
| dense | 45.00 | ~1418 | 1.46× | cheaper than baseline |
| **baseline** | **54.38** | **2071** | **1.00×** | the H11 N=112 cell |
| dilute | 68.00 | ~3238 | 0.64× | ~1.6× cost |

Everything else identical to H11: production chemistry, `plant="random"`, kT = 0.45, phi = 0.55,
1e6 steps, checkpoint 10 000, `bend_r0 = 2.0`.

Seeds **1000-1019**, 20 per arm, fresh — H11 used 900-919.

**The baseline arm is re-run rather than reused.** It is the same configuration as H11's N=112 cell but
with different seeds, so it doubles as an independent replication of that cell's 2/20. Reusing H11's
numbers would make the comparison share seeds with one arm and not the others.

## Gate, fixed before data

```
H12 PASSES iff  the dilute arm gives >= 5/20
           AND  Fisher one-sided vs the baseline arm of THIS sweep p <= 0.05
```

Comparator is this sweep's own baseline, not H11's — contemporaneous, same seeds.

The bar is 5/20 rather than H11's 4/20 because H11 showed 2/20 arises without any intervention; a bar
of 4 would be within noise of that.

## Predictions, registered

1. **dilute > baseline > dense.** Lower density slows merging, so more aggregates stay short enough to
   reach their own ends.
2. Mean largest aggregate **falls** with dilution — the direct check that the intervention does what it
   is supposed to. If mean largest does not move, the arm did nothing and the rate is uninformative.
3. The fraction of the system in the largest aggregate falls with dilution.

## What each outcome means, written before running

- **PASS.** Density is the lever, and the project finally has a knob that moves emergence. That makes a
  powered emergence endpoint possible for the first time, which unblocks every downstream comparison.
- **FAIL, rate flat while mean largest DOES move.** The intervention worked and the rate did not follow
  — so the merge-race model is wrong, and three independent geometric levers (N at fixed L, N at fixed
  density, L at fixed N) have now all failed. That would be strong evidence the limiter is not geometry
  at all, and would promote the gate question (roadmap item 2) to the top.
- **FAIL, and mean largest does NOT move.** The density range was too narrow to matter. Uninformative
  about the hypothesis; report as such rather than as a null.
- **Reversed (dense > dilute).** Merging helps rather than hurts — the race model has the sign
  backwards, which would be as useful as a pass and should be said out loud.

## Threat

Dilution lengthens the time to form any aggregate at all. At the dilute arm a run may spend most of
1e6 steps still condensing, so a null there could be "not enough time" rather than "density does not
help". Mean largest aggregate is reported per arm precisely so that confound is visible rather than
inferred; if the dilute arm's mean largest is far below baseline, read it as under-run, not as a null.
