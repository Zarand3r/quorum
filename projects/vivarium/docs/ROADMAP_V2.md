# Roadmap v2: ablation from a working oracle

**Adopted 2026-08-11**, replacing `ROADMAP_RESET.md`. Written after `pair_style ylz` in stock LAMMPS
produced self-assembled vesicles in ~3 minutes (commit `61c4670`), ending a week in which a custom
NumPy DPD engine produced none.

## The change

The old ladder made our own DPD engine the Stage-D reference, and deferred the open-source rungs
because LAMMPS was not installed. That deferral was the single most expensive decision in the
project: it forced us to debug a thermostat, rebuild a cell list, reconstruct published parameters
from web searches, and survive five metric failures, none of which was needed to answer "does
vesicle emergence happen".

The new ladder starts from a known-working implementation and removes one thing at a time. Every
failure then localises to the step that caused it.

| rung | system | status |
|---|---|---|
| **M0** | stock LAMMPS `pair_style ylz`, unmodified | **DONE** — vesicles, 129-particle shells, R=3.08+/-0.16 |
| **M0b** | stock LAMMPS `examples/micelle`, unmodified, 2-D | **DONE** — bilayer strips, NO closure |
| M1 | YLZ physics reimplemented in our engine | **DONE** -- vesicle, 94 particles, R=2.62+/-0.12, stable 1.05M-1.5M |
| M2 | YLZ written as one attention layer | **DONE** -- exact identity, 1.6e-16 relative |
| M3 | bounded repulsive core (Vivarium forbids divergent kernels) | **FAILS at 3 eps** -- collapse, see below |
| M3.. | continue substituting, one at a time | |
| G | strict-2-D closure | open research question |

The first rung where vesiculation disappears is the answer to the project's actual question.

## What M0 established

**1. Our 2-D branched ribbons were never a failure.** The unmodified LAMMPS 2-D example produces the
same branched bilayer strips and scores 0.000 on our own D11 vesicle metric. 2-D closure is not
something the open-source reference achieves either. Weeks of treating the ribbons as our bug were
misdirected; `G` is a genuine research problem, not a defect.

**2. The missing mechanism is spontaneous curvature.** YLZ carries an explicit term for it. With
beta=0 a finite patch stays an open flat disc, because its radius sits below the closure threshold
2*kappa/Gamma. beta=0.1 closes it; beta=0.2 and 0.3 overshoot into 38- and 24-particle shells. Our
DPD amphiphile has no equivalent knob at all, so no amount of tuning concentration, box size or
chain chemistry could have produced closure.

**3. Our geometric analysis was correct and transfers.** Morphology is decided by what the particle
count can afford. Measured area per particle is exactly 1.50 sigma^2. At L=30, 600 particles tile a
box-spanning sheet; at L=34 they still afford a spanning tube (498 needed). Only when sheet AND tube
are both unaffordable does a finite aggregate form. LAMMPS obeys the same mass-balance rule derived
for our DPD.

**4. The performance gap is mostly the MODEL, not the code.** Measured per particle-step, LAMMPS is
1.7e7 against our 2.5e5, a 69x implementation gap. But YLZ needs 600 particles for one vesicle where
our 11-bead lipid with explicit rho=3 solvent needs 59049 -- 98x fewer. Combined, that is 3 minutes
against 20 hours.

## Why YLZ is a better bridge to Vivarium than DPD

This was not obvious and is the main strategic finding.

* **CORRECTION (2026-08-12).** An earlier version of this document claimed the YLZ pair potential
  has no divergent core. That is WRONG. Its repulsion is `eps[(rmin/r)^4 - 2(rmin/r)^2]`, which
  diverges as r^-4: u_R(0.01) ~ 1.6e8. It is softer than Lennard-Jones r^-12 but not bounded, so it
  violates Vivarium's no-divergent-kernel requirement and must be replaced. See M3 below.
* **One particle per lipid patch.** A fixed particle count with no solvent maps directly onto a fixed
  token count, which is Vivarium's hard constraint. Our 11-bead-plus-solvent model does not.
* **The interaction is already dot-product algebra.** Each particle carries a unit orientation
  n_i, and the angular function is built from
  `(n_i x r_hat).(n_j x r_hat)` and `beta (n_i - n_j).r_hat`. Those are inner products between
  per-particle vectors modulated by a relative-position direction -- structurally the same algebra
  attention performs between query and key vectors. Reproducing YLZ with attention kernels is a far
  shorter reach than reproducing Groot-Warren DPD.

## Immediate next steps, in order

1. **Validate D11 against the oracle.** The YLZ vesicle is the first true positive this project has
   from an independent implementation. Its shape half (shell_cv, hollowness, eigenvalue spectrum)
   applies directly. CAVEAT: the amphiphile half (`paired`, `inward`, `filling`) cannot be evaluated
   on YLZ at all, because YLZ is solvent-free with no head/tail distinction. Validating that half
   needs a vesicle from an explicit-solvent head/tail model, which we do not yet have from any
   source.
2. **M1: port YLZ into our engine** and require vesicles to survive the port. This isolates our
   integrator and boundary conditions from the physics.
3. **M2: substitute one interaction** with a transformer-expressible form, starting with the angular
   function, since that is the piece attention most naturally expresses.

## Corrections this supersedes

* `bilayer_frac > 0.5` as a success target (D10): void, a thermalized healthy bilayer reads 0.12-0.31.
* The D9 ranking of 2-D ribbons over the 3-D slab: retracted as sampling noise.
* "Planted R=9 vesicle is stable": downgraded, equilibrium stability unproven at 30% shedding.
* Shape classification by `ev3/ev1` alone: cannot separate a flat sheet from a tube, both near zero.
  The full eigenvalue spectrum is required. Four states previously called tubes were flat sheets.

## Reproduction

```bash
sudo apt-get install -y lammps lammps-examples
cd projects/vivarium/lammps
lmp -in in.b0.1        # self-assembling vesicles, beta = 0.1, ~3 minutes
lmp -in in.long        # 2-D bilayer strips, examples/micelle model unmodified
```


## M3 result: a bounded core matched to YLZ's curvature COLLAPSES the membrane

Vivarium forbids divergent kernels, so the `r^-4` core has to go. The first replacement was a
harmonic matched to the original in value, slope and curvature at r_min (u = -eps + k(rmin-r)^2 with
k = 4 eps/rmin^2), giving a finite contact energy of 3 eps. Gradient checks still pass (1.8e-8).
Everything else in the model is untouched.

| step | divergent r^-4 core | bounded core, 3 eps contact |
|---|---|---|
| 150k | E/particle -1.84, R 2.27 | -3.50, R **0.81** |
| 300k | E/particle -2.14, R 2.63 | **-5.96**, R **0.82** |

R ~ 0.8 with 50 particles in the cluster is roughly 12x denser than close packing: the particles have
collapsed into each other. Energy falling steeply while radius stays fixed is the signature.

**What this does and does not establish.** It shows that THIS bounded core is too soft, not that
bounded cores cannot work. The contact energy of 3 eps against kT = 0.1724 is only ~17 kT, and with
many simultaneous neighbours that barrier is surmountable. The obvious next experiment is a scan over
contact energy (say 10, 30, 100, 300 eps) asking whether any value both prevents collapse and
preserves vesiculation. If a window exists, Vivarium's constraint is satisfiable. If none does, the
no-divergent-kernel requirement and membrane self-assembly are in genuine tension, which would be a
real architectural result and the most valuable output of this ladder so far.
