# H7 — does a 2-D vesicle EMERGE from the reduced chemistry?

**Registered 2026-09-03, before any run.** 2-D only.

## Why now

`specs/2026-09-02_knob_ladder_2d.md` reduced five hand-set affinities plus an explicit solvent to
**one affinity (`chi_TT = 1.0`) plus one geometric ratio (`sigma_head = 0.95`)**, with no measurable
loss on closure (19/20 vs production 10/10) or persistence (17/20 vs 9/10).

Every rung of that ladder was run on a **planted arc**. It shows the chemistry needed to CLOSE and
HOLD a vesicle. It does not show one EMERGES. That is the gap this closes.

It is testable now only because the reduction made it cheap: solvent-free runs at 0.55 ms/step against
2.2 with explicit water, turning a ~3.3-hour self-assembly run into ~17 minutes.

## H7

A vesicle self-assembles from a dispersed random start under the reduced chemistry.

## Design

| | |
|---|---|
| arm | 6B chemistry: `chi_TT = 1.0` only, `sigma_head = 0.95`, solvent-free |
| system | 2-D, N = 160 lipids, L = 65, kT = 0.45 — the same lipid count and box as every production emergence run |
| start | `plant="random"`, dispersed |
| seeds | 20, fresh: 200-219 (the ladder used 100-119) |
| steps | 1e6, checkpoint every 50,000 |

## Endpoint, fixed before data

Primary: **`vesicle_call` true at any checkpoint** — the strict two-gate detector (n_enclosed stable
at 1 across dilations 1.0-3.0, AND lumen the right size for the lipid count). This is the same gate
the original 2/18 emergence result was scored on.

Secondary, reported: `n_enclosed >= 1` at any checkpoint, and largest aggregate size.

## The baseline, and its weakness stated up front

The production-chemistry comparator is **historical, not contemporaneous**:

- the original emergence result, **2 of 18** fresh dispersed seeds
- H5, 2026-09-02, **0 of 24** runs at N=160, L=65, kT=0.45, phi=0.55, 1e6 steps, both arms

Pooled: **2 of 42**. Same N, box, temperature, step budget and detector.

This is a weaker comparison than a paired run, and the reason is cost: a production arm at 20 seeds is
~66 CPU-hours against ~6 for the reduced arm. **The asymmetry is real and is not hidden — if H7's
result is close to the baseline rate, a contemporaneous production arm must be run before anything is
claimed.** Only a large effect is interpretable against a historical control.

```
PASS  iff  reduced arm >= 6/20  AND  Fisher one-sided vs 2/42 gives p <= 0.01
```

The margin is deliberately harsh (6/20 = 30% against a 4.8% baseline) precisely because the control is
historical.

## What each outcome means, written before running

- **PASS.** Vesicles emerge from one attraction plus a size ratio. Combined with the ladder, that is
  the project's central claim demonstrated end to end in 2-D: emergence AND closure from physics and
  geometry, with a single chosen number.
- **FAIL, and the arm assembles but does not close.** The reduction preserves closure-given-a-membrane
  but not emergence. The ladder result stands as scoped; the emergence claim does not follow from it,
  and the difference localises to nucleation rather than to closure.
- **FAIL, and the arm does not even aggregate.** Solvent-free 2-D at this density does not condense.
  That is a statement about density and dimensionality, not about the chemistry reduction, and would
  need a density sweep before meaning anything.
- **Rate near the 2/42 baseline.** Uninterpretable against a historical control. Run the
  contemporaneous production arm.

## Threat register

- `vesicle_call` is validated in 2-D (planted ring reads 1,1,1,1; branched net rejected at lumen ratio
  0.028). Inside its domain.
- Removing the solvent removes crowding. Lipids must find each other by diffusion alone, with no
  osmotic assistance. That is a real physical difference from the production system and could suppress
  nucleation independently of the chemistry.
- Box and lipid count are held at production values so lipid concentration is matched; what is not
  matched is total bead density, which necessarily falls when 2799 water beads are removed.

---

## H7 — RESULT: FAILS the registered gate, 2026-09-03

20 runs, seeds 200-219, reduced chemistry (`chi_TT` only + `sigma_head = 0.95`), solvent-free.

| | |
|---|---|
| vesicles (`vesicle_call` at any checkpoint) | **0/20** |
| any enclosure (`n_enclosed >= 1`) | **0/20** |
| mean largest aggregate | **80.3** of 160 lipids |

    GATE (>= 6/20 AND p <= 0.01 vs 2/42): FALSE

This is the second registered outcome, verbatim: *"FAIL, and the arm assembles but does not close.
The reduction preserves closure-given-a-membrane but not emergence."* The system condenses to half its
lipids in one aggregate and never encloses anything.

### But the reduction is NOT what failed

| runs at N=160, L=65, kT=0.45, 1e6 steps | vesicles |
|---|---|
| historical, production chemistry | 2/18 |
| H5, 2026-09-02, production chemistry | **0/24** |
| H7, 2026-09-03, reduced chemistry | **0/20** |
| **recent, pooled across both chemistries** | **0/44** |

`0/20` against the registered comparator `2/42` gives p = 1.000 -- the two arms cannot be
distinguished, because both are approximately zero. The reduced chemistry is not worse at emergence
than the production chemistry. **Neither of them emerges anything in recent runs.**

Historical 2/18 against recent 0/44 is one-sided p = 0.0809: suggestive, NOT established. The
operative fact is 0/44, not a demonstrated discrepancy.

### The most likely artifact, and it is checkable

**H7 checkpoints every 50,000 steps.** The gap assay measured rings that close and REOPEN inside that
window -- rung 3B seed 105 closed at step 10,000 and was open again by 60,000. A transient vesicle
shorter than one checkpoint interval is invisible to this harness, and transient is exactly what a
marginal, encounter-limited closure would be.

So `0/20` may be a **sampling-cadence artifact rather than a physical result**, and the same applies
to H5's `0/24`. This must be resolved before H7 is read as evidence about the chemistry at all.

## H8 — registered 2026-09-03, before running

**Does the original 2-D emergence result reproduce under dense checkpointing?**

| | |
|---|---|
| arms | production chemistry (rung 0) **and** reduced (6B), run contemporaneously |
| change | `CHECK_EVERY = 10,000` instead of 50,000 -- 5x denser |
| seeds | 20 per arm, fresh: 300-319 |
| everything else | identical to H7 |

```
The question is not which arm wins. It is whether EITHER arm reproduces 2/18.

  BOTH arms > 0    -> emergence is real and was being missed by cadence. Compare the arms.
  BOTH arms 0/20   -> the historical 2/18 does not reproduce at 5x denser sampling either.
                      The project's headline 2-D emergence result is then in question and that,
                      not the knob ladder, becomes the most important open item.
  production > 0, reduced 0 -> the reduction genuinely costs emergence. The ladder result stands
                      for closure and explicitly does not extend to emergence.
```

The production arm is run **contemporaneously** this time. H7 leaned on a historical control and its
own spec said a near-baseline result would be uninterpretable without one. It was, so here it is.

---

## H8 — RESULT, 2026-09-03. Both arms 0/20 on the strict gate.

40 runs, seeds 300-319, both arms contemporaneous, checkpoint every 10,000 steps.

| arm, n = 20 | vesicles (`vesicle_call`) | seeds with any enclosure | total enclosure-checkpoints | mean largest aggregate |
|---|---|---|---|---|
| production (rung 0) | **0/20** | **13/20** | 181 | **131.4** / 160 lipids |
| 6B reduced | **0/20** | **2/20** | 8 | **78.0** / 160 lipids |

### Finding 1 — the reduction costs self-assembly, and this is established

Seeds with enclosure, 13/20 against 2/20: **Fisher one-sided p = 0.000386**. Production also
aggregates far more of the system (131 of 160 lipids against 78).

So the ladder's scope limit was the right call and the honest reading is:

> Reducing five affinities plus an explicit solvent to one affinity plus a size ratio **preserves the
> ability to close and hold a planted vesicle** (19/20 closure, 17/20 persistence, indistinguishable
> from production) and **degrades self-assembly** (2/20 against 13/20 seeds reaching any enclosure).

Nucleating a membrane from dispersed lipids and holding one shut are different problems. The ladder
only ever tested the second, said so in advance, and H8 is why that mattered.

### Finding 2 — the "2/18 does not reproduce" reading is probably a CRITERION change, not physics

Both arms give 0/20 on `vesicle_call`, against a historical 2/18. Before concluding the headline
result fails to reproduce, note what this project has already written down about it:

- `vesicle.py`: *"every saved 2-D production state was checked on 2026-08-27 and **not one passes
  `vesicle_call`**"* -- listing five states with lumen ratios 0.021-0.070 against a 0.10 threshold.
- `_lumen_field.vesicle_call` docstring: *"Gate 2 exists because the pre-registered emergence
  criterion had only gate 1, and a 160-lipid branched network passed it. The render caught that, not
  the metric."*

**The historical 2/18 was scored on gate 1 alone.** Gate 2 -- the lumen must be the right size for the
lipid count -- was added afterwards, and it rejects every 2-D state the project ever saved. H8 applies
both gates.

Under a weak enclosure criterion, production gives **13/20** -- *more* than 2/18. Under the strict
two-gate criterion, **0/20**. The old number and the new number were never measuring the same object,
and 2/18 vs 0/40 is therefore **not** evidence of non-reproduction.

**What this does mean, and it is not comfortable:** the project's headline 2-D emergence result is
stated against a criterion that its own successor instrument rejects, and no saved state survives the
current gate. The result is not refuted -- it is **unverifiable from the artifacts on disk**. Deciding
what 2-D emergence should be scored on is a judgement call about what counts as a vesicle, not a
measurement, and it is handed to review rather than settled here.

### What was NOT done

No re-scoring of the historical runs under gate 1 alone, which would make the comparison exact. The
raw states are the five listed in `vesicle.py` and they do not include the two that were counted as
successes -- one was overwritten in place by a relaunch (`docs/states_protected/former_sd45007_*`,
whose filename says step 960,000 while the file reports 1,600,000). **The vesicle that existed at
960k is gone from disk.** That is the reason this cannot be closed by measurement.
