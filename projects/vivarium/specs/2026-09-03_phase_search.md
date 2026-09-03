# Recovering emergence in the reduced chemistry — a phase-space search in reduced units

**Registered 2026-09-03, before any run.** 2-D.

## The problem

The knob ladder reduced five affinities plus an explicit solvent to one affinity plus a size ratio,
and that reduction **preserves closure** (19/20 on a planted arc) but **degrades self-assembly**
(2/20 seeds reaching any enclosure against 13/20 for production; largest aggregate 78 vs 131 lipids
of 160). Goal: recover assembly from physics, not by re-adding knobs.

## A CONFOUND IN THE LADDER, found before this search and stated first

Every rung held `kT = 0.45` fixed. The phase of a cohesive fluid depends on the **reduced**
temperature `T* = kT / (eps * chi_TT)`, not on `kT`. So:

| rung | `chi_TT` | `T*` |
|---|---|---|
| 0-5 (production through `chi_WW` removed) | 0.70 | **0.643** |
| 6A solvent-averaged | 1.20 | **0.375** |
| 6B Cooke, one affinity | 1.00 | **0.450** |

Rungs 0-5 are all at one reduced temperature, so the ladder is clean up to rung 5. **Rung 6 changed
the reduced temperature as a side effect of changing the chemistry**, and rung 6 is exactly where
emergence was tested and failed. 6B is 1.43x colder than production in the units that set the phase.

This is the failure mode CLAUDE.md names -- "derive constants from the configuration; do not pick
them". `kT` was held constant when the quantity that should have been held constant was `T*`.

## The physics, from the project's own literature file

`docs/DEEP_RESEARCH_2026-08-31.md`, quoting Cooke, Kremer & Deserno (PRE 72 011506; JCP 123 224710):

- Three outcomes, not two: **gel / fluid / unstable**. *"At sufficiently low temperature the bilayer
  adopted a gel phase; within a more elevated temperature range a fluid phase can be reached,
  provided w_c >~ 0.8 sigma; at sufficiently high temperature a bilayer under zero tension always
  fell apart."*
- Their fluid reference point is **kT = 1.1 eps**, i.e. `T* = 1.1`, with `w_c` ~ 1.4-1.6 sigma.
- Operational signature, quoted: *"gel = high orientational order plus near-zero lateral diffusion;
  fluid = order with diffusion; unstable = box-spanning breakup"*.

**Our attraction range is already correct.** `field._well` is a cosine tail from contact to `rc`, so
the effective width is `rc - sigma = 1.5 sigma`, inside the safe band. Range is not the deficit.

**Our temperature is not.** Every configuration this project has run sits below Cooke's fluid point:
production at `T* = 0.64`, 6B at `0.45`, against `1.1`.

## Why a gel explains what we see, and what else it predicts

A gel is kinetically arrested: lipids stick where they first touch and cannot rearrange. That
predicts, and matches:

- assembly stalls at several small aggregates instead of coarsening to one (2-D: largest 78/160;
  and independently the 3-D handoff's *"five or six separate aggregates of 30-80 molecules"*);
- **closure of a PLANTED arc is unaffected**, because it needs no coarsening -- which is why 6B scores
  19/20 there while failing assembly. One mechanism, both observations.

## H9 — the hypothesis

The reduced chemistry's assembly deficit is a **reduced-temperature** effect, not a chemistry effect.
At matched `T*`, the reduced chemistry assembles as well as production.

## The search, in dimensionless groups

Raw parameters number nine (`kT, chi_TT, rc, sigma_head, density, k_bond, bend_r0, k_theta, dt`).
Searching them directly is both intractable and **redundant**: `kT` and `chi_TT` are not independent,
only their ratio sets the phase, which is precisely how the confound above arose. The physics depends
on

    T* = kT / (eps * chi_TT)          reduced temperature
    w* = (rc - sigma) / sigma         reduced attraction width
    s  = sigma_head / sigma_tail      packing geometry
    rho*                              reduced lipid density

Cooke's published phase diagram is in `(w*, T*)`. **The search is therefore 2-D, not 9-D**, with `s`
and `rho*` held at their current values and varied only if the 2-D map fails to find a fluid band.

## Protocol — three stages, cheapest first

**Stage 1 — build and validate the phase instrument. It can fail, and nothing proceeds if it does.**

Two observables, because either alone misleads (`_fluidity.py` already argues this and supplies both):

- `condensed` — largest aggregate as a fraction of all lipids. Separates gas from everything.
- `mobile` — neighbour retention: fraction of a lipid's initial nearest in-leaflet neighbours still
  nearest after t. A fluid forgets its neighbours; a gel keeps them. Chosen over bare MSD because it
  cannot be faked by collective drift or breathing modes.

    gel      = condensed AND NOT mobile
    fluid    = condensed AND mobile
    gas      = NOT condensed

Validation requires the instrument to **SEPARATE three known-answer cases**, not merely score one well:

| control | must read |
|---|---|
| `T* = 0.1` (deep freeze) | gel |
| `T* = 1.1`, the Cooke reference point | **fluid** |
| `T* = 5.0` (boil) | gas |

If those three do not separate, the instrument is not usable and Stage 2 does not run.

**Stage 2 — map the phase in `(T*, w*)`.** `T*` in {0.38, 0.45, 0.64, 0.9, 1.1, 1.4, 1.8} (covering
every configuration this project has used, plus Cooke's point and above), `w*` in {1.0, 1.5, 2.0}.
Planted membrane, short runs, phase measured not guessed. 6B chemistry throughout.

**Stage 3 — emergence, only inside the fluid band.** Dispersed start, the endpoint from
`specs/2026-09-03_H7_*.md`, both 6B and production at the *same* `T*`.

## Predictions, registered before data

1. 6B at its current `T* = 0.45` reads **gel**.
2. Production at `T* = 0.64` also reads gel, or marginal — it is below Cooke's point too.
3. `T*` near 1.1 reads **fluid**.
4. At matched `T*` inside the fluid band, 6B assembles at least as well as production, because the
   ladder already showed its closure physics is intact.

## What each outcome means, written before running

- **All four hold.** The reduction is sound and the assembly deficit was a temperature artifact of
  rung 6. The ladder result extends to emergence once `T*` is held fixed rather than `kT`.
- **1-3 hold, 4 fails.** The chemistry reduction genuinely costs assembly even at matched phase. The
  ladder stands for closure only, permanently, and the deficit is chemical.
- **1 or 2 fails (we are already fluid at `T* = 0.45`).** The gel hypothesis is dead and the deficit
  is something else. This is the outcome that would embarrass the whole framing, and it is the reason
  Stage 1 validates against Cooke's own reference point rather than against our intuition.
- **No fluid band anywhere in the map.** The model class cannot support a fluid membrane at any
  temperature with this core, which would be a far more serious finding than the knob ladder and
  would point at the bounded soft core (the one deviation from Cooke the literature flags as
  unverified).

## Threats

- `T*` as defined uses the tail-tail well depth as the energy scale. With explicit solvent present,
  water terms also carry energy and the single-parameter reduction is approximate. The comparison is
  therefore cleanest **between solvent-free arms**; production is included but its `T*` is a
  lower bound on the relevant energy scale, and that is stated wherever its number is quoted.
- Raising `kT` raises thermal noise everywhere, including across the bonded terms. Bond and bending
  stiffness are NOT rescaled with `T*`, so at high `T*` the chains become effectively floppier. This
  is a real confound at the top of the range and is why the map reports bond integrity alongside phase.

---

## STAGE 1 — instrument VALIDATED, 2026-09-03

Structural controls, fixing the connectivity cut with no dynamics and no temperature:

    planted ring (intact)  condensed = 1.000
    dispersed (gas)        condensed = 0.086      cut = 3.0 separates them

Phase controls, which had to land in three DIFFERENT boxes:

| control | T* | condensed | retention | phase | expected |
|---|---|---|---|---|---|
| deep freeze | 0.10 | 1.000 | 0.945 | gel | gel |
| **Cooke's published fluid point** | 1.10 | 0.829 | 0.195 | **fluid** | fluid |
| boil | 5.00 | 0.043 | 0.057 | gas | gas |

**INSTRUMENT USABLE: True.**

The first attempt FAILED and the failure is worth keeping: at `cut = 2.0` a perfectly intact planted
ring read `condensed = 0.600` and was classified **gas**, because 2.0 sigma spans one leaflet and the
two leaflets' centroids sit ~2.4 apart. The cut was then derived from the model's own geometry
(1.5x the branched lipid's `lat = 2.0` footprint) and fixed against the structural controls, which
contain no temperature — so it was not tuned on the runs used to validate it.

Note also that **neither observable is sufficient alone**, which is why both are required: `retention`
cannot separate fluid (0.195) from gas (0.057), and `condensed` cannot separate gel (1.000) from
fluid (0.829).

## STAGE 2 — the phase map

63 runs, 7 x 3 cells, 3 seeds, 6B chemistry, planted ring.

| T* | w*=1.0 | w*=1.5 | w*=2.0 | |
|---|---|---|---|---|
| 0.375 | gel 1.00/0.72 | gel 1.00/0.81 | gel 1.00/0.88 | rung 6A |
| **0.45** | fluid 1.00/0.56 | **gel 1.00/0.78** | gel 1.00/0.82 | **rung 6B** |
| **0.643** | fluid 0.78/0.28 | **fluid 1.00/0.44** | fluid 1.00/0.63 | **production, rungs 0-5** |
| 0.9 | gas 0.18/0.14 | fluid 0.72/0.24 | fluid 1.00/0.34 | |
| 1.1 | gas 0.10/0.11 | fluid 0.70/0.17 | **fluid 1.00/0.21** | Cooke reference |
| 1.4 | gas 0.09/0.08 | gas 0.22/0.09 | fluid 0.97/0.15 | |
| 1.8 | gas | gas | gas 0.42/0.12 | |

*(cells: phase, condensed/retention)*

### The finding

**At our operating width w\* = 1.5, the gel/fluid boundary falls between T\* = 0.45 and T\* = 0.643 —
exactly between rung 6B and production.** 6B is a gel; production is a fluid. The H8 assembly gap
(2/20 against 13/20) was a phase difference, produced by holding `kT` fixed while `chi_TT` changed.

### Scoring the registered predictions

| # | prediction | outcome |
|---|---|---|
| 1 | 6B at T* = 0.45 reads gel | **CONFIRMED** (1.00/0.78) |
| 2 | production at T* = 0.643 reads gel or marginal | **WRONG.** It reads comfortably fluid (0.44 against a 0.70 threshold) |
| 3 | T* near 1.1 reads fluid | **CONFIRMED** |
| 4 | at matched T*, 6B assembles as well as production | Stage 3, running |

Prediction 2 is recorded as a miss. The reasoning behind it -- that everything below Cooke's kT = 1.1
must be gel-ward -- was wrong: in this model the fluid band extends well below Cooke's reference
value, down to about T* = 0.5 at w* = 1.5. Being below Cooke's point does not mean being in the gel.

### The registered high-T threat did NOT materialise

Bond stiffness is not rescaled with T*, so chains were expected to go floppy at the top of the range.
Mean bond length at w* = 2.0 runs 1.013 / 1.011 / 1.010 / 1.015 / 1.017 / 1.015 / 1.025 across
T* = 0.375 to 1.8, against a rest length of 1.0. Flat. The threat is retired for this range.

## STAGE 3 — registered before running

Two arms, both solvent-free 6B chemistry, both moved into the fluid band. Single variable against the
H8 6B arm in the first case:

| arm | change from H8's 6B | T* | w* | phase-map cell |
|---|---|---|---|---|
| **6Bf** | `kT` 0.45 -> 0.643 only | 0.643 | 1.5 | fluid 1.00/0.44 |
| **6Bo** | `kT` -> 1.1, `rc` 2.5 -> 3.0 | 1.10 | 2.0 | fluid 1.00/0.21, the most mobile fully-condensed cell |

Seeds 400-419, 20 per arm, 1e6 steps, checkpoint 10,000 — identical to H8 otherwise, so the
comparators are H8's 6B (gel, 2/20) and H8's production (fluid, 13/20).

```
PASS  iff  6Bf seeds-with-enclosure >= 8/20  AND  Fisher one-sided vs H8's 6B (2/20) p <= 0.05
```

8/20 is set below production's 13/20 deliberately: the claim under test is that the *phase* explains
the gap, not that the reduced chemistry must match production exactly.

**Threat, stated before running.** The phase map used a PLANTED ring at N = 70 in L = 45; the
emergence runs use a DISPERSED start at N = 160 in L = 65. Bead densities are 0.173 and 0.189 per
sigma^2, close but not equal, and a planted membrane's phase need not be the phase a dispersed system
condenses into. If 6Bf fails, re-measuring the phase at the emergence density is the first check, not
a new hypothesis.
