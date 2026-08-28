# Pre-registration: does head-area geometry select the vesicle phase?

**Registered:** 2026-08-28, before any `sigma_head != 1.0` run existed.
**Status at registration:** harness built and cost-measured; zero outcome data.

---

## 1. Why this experiment

Every *energetic* lever on closure has been measured and come back null: `chi_TW` (null with power,
+2.8 ± 2.8 vs −5.2 ± 4.2 ε), `chi_HH` (4/13 vs 2/13, p = 0.64), lipid shape by tail count (dissolves
to micelles), leaflet thickness asymmetry (0/5), leaflet area asymmetry (0/5), and more material
(0/5, worse). `docs/WHY_THE_ORACLE_DOES_NOT_TRANSFER.md` establishes that the one thing that *does*
produce vesicles — YLZ's `beta` — is spontaneous curvature supplied as an **input**, and correctly
refuses to import it.

The geometric route is the bottom-up origin of that same quantity. The packing parameter
`P = v / (a0 * l)` selects morphology (< 1/3 micelles, 1/2–1 vesicles/flexible bilayers, ≈ 1 planar),
and spontaneous curvature is the mesoscale shadow of `P != 1`. `_mixture.chain_bonds` already records
that the **tail** axis cannot move `P` ("both v and l proportional to the tail bead count, so P is
INDEPENDENT of tail length"). That leaves head area `a0`, which had no knob at all: `field.Field`
carried one scalar `sigma` for every bead. Cooke–Deserno calls the head diameter "the single most
important parameter in the model".

`sigma_species` (added 2026-08-28, exact no-op at its default, transformer identity re-verified at
1e-13 on the new path) makes `a0` reachable for the first time.

## 2. Hypothesis

**H1.** Increasing `sigma_head` raises `a0`, lowers `P`, and there exists a `sigma_head` window in
which closed vesicles form from a dispersed start in the 3-D solvent-free transformer model, where
`sigma_head = 1.0` does not.

Stated so it can be wrong: if no arm forms vesicles, or if every arm including the baseline forms
them equally, H1 is not supported.

## 3. The strongest baseline, named in advance

**`sigma_head = 1.0`** — the current model, the exact configuration every result to date was measured
under, run in the identical 3-D solvent-free harness with identical N, L, kT, steps, seeds and
engine. It is not a weakened straw arm: it is the model as it stands.

## 4. Arms and budget parity

| | |
|---|---|
| arms | `sigma_head` ∈ {1.0 (baseline), 1.2, 1.4, 1.6, 1.8} |
| lipids | 200, all four-tail branched (`frac_short = 0.0`), 1000 beads |
| dimension / solvent | 3-D, `phi = 0.0` (solvent-free, `solvent_averaged_chi`) |
| box | L = 25 |
| chemistry | `chi_HT = -0.25`, `chi_WW = 0.50` (the amphiphile values); unchanged across arms |
| kT | 0.45 |
| engine | `VIVARIUM_ENGINE=transformer` for every arm |
| seeds | screen 3/arm; decision run 10/arm |
| steps | screen 100,000; decision run 1,000,000 |

Every arm gets identical budget. `sigma_head` is the **only** variable that differs between arms.
Measured cost: 2.90 ms/step, so a decision run is ~48 min/seed.

## 5. Primary endpoint and the gate

A seed **forms** iff `nves >= 1` at **two or more consecutive checkpoints** (debounced; the project
has twice been burned by single-checkpoint flicker, measured at a 0.057 rate) **and** an
isolated-cluster render confirms a closed shell. Metric and picture are both required — this project
records that "the render and the metric have each flattered the other".

Note, fixed in advance: `_lumen_field.vesicle_call`'s size clause is a **2-D** formula (contour `n`,
`R = n/2pi`). It is NOT used here. The 3-D endpoint is `nves` + render, as above.

### Gate (mechanical, in code, no judgment)

```
PASS iff  max over sigma_head > 1.0 arms of formed_fraction  >= 0.6   (>= 3/5 at n=5, >= 6/10 at n=10)
     AND  baseline (sigma_head = 1.0) formed_fraction        <= 0.2
     AND  Fisher one-sided p(best arm vs baseline)           <= 0.05
```

Any other outcome is a FAIL. The margins above do not move once data exists.

### AC-2: the criterion we can fail by winning

**If `sigma_head = 1.0` also forms at >= 0.6**, then vesicles in this harness are produced by the move
to 3-D solvent-free — dimensionality and the removal of the broken explicit solvent — and **not** by
head area. H1 is then NOT supported by this experiment, regardless of how the other arms look, and
the honest headline is "3-D solvent-free produces vesicles; geometry was not shown to matter."

This is the outcome a merely-stronger configuration would produce, and it is registered as a failure
of the stated mechanism on purpose.

## 6. Screen

3 seeds/arm at 100k steps, on validation only. Purpose: decide whether the 1M-step decision run is
worth 25 seed-runs. Escalate to the decision run iff any arm reaches >= 2/3 formed, or shows a
monotone trend in largest-cluster/`hollow` across `sigma_head`. Screen thresholds are calibrated on
these runs and are therefore **fitted, not predictive**; the decision run is the real test.

## 7. What each outcome means — written before the data

- **PASS.** Head area moves the phase. Spontaneous curvature is then earned from molecular geometry
  rather than imported as `beta`, which is what `WHY_THE_ORACLE_DOES_NOT_TRANSFER` asks for and what
  no lever has yet delivered. This would be the project's first positive closure lever.
- **FAIL, no arm forms.** The geometric route is dead in this model at this box and duration, and the
  remaining candidates are branch count (chains per head, currently hardcoded to 2) and a
  momentum-conserving thermostat. Report as a negative; it removes the last untested cheap lever.
- **FAIL via AC-2 (baseline also forms).** The interesting result is then about dimensionality, not
  geometry, and the paper's "2-D closure is encounter-limited" analysis gains a direct 3-D control.
  Report it as such and do not claim the geometry mechanism.
- **Ambiguous / underpowered.** Report as underpowered and state the observed effect size. Do not
  reclassify as a partial success. This project has had three n=5 effects shrink on replication, one
  by a factor of 6.

## 8. Threats to validity, acknowledged now

- **Task chosen by us.** The box, lipid count and duration are ours. The `sigma_head` values are a
  guess at where `P` crosses the vesicle window; if the window lies outside {1.0 … 1.8} a null is
  uninformative rather than evidence of absence. A null will say so.
- **Two variables changed vs the 2-D production system** (dimension AND solvent). That is precisely
  why the baseline arm is run in the same harness: the comparison between arms is single-variable
  even though the harness differs from the paper's.
- `sigma_head` changes head–head, head–tail *and* head–water contact distances together. It is a
  geometric change, not a clean `a0`-only change; no bead model can separate them.
- Screen thresholds are fitted (§6).

## 9. Amendments

Appended below, dated, never by rewriting the above.

### Amendment 1 — 2026-08-28: the registered box is a gas, not a liquid

**What was wrong.** §4 fixed `L = 25` for 200 lipids (1000 beads). That is a packing fraction of

    phi = 1000 * (pi/6) / 25^3 = 0.034

i.e. a dilute gas, **16x thinner than the 2-D production system this experiment is meant to speak
to**, which runs at phi = 0.55. The error is mine and it was in the pre-registration, not in the
result.

**Evidence it matters, from the one run that completed before the sweep was stopped.**
`sigma_head = 1.0`, seed 1: `largest` was 27 molecules at step 5,000 and **28 at step 100,000**.
The aggregate does not coarsen — at that density micelles form quickly and then have to find one
another by diffusion, which does not happen on this budget. A screen there cannot discriminate
between `sigma_head` arms, because no arm can reach a closable aggregate regardless of its geometry.
A null would have been a statement about the box, not about head area.

**Correction.** `L = 13`, giving phi = 0.24 -- a liquid, in the band the 3-D solvent-free literature
assembles at, and comparable in spirit to the 2-D system's 0.55 without crowding a 200-lipid vesicle
(a 200-lipid shell at ~1.5 sigma^2 per lipid has R ~ 4.9 sigma, comfortably inside L = 13).
Everything else in §4 is unchanged, and **the gate in §5, the AC-2 clause and all margins are
untouched.**

**Status of the data already collected.** The single phi = 0.034 row is preserved as
`docs/results/head_area_sweep_L25_phi0.034.tsv` and is NOT pooled with the corrected screen. The
results schema gains an explicit `L` column so this class of confusion cannot recur silently.

**Why this is an amendment and not a fix.** No `sigma_head != 1.0` run has been executed at any
density. The correction is to the harness, decided from an arithmetic property of the box and one
baseline run, with no treatment-arm outcome in evidence. Recording it here rather than editing §4 so
the original error stays visible.

### Amendment 2 — 2026-08-28: L = 13 was wrong in the other direction; L = 22. And Amendment 1's diagnosis is partly withdrawn.

**L = 13 is jammed, measured.** At `L = 13` the dispersed start is not dispersed: `largest = 199 of
200 at step 0`. Every lipid is already inside one connected cluster, so there is no self-assembly to
observe. It is also 16.6 ms/step against 2.9 at L = 25, because the box drops below three cells per
axis and the neighbour list falls back to the dense path. Amendment 1 replaced a gas with a solid.

**The measured window** (`largest` at step 0, 200 lipids, seed 1, cluster cutoff 1.4 sigma):

| L | phi | largest @ step 0 |
|---|---|---|
| 13 | 0.238 | 199 |
| 15 | 0.155 | 184 |
| 16 | 0.128 | 158 |
| 17 | 0.107 | 62 |
| 18 | 0.090 | 55 |
| 20 | 0.065 | 31 |
| **22** | **0.049** | **9** |
| 25 | 0.034 | 8 |

**Corrected value: L = 22.** The densest box that still gives a genuinely dispersed start (9 of 200),
at 1.4x the number density of the registered L = 25, keeping the fast cell-list path (7 cells/axis).

**PARTIAL WITHDRAWAL OF AMENDMENT 1.** Amendment 1 asserted the L = 25 stall was a density artifact —
aggregates too dilute to find one another. Re-reading that run against the step trace, most of the
growth happened by step 5,000 (`largest` 8 -> 27) and then nothing moved for the remaining 95,000
steps. That is the signature of a **stable preferred aggregate size**, which is what a micelle is and
what `P < 1/3` predicts. So the baseline may have been reporting the physics, not a broken box, and
"the aggregate does not coarsen" in Amendment 1 was too strong.

Both readings survive the evidence available, and they are not distinguishable from one baseline run.
Stating the ambiguity rather than picking the convenient half. L = 22 is chosen because it is denser
while still dispersed, so a null there is harder to attribute to density; it is NOT chosen because
L = 25 is known to be wrong.

**Unchanged:** the gate in §5, the AC-2 clause, every margin, the arms, and the endpoint. Only the box
moves, and it moves before any treatment-arm run exists at any density.

---

## 10. Outcome — screen, 2026-08-28

**Gate output, verbatim:**

```
  verdict: FAIL
  fractions: {1.0: 0.0, 1.2: 0.0, 1.4: 0.0, 1.6: 0.0, 1.8: 0.0}
  best_arm: 1.2
  best_formed: 0/3
  baseline_formed: 0/3
  fisher_p: 1.0
  ac2_triggered: False
```

**0 of 15 runs formed a vesicle.** Every arm is 0/3, including the baseline, at L = 22 / 100k steps.
The accidental L = 25 (phi = 0.034) sweep that ran in parallel adds **0 of 12**, across the same arms
at a fourth of the density. Twenty-seven runs, no closure anywhere.

**Escalation rule (§6) does not fire.** No arm reached >= 2/3, and mean `largest` across
`sigma_head` = 1.0 → 1.8 is 38.3, 39.3, 43.3, 40.0, 36.7 — **not monotone** (computed, not eyeballed).
The decision run is therefore NOT authorised by this pre-registration. Spending 25 seed-runs at 1M
steps would be spending budget the screen says is unlikely to pay.

**What this does and does not establish.** It does not falsify H1. The screen was 100k steps, and
formation in the 2-D system takes 6e5–1e6; a null at 100k is consistent with "too short" as much as
with "no effect", and §8 registered exactly that risk. What it does establish is that head area does
not produce a *fast* route to closure at this box, duration and lipid count, which is the question the
screen was built to answer.

**AC-2 did not trigger** (baseline 0/3), so the "3-D solvent-free is what did it" alternative is not
in play either — nothing formed under any condition.

**Status: H1 not supported by the screen; not falsified. Decision run not authorised.**
