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
- **DONE — seven chemistry settings cut to one.** The old model hand-set seven "how much does X like
  Y" numbers, two of them purely to force the molecules to behave like soap. Now there is exactly one
  attraction (tail-to-tail) and the heads have none at all — what makes a molecule soap-like is only
  that its head is a different *size*. Chemistry replaced by shape.
- **TRIED, FAILED — 3-D bubble at 1000 molecules.** 0 of 6. Sheets formed and fell apart again and
  again; nothing ever closed. The cause looks like too few molecules: the box has to be big enough
  that the sheet cannot stretch across it, *and* crowded enough that pieces meet and stick. With 1000
  molecules you cannot have both — we got the first and lost the second, and the pieces evaporated.
- **DONE — "too thin" was wrong.** Tested it directly: varied only how crowded the box was, across a
  3x range. Membranes fell apart just as much when crowded as when sparse — the *most* sparse setting
  did best. So thinness is not the reason.
- **NOW — find why membranes will not hold together at all.** In this stripped-down setup a sheet
  never survives; it keeps forming and falling apart at every crowding level, never reaching even
  two-thirds of a real membrane's thickness. Next: run the outside reference model at the same
  settings. If its membranes also fall apart, our recipe is wrong; if they hold, the fault is in our
  simulator and can be tracked down against a working example.
- **NEXT if that fails** — run the outside reference model at the same settings, to tell whether the
  fault is our engine or the recipe.
- **LATER — fusion and splitting.** Neither has ever been seen. Splitting stalls at a dumbbell that
  never pinches; the leading suspect is the thermostat, untested.
- **LATER — cut the remaining knobs.** Three left are not physics at all, just "don't do anything
  absurd" conditions, and can each be replaced by a rule (make beads solid enough not to pass through
  each other; make bonds stiff enough not to stretch). One more (chain floppiness) can be fitted to a
  measurable property instead of chosen. The last two — how strongly and how far tails attract — are
  irreducible unless water is put back into the simulation, which costs about 9x.

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
- **Seven chemistry numbers are now one, and it still makes a membrane.** Heads carry no attraction at
  all; being soap-like comes from head size alone. Sheets of the right thickness still form under it,
  so the six deleted settings were not needed for that. Whether they are needed for a *bubble* is
  still unknown.
- **The first 3-D attempt at a workable size failed, 0 of 6**, and the reason is not what we first
  thought. Membranes never held together long enough to try closing — they formed and fell apart
  repeatedly, at every crowding level tested. The best case reached about half a real membrane's
  thickness. So this says nothing yet about whether a bubble can close; it says a sheet will not even
  survive in this stripped-down setup.
- **"Transformer-only" is structural, not learned.** The network's weights are fixed and its MLP is
  switched off in every run. It is a hand-written force law expressed as attention, not a trained model.
