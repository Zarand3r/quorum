# Ladder II — remove the knobs again, but gate on EMERGENCE

**Registered 2026-09-06, before any run.** 2-D.

## Why a second ladder

Ladder I (`specs/2026-09-02_knob_ladder_2d.md`) reduced five affinities plus an explicit solvent to one
affinity plus a size ratio, and it was gated on **closure of a planted arc**. That gate never required
the system to make a membrane, so a chemistry that cannot nucleate can still pass it — and one did.
H8 measured the cost: the reduced chemistry closes a planted arc 19/20 and assembles 2/20 against
production's 13/20.

Ladder II fixes the gate: **start from the configuration that actually emerged a vesicle, remove one
knob at a time, and require emergence after every removal.**

## The starting point — the configuration that worked

    mix2d_random_N160_L65_exp_kT0.45_fs0.0_ht-0.25_ww0.50

160 branched 4-tail lipids, L = 65, kT = 0.45, phi = 0.55 explicit solvent, all six chi affinities,
dispersed random start. `docs/RESULTS.md` records the emergence directly in the trajectory:

| step | largest | n_enclosed | lumen | ratio |
|---|---|---|---|---|
| 320 000 | 116 | 0 | 0 | - |
| **360 000** | **116** | **1** | **2145** | **0.501** |
| 400 000 | 160 | 1 | 2191 | 0.269 |

It closed at 116 lipids at constant size (two ends meeting, not accretion), held closure for a further
400,000 steps, and a perturbation test gave 3/5 intact against a bar of >= 3/5 fixed before the run.

The transformer path is **bit-identical** on this exact topology (2959 beads, 640 bonds, 320 angles):
forces match to 1.4e-16, one forward pass against one integrator step differs by **exactly 0.0**. So
this is a transformer-only result regardless of which path executed it.

## Instrument defect fixed first, 2026-09-06

`vesicle_call` sized the expected lumen from `len(mols)` -- the WHOLE system -- so a vesicle made of a
subset of the lipids was penalised by `(n_cluster / n_total)**2`. The historical vesicle is 116 of 160
lipids: the gate read 0.263 where `RESULTS.md` recorded 0.501. Both clear the 0.10 threshold so no
verdict changes, but the gate and the analysis were computing different quantities under one name.

Now normalised by the enclosing cluster (`largest_lipid_cluster`). Checked against controls it must
still REJECT: the branched network sd313 spans all 160 lipids so its ratio is unchanged and it still
fails; a planted closed ring passes at 0.353; an open arc still fails.

## THE BLOCKER: emergence at 2/18 cannot serve as a gate

At an 11% rate, twelve seeds per arm cannot distinguish anything -- which is the lesson Ladder I
already paid for twice. **Ladder II cannot start until the emergence rate is high enough to test
against.** Raising it is therefore step zero, and it must be raised by physics, not by tuning.

## H10 — the spanning hypothesis

`references.py` states the mechanism this project has never applied to its own box size:

> *"A finite patch pays edge energy 2*pi*R*gamma along its exposed rim and closes into a vesicle to
> escape it, which is why bulk water makes vesicles rather than sheets. **A periodic box removes the
> rim, so the flat phase becomes reachable** -- this is exactly why coarse-grained membrane
> simulations plant spanning bilayers."*

Vesiculation is edge-driven. If the aggregate can span the periodic box it has **no rim at all** and
never needs to close. A branched 4-tail lipid has a lateral footprint of 2 sigma (`_plant_ring`'s
`lat`), so a bilayer ribbon spanning a box of side L needs about `2*(L/2) = L` lipids.

| run | L | spanning needs | N | |
|---|---|---|---|---|
| every emergence run to date | 65 | ~65 lipids | **160** | can span 2.5x over |

**Every emergence run this project has done has had enough lipids to reach the flat, rimless state**,
which competes with closure as a sink. And the historical success fits: it closed at **116** lipids and
only then absorbed the remaining 44 as appendages, diluting the ratio 0.501 -> 0.269. Closure won a
race it did not have to win.

**H10: lowering N below the spanning threshold raises the emergence rate**, because closure becomes
the only way to shed edges.

### Design

| | |
|---|---|
| arm | production chemistry, unchanged (the configuration that worked) |
| swept | `N` in {50, 80, 116, 160} at fixed L = 65 |
| seeds | 12 per cell, fresh: 500-511 |
| steps | 1e6, checkpoint 10,000 |
| endpoint | `vesicle_call` true at any checkpoint, with the cluster-normalised gate |

Cost is flat in N: water backfills, so every cell is ~2959 beads. Growing the box instead would be
prohibitive -- L = 140 at phi = 0.55 is 13,725 beads.

```
H10 PASSES iff some N <= 80 gives >= 5/12 AND Fisher one-sided vs N=160's 0/20 (H8) p <= 0.05
```

### Predictions, registered

1. N = 50 (cannot span) has the highest rate.
2. N = 160 (spans 2.5x over) has the lowest, consistent with H8's 0/20.
3. The rate falls monotonically with N.

### What each outcome means, written before running

- **H10 passes.** The 2/18 rate was a kinetic competition we imposed by choosing the box, not an
  intrinsic property. Ladder II then runs at the winning N with a usable gate, and the historical
  emergence claim is strengthened rather than withdrawn.
- **H10 fails, all N give ~0.** Emergence is rare for a reason other than spanning. The N sweep is
  cheap and its failure is informative: it removes the one geometric explanation currently on the
  table, and Ladder II cannot proceed without another way to raise the rate.
- **Rate is flat in N.** Spanning is not the competing sink. Same conclusion as above.
- **N = 50 assembles nothing** (aggregates too small to be vesicles at all). Then the lower bound is
  `R_c`, not spanning, and the window between `R_c` and the spanning threshold may be empty at L = 65
  -- which would itself explain the 11% rate and point at a larger box with implicit solvent.

## Ladder II protocol, once H10 gives a usable rate

Each rung, in this order, each a single variable against the rung below:

| rung | knob | replacement |
|---|---|---|
| 1 | `chi_HT` = -0.25 | head size (geometry) |
| 2 | `chi_HH` = +0.20 | excluded volume only |
| 3 | `chi_HW`, `chi_TW`, `chi_WW` + explicit solvent | Flory-Huggins solvent averaging (derived) |
| - | `chi_TT` | kept, irreducible |

```
A RUNG PASSES iff  emergence rate >= the rung below it, Fisher one-sided p > 0.05 (not degraded)
```

A failure means the replacement was wrong, not that the knob is irreplaceable -- that is the user's
framing and it is the right one, but it is only honest if a failure is allowed to stand as a failure
after a bounded number of attempts at a better replacement. **Two attempts per rung**, then the rung
is recorded as failed and the knob as load-bearing.

## ASSUMPTION, stated because it shapes everything

"Replacing a knob with transformer-only" is taken to mean: the knob's effect must be reproduced by
something that is **not a hand-chosen number** -- bead geometry, a derived thermodynamic quantity, or
network structure. It cannot mean "make it transformer-only" in the literal sense, because the force
law is *already* exactly a transformer: every chi entry is a species-channel q.k product, verified to
0.000e+00 over 30,186 pairs. A chosen number expressed as attention is still a chosen number, and the
count of chosen numbers is what this ladder is trying to reduce.

---

## H10 — RESULT: FAILS, and the prediction was backwards

48 runs, production chemistry, L = 65, seeds 500-511, 1e6 steps, cluster-normalised gate.

| N | spanning threshold ~65 | vesicles | any enclosure | mean largest aggregate |
|---|---|---|---|---|
| 50 | **cannot span** | 0/12 | 0/12 | **17.8** |
| 80 | can span | 0/12 | 0/12 | 37.5 |
| 116 | can span | 0/12 | 2/12 | 62.4 |
| 160 | can span 2.5x | **1/32** | 23/32 | **130.3** |

    GATE: some N <= 80 gives >= 5/12 AND p <= 0.05 vs H8's 0/20
    N=50: 0/12, N=80: 0/12  ==> FAILS

### The predictions were wrong, all three

Registered: (1) N=50 highest, (2) N=160 lowest, (3) rate falls monotonically with N. The rate **rises**
monotonically with N. Every prediction was backwards.

### What is actually limiting emergence

Mean largest aggregate scales almost linearly with N: 17.8, 37.5, 62.4, 130.3. **At N = 50 the system
never builds an aggregate big enough to be a vesicle at all** -- 17.8 lipids against the ~116 at which
the historical vesicle closed. This is the fourth outcome registered in advance:

> *"N = 50 assembles nothing (aggregates too small to be vesicles at all). Then the lower bound is
> `R_c`, not spanning, and the window between `R_c` and the spanning threshold may be empty at
> L = 65."*

So the binding constraint is the **minimum viable vesicle size**, not the box. Starving the system of
lipids to remove the flat state removes the vesicle instead. The edge-energy argument in
`references.py` is not wrong -- it is simply not the active constraint here, and it was worth one cheap
sweep to find that out.

**H10's failure retires the spanning hypothesis.** It does not tell us why emergence is rare; it tells
us one candidate explanation is not it.

### The one positive: the gate fix produced a vesicle

N = 160 reads 1/32, and the composition matters. The 20 H8 runs were scored during execution with the
OLD whole-system normalisation and gave 0/20. The 12 H10 runs used the cluster-normalised gate and gave
**1/12**. That is the first `vesicle_call` pass in any recent run, and it appeared when the
normalisation defect was fixed rather than when the physics changed.

**Not claimed as a result.** n = 12, one event, and the comparison against H8 is confounded because the
two batches were scored by different gate versions -- which is exactly the kind of cross-version
pooling this project has already been burned by. What it justifies is re-scoring the H8 states with the
fixed gate, which is free, before anything else is concluded.
