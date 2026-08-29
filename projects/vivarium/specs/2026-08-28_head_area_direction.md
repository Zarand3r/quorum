# Pre-registration H2: a SMALLER head, i.e. the other direction

**Registered:** 2026-08-28, after the H1 screen returned FAIL and before any `sigma_head < 1.0`
production run existed. One 20k-step feasibility probe at `sigma_head = 0.85` was run to measure cost
and confirm the harness works; its numbers are quoted in §2 as motivation and are **not** evidence for
H2.

Supersedes nothing. `specs/2026-08-28_head_area_geometry.md` (H1) stands as a recorded negative.

---

## 1. What H1 established, and the mistake it exposed

H1 swept `sigma_head` **upward** (1.0 → 1.8) and returned 0 formations in 27 runs. Buried in that null
is the reason:

| sigma_head | burial (tail beads buried), 3 seeds | mean |
|---|---|---|
| 1.0 | 34.6, 46.0, 63.7 | 48.1 |
| 1.2 | 32.1, 38.8, 44.8 | 38.6 |
| 1.4 | 30.6, 33.0, 35.2 | 32.9 |
| 1.6 | 19.4, 19.4, 24.5 | 21.1 |
| 1.8 | 19.4, 19.6, 20.9 | 20.0 |

Spearman rho = **−1.000** across arm means; 79 concordant against 11 discordant pairs across all 15
runs. **The knob works. It was pointed the wrong way.**

`P = v / (a0 * l)`. A larger head raises `a0` and therefore **lowers** `P`, toward the micelle band
(`P < 1/3`). This project's standing complaint is that it *keeps producing micelles* — so `P` was
already too low and H1 lowered it further. Falling burial is that, measured: less tail shielding,
looser aggregates, further from lamellar.

**Direction is fixed by theory, not by the data.** `P` must go UP to reach the bilayer window
(`1/2 < P < 1`), so `a0` must go DOWN.

**External anchor, not our taste.** Cooke–Deserno (`cooke_deserno.py`, already vendored here) is a
solvent-free 3-D lipid model that *does* self-assemble vesicles, and it uses head diameter **0.95
sigma against tail 1.0 sigma** — its own docstring calls the smaller head diameter "the single most
important parameter in the model". Our model sits at 1.0 : 1.0, on the wrong side of a known-working
reference. The arms below bracket it.

## 2. Hypothesis

**H2.** Reducing `sigma_head` below 1.0 raises `P` and crosses the model out of the micelle band, so
that a closed vesicle forms from a dispersed start where `sigma_head = 1.0` gives only micelles.

Motivation from the probe (NOT evidence): at `sigma_head = 0.85`, N = 400, burial reached 61.7 by
step 20,000, above anything H1 reached in 100,000 steps. `largest` still plateaued at 48 of 400.

## 3. Baseline, named in advance

**`sigma_head = 1.0`**, re-run in this harness at the new N and L. Not reused from H1 — N, L and
duration all differ, so the H1 baseline is not a valid control here.

## 4. Arms and budget parity

| | |
|---|---|
| arms | `sigma_head` ∈ {1.0 (baseline), 0.9, 0.75, 0.6} |
| lipids | 400 four-tail branched, 2000 beads |
| box | L = 28 (phi = 0.048; dispersed start verified, largest = 12/400 at step 0) |
| dimension / solvent | 3-D, `phi = 0.0` solvent-free |
| chemistry, kT, engine | `chi_HT = -0.25`, `chi_WW = 0.50`, kT = 0.45, transformer |
| seeds | 3/arm (screen) |
| steps | 100,000 |

Measured cost 10.75 ms/step at N = 400, so ~18 min/run, ~3.6 h for the screen. `sigma_head` is the
only variable differing between arms.

## 5. Endpoint and gate

Unchanged from H1: a seed **forms** iff `nves >= 1` at two or more consecutive checkpoints AND a
render confirms.

```
PASS iff  max over sigma_head < 1.0 arms of formed_fraction >= 0.6
     AND  baseline (1.0) formed_fraction <= 0.2
     AND  Fisher one-sided p <= 0.05
```

### Secondary, registered because the primary may be too strict for 100k steps

**S1 — escape from the micelle band.** Every run to date, across three densities, two lipid counts and
five head sizes, has plateaued at `largest` in 26–72 regardless of available material. If any
`sigma_head < 1.0` arm reaches **`largest >= 150` of 400** in >= 2/3 seeds while the baseline stays
below 100, the preferred aggregation number has been broken even if nothing closes. That is the
mechanism H2 actually predicts, and it is reportable on its own.

### AC-2: the criterion we can fail by winning

If the **baseline** also escapes (S1) or forms, the cause is N = 400 / L = 28 — more material — and
not head area. H2 is then unsupported however good the small-head arms look.

## 6. What each outcome means — written before the data

- **PASS, or S1 fires only in small-head arms.** Head area moves the phase and the direction is now
  established. Escalate to a decision run at 1M steps.
- **Null on both.** Head area is not the lever in either direction, across 0.6–1.8. The remaining
  geometric lever is **branch count** — `chain_bonds` hardcodes two chains per head, and a third
  raises `v` at fixed `l`, which is the strongest term in `P` and the one no experiment here has
  touched. Report the null and go there.
- **AC-2 fires.** Report it as a material-quantity result, not a geometry one.

## 7. Threats

- Direction was inferred from H1's `burial` trend, which is **post-hoc on a null**. It is used only to
  choose the sweep direction; H2 is tested on fresh runs. No H1 data enters the H2 gate.
- 100k steps against a 2-D formation time of 6e5–1e6. A null is consistent with "too short". S1 exists
  because it is measurable within the screen budget.
- N and L both differ from H1, so H2's arms are comparable to each other and NOT to H1's.
- `sigma_head` moves head–head, head–tail and head–water contact distances together (unchanged from
  H1; no bead model separates them).

## 8. Amendments

*(none yet)*

---

## 9. Outcome — screen, 2026-08-28

**Gate output, verbatim:**

```
  verdict: FAIL
  s1_escape_fraction: {0.6: 0.0, 0.75: 0.0, 0.9: 0.0, 1.0: 0.0}
  fractions: {1.0: 0.0, 0.9: 0.0, 0.75: 0.0, 0.6: 0.0}
  best_arm: 0.9
  fisher_p: 1.0
  ac2_triggered: False
```

**0 of 12 formed. S1 did not fire in any arm** — the threshold was `largest >= 150` and the largest
value observed anywhere in the sweep was **78**. Both registered endpoints fail.

`largest_max` by arm: 1.0 → [45, 47, 48]; 0.9 → [38, 61, 63]; 0.75 → [39, 51, 62]; 0.6 → [58, 70, 78].

**Combined with H1, head area has now been swept from 0.6 to 1.8 — a threefold range spanning both
sides of the Cooke-Deserno reference ratio — with zero vesicles in 39 runs.**

### An unregistered observation, recorded as a lead and NOT as a result

At `sigma_head = 0.6`, all 3 seeds exceed the baseline's maximum (58, 70, 78 against 45, 47, 48).
Under exchangeability that is exact one-sided p = 1/C(6,3) = **0.050**, and mean burial also rises
(71.3 against 58.3) while the intermediate arms show neither.

This is **not** a result and is not claimed as one:

- It is not the registered endpoint. S1 was `>= 150`; 78 is half that, and the threshold was fixed
  before the data precisely so it could not be renegotiated afterwards.
- n = 3, at p exactly on the conventional line, on the smallest arm — the shape of finding this
  project has watched shrink on replication three times, once by a factor of six.
- Burial is **not** monotone across the arms (58.3, 59.9, 57.2, 71.3), so the mechanism story that
  motivated H2 is not cleanly supported even by the suggestive arm.

If it is worth anything it is worth a fresh pre-registration at `sigma_head <= 0.6` with n >= 10 and
its own endpoint. It does not license reading H2 as a partial success.

**Status: H2 not supported. Head area is not the lever, in either direction, over 0.6-1.8.**

### The invariant that keeps surviving

Across 39 runs spanning three densities (phi 0.034-0.060), two lipid counts (200 and 400), two box
sizes and head sizes from 0.6 to 1.8, **the largest aggregate has never left the range 13-78**, and at
N = 400 the baseline reproduces at 45, 47, 48 — a spread of 3 with 400 lipids available. A stable
preferred aggregation number that survives this much variation is the definition of a micelle phase,
and it is a stronger and more reproducible measurement than anything the closure endpoint has
produced. Per §6, the next lever is **branch count**: `chain_bonds` hardcodes two chains per head, and
a third raises `v` at fixed `l`, which is the largest term in `P` and the only one no experiment here
has touched.

---

## ERRATUM — 2026-08-29: the primary endpoint could not fire in 3-D

**The `formed` endpoint of this experiment is WITHDRAWN as uninformative.**

`n_enclosed`, `count_vesicles` and `vesicle_call` are **two-dimensional detectors**.
`_lumen_field._interior_mask` builds its occupancy grid as `np.zeros((n, n))` -- two axes -- and the
flood fill uses 4-connectivity `((1,0),(-1,0),(0,1),(0,-1))`. Given 3-D coordinates it projects them
onto a plane, which fills the disc and leaves no interior region to find.

Known-answer test, run 2026-08-29:

| planted structure | correct answer | measured |
|---|---|---|
| 2-D ring, 160 lipids | nenc 1, nves 1, call True | **[1,1,1,1], 1, True** |
| 3-D sphere, 200 lipids | nenc 1, nves 1 | **[0,0,0,0], 0, False** |

The planted sphere is genuinely hollow -- its lipid beads span r = 2.66 to 6.66 about the centroid
with the five-band inner-head / tail / outer-head profile of a bilayer shell.

**Therefore `nves >= 1` could never have fired in any 3-D run, and "0 formations" measures the
instrument, not the physics.** Every closure claim in this spec is withdrawn.

**What survives, because it never touched the grid:**

- **S1** (`largest >= 150`) is a cluster count. It did not fire in any arm. Stands.
- The aggregation-number invariant (13-78 across 39 runs; 45, 47, 48 at N = 400). Stands.
- The `burial` trend against head size (Spearman rho = -1.000). Stands.

So **"head area does not move this model out of the micelle phase" stands**; **"head area does not
produce vesicles" was never tested** and is withdrawn.

**Cause, recorded plainly.** A 2-D-validated endpoint was carried into 3-D and 39 runs were scored
against it without once planting a 3-D vesicle to confirm it read 1. `CLAUDE.md` requires exactly that
check ("validate against a known-answer case AND a null case"), and
`docs/MEASUREMENT_DISCIPLINE.md` records fifteen prior defects, "all instrument bugs, none physics".
This is the sixteenth. The check costs ninety seconds.

**Blocking item before any 3-D closure experiment:** generalise `_interior_mask` to a 3-D occupancy
grid with 6-connectivity, then gate it on the planted sphere (must read 1) and a planted micelle
(must read 0).
