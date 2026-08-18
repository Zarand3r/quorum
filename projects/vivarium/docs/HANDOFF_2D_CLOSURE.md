# Reviewer prompt: is a closed bilayer ring a stable phase in strictly 2-D?

**Date:** 2026-08-15. Worktree `/home/rbao/quorum-thermolife`, branch `autoresearch/bilayer-emergence`.
Self-contained; you need no prior context. **One question, in §4.** Everything before it is the
evidence, so you can judge whether the question is even well posed.

---

## 0. What we are asking, in one line

We cannot make a symmetric two-leaflet bilayer close into a hollow ring in two dimensions without
importing spontaneous curvature as a parameter, and we now suspect that is not a limitation of our
model but a property of 2-D. We want a membrane physicist's judgement on whether it is excluded in
principle.

This is deliberately **not** a request to review our code, our roadmap, or our five open questions. A
previous handoff did that and got useful answers. This one asks a single physics question.

## 1. The system

A coarse-grained amphiphile in a periodic box with explicit solvent. Beads of three species (head,
tail, water). A molecule is a linear chain: one head, `n_tail` tails, harmonic bonds. Interactions are
pairwise and isotropic:

    U_ij = eps * [ core(r/sigma) + well(r/sigma) * chi_ij ]

with one energy scale, one length scale, and a symmetric dimensionless 3x3 matrix `chi` over the
species. `core` is bounded and quadratic in overlap (the DPD form); `well` is a cosine tail truncated
smoothly at `rc = 2.5 sigma`. Amphiphilicity is entirely in `chi`: tails attract tails, tails gain
nothing from water, heads are solvated.

**There is no orientation-dependent term.** Bead orientation never enters the energy. Forces are
`-dU/dX` analytically. Verified and gated in CI:

| gate | result |
|---|---|
| analytic forces vs numerical `dU/dx` | 1.5e-07 (2-D), 9.9e-07 (3-D) |
| neighbour list vs dense evaluation | exactly 0.0 |
| isolated attracting pair settles at contact | within 0.02 sigma |
| rotation / translation invariance, zero net force | pass |

Sanity of the phase behaviour: median non-bonded separation is **0.95-0.99 of contact**, so beads are
not interpenetrating. Head/tail segregation is **emergent** -- there is no polarity or hydrophobicity
knob, only `chi` -- with heads pointing outward at 0.95-1.00. A 1-head/2-tail lipid gives micelles
(one when concentrated, several when dilute); raising to 4 tails moves the packing parameter into the
bilayer band and gives branched bilayer networks.

## 2. The measurement that motivates the question

Our reference model is the Yuan-Li-Zhang potential, which reproduces vesicles in stock LAMMPS and in
our own independent implementation. YLZ has an orientation term whose optimum sits at
`sin(theta*) = -beta`, so `beta` is the spontaneous curvature. Same N, same box, same seed, same
integrator, 1.5 million steps, **only `beta` differs**:

| beta | outcome at 1.5M steps | heads outward | shell CV |
|---|---|---|---|
| 0.00 | **0 vesicles at every checkpoint**; flat sheet / disc | 0.42 | 0.367 |
| 0.15 | first vesicle by 625k; **3-4 sustained** | 1.00 | 0.045 |

So in the reference model, closure is bought by `beta`. It is not something the potential does on its
own.

## 3. What we have falsified in 2-D, each with a control

Every one of these was run with an explicit falsification criterion stated in advance, and several
retracted earlier claims of our own.

* **Excluded volume was the first real defect, and fixing it was necessary but not sufficient.** Beads
  had been sitting at 0.36 of contact (0.15 in the historical configuration), so membranes had no
  thickness and no planted ring could hold a lumen at any size. Corrected; rings still do not survive.
* **Cone-shaped lipids do not close a bilayer.** Enlarging the head (`head_sigma` 1.0 -> 1.4 -> 1.8 ->
  2.2) gives a monotone dose-response of *destruction*: alignment 0.856 -> 0.400 -> 0.165 -> 0.117,
  fragmenting by 1.8. We read this as correct physics rather than an engine defect, because a
  symmetric bilayer gives both leaflets the same enlarged head, so the two spontaneous curvatures
  cancel and only lateral frustration remains.
* **Edge tension does not close a finite patch here.** The 2-D criterion `kappa/L < 2*lambda` predicts
  closure gets easier as the patch grows. Patches fragment into multiple micelles before they close.
* **Not kinetic trapping.** An order parameter tracked over 60 000 steps is stationary (0.589, 0.581,
  0.577, 0.575, 0.593, 0.580, 0.578, 0.574, 0.574, 0.574), and an annealed arm started at 4x
  temperature and cooled tracks the cold arm exactly.
* **Not parameter balance.** A 6-point grid over the two segregating forces spans only 0.402-0.595,
  with the strongest forces giving the worst result; rescaling every interaction coherently by 4x
  moves it 0.577 -> 0.631, not to the 0.8+ predicted.

## 3b. Since writing §3 we have largely answered our own question

Three experiments run after the sections above, all under the force field of §1.

**The closed ring is a stable phase.** A planted two-leaflet ring of 70 lipids holds for 200 000 steps,
and its shell CV TIGHTENS rather than decays:

| component | largest | R_mid | shell CV start -> end | lumen water | lumen/bulk |
|---|---|---|---|---|---|
| mixed 2-tail + 4-tail | 70/70 | 8.07 | 0.277 -> 0.211 | 50 | 1.18 |
| single component, 4-tail | 70/70 | 8.90 | 0.284 -> 0.204 | 56 | 1.54 |

The render shows a closed annulus with heads on both the outer surface and the lumen boundary and
water inside. Every planted ring before this collapsed to a filled micelle at every size. So option (1)
in §4 -- excluded in principle -- appears to be **false**: the phase exists and is at least metastable.

**Leaflet compositional asymmetry does not happen.** In the mixture, enrichment stays pinned at its
t = 0 random value (+0.081, +0.081, +0.039, never drifting) through 200 000 steps. The species do not
exchange between leaflets because that requires flip-flop, and flip-flop is kinetically forbidden here
as it is in real membranes, where it takes hours and is enzyme-catalysed. Cells build leaflet asymmetry
with flippases, not by equilibration. The single-component control confirms the mixture was irrelevant
to the ring's stability.

**An open arc does not close.** Planted at three quarters of a ring, at the same radius the closed
state prefers, it stays a C for 250 000 steps with a persistent gap, both ends capped by head groups.

**Our reading, which is what we would most like checked.** In 2-D a bilayer edge is a POINT; in 3-D it
is a LINE. Closing a 3-D vesicle removes an edge cost proportional to the perimeter, a driving force
that grows with the aggregate. Closing a 2-D ring removes only two point-like ends, each costing O(1),
and those ends are cheaply capped by a few heads. So the thermodynamic drive for 2-D closure does not
scale with size, while the kinetic barrier does not shrink -- which would explain why both oracles work
in 3-D, why LAMMPS's own 2-D example produces branched strips with stable ends, and why our arc sits
open next to a ring we know is stable.

If that argument is right, 2-D closure is not excluded, merely never driven, and the milestone should
move to 3-D rather than be pursued with better sampling.

## 4. The question

**In strictly two dimensions, is a closed ring a thermodynamically stable phase for a SYMMETRIC
two-leaflet bilayer of identical amphiphiles with isotropic pair interactions, or is it excluded in
principle?**

Concretely, we would like to know which of these is true:

1. **Excluded in principle.** ~~In 2-D the bilayer's two leaflets are two lines...~~ **We now believe
   this is false** -- see §3b, where a planted ring is stable for 200 000 steps and tightening. We leave
   the option here because a reviewer may read our ring as long-lived-but-not-stable, and we would like
   to know how to tell the difference on a timescale we can afford.
2. **Reachable, but never driven.** This is now our own reading (§3b): the closed state is stable, the
   open state is also stable, and nothing carries the system from one to the other because a 2-D edge
   costs O(1) rather than scaling with perimeter. If you agree, the honest move is 3-D. If you
   disagree, what supplies the drive in 2-D? Leaflet compositional asymmetry was our candidate and it
   is falsified as an equilibrium mechanism, since flip-flop does not occur.
3. **The question is malformed.** For example, if "spontaneous curvature" is not separable from
   "orientation-dependent interaction" in a coarse-grained model -- i.e. if any model that closes must
   have an orientation term somewhere, whether written as `beta` or emergent from composition -- then
   our distinction between "imported" and "emergent" curvature is not meaningful, and we would like to
   be told that plainly.

## 5. Why the answer changes what we do

Our simulator's vesicle milestone is currently specified in 2-D. Both vesicle oracles work in 3-D, no
open-source 2-D reference we found closes a ring, and LAMMPS's own 2-D example produces branched
bilayer strips indistinguishable from ours. Our force field is dimension-agnostic and gated in 3-D, so
moving costs a builder function rather than a rewrite.

If the answer is (1), we retire 2-D closure immediately instead of spending weeks proving a negative
with increasingly elaborate controls. If (2), we want the mechanism. If (3), we want the correction.

## 6. Standing caveat

This project has withdrawn nine results, and six were measurement artefacts rather than physics --
including four false "hollow" verdicts from one centroid-based lumen detector, and a whole family of
"working bilayers" that turned out to be interpenetrating piles scoring well on shape metrics. Treat
every number above as provisional unless it has a control or a rendered image behind it. The ones in
§1 and §2 do.
