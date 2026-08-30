# Pre-registration: a vesicle at a size where a vesicle can exist

**Registered:** 2026-08-30, before any run at N >= 1000 existed.

---

## 1. Why every previous attempt could not have worked

A vesicle is a closed shell of a membrane with finite thickness. It is only a coherent object if its
radius comfortably exceeds that thickness. Measured here: bilayer thickness ~4.0 sigma (planted
reference 4.40; the Cooke-Deserno oracle reads 4.05 under the same instrument).

| N lipids | vesicle R | **R / thickness** | patch side |
|---|---|---|---|
| 200 | 3.3 | **0.82** | 11.6 |
| 400 | 4.6 | **1.16** | 16.4 |
| 1000 | 7.3 | 1.83 | 26.0 |
| 1600 | 9.3 | 2.32 | 32.9 |

**Every sweep in this project used N = 200 or 400**, i.e. a shell no thicker than its own membrane.
Head area, temperature, attraction width and excluded volume were each swept across wide ranges
against a target that could not exist. That is a better explanation of four null results than any of
the four hypotheses proposed during them, and it required arithmetic rather than simulation.

## 2. The second condition, from the paper rather than from us

Cooke & Deserno (JCP 123, 224710, 2005), section III: *"a bilayer patch quickly self-assembled,
which, at the correct box size could zip up to span the box... **If the box was too big, the patch
either remained free, or (sometimes) closed upon itself to form a vesicle.**"*

A patch that spans a periodic box has no edges and therefore nothing to gain by closing. Every box in
this project was sized for density and never checked against the spanning threshold. Box must exceed
the patch side (26.0 sigma at N = 1000).

## 3. Hypothesis

**H3.** At N = 1000 (R/thickness = 1.83) with the box above the spanning threshold, a dispersed start
produces a closed vesicle, where the same chemistry at N = 200-400 cannot.

## 4. Arms

| | |
|---|---|
| lipids | **1000**, CD architecture: linear 3-bead (1 head, 2 tails), `sigma_head` 0.95 |
| box | L in {30, 36} -- 15% and 38% above the 26.0 spanning threshold |
| chemistry | `cooke_chi`: tail-tail attraction only, heads purely steric |
| w_c / kT | 1.4 / 1.0 -- inside the fluid band of our own reproduced phase map |
| bonds | k_bond 30 (CD's stiffness constant) |
| start | random dispersion |
| engine | ours, `VIVARIUM_ENGINE=transformer` |
| seeds | 3 per box |
| steps | 400,000 (CD reach a bilayer at 4000 tau, dt 0.01, i.e. 400k) |

**Control, run in the same grid:** the vendored `cooke_deserno.py` oracle at identical N, L and
parameters. Ours and theirs are scored by the same instrument, so a disagreement localises to the
engine and an agreement validates both.

Measured cost: 23.1 ms/step at 3000 beads, so ~2.6 h per seed; 12 runs fit in one parallel pass.

## 5. Endpoint

Scored with `bilayer_metrics`, validated on four synthetic controls (vesicle / sheet / blob / gas)
that it must SEPARATE, not merely score one well:

    vesicle   thickness 2.85   hollow 0.000   L1/L3 0.83
    sheet     thickness 7.00   hollow 0.573   L1/L3 0.21
    blob      thickness 3.11   hollow 0.987   L1/L3 0.89
    gas       thickness 0.10   hollow 0.493   L1/L3 0.83

A seed **forms a vesicle** iff, at two or more consecutive checkpoints:

    hollow < 0.25          (vesicle 0.000 vs sheet 0.573, blob 0.987)
    AND aniso L1/L3 > 0.5  (isotropic -- excludes the sheet at 0.21)
    AND thickness > 3.0    (a real bilayer -- excludes the gas at 0.10)

and a render confirms it. Metric AND picture, because in this project each has flattered the other.

```
PASS iff  any box gives >= 2/3 seeds forming, in OUR engine
```

### AC-2, the criterion we can fail by winning

**If the CD oracle also fails to form a vesicle at these N and L**, then the recipe is not sufficient
as stated and a null in our engine says nothing about our engine. H3 would be untested rather than
refuted, and the honest report is about the recipe, not about vivarium.

### AC-3

**If both form**, the engine is validated for 3-D vesicle assembly and the four null sweeps are
explained by infeasible geometry alone.

## 6. What each outcome means -- written before the data

- **Ours forms, oracle forms.** The engine can assemble a 3-D vesicle. Everything earlier was a
  size artifact. This is the project's first 3-D result.
- **Oracle forms, ours does not.** The difference is in our engine, and it is now bisectable against a
  working control: chain stiffness (CD's 1-3 spring is permanently stretched at rest length 4 sigma,
  ours merely makes straight the minimum), bond form (FENE vs harmonic), core form (divergent WCA vs
  bounded quadratic).
- **Neither forms.** N = 1000 is still too small (R/thickness 1.83), or 400k steps too short. Escalate
  to N = 1600 (R/thickness 2.32) before concluding anything.
- **Ours forms, oracle does not.** Suspect our instrument or harness before celebrating.

## 7. Threats

- N = 1000 gives R/thickness 1.83, workable but not comfortable; 1600 would be safer and costs ~1.6x.
- Bigger box prevents spanning but lowers density (0.111 at L=30, 0.070 at L=36, against CD's 0.192),
  which slows coarsening. The two requirements pull against each other and 400k steps may not suffice.
- Vesicle formation is explicitly stochastic in the source ("sometimes"), so 3 seeds may under-power.
- Our thickness (3.3) is below the oracle's (4.05), so our R/thickness is slightly better than tabled.

## 8. Amendment 1 — 2026-08-30: the oracle control is STAGED, not dropped

**Measured before the run, not extrapolated:** 2000 steps at N = 1000, both engines, same box.

    ours    13.6 s   ->  400k steps ~ 0.8 h
    oracle 416.2 s   ->  400k steps ~ 23.1 h

The oracle is **30x slower** (dense numpy, no efficient neighbour list at this size). Six oracle runs
is ~23 h of wall clock even fully parallel, against ~1 h for our six.

**Staged instead.** Our engine runs first at full power (2 boxes x 3 seeds). The oracle control runs
only if our engine FAILS, which is the branch where AC-2 actually matters -- its job is to decide
whether a null in our engine indicts the engine or the recipe. If our engine forms a vesicle, AC-3 is
satisfied without it, and the oracle becomes a confirmation rather than a discriminator.

**This is a deviation and it weakens the design**: if ours forms, the result rests on our engine and
our instrument with no simultaneous external control at this N. Stated here rather than discovered in
the writeup. The instrument itself is separately validated against four synthetic controls and against
the oracle at N = 200, where it correctly read a bilayer sheet of thickness 4.05.
