# vivarium — executive summary

*Updated 2026-08-30. Keep this current after every significant development. Plain language, no jargon,
as short as possible.*

## Objective

Can a lipid vesicle — a hollow bubble with a two-layer skin, the basic form of a cell membrane — build
itself in a simulation where **every force is a transformer attention operation**? Each molecule is a
token, each simulation step is one forward pass. Three target behaviours: **emerge** (form from a
random soup), **come together** (fuse), **split** (divide). The rule that makes it meaningful: nothing
may be put in that already contains the answer. Specifically, "spontaneous curvature" — a knob that
tells the membrane to bend — is refused, because a bubble that forms because we told it to bend is not
a bubble that emerged.

## Roadmap

- **DONE — 2-D vesicle emerges.** Rare (2 of 18 random starts) but real, confirmed by picture as well
  as metric.
- **DONE — the transformer version is exact and free.** Forces match the ordinary physics to 1e-13,
  one forward pass equals one simulation step bit-for-bit, and it costs no extra time.
- **DONE — measurement tools rebuilt.** The old 3-D detector was broken; the new one is checked
  against four known shapes it must tell apart.
- **DONE — validated against an outside reference.** Our engine reproduces the published phase
  behaviour of a known-good lipid model, and makes a flat membrane sheet nearly identical to it.
- **NOW — first 3-D vesicle.** Running: 1000 molecules in a box big enough that the membrane cannot
  span it, so its only way to lose its edges is to close into a ball.
- **NEXT if that fails** — run the outside reference model at the same settings, to tell whether the
  fault is our engine or the recipe.
- **LATER — fusion and splitting.** Neither has ever been seen. Splitting stalls at a dumbbell that
  never pinches; the leading suspect is the thermostat, untested.
- **LATER — fewer knobs.** Three of the current settings are not physics, just "don't do anything
  absurd" conditions, and can be replaced by rules. Two are irreducible unless water is put back in.

## Results

- **A 2-D vesicle forms, persists, and the reason is known.** It closes when the two ends of a ribbon
  happen to meet — not because the membrane curls. Measured: the end-to-end gap controls closure;
  length, radius and molecule count do not.
- **The transformer formulation is not an analogy.** It reproduces the physics exactly and produces
  the science result, not just a matching single step.
- **Fusion has never happened. Splitting has never happened** (0 in 50 attempts).
- **No 3-D vesicle yet** — but every 3-D attempt so far used 200–400 molecules, where the bubble's
  radius would be *smaller than the skin is thick*. Those experiments could not have worked, whatever
  settings were used. This was arithmetic, not simulation, and it was checked far too late.
- **Four settings were swept and none mattered**: head size, temperature, stickiness range, and how
  hard molecules resist overlapping. All were tested at the impossible size above, so they are not
  ruled out — just untested.
- **The membrane itself is fine.** Our engine makes a proper flat two-layer sheet, essentially
  identical to the reference model's.
- **A box that is too small is a trap.** A membrane that stretches across the whole box has no edges,
  so it has no reason to close into a ball. Boxes here were always sized for density and never checked
  for this.
- **Measurement has been the main obstacle, repeatedly.** Eighteen instrument defects on record, three
  found in one day. Each time the tool could not tell success from the specific way things were
  failing. Every structural claim now needs both a number and a picture.
- **"Transformer-only" is structural, not learned.** The network's weights are fixed and its MLP is
  switched off in every run. It is a hand-written force law expressed as attention, not a trained model.
