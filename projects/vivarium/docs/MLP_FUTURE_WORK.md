# Future MLP work

*Recorded 2026-09-18. This is a design backlog, not a claim about the current production model.*

## Current decision

There is one active production path:

```
_mixture.make_step_engine(engine="transformer")
    -> transformer.VivariumTransformer(field.Field)
```

`manifest.py` prevents that path from importing archived simulations or external physics oracles.
The repository intentionally still contains archived `pack`, `polar_pack`, and `pure` engines plus
independent reference models, so "one production path" does not mean "one force law in the tree."

The production force is expressible as masked attention and uses fixed species query-key factors.
The genuine token MLP in `transformer.py` is not live: `forward()` does not call it, and its hidden
state does not reach the force calculation. The optional `ShapeMLP` and `ManyBodyMLP` names refer to
fixed scalar constitutive curves rather than multilayer networks; both are off in production.

Do not enable the existing token MLP merely to satisfy the label "transformer-only." A network is
useful only after its physical state, governing law, and observable consequence are specified.

## What the archived work established

`pack` and `polar_pack` used a true MLP residual to update shape and hidden channels. Those channels
changed token contours and subsequent interactions, so the MLP genuinely contributed to morphology.
This was an exploratory morphing model, not validated molecular physics: it had no conservative
energy ledger, and `polar_pack` used softmax interactions that could violate momentum conservation.

The conservative mechanism transferred to the active model was environment-dependent head size.
It preserves an energy ledger and demonstrably changes the packing parameter, but it is a fixed
sigmoid response rather than an MLP. Its tested outcome was bilayer-to-micelle fragmentation, with
no demonstrated curl or vesicle benefit. This result argues against turning it on in production;
it does not rule out a different, direction-aware internal-shape model.

## Candidate physical roles

A future live MLP must implement one declared role:

1. **Internal conformation or induced fit.** Predict a bounded molecular shape variable from a local,
   symmetry-respecting environment descriptor. A direction-aware first moment is more relevant to
   curvature than the current scalar neighbour count.
2. **Local chemical reaction.** In a reaction-diffusion model, use a position-wise MLP for the local
   nonlinear reaction while attention implements neighbour diffusion. This is a separate model from
   the current molecular membrane and should not be introduced as an explanation for its assembly.
3. **History-dependent material state.** Model slow adaptation only with an explicit state energy and
   consistent reversible or dissipative dynamics; an arbitrary hidden-state residual can do
   unaccounted work.

## Acceptance gates before production use

The design must be written and registered before outcome runs. At minimum it must establish:

- **Load-bearing wiring:** an intervention on the internal channel measurably changes its declared
  physical output and, when intended, the force. Keep the existing strict expected-failure wiring
  test: it must become an XPASS (and therefore fail the suite) when the channel is connected, forcing
  this audit and its acceptance gates to be updated deliberately.
- **Energy accounting:** place a conformation output inside a scalar energy and include its complete
  chain-rule force, or specify and test the thermodynamics of a deliberately non-conservative model.
- **Symmetries and conservation:** translation, rotation, permutation, periodicity, net momentum,
  and `F = -grad U` where the model claims conservative dynamics.
- **Boundedness and stability:** bound physical outputs such as bead size and affinity, then test the
  full allowed range for finite forces and stable integration.
- **Null controls:** a symmetric flat bilayer must not acquire handedness or curvature merely because
  the network is present. Frozen, shuffled, and zero-output controls must isolate the proposed
  mechanism.
- **Physical calibration:** compare the represented quantity with a measurable target such as head
  area, conformational relaxation time, bending modulus, or a specified reaction curve. More layers
  are not evidence of greater realism.
- **Morphology outcome:** score bilayer retention, micelles, fragmentation, closure, and vesicles with
  the existing registered gates across matched seeds. Report harmful and null outcomes.
- **Trajectory provenance:** enabling the network defines a new model version. Do not reinterpret or
  mix earlier production trajectories with it.

## Decision sequence

First settle whether the architecture contract requires a live adaptive token channel or only an
attention-expressible force law. Then choose one physical role above and write its energy/dynamics.
Only after the acceptance tests exist should the channel be connected to production forces and run
against the present MLP-off baseline.

See `PHYSICS_REVIEW_2026-09-18.md` for the physics audit and `ROADMAP.md` sections 5a, I7, and 9 for
the experiments and historical results behind this backlog.
