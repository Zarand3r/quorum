# Reviewer handoff — autonomous roadmap loop, 2026-09-16

**Loop ran 14:00–17:30 PDT (3.5 h of a 12 h budget), 24 ticks, 5 cycles of implement → review →
document. Stopped early, deliberately, on the contract's re-assessment condition.** Contract:
`LOOP_PLAN.md`. Tick log: `LOOP_STATE.tsv`. Nothing pushed; `origin/main` still `f96c717e`.

## Why it stopped

**The registered gate on the one active physics experiment cannot return a decision.**
BF's AC-2 (`specs/2026-09-16_chain_bending_form.md`) asks whether the derived `k_θ` reproduces
Cooke's bending stiffness within ±20%. Twelve seeds:

```
3.1549 3.6665 3.4567 3.7036 3.5614 3.1374 3.3452 3.0435 3.1172 3.1245 3.5306 3.7898
mean 3.3859   sd 0.2653   sem 0.0766   2sem interval [3.2328, 3.5391]
registered band 3.2727 - 4.9091        VERDICT: INDETERMINATE
```

The interval straddles the lower bound. **This is not a near-miss to be resolved with more seeds** —
adding seeds until it lands on one side is p-hacking, and the sample size was pre-committed before
the last six ran.

**The criterion appears mis-specified, and only a person should change it.** AC-2 targets `k_θ` but
measures `kT/Var(δ)`, the chain's *net* bending stiffness. Those differ systematically here because
the molecule's own tail–tail attraction bends it: the isolated lipid's **T = 0 ground state is bent
23.86°**, and setting `chi_TT = 0` removes that entirely (0.61°). So the net stiffness sits ~17%
below `k_θ` for a physical reason, and the ±20% band is the same size as the effect. Three ways out,
all judgement calls:

1. re-specify AC-2 to measure `k_θ` directly (e.g. with `chi_TT` off), or
2. widen the band with a stated rationale, or
3. accept the derived value and record the deficit as a known offset.

**I did not amend it.** The spec's own rule is that a gate may be amended only *before* its data
exists. It exists now.

## What is ready to use

**The angle potential is built and passes AC-1**, in both force paths, and **ships off** (`k_θ = 0`,
bit-identical to before — no existing result moves).

| gate | result | required |
|---|---|---|
| `F = −∇U` | 9.6e-07 | < 1e-4 |
| `ΣF = 0` | 1.1e-13 | < 1e-9 |
| field vs attention, `k_θ` 0/1/10/50 | **0.000e+00** | exactly 0 |

Turn it on with `VIVARIUM_K_THETA`, and set `VIVARIUM_BEND=0` to remove the 1-3 spring it replaces.
`tests/test_angle_potential.py`, 17 tests, four injected bugs verified to trip.

**R1 was read too tightly and is now corrected in `SUMMARY.md`.** A three-body force is *two*
composed attention passes — accumulate a per-bead quantity from a masked neighbourhood, then
redistribute — not one masked head. The many-body term has always been written that way and is in
the production path. I briefly reported that an angle term might be barred by transformer-only; it
is not.

## What is parked, and why

- **D9 (ribbon spacing).** Three cycles, no installable value. The constant is named
  (`_mixture.RIBBON_GAP_BRANCHED`) and overridable, **value unchanged at 2.05**. A T = 0 spanning
  calculation gives **1.903 σ** but ran **dry**, and the production membrane sits in solvent. The
  finite-T route failed at N = 28: the ribbon splits into two 14-lipid blobs before it equilibrates
  (§5b D9c). Needs a substantially larger ribbon.
- **The token-channel decision.** Untouched by design — it needs a person, and it still blocks any
  push. `1 failed / 296 passed / 14 skipped`; the one failure is that blocker.

## Instrument defects found and fixed this session

Every one was mine, and each was caught by the review mode rather than by the run that used it.

| defect | how it showed |
|---|---|
| fragmentation guard clustered **heads at 2.6**, not beads at 1.4 | read **14** on a planted 28-lipid ribbon — fails a known answer by construction. Third implementation of a concept `vesicle_gate._aggregates` already owns (R8) |
| angle sampler had **no minimum-image** correction | ⟨δ²⟩ 1.4048 → **0.1770** after the fix, which then matched 0.1817 measured independently on 14 real melt states |
| `n_water = 0` in a finite-T run | no hydrophobic effect at all; `chi_WW = 1.00` is the most cohesive species |
| defensive branch guarded **θ = π**, which is harmless | the real NaN is at **θ = 0**; injecting the naive form tripped no test, which is how it was found |
| system-size check on the T=0 scan | passes **by construction** — a periodic crystal's energy per lipid cannot depend on cell count. Differences were 1e-15 |
| verdict declared on **one seed** with a 0.8% margin | seed spread is **7.2%** — the FAIL was retracted |

New rules: **22** (expand a potential only around a stationary configuration), **23** (a modulus is a
free-energy second derivative, not `V''(0)`), **24** (validate the guard, not just the metric).

## Suggested next steps

1. **Decide AC-2** — re-specify, widen, or accept. Blocks BF entirely.
2. **Decide the token channel** — blocks the push, and blocks the rest of the MLP work.
3. D9 needs a bigger ribbon, or drop it: the evidence now says 2.05 is closer to right than the
   "16% too dilute" framing implied.
