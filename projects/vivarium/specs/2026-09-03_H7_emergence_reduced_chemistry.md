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
