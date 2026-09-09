# The MLP as the missing MANY-BODY term

**Registered 2026-09-07, before any implementation is run.** 2-D first.

## The structural problem this addresses

`docs/RESULTS.md` states the blocker as close to a theorem, not an empirical failure:

> **This force field cannot curve a flat bilayer.** ... The reason is structural: chi terms are
> symmetric pair interactions, and spontaneous curvature is by definition a difference between the two
> leaflets.

Every candidate curvature source has come back a measured null with the membrane intact: `chi_TW`
(lambda = +2.8 +- 2.8, null WITH power), `chi_HH` (0/5 over ten runs), lipid shape, **imposed leaflet
thickness asymmetry (0/5)**, **imposed leaflet area asymmetry (0/5)**. Even handing the membrane an
asymmetry did not curl it.

No amount of chi tuning escapes this, because the obstruction is the FORM of the interaction, not its
parameters.

## The reaction-diffusion reading

| reaction-diffusion | transformer |
|---|---|
| `D grad^2 u` -- spatial coupling between sites | **attention** -- pairwise coupling over a mask |
| `f(u)` -- pointwise nonlinear reaction | **MLP** -- per-token nonlinear map on local state |

Turing patterns require BOTH. Pure diffusion relaxes to uniformity; it cannot break symmetry. Vivarium
today is the pure-diffusion half: every molecule is rigid, carries no evolving internal state, and the
only coupling is pairwise.

**And the MLP is not merely zeroed -- it is never called.** `transformer.attention()` and
`transformer.forward()` do not invoke `mlp()`; the only caller in the repository is
`tests/test_transformer.py:130`. So `docs/RESULTS.md`'s gate *"MLP is live, not decorative"* exercises
a code path the simulation never executes. That is recorded here as a claim-vs-code gap.

## What is actually missing, stated in membrane terms

The standard theory of vesiculation is **area-difference elasticity (ADE)**: the bending energy carries
a term proportional to `(dA - dA_0)^2`, where `dA` is the area difference between the two leaflets.
That term is **non-local and many-body** -- it depends on an aggregate over each leaflet, not on any
pair. A sum of symmetric pair potentials cannot express it, which is exactly the obstruction
`RESULTS.md` identified from the other direction.

An MLP acting on a per-token invariant aggregate CAN express a density-dependent, many-body
contribution. That is the specific reason to wire it in, and it is a structural argument rather than a
hope that more parameters will help.

## The mechanism, DERIVED not fitted

Solvation energy scales with **solvent-accessible surface area**. This is the standard SASA model in
biophysics, not an invention for this project. A head bead that is crowded by neighbours exposes less
surface to water and is therefore less solvated than an exposed one:

    chi_HW_eff(i) = chi_HW * f_exposed(i),     f_exposed(i) = max(0, 1 - n_i / n_max)

where `n_i` is the head's coordination among lipid beads within the well range, and `n_max` is the
close-packing coordination number -- **geometrically fixed, not chosen**: 6 in 2-D, 12 in 3-D.

There is **no free parameter**. `chi_HW = 0.75` is the existing production value; `n_max` is geometry.

## Why this is not smuggling in the answer

The rule is that nothing may be supplied which already contains the answer, and a "make the membrane
bend" term is refused. This term says only *a buried head is less solvated than an exposed one*, which
is true independently of vesicles and mentions neither curvature nor leaflets.

**Its null behaviour is the check.** In a FLAT bilayer both leaflets are equally exposed, so
`f_exposed` is equal on both sides, no asymmetry is generated, and the term cannot produce spontaneous
curvature. It can only respond to curvature that already exists -- amplifying or damping it. **Which
sign it takes is genuinely unknown to me at registration time**, and that is the strongest evidence
that the answer is not being supplied.

## Gates, in order. Each can fail.

**G1 -- the existing correctness gate must survive.** With the MLP disabled, one forward pass must
still equal `Inertial.step` bit-for-bit and the attention sum must still equal `field.forces()`. The
MLP is additive and off by default; if this breaks, the wiring is wrong.

**G2 -- the null control.** On a planted FLAT bilayer, the MLP must produce equal `f_exposed` on the
two leaflets, to within thermal noise. If it produces an asymmetry on a flat membrane, the term is
manufacturing curvature and must be rejected.

**G3 -- the mechanism engages.** On a planted CURVED bilayer (a ring), the two leaflets must show
measurably different `f_exposed`, with the inner leaflet more crowded. If not, the term is inert and
nothing downstream is worth running.

**G4 -- the experiment.** Planted FLAT ribbon, does it curl? This is the exact protocol on which
every prior candidate returned **0/5 with the membrane intact**, so the null is established and
unusually well characterised.

```
G4 PASSES iff  curl rate >= 3/10 with the MLP on  AND  0-1/10 with it off, same seeds
```

## What each outcome means, written before running

- **G4 passes.** A many-body term is what the model was missing, and it was derivable rather than
  chosen. This would be the first positive on a protocol with five recorded nulls.
- **G4 fails, G3 passes.** The mechanism engages but does not drive curvature. The many-body term is
  real but this particular one is not the missing piece; ADE proper (an explicit leaflet-area-difference
  term) becomes the next candidate, and it is a much harder sell under the no-smuggling rule.
- **G2 fails.** The term manufactures asymmetry on a flat membrane. Reject it and say so -- that would
  mean it does contain the answer.
- **G1 fails.** Implementation error, not physics.

## Threats

- The MLP's current input is the summed attention SCORE, a force-like quantity, not a coordination
  count. Implementing `n_i` requires passing a different invariant message. That is a change to the
  architecture's inputs and is noted as such, not hidden.
- A live MLP breaks the "one forward pass = one integrator step" identity in the general case. G1
  preserves it only for the MLP-off path. The project's strongest correctness claim therefore becomes
  conditional, and any result here must state that.
- `chi_HW` only exists with explicit solvent. This mechanism is defined for the 2-D production
  chemistry and does NOT transfer to the solvent-free arms without a separate derivation.

---

## G2 and G3 — PASSED, 2026-09-07

Planted geometries, N = 56 lipids (the size of the confirmed emergent vesicle), L = 100, phi = 0.55.

| geometry | outer leaflet | inner leaflet | asymmetry |
|---|---|---|---|
| **FLAT bilayer (G2, the null)** | 0.5000 | 0.5000 | **0.0000 exactly** |
| **RING, curved (G3)** | 0.5000 | 0.3821 | **+0.1179** |

**G2 PASSES.** The term is identically zero on a flat membrane, so it cannot manufacture curvature --
which is the check that it does not contain the answer. **G3 PASSES.** On a ring the inner leaflet is
measurably more buried, so the mechanism engages.

0.5000 for an exposed head is correct by inspection: a head on a flat surface has half its perimeter
facing solvent.

### A conceptual error the controls caught before it reached the dynamics

The first implementation treated EVERY bead as an occluder, including water. But the probe *represents*
a water molecule -- water cannot block water's access; it is the thing being granted access. With that
error, heads in a normal flat bilayer read as 85% buried and the numbers inverted:

    spurious FLAT asymmetry 0.0222   >   real RING signal 0.0093

i.e. the noise exceeded the signal and both gates failed. Fixed by passing lipid beads as the only
occluders. Had this gone straight into the dynamics it would have been a force term driven mostly by
solvent packing noise.

`_sasa.validate()` separates four known-answer cases, including one with an exact analytic value: two
expanded circles of radius 1.0 whose centres are 1.0 apart occlude arccos(1/2) = 60 degrees either
side, so 120 of 360 degrees are blocked and exactly 2/3 remains. It reads 0.6667.

## Amendment 1 — the implementation scales ALL of a head's interactions, not only `chi_HW`

The derivation above justifies `chi_HW_eff = chi_HW * f_exposed`. The natural implementation in this
architecture scales the token's channel, `h_i <- f_i * h_i`, and since `q = h @ Wq`, that scales every
interaction the head takes part in: `chi_HW` by `f_i`, and `chi_HH` by `f_i * f_j`.

**Stated rather than hidden, because it is broader than what was derived.** The physical justification
extends: if interactions are mediated by exposed surface, then a buried head engages less with
everything, not only with water. A pair term scaling as `f_i * f_j` is the correct form for a
surface-mediated interaction between two partially buried objects. But `chi_HT` and `chi_HH` are
scaled as a consequence of the architecture rather than as a consequence of the SASA argument, and any
result must say so.

Tails are NOT scaled. The hydration shell is a property of the polar head group; tail beads are
hydrophobic and carry none.

---

## Amendment 2 — 2026-09-08: the MLP IS usable. Demonstrated, not argued.

Two objections were raised against a live MLP. One was real and one was not.

**Not a blocker: the MLP.** `manybody.py` gives each token a scalar internal state -- a smooth
coordination number over lipid beads, `n_i = sum_j (1 - (r/rc)^2)^2` -- and an MLP maps it to an
exposure `f_i` that modulates the pair chemistry as `chi_ij = chi0_ij * f_i * f_j`. Symmetric in the
pair, so antisymmetry of the pair force is preserved.

**Real, and solved:** with `chi` configuration-dependent the force is no longer the radial derivative
alone. `field.forces` and `transformer.attention` both compute `dudr = eps*(duc + duw*chi)/sig` with
chi held constant, so both would silently omit

    - sum_ij eps * well(r_ij) * chi0_ij * [ f_j * df_i/dx_k + f_i * df_j/dx_k ]

Omitting it makes the dynamics non-conservative: energy drifts, temperature is undefined, and the
thermostat fights a non-gradient force. This is the same embedding-density term EAM and many-body DPD
carry, and it is why the descriptor is a smooth coordination number rather than exact SASA -- the arc
geometry is more accurate but piecewise, and an underivable descriptor is exactly how a
non-conservative force gets in unnoticed.

### The gate: does F equal -grad U?

Central differences at h = 1e-6, worst relative error over probed coordinates:

| MLP scale | max rel. error |
|---|---|
| 0.0 (off) | 1.079e-06 |
| 0.5 | 1.072e-06 |
| 1.0 | 1.072e-06 |
| 2.0 | 1.071e-06 |

That is the central-difference truncation floor, flat in MLP strength. **The force is exact.** And the
term is not inert: `||F_on - F_off|| / ||F_off|| = 0.0076`.

### What still cannot cross over from polar_pack

**Softmax.** Row-stochastic weights give `w_ij != w_ji`, so `F_ij != -F_ji`: Newton's third law fails
and momentum is not conserved. Normalisation also makes the force INTENSIVE -- a bead with 100
neighbours feels the same total as one with 3. Symmetrising restores the third law but destroys
row-stochasticity, so it is no longer softmax. polar_pack can use it because it has no energy ledger.

### Amendment 3 — the G4 gate as registered is too weak, corrected BEFORE any data

Registered: `on >= 3/10 AND off <= 1/10`. Computed power:

| true rate, if the MLP does nothing | P(false pass) |
|---|---|
| 0.10 | 0.052 |
| 0.20 | **0.121** |

and the boundary case the gate would PASS, 3/10 vs 1/10, is **Fisher p = 0.291** -- not significant.
The gate licenses a non-result.

**Corrected gate, no data yet seen:**

```
G4 PASSES iff  on >= 6/12  AND  off <= 1/12  AND  Fisher one-sided p <= 0.05
```

Twelve seeds per arm rather than ten, and an explicit significance clause. Changing a gate after
seeing data would be the failure this spec exists to prevent; changing one found broken before any run
is not, and the correction is recorded here rather than made silently.

### Remaining free parameter, declared

`ManyBodyMLP.scale` multiplies the coordination before the exposure map, and `n_ref = 6.0` is the
close-packed 2-D coordination number (geometry). `scale = 1.0` is the natural value and is what the
gradient gate was run at, but it IS a knob and must not be tuned to make G4 pass. If G4 is run at more
than one `scale`, every value must be reported.
