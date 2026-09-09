# vivarium — executive summary

*Updated 2026-09-09. Current state only — history lives in `RESEARCH_LOG.md`. Plain language, short.*

## Objective

Can a lipid vesicle — a hollow bubble with a two-layer skin, the basic unit of a cell membrane — build
itself in a simulation where **every force is a transformer attention operation**? Each molecule is a
token; each step is one forward pass. Three target behaviours: **emerge**, **fuse**, **divide**. The
rule that makes it meaningful: nothing may be put in that already contains the answer — in particular a
"make the membrane bend" term is refused, because a bubble that forms because we told it to bend has
not emerged.

## Roadmap

- **DONE — the transformer version is exact and free.** Matches the ordinary force law to 1e-13, one
  forward pass equals one simulation step exactly, costs no extra time.
- **DONE — a 2-D bubble emerges.** Rare (2 of 18 random starts), confirmed by picture and metric. It
  closes when two ends of a ribbon happen to meet, not by curling.
- **RETRACTED — the "fix" to the straightening spring was not what we thought.** Lengthening its rest
  length was supposed to make molecules resist bending. Measured directly, it instead **stretches every
  bond by 67%**, inflating the molecule from 2 units long to 3.3. The reference model gets away with the
  same trick only because its bonds cannot stretch; ours can. Consequence: the 3-D membranes we called
  "reference quality" were measured against a yardstick for a *different, shorter* molecule — against
  their own, they are about half as thick as a proper membrane. The 2-D results are unaffected: none of
  them ever used the change.
- **DONE — first hand-set number removed, now on a test that can actually tell.** The number said
  "heads dislike tails", and the code called it the thing that makes soap behave like soap. Removed
  entirely, ribbons still close 9 times in 10 against 10 in 10 with it — indistinguishable. So it was
  decoration. No replacement was needed, and none was kept.
- **DONE — all five hand-set chemistry numbers removed, one at a time.** A sixth was on the list but
  was already set to "no effect", so it never did anything; the honest count was always five.
- **DONE — and one of them genuinely replaced by physics.** See Results. This is the first time in the
  project a chosen number has been *replaced* rather than merely deleted.
- **DONE — yes, for closing a bubble that already exists.** One attraction between oily tails, plus a
  head that is 5% smaller, closes a nearly-shut ribbon 19 times in 20 and holds it 17 times in 20 —
  as good as the original six-number recipe.
- **DONE — but NO, for building one from scratch.** Starting from scattered molecules, the stripped-down
  recipe almost never gets to an enclosed shape: 2 runs in 20 against 13 in 20 for the original. Making
  a membrane and keeping one shut are different problems, and only the second one was simplified.
- **WITHDRAWN — the "it froze solid" explanation was wrong.** The test that produced it accidentally
  measured the stripped-down recipe twice instead of comparing it against the full one. Measured
  correctly, *both* recipes are equally frozen, so freezing cannot be what separates them.
- **Warming it up does help, but does not close the gap.** Reaching an enclosed shape goes from 2 runs
  in 20 to 6, then 9, as the mixture is warmed — but the full recipe still gets there far more often
  (23 in 32), and the difference is real, not chance. So the deficit is genuinely in the *chemistry*,
  not the temperature.
- **CORRECTED — the stripped-down recipe does lose something after all.** On the strictest test it
  makes a proper bubble 11 times in 20 against the fuller recipe's 18. Earlier we reported only the two
  looser tests, on which it looked equal.
- **NOW — a problem with our own older result.** See Results. It needs a human decision, not more runs. Each is either swapped for a
  physical or geometric mechanism, or shown to be irreducible. The one attraction between oily tails
  is declared irreducible up front: without it nothing sticks to anything and there is no liquid.
- **DONE — a much better way of measuring it, and it works.** The old test asked "did a bubble
  appear?", which happens 11% of the time, so six tries per side could never tell two recipes apart —
  and did not, twice. The new test plants a nearly-closed ribbon and asks whether the two ends find
  each other. Checked on the current code: **10 closures out of 10** when the ends start 3.4 apart,
  **2 out of 10** when they start 10.1 apart. A graded answer instead of a coin flip.
- **BLOCKED — closing a sheet into a bubble in 3-D.** Six explanations tried, all refuted. Paused for
  outside review: `docs/REVIEWER_HANDOFF_2026-08-31.md`.
- **NOT STARTED — fusing and dividing.** Neither has ever been observed.

## Results

- **Membranes work in 3-D now; bubbles do not.** With the stiffness fix, molecules assemble into correct
  two-layer patches from a random start and stay put. Without it they disintegrate.
- **What assembles is several small patches, not one large membrane.** A properly-cut picture shows five
  or six separate blobs of 30–80 molecules — right local structure, no continuous sheet. The thickness
  measure reads the same for a small patch as a large membrane, so it could not tell the difference.
- **Closing is a separate problem from making a membrane.** The hollowness measure has sat at 0.49 (a
  bubble needs below 0.25) across a 40x range of membrane quality, three molecule counts, four box sizes
  and every stiffness tried — including runs where membranes reached full real-membrane thickness.
- **Three of the five numbers were decoration.** "Heads dislike tails", "heads attract each other",
  and "water sticks to itself" can all be deleted outright with no measurable cost. Ribbons still close.
- **One number was real, and we found out how.** "Heads are held in water" does not change whether a
  ribbon's two ends find each other — it changes whether the ring they make *stays shut*. Deleting it,
  half the rings that formed came back open (10 of 20, against 18 of 20 with it). Closing and staying
  closed are different physics, and this is the first measurement here that separates them.
- **And it was replaced, not just deleted.** Water can be removed from the simulation entirely and its
  effect folded into a computed attraction between the parts that remain — standard thermodynamics, no
  new chosen numbers. Doing that brings the rings back: 16 of 20 stay shut, indistinguishable from
  having the original number. 2,799 water particles replaced by three lines of arithmetic.
- **The "makes soap soap" number turned out to be decoration.** With it, ribbons close 10 times in 10;
  without it, 9 in 10. What actually makes the molecules soap-like is a different pair of numbers —
  heads are held in water while tails are indifferent to it — and those are next on the list.
  We also tried giving the head a different *size* to do the job instead. It closed 10 in 10, but since
  simply deleting the number already worked, the size change earns no credit and was not kept.
- **A curious signal, replicated, and it was noise.** Earlier, 4 of 6 runs without the knob briefly
  enclosed a region against 0 of 6 with it. On a fresh 12-per-side rerun it is 4 of 12 against 4 of 12
  — no difference at all. The 0-of-6 was the fluke, not the effect. That is the fourth time a small
  result here has vanished when repeated, and it is why the measurement was changed.
- **The new test was checked against a trick it could have fallen for.** Its detector counts enclosed
  space after fattening the molecules slightly. Fattened enough, it bridges a 3.4-wide gap on its own
  and would have scored the starting arrangement as already closed. The setting actually used reads
  "not closed" on every starting arrangement and "closed" on a real ring, and that setting was written
  down before the check was run.
- **The new measurement was checked against pictures, not trusted from the count.** The near case is a
  continuous closed ring with water inside, heads on both faces and oily cores between them. The far
  case is an open C whose two ends never met. Metric and picture agree, which is not something this
  project can take for granted.
- **A rendering trap, caught and fixed.** The first picture showed four separate fragments in the
  corners of the box, because the ring is built around the origin and the box wraps around. Recentring
  it properly showed one intact ring. Had that picture been believed, a perfectly good result would
  have been thrown away.
- **Measurement is the recurring obstacle.** Nineteen instrument defects on record, six in two days.
  Every time, the tool could not tell success from the way things were actually failing. Every
  structural claim now needs a number **and** a picture.
- **"Transformer-only" is structural, not learned.** Weights are fixed and the network's MLP is off in
  every run. A hand-written force law expressed as attention, not a trained model.

## The open question that matters most

The project's headline 2-D result — "a bubble emerges in 2 runs out of 18" — was scored with a test
that has since been tightened. The stricter test rejects **every** saved picture from those runs, and
the two runs that counted as successes are no longer on disk: one file was overwritten by a re-run.
So the old result is not disproved, it is **uncheckable**. Recent runs give 0 out of 40 under the strict
test and 13 out of 20 under a loose one — but we looked at the pictures behind the loose number, and
they are tangled ribbons with a small trapped gap, not bubbles. The loose test counts the wrong thing,
and the old result was scored with a test closer to the loose one than the strict one.

Deciding which test is the right one is a judgement about what should count as a bubble, not something
another run can settle. That decision is what the project needs next.

## The newest result: giving molecules an internal state did not make membranes bend

Real molecules change shape depending on how crowded they are; ours were rigid. We gave each one a
sense of how buried it is — computed from geometry, with no new tunable numbers — and let that change
how it interacts. It provably does nothing on a flat sheet (so it cannot secretly force bending) and
responds strongly on a curved one, which is exactly how an honest version of this should behave.

Then we asked the question that matters: does a flat sheet now curl up? **No — 0 out of 12, same as
without it.** That makes six different things we have tried that all fail to bend a flat membrane. The
previous five had a shared explanation; this one does not fit it, so the explanation was incomplete.

## Known gaps

- **A recent run made a bubble, and we have the picture.** Seed 509, full recipe, from scattered
  molecules: at step 500,000 a closed ring with water inside, oily cores between two layers of heads.
  It held for 22 consecutive snapshots. Re-running the same seed reproduced it exactly and this time
  saved the picture at the moment it formed — the earlier version only kept the final picture, by which
  time it had come apart, which is the same mistake that lost the original one years of runs ago.
  The bubble is 56 of the 160 molecules; the rest are still scattered fragments around it.

- Two deviations from the reference model's known-good recipe were never reconciled: molecule density is
  about half the reference value, and the one architectural comparison the plan called for (soft
  repulsion vs the standard hard one) has never been run.
- Fusion and division untouched.
