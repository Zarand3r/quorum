# Vivarium membrane results

**Updated 2026-08-12.** Every number here is reproducible from the commands in §6 and locked by
`tests/test_ylz.py`. Claims that were withdrawn are listed in §5 rather than deleted.

---

## 1. Headline

Vesicles now emerge, from a random start, in our own engine, from interactions that are **bounded**
and **exactly expressible as one attention layer**. That is three of Vivarium's hard constraints
satisfied simultaneously by a model that self-assembles the target structure.

| | result | evidence |
|---|---|---|
| emergent vesicle, open-source reference | 129-particle shell | LAMMPS `pair_style ylz`, ~3 min |
| emergent vesicle, **our engine** | 94 particles, R = 2.62 ± 0.12, zero inside 0.5R | stable over 1.05M–1.5M steps |
| energy is **exactly** one attention layer | rel. error 1.6e-16 (r^-4 core), 2.1e-16 (bounded) | `attention_ylz.check_identity` |
| vesicles with **no divergent kernel** | 10, 100, 300 eps contact all close | 1.5M-step scan |

## 2. The mechanism we were missing

Every failure before this was traceable to one absence: **nothing in our model referred to the
molecular axis**. Interactions were isotropic between beads and depended only on species and
distance. Spontaneous curvature is

    beta (u_i - u_j) . r_hat

which is odd under `u -> -u` and therefore needs a signed per-molecule orientation. With `beta = 0` a
finite membrane patch stays an open flat disc, because its radius sits below the closure threshold
`2 kappa / Gamma`. With `beta = 0.1` it closes. `beta = 0.2` and `0.3` overshoot into 38- and
24-particle shells.

This was not a tuning failure. No amount of adjusting concentration, box size, tail length or the
`a_ij` matrix could have produced closure, because the term that drives it was not representable.

## 3. Two supporting results that transfer

**Mass balance decides morphology.** Measured area per particle is exactly 1.50 sigma^2 (a 900
sigma^2 spanning sheet held 600 particles). A morphology is only reachable if the particle count can
afford it:

| structure | cost |
|---|---|
| box-spanning sheet | `L^2 / a` |
| box-spanning tube | `2 pi r L / a` |
| closed vesicle | `4 pi R^2 / a` |

At L=30 six hundred particles tile a sheet; at L=34 they still afford a tube (498 needed), and a tube
is what formed. Only when both are unaffordable does a finite aggregate close. LAMMPS obeys this rule
exactly as our own engine does, which retroactively validates the geometric analysis done for DPD.

**The performance gap is mostly the model, not the code.** Per particle-step, LAMMPS runs 1.7e7
against our 2.5e5 -- a 69x implementation gap. But YLZ needs 600 particles for one vesicle where an
11-bead lipid with explicit rho=3 solvent needs 59049, a 98x difference in problem size. Three
minutes against twenty hours is mostly the second factor.

## 4. Why this representation suits Vivarium

| | Vivarium as built | this model |
|---|---|---|
| token | one bead (11/lipid + solvent) | one lipid patch, or one head/tail dimer |
| token state | position + species label | position + orientation |
| interaction | species-indexed repulsion matrix | inner products `<q_i, k_j>`, `<n, r_hat>` |
| tokens per vesicle | ~59 000 | 300–600 |

A species label is a lookup; an orientation vector participates in inner products, which is what
attention computes. The identity that makes M2 exact is

    n_i . n_j - (n_i.r_hat)(n_j.r_hat)  ==  n_i^T (I - r_hat r_hat^T) n_j

a query-key inner product under a metric fixed by the pair direction. The whole potential is then
`U = A(r) + B(r) a_ij`: a radial gate (the distance penalty) times a content term. Attention is left
**unnormalized** deliberately -- softmax would make each pair's contribution depend on a particle's
other neighbours, destroying the pairwise additivity the potential relies on. `SPEC.md` asks for
"local attention ... distance-penalized" and does not mandate softmax.

## 5. Withdrawn claims

Kept visible because the failure modes recur.

| claim | why it fell |
|---|---|
| `bilayer_frac > 0.5` as a success target | a thermalized healthy bilayer reads 0.12-0.31; target was calibrated on a zero-temperature lattice |
| 2-D ribbons beat the 3-D slab by 1.7x | both inside a noise band whose own reference oscillates 0.117-0.312 |
| planted R=9 vesicle "is stable" | 30% of amphiphiles shed; equilibrium stability unproven |
| YLZ has no divergent core | it is `r^-4`; `u_R(0.01) ~ 1.6e8`. Stated twice before being checked |
| our engine cannot reproduce the LAMMPS vesicle | diagnosed from a run truncated at 450k steps; it closes at 1.05M |
| flood-fill lumen detection | five successive versions, each fixing one planted control and breaking another; replaced by percolation-gated shell metrics |

Two of these were reported to a reviewer as findings before being withdrawn. The instrument, not the
simulation, has been the expensive part of this project throughout.

## 6. Reproduction

```bash
sudo apt-get install -y lammps lammps-examples
cd projects/vivarium

lmp -in lammps/in.b0.1                                   # M0: LAMMPS vesicles, ~3 min
bazel run //projects/vivarium:ylz                        # force/torque gradient check
bazel run //projects/vivarium:attention_ylz              # exact attention identity, both cores
bazel run //projects/vivarium:bilipid                    # two-species chain-rule gradient check
bazel run //projects/vivarium:_ylz_run -- 300 25 1500000 0.1 tag 30   # M3: bounded-core vesicle
bazel test //projects/vivarium:test_suite
```

## 7. Open

* **Softmax normalisation** -- untested, and the substitution most likely to break vesiculation.
* **Two-species closure** (M4) -- a head/tail dimer carrying a derived orientation; assembling and
  curving at 500k steps, not yet closed.
* **The "one clock" spec** -- weight-tied per-tick block with a local learning rule: untouched.
* **Strict 2-D closure** -- unsolved, and the open-source 2-D reference does not solve it either, so
  it is a genuine research question rather than a defect.
