# vivarium — executive summary

*Updated 2026-09-02. Current state only — history lives in `RESEARCH_LOG.md`. Plain language, short.*

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
- **DONE — found and fixed a real defect.** The spring meant to keep a molecule straight rested at its
  own natural length, giving *zero* resistance to small bends — about 37,000x weaker than the reference
  model. Before the fix, 3-D membranes dissolved to nothing; after it, they form by themselves and hold.
- **DONE — first hand-set number removed, and it survives.** Removing the number set purely to force
  soap-like behaviour changed nothing measurable: clump sizes 109.5 vs 113.2, overlapping. Neither arm
  produced a bubble in six runs each, but that was the expected outcome for both (see Results).
- **NOW — replace all six hand-set numbers, one at a time, in 2-D.** Each is either swapped for a
  physical or geometric mechanism, or shown to be irreducible. The one attraction between oily tails
  is declared irreducible up front: without it nothing sticks to anything and there is no liquid.
- **NOW — measuring it a completely different way.** The old test asked "did a bubble appear?", which
  happens 11% of the time, so six tries per side could never tell two recipes apart — and did not,
  twice. The new test plants a nearly-closed ribbon and asks whether the two ends find each other.
  That closes 5 times in 5 when the ends start 3.4 wide apart and 1 time in 10 at 10.1, so it gives a
  graded answer instead of a coin flip, and each run is about 30x cheaper.
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
- **The first knob removal did no harm.** Full-length 2-D runs, six seeds per arm: clump sizes overlap
  completely (78–154 with the knob, 80–155 without). Neither arm made a bubble — but at the known 2-in-18
  rate, getting none in six runs is a coin flip (50%), so that is not evidence either way.
- **A curious signal, now being replicated.** Counting runs rather than snapshots, 4 of 6 runs without
  the knob briefly enclosed a region against 0 of 6 with it. None passed the full bubble test. It is
  the first hint that removing the knob helps rather than hurts, and it is exactly the kind of
  small-sample pattern this project has repeatedly watched evaporate. A fresh 12-per-side replication
  is running.
- **The new test was checked against a trick it could have fallen for.** Its detector counts enclosed
  space after fattening the molecules slightly. Fattened enough, it bridges a 3.4-wide gap on its own
  and would have scored the starting arrangement as already closed. The setting actually used reads
  "not closed" on every starting arrangement and "closed" on a real ring, and that setting was written
  down before the check was run.
- **Measurement is the recurring obstacle.** Nineteen instrument defects on record, six in two days.
  Every time, the tool could not tell success from the way things were actually failing. Every
  structural claim now needs a number **and** a picture.
- **"Transformer-only" is structural, not learned.** Weights are fixed and the network's MLP is off in
  every run. A hand-written force law expressed as attention, not a trained model.

## Known gaps

- Two deviations from the reference model's known-good recipe were never reconciled: molecule density is
  about half the reference value, and the one architectural comparison the plan called for (soft
  repulsion vs the standard hard one) has never been run.
- Fusion and division untouched.
