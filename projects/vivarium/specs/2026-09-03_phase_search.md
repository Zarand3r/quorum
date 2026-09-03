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
