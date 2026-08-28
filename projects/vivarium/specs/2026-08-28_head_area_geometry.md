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

*(none yet)*
