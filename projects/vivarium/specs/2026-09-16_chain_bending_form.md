# BF — replace the 1-3 distance spring with an explicit angle potential

**Registered 2026-09-16, before any run.** 2-D, production chemistry, one term changed.

## Why

The chain stiffener in this model is a **distance** spring between beads 1 and 3 at rest length
2σ (`field.py:_springs`). Cooke, Kremer & Deserno (PRE 72, 011506, 2005) use the same device but
pre-stretch it to 4σ against **FENE** bonds, which are inextensible. Ours are harmonic, so the same
pre-stretch inflates the molecule instead of straightening it — measured at **+67% bond length**, and
retracted (§7 of the roadmap).

What the term actually delivers at rest length 2σ, verified on the shipped `Field` this session:

| quantity | value | how established |
|---|---|---|
| harmonic coefficient at straight | **0** | bend-mode Hessian eigenvalue 6e-6 vs 600 for stretch |
| potential shape, bonds free to relax | **V = 2.083·δ⁴**, monotonic from δ=0 | energy minimised over both bond lengths at fixed δ |
| effective bending modulus at kT=0.45 | **2.69 ε/rad²** | applied torque on a simulated chain; variance estimator `kT/Var(δ)` agrees to 1% |

**And it has a visible morphological consequence, which is the real motivation.** With nothing to
resist it, the lipid's own two tails attract each other into a permanent kink: the isolated 5-bead
molecule at T = 0 relaxes to a state **bent 23.86°** with ⟨b⟩ = 1.014390, accounting for 91% of the
melt bond-length excess before any thermal energy is added. Setting `chi_TT = 0` removes it completely
(bend 0.61°, ⟨b⟩ = 1.000012). Every lipid in this model is therefore permanently bent by roughly a
quarter-turn of its own doing — a chain with real bending stiffness would resist that.

So the departure from nature is the **functional form**, not the absence of stiffness. A real acyl
chain resists bending harmonically at every deviation; this one is soft near straight and stiff far
from it. Two errors were made reading this and are recorded so they are not repeated: computing
`V(δ)` with the bond length **pinned** (not an equilibrium — 9.3 ε/σ of unbalanced force) produced a
spurious double well; and identifying the modulus with `V''(0)` is wrong, because a modulus is a
**free-energy** second derivative and `F''(0) = kT/Var(δ)` is finite for a quartic.

## Hypothesis

Replacing the 1-3 distance spring with `V = ½·k_θ·(θ−π)²` gives Cooke's bending physics with **zero
coupling to bond length**, which is the specific mechanism that sank `bend_r0 = 4.0`.

## The strongest baseline, by name

**Production as it stands today** — the quartic 1-3 spring at `bend_r0 = 2.0`, scored by
`vesicle_gate`, at **3/20** on seeds 300–319 (roadmap §2a, W1). Not enclosure, and not the
historical 2/18.

## Design

| | |
|---|---|
| chemistry | production, φ = 0.55, **kT = 0.45**, `rc = 2.5` |
| change | 1-3 distance spring → explicit angle term; nothing else |
| `k_θ` | **derived, not picked** — see BF2 |
| start | `plant="random"`, dispersed, nothing planted |
| seeds | 20 fresh, 400–419 (300–319 are spent on the baseline) |
| steps | 1e6, `check_every` 10 000, matching W1 exactly |
| budget parity | same steps, same N, same checkpoint cadence as the baseline |

## Acceptance criteria — all registered before data

**AC-1 (the law still holds).** The new term passes every gate in `tests/test_physical_realism.py`:
`F = −∇U` to < 1e-4, `ΣF = 0` to < 1e-9, translational and rotational invariance to < 1e-8, and the
`field` and `transformer` paths agree to **0.000e+00**. Binary. A fidelity fix that breaks the energy
ledger is not a fidelity fix.

**AC-2 (`k_θ` is derived).** Set `k_θ` from Cooke's `k_bend σ² = 10 ε`, **temperature-matched** —
report the dimensionless stiffness `k_θ/kT` for both models and state the matched target before
running. Then verify by measuring `kT/Var(δ)` on a relaxed chain: it must land within **±20%** of the
target. If it does not, the derivation is wrong and the run does not proceed.

**AC-3 (no molecular inflation) — the criterion this can fail by winning.**
*Amended 2026-09-16, before any data existed. The original form was wrong and would have voided a
correct arm; it is replaced, not deleted, so the error is on the record.*

~~Mean bond length must stay at the baseline 1.0155 σ ± 0.010.~~ That is invalid, because bond length
in this model is **not independent of bend angle**. The mechanical relation, verified against 30 228
real triples to ±0.0026, is

    b*(δ) = (1 + 2c) / (1 + 2c²),    c = cos(δ/2),    b*(0) = 1 exactly

so anything that straightens the chains *must* shorten the bonds toward 1.0000. The original
criterion would therefore have failed a correctly-implemented angle potential for doing exactly what
it is supposed to do.

**The criterion is instead that bond length must remain CONSISTENT with the bend angle.** Measure
⟨b⟩ and the bend distribution; require

    | ⟨b⟩ − mean over the observed δ of b*(δ) | ≤ 0.003

This still fails `bend_r0 = 4.0` decisively (b\* = 1.6654 with no bend anywhere near the value that
would explain it) while passing any legitimate change in chain straightness. **If it fails, the arm is
void regardless of what it does to the vesicle rate** — a higher rate bought by inflating the molecule
is the retracted 3-D result over again.

**AC-3b (the intrinsic kink must shrink).** At T = 0 the isolated 5-bead lipid on the shipped `Field`
relaxes to a state **bent 23.86°** with ⟨b⟩ = 1.014390 — 91% of the melt bond excess, with no thermal
energy at all. Ablating `chi_TT` removes it entirely (bend 0.61°, ⟨b⟩ = 1.000012), so the cause is the
molecule's **own two tails attracting each other** across the four unexcluded intramolecular tail–tail
pairs, with no chain stiffness to resist. A harmonic angle term at θ = π competes directly with that.
Registered: the T = 0 ground-state bend must fall below **10°**. If it does not, `k_θ` is too weak to
do the job the term exists for, whatever the vesicle rate says.

**AC-4 (does a flat sheet bend?).** Flat-ribbon protocol, 12 seeds, planted at the **relaxed** spacing
1.7651 σ (D9), not the hard-coded `gap = 1.05`. Registered outcome: curl `aspect` > 0.10 in ≥ 6/12,
against the standing **six nulls** at 0/5–0/12. This is the question the six nulls could not answer.

**AC-5 (emergence rate).** 20 seeds scored by `vesicle_gate`, Fisher exact against the 3/20 baseline.

## What each outcome means — written before the run

- **AC-3 fails** → void, report as void, no rate is quoted. The term is coupled to bond length after
  all and the implementation is wrong.
- **AC-4 passes** → the first non-null on bending in this project, and the six-null explanation
  ("a pair force cannot tell the leaflets apart") gains a counterexample that is not a pair force.
- **AC-5 rate rises** → report it, but *do not* claim the bending form caused it until AC-4 says a
  sheet bends. A rate that rises with a flat sheet still refusing to curl means something else moved.
- **AC-5 rate falls, AC-1 and AC-3 pass** → **this is a PASS, not a regression.** Under R9 a term that
  is physically correct and makes vesicles rarer is a success and is reported as one. There is a
  concrete mechanism for expecting exactly this: line tension λ was measured as **indistinguishable
  from zero** (§2, B1), and closure needs `R_c = 2κ/λ`; raising κ with λ ≈ 0 pushes `R_c` up, so
  correct chains may close **less** often. Registering that prediction now so it cannot be
  reinterpreted later as a disappointment.
- **AC-5 unchanged** → the honest result is that chain bending form is not what limits emergence
  here, and the next lever is size selection (D1), not stiffness.

## What this does NOT establish

Nothing about 3-D, which is archived. Nothing about the membrane bending modulus κ, which this
project still records as "not measurable by any of three routes" — AC-2 measures the **chain's**
bending constant, which is not the same quantity. And nothing about electrostatics or hydrodynamics.
