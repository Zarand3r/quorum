# Reset roadmap: reproduce emergence, then bound it, then transformerize it

**Adopted 2026-08-10**, after F48/F49 withdrew the 2-D self-assembly result. Frozen baseline: `3a70fce`.

## The rule

> First reproduce emergence. Then reproduce it with bounded forces. Then reproduce the bounded model
> with transformer operations. Never ask one experiment to prove all three.

## Why the previous strategy stalled

Every negative result was ambiguous because the force law, the solvent, the molecular topology, the
metrics and the transformer representation were all being varied at once. When the membrane failed to
appear there was no way to localise the cause — and it turned out to be the solvent, which nothing was
watching.

## Ladder

| stage | system | forces | required phenomenon | what a failure localises |
|---|---|---|---|---|
| A | LAMMPS `examples/micelle` | conventional | spontaneous 2-D bilayer | environment / our metrics |
| B | Martini 3 DSPC | conventional CG | wet bilayer from random start | reproduction / config |
| C | AOT Martini 3 | conventional CG | micelle → bicelle → vesicle | reproduction / config |
| **D** | **DPD amphiphile, in-repo** | **bounded soft pairwise** | **micellar / lamellar mesophase** | **bounded-force premise** |
| **E** | **exact DPD inside Vivarium** | same equations | reproduce D | **our engine / integrator / BCs** |
| **F** | **transformerised DPD** | transformer-compatible | reproduce E | **the architecture** |
| G | custom Vivarium chemistry | research model | reproduce the phase family | the research question |

### Deviation from the review, and why

**A, B and C are deferred.** Neither LAMMPS nor GROMACS is installed here, and installing them is a
heavy, outward-facing action that should be a deliberate decision rather than something an autonomous
run does on its own. They are also the *least* diagnostic rungs for the open question: they validate
our analysis stack against conventional forces, which is useful, but the architectural question lives
at D→E→F.

This is not a new pattern for the project. `cooke_deserno.py` is already a hard-coded conventional
reference built in-repo for exactly this purpose — to answer "is this reachable at all in a box this
size?" — and it worked: it produced a stable bilayer where Vivarium could not, which is what made the
earlier negatives interpretable.

So the executed order is **D → E → F**, with A–C available later if the metric-calibration question
becomes the blocker.

## Stage D in detail (the part being built now)

Groot–Warren DPD, plain numpy, no transformer constraint, its own module. Three pair forces:

    F_C = a_ij (1 - r/rc) r_hat                  conservative, bounded, finite at r=0
    F_D = -gamma w_D(r) (r_hat . v_ij) r_hat     dissipative
    F_R = sigma w_R(r) theta r_hat               random,  sigma^2 = 2 gamma kT,  w_D = w_R^2

The dissipative and random terms are tied by fluctuation–dissipation, which is what gives DPD a real
temperature — the same property whose absence produced the `speed` defect here.

**The point of the exercise is calibration, not realism.** Vivarium's `repel` was *chosen*; DPD's `a`
is *fitted* to a target compressibility. That is the substantive difference between a solvent that
condenses and one that does not, and it is the hypothesis this stage tests.

### D gates, in order — each must pass before the next

1. **Solvent EOS.** One component. Measure `P(rho)`, `g(r)`, self-diffusion, nearest-neighbour
   distribution, density homogeneity. Required: homogeneous, no droplet/vacuum separation, no growing
   deep-overlap population, positive compressibility, non-zero diffusion, timestep-converged.
2. **Species incompatibility.** Two bead types, `a_AA`, `a_BB`, `a_AB`. Demonstrate miscible, weakly
   incompatible and strongly segregating regimes.
3. **Amphiphile mesophase.** Bond beads into amphiphiles. Require concentration-dependent morphology:
   isotropic/micellar, elongated, lamellar.

## Standing gates for everything downstream

**No lipid result counts unless a matched pure-solvent control passes** at the same density,
temperature, timestep, box and parameters. This is the gate whose absence invalidated the whole
previous phase. It is now a precondition, not a post-hoc check.

**No membrane claim from a single scalar.** Requires two leaflets, opposed axes across a shared core,
heads solvent-facing on both sides, stable thickness, healthy solvent, and an image.

## Claims frozen as provisional

Not deleted, not trusted. All measured while the solvent was collapsing; all need remeasuring:

- the ~81-lipid minimum planted vesicle
- the ~45-lipid largest emergent aggregate, and the 18–20 dispersed plateau
- the head_sigma ≈ 1.0 phase optimum
- single- vs double-tail conclusions
- curvature tolerance at R ≈ 5
- the "kinetic ceiling" reading (also weakened independently by the omitted mixing-entropy term)

## What would count as a result

**Positive:** transformerised DPD reproduces reference DPD phase behaviour → a transformer-compatible
bounded interaction architecture can reproduce the self-organised phase behaviour of a known
soft-matter model. Far stronger than "a vesicle appeared".

**Negative:** reference DPD works, exact DPD in Vivarium works, transformerised DPD fails → a genuine
architectural result, with the failing substitution isolated (normalisation, radial features,
directional encoding, species representation, force symmetry, precision).

Either outcome is worth more than the current global negative, which cannot distinguish "the
architecture cannot" from "these parameters do not".
