# Why the vesicle oracle does not transfer into Vivarium

**Date:** 2026-08-15. Worktree `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.

Two reference systems emerge vesicles: stock LAMMPS `pair_style ylz`, and our `bilipid.py` (94-molecule
shell, heads outward 1.000, gradient check 1.2e-8). Vivarium does not. Both are described as physically
accurate, so the failure to transfer needs an explanation that is not "one of them is wrong."

Four causes are now measured. They are ordered by how much they explain.

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

## What follows

1. Calibrate `repel` on condensed geometry, not on a planted flat sheet, and raise `MIN_PACKING` to
   match.
2. Test the edge-tension closure criterion by sweeping patch size at fixed density, since the theory
   predicts closure appears above a critical size rather than at a critical parameter value.
3. Delete the curvature term. It was added to import the oracle's `beta`, cause 1 says that imports the
   answer, and cause 4 removed the only emergent substitute it was standing in for.
