# Why the vesicle oracle does not transfer into Vivarium

**Date:** 2026-08-15. Worktree `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.

Two reference systems emerge vesicles: stock LAMMPS `pair_style ylz`, and our `bilipid.py` (94-molecule
shell, heads outward 1.000, gradient check 1.2e-8). Vivarium does not. Both are described as physically
accurate, so the failure to transfer needs an explanation that is not "one of them is wrong."

Four causes are now measured. They are ordered by how much they explain.

## 0. The decisive measurement: the oracle's vesicle is bought, not emergent

Cause 1 below was a suspicion when this document was written. It is now measured. Same N, L, seed and
integrator, 1.5 million steps, with only `beta` differing:

| beta | outcome at 1.5M | headOut | shell CV |
|---|---|---|---|
| 0.00 | **0 vesicles at every checkpoint**, flat sheet/disc | 0.42 | 0.367 |
| 0.15 | first vesicle by 625k, **3-4 sustained** | 1.00 | 0.045 |

`beta` is the spontaneous curvature: the YLZ angular term reaches its optimum at `sin(theta*) = -beta`.
Set it to zero and the same potential, the same code and the same run length produce flat sheets.

So porting the oracle's angular term into Vivarium would have imported the answer rather than the
physics. That settles the question this document exists to answer, and it is why the replacement force
field described below contains **no orientation term at all**, with a test pinning that.

## 1. The two models sit at different levels of description

The oracle's YLZ potential is a **top-down coarse-grained effective potential**. Its angular term
carries a parameter `beta` that sets the preferred tilt through `sin(theta*) = -beta`, and `beta` is
where spontaneous curvature lives. Curvature is an *input*, fitted so that the mesoscopic phase comes
out right.

Vivarium is **bottom-up**: `repel` and `attract` are meant to stand for fundamental interactions, and
any curvature must emerge from molecular shape and packing. Porting YLZ's angular term into Vivarium
therefore does not transfer physics; it transfers the answer. A vesicle produced that way would be a
vesicle we specified, not one that emerged.

This is the reason the port kept feeling wrong, and it is why the curvature term added this session
should be deleted rather than tuned once a genuine mechanism is found.

## 2. Vivarium's excluded volume was roughly 4x too weak

Measured on a planted flat bilayer relaxed 8000 steps, reporting median non-bonded separation over
nominal contact (`2*sigma`):

| repel | repel_sharp | nn/contact | thickness |
|---|---|---|---|
| 12 | 0 | **0.36** | 3.18 |
| 24 | 0 | 0.70 | 3.17 |
| 48 | 0 | 0.93 | 5.29 |
| 12 | 8 | 0.96 | 4.74 |

Row 1 is the standard configuration: beads sitting at 36% of contact distance, i.e. deeply inside one
another. A membrane whose beads interpenetrate has no well-defined thickness and cannot hold a lumen
open. That alone accounts for every planted ring collapsing to a filled blob at every size, and it is
the same transition the oracle shows between 10 eps (collapse) and 30 eps (vesicles).

The cheaper fix is the saturating core: the default repulsion is linear in overlap and too soft near
contact, while `repel_sharp = 8` holds at the *same* `repel = 12`. At `repel = 48` the relaxed bilayer
reads align 0.862 against a bilayer reference of 1.00, ADMISSIBLE, with heads on both faces and a clean
tail core -- the best genuine bilayer this project has produced, from excluded volume alone.

**Scope correction.** That table was measured on a planted *flat sheet*, which is the easy geometry:
low coordination, no curvature stress. On a condensed ribbon that has balled up, the same
`repel = 12, sharp = 8` reads **0.13**, because a 2-D blob packs every bead against many more
neighbours and cohesion wins. Excluded volume must be calibrated on the geometry that actually occurs.
The flat-sheet number is not wrong, but it does not generalize, and the sweep on condensed geometry is
what decides the working value.

## 3. Vivarium's parameters are coupled, and were mutually tuned at the wrong steric strength

`k_bond = 30` was tuned against the too-weak repulsion. Raise the repulsion to a value that actually
excludes volume and the bond loses to it: the molecule is pulled apart, bond mean 1.20 against a rest
length of 1.0, and the configuration is DISQUALIFIED as deformed. Raising `k_bond` to 120 restores
bond mean 1.10 and admissibility.

This generalizes, and it is the sharpest answer to "why is transferring the physics hard." The oracle
has **one** potential with **one** length scale, so `epsilon`, `sigma` and `r_min` are dimensionally
anchored to each other and a single physical fact can be imported by itself. Vivarium has independent
multipliers -- `repel`, `attract`, `k_bond`, `polarity`, `hydrophobic`, `satt`, `head_q` -- with no
shared length scale, tuned as an ensemble that was self-consistent only at the wrong steric strength.
Correcting any one of them breaks the balance of the others. There is no single knob into which an
oracle fact can be deposited.

## 4. Vivarium's lipid is a cylinder, and making it a cone does not help

`head_sigma` defaults to 1.0, so head and tail steric radii are identical: the lipid has zero intrinsic
curvature by construction. The obvious fix is a cone, `head_sigma > 1`, which would give spontaneous
curvature emergently rather than by importing `beta`.

It was tested on a finite ribbon, 20 000 steps, with the steric core corrected and `k_bond = 120`:

| head_sigma | largest | align | ring_assay |
|---|---|---|---|
| 1.0 | 59/60 | 0.856 | filled |
| 1.4 | 59/60 | 0.400 | filled |
| 1.8 | 25/60 | 0.165 | fragmented |
| 2.2 | 15/60 | 0.117 | fragmented |

**The hypothesis is falsified**, with a clean monotone dose-response: enlarging the head disorders the
bilayer and then tears it, and never bends it. This is correct physics rather than an engine defect. A
symmetric bilayer gives both leaflets the same enlarged head, so the two spontaneous curvatures cancel
and only lateral frustration is left. Cones curve a *monolayer*; they do not close a bilayer.

What closes a finite bilayer patch is **edge tension** -- the hydrophobic cost of the exposed tail ends.
In 2-D a ribbon of contour length L pays a fixed `2*lambda` to stay open and about `kappa/L` to bend
into a circle, so closure gets easier as the patch grows and there is a critical size
`L* ~ kappa / (2*lambda)`. Both knobs are fundamental forces already present: `lambda` from
`hydrophobic`, `kappa` from the steric core and the bond. That is the live hypothesis.

## Instrument defects found along the way

Two measurement problems were caught before they produced conclusions, and both are recorded because
this project has now withdrawn eight results, five of them measurement artefacts rather than physics.

* **A degenerate closure metric.** Closure was first scored as end-to-end distance over contour length,
  with molecules ordered by polar angle about the centroid. Sorting by angle produces a cycle for *any*
  compact aggregate, so a shapeless blob scores 0.02 exactly like a closed ring. It read 0.02 and 0.04
  while the renders showed wavy open ribbons. Closure is now read by `ring_assay.classify`, the only
  topology instrument here whose positive, negative and adversarial gates all pass.

* **The admissibility floor codifies the defect.** `harness.py` sets `MIN_PACKING = 0.35`, so a
  membrane whose nearest non-bonded neighbours sit at 35% of contact is accepted as admissible. Every
  historical ADMISSIBLE verdict was measured against a floor calibrated to the broken steric physics.
  The threshold should rise once the working steric value is fixed.

## The resolution: one scalar energy, differentiated

Causes 2, 3 and 4 are all symptoms of one structural defect -- forces assembled by hand from seven
independent multipliers with no shared length scale. `field.py` replaces it:

    U_ij = eps * [ core(r/sigma) + well(r/sigma) * chi_ij ]

One energy scale, one length scale, and a dimensionless symmetric 3x3 chemistry matrix over
(head, tail, water). Forces are `-dU/dX`, so they cannot disagree with any energy. `chi` factors as
`chi_ij = q_i . k_j` through its eigendecomposition, so the content term is a query-key inner product
and the whole energy is one unnormalized distance-penalized attention layer, verified at 6.7e-16. The
coupling problem disappears because `eps` and `sigma` rescale the model coherently instead of
unbalancing it.

Verified, all gated in `tests/test_field.py`:

| gate | result |
|---|---|
| forces vs numerical `dU/dx` | 1.5e-07 |
| `chi` as an inner product | 6.7e-16 |
| neighbour list vs dense | **0.0** (exact, not approximate) |
| isolated pair settles at contact | within 0.02 sigma |
| rotation/translation invariance, zero net force, asymmetric `chi` rejected | pass |

What it produces: median non-bonded separation **0.95-0.99 of contact**, against 0.15 historically.
Head/tail segregation **emerges** with no polarity knob and no orientation term, headOut 0.95-1.00. A
1-head/2-tail lipid gives micelles, matching its packing parameter; four tails raise `P` into the
bilayer band and give a branched bilayer network -- the phenotype LAMMPS's own 2-D reference produces.

Two further constants inherited from the broken physics were corrected: the box density (430/13^2 puts
unit-diameter beads above 2-D close packing, forcing overlap before any force acts) and the core shape
(a quartic is too soft near contact; the quadratic DPD form holds).

## What follows

1. **2-D closure is now the open question, and the evidence says it needs curvature.** The oracle
   closes only at `beta != 0`; no open-source 2-D reference we found closes a ring; ours produces
   branched networks. Either 2-D closure requires spontaneous curvature -- in which case it must come
   from molecular geometry, since importing `beta` imports the answer -- or the milestone belongs in
   3-D, where both oracles work.
2. **Raise `MIN_PACKING`.** At 0.35 it admits membranes at 35% of contact, codifying the defect.
3. **Delete the curvature term in `pack.py`.** It existed to import `beta`; section 0 shows what that
   would mean, and the cone-shape substitute is falsified.
4. **`ring_assay` needs a fourth gate.** Its three gates use compact aggregates, so a spanning
   percolating network is outside its calibration domain and a pore can read as a lumen. It reported
   HOLLOW on exactly that; the render caught it.

---

## RETRACTION (2026-08-18): the 2-D edge-scaling argument was wrong

The leading explanation offered above -- that a 2-D bilayer edge is a POINT costing O(1), "cheaply
capped by a few heads", so closure is never strongly driven, whereas a 3-D edge is a LINE whose cost
grows with perimeter -- is **withdrawn**. It was put in the reviewer handoff as our own reading, and
the data refuting it was already in hand.

Two planted runs at IDENTICAL configuration (70 four-tail lipids, L = 40, 770 water, kT = 0.35,
packing fraction 0.55), differing only in what was planted:

| planted | E/lipid | shell CV |
|---|---|---|
| closed ring | **-28.91** | 0.204 |
| open arc (3/4) | -28.54 | 0.245 |

The ring is lower by 0.37 eps/lipid, about 26 eps over 70 lipids, or **~74 kT**. That is consistent
with an edge cost near 13 eps per exposed end -- roughly ten tail beads losing their water-excluded
contacts -- and it is a large driving force, not a negligible one.

**So 2-D closure is thermodynamically FAVOURED and the obstacle is kinetic.** The system does not fail
to prefer the closed state; it fails to reach it. That agrees with everything else measured: a planted
ring is stable with its shell CV tightening monotonically, a planted arc is ALSO metastable and sits
open for 250 000 steps, and both emergence arms are under-sampled with `D_M = D_1/N` making coarsening
progressively worse. Two local minima with a barrier between them, and the lower one is the ring.

**Caveats.** This is energy, not free energy -- the open arc carries more configurational entropy,
though a few kT does not overturn 74 kT. One seed per arm, mitigated by the quantity being an
intensive average over 70 lipids rather than a cluster count. And the arc is not literally "the ring
with a gap": at the same lipid count over 3/4 of a circle it relaxes to a larger radius (9.54 against
8.90), so this compares two geometries rather than one geometry with and without a seam. A cleaner
version would open a seam in an equilibrated ring and hold N, R and density fixed.

**Consequence for "is 3-D required".** The evidence now says **no**. The 2-D ring phase exists, is
stable, and is energetically preferred to the open state. 3-D remains easier for the reference models
-- both close there and neither closes in 2-D -- but the case that 2-D closure is thermodynamically
excluded has collapsed, and with it the argument for moving the milestone.
