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
