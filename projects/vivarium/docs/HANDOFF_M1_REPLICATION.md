# Handoff: our engine reproduces the YLZ *potential* exactly but not its *morphology*

**Date:** 2026-08-12. **Worktree:** `/home/rbao/quorum-thermolife`, branch `quorum-asal-boids-reproduction`.
Self-contained. Prior context in `docs/ROADMAP_V2.md`; not required to answer the question below.

**Standing instruction:** be adversarial about over-claiming. Five results have been withdrawn in this
project, two after being reported to a reviewer as findings.

---

## 1. The question

Stock LAMMPS `pair_style ylz` self-assembles closed vesicles from a random start in ~3 minutes. We
reimplemented the same potential in our own NumPy engine (roadmap rung M1). With an **identical**
configuration it produces flat sheets and tubes, never a closed vesicle.

We have eliminated the potential as the cause. **What dynamical difference selects the vesicle?**

---

## 2. What is definitively NOT the problem

### 2.1 The potential is bit-for-bit the same physics

Gradient checks (analytic force and torque vs finite differences of our own U) pass at ~2e-8. But
that only proves `force = -grad(our U)`; it cannot prove `our U == LAMMPS's U`. So we tested that
directly: dumped LAMMPS configurations *including quaternions*, converted them to orientation
vectors, and evaluated our energy on the identical coordinates.

| step | LAMMPS `E_pair`/atom | ours, n = body **x** | ours, n = body y | ours, n = body z |
|---|---|---|---|---|
| 0 | 0.155377 | **0.155382** | 0.203385 | 0.228421 |
| 20 000 | -0.089530 | **-0.089530** | 0.329034 | 0.304934 |
| 40 000 | -0.116575 | **-0.116573** | 0.417287 | 0.472339 |

Agreement to ~6 significant figures with `n` taken as the particle's **body x-axis**. The residual is
consistent with the dump's 6-decimal coordinate precision. Our implementation of

    U   = u_R(r) + [1 - phi] eps                  r <  r_min
    U   = u_A(r) phi                              r_min < r < r_c
    phi = 1 + mu (a - 1)
    a   = n_i.n_j - (n_i.r_hat)(n_j.r_hat) + beta[(n_i - n_j).r_hat] - beta^2

is therefore correct, including the angular term and the beta (spontaneous-curvature) term.

### 2.2 It is not a failure to converge, and not under-binding

Matched runs, same N=300, L=25, beta=0.1, zeta=4.5, mu=3, eps=1, rc=2.6, kT=0.1724:

| | LAMMPS | our engine |
|---|---|---|
| E/particle at 150k | -0.340 | **-1.837** |
| E/particle at 300k | -0.900 | **-2.141** |
| E/particle at 450k | -1.530 | **-2.185** |
| E/particle converged (1.5M) | **-1.93** | (still running) |
| morphology | **closed vesicles**, largest shell 129 | flat sheets / tubes, largest 52 |

Our engine aggregates *faster* and reaches a **lower** pair energy than LAMMPS reaches at any point,
including its converged value. So this is not slow kinetics and not a weak interaction.

**This is the part we find most interesting and would like challenged:** if both engines evaluate the
same U, and ours reaches -2.19 while the vesicle state sits at -1.93, then the vesicle is *not* the
lowest-energy configuration available. It appears to be dynamically selected rather than
energetically preferred. Is that a known property of YLZ (i.e. a finite flat/stacked aggregate is
lower energy than a small closed shell, and vesiculation depends on the assembly pathway), or does it
indicate we are falling into a state LAMMPS's dynamics correctly avoids?

---

## 3. The candidate causes, all dynamical

Everything below differs between the two engines. We have not yet isolated which matters.

**3.1 Moment of inertia is ~20x too large in ours.** LAMMPS `set shape 1 1 1` + `set density 1.0`
gives semi-axes 0.5, mass ~= 0.524, and ellipsoidal inertia `I = m(b^2+c^2)/5 ~= 0.052`. Our
implementation uses `m = 1` and `I = 1` implicitly (`w += dt*torque`). Orientational relaxation is
therefore roughly 20x slower relative to translation in our engine. Since the whole model encodes
membrane normals in the orientations, we consider this the leading suspect: patches could translate
and merge faster than they can re-orient, favouring stacking over curving.

**3.2 Thermostat.** LAMMPS uses `fix nvt/asphere` (Nose-Hoover, deterministic, momentum-conserving).
We use Langevin with `gamma = 1.0` applied to both translation and rotation, via an exact
Ornstein-Uhlenbeck update. Langevin damps collective and hydrodynamic motion, which is exactly the
mode that drives cluster coalescence and shape relaxation. Our temperature is timestep-independent
(0.181 / 0.195 / 0.182 across a 4x dt range) but sits ~8% above the 0.1724 target.

**3.3 Rotational integrator.** LAMMPS integrates a quaternion with the full inertia tensor. We use a
first-order update `n <- normalize(n + (w x n) dt)` with `w` projected perpendicular to `n`.

**3.4 Rotational degrees of freedom.** We constrain `w . n = 0` (uniaxial particles, spin about `n`
is unobservable), giving 2 rotational DOF. LAMMPS integrates 3 and lets the spin ride free. This
changes the equipartition bookkeeping and hence the effective rotational temperature.

---

## 4. Specific questions

1. **Is the vesicle energetically or kinetically selected in YLZ?** Our engine finds a state ~13%
   lower in pair energy than LAMMPS's vesicle. If vesiculation is pathway-dependent, then matching
   the potential is insufficient by construction and we need to match the *dynamics*, which changes
   what "porting the model" means for the rest of our roadmap.
2. **Is the inertia mismatch sufficient on its own** to switch the outcome from vesicle to sheet? Is
   there a published statement of the Sc = (rotational relaxation)/(translational relaxation) regime
   the YLZ model requires? We can set `m = 0.524`, `I = 0.052` immediately; we would rather know
   whether that is the expected fix than discover it by scanning.
3. **Would you expect Langevin at gamma = 1.0 to suppress vesiculation** relative to Nose-Hoover, or
   is that second-order next to the inertia? If Langevin is the problem, what damping would you use?
4. **Is our 2-DOF rotational constraint wrong** for this model, given that LAMMPS carries a full
   quaternion?
5. **Is there a cleaner acceptance test for M1** than "does a vesicle appear"? For example a measured
   bending rigidity kappa from the fluctuation spectrum of a planted flat patch, compared against the
   value LAMMPS gives for the same parameters. That would validate the port quantitatively without
   depending on a stochastic assembly pathway.

---

## 5. Reproduction

```bash
sudo apt-get install -y lammps lammps-examples
cd projects/vivarium

# LAMMPS reference, produces vesicles
lmp -in lammps/in.b0.1

# our port: gradient check, then self-assembly
bazel run //projects/vivarium:ylz                     # analytic vs numerical force/torque
bazel run //projects/vivarium:_ylz_run -- 300 25 1500000 0.1 ourylz_m1
```

Energy cross-check: dump LAMMPS with
`compute q all property/atom quatw quati quatj quatk` and
`dump ... id type x y z c_q[1] c_q[2] c_q[3] c_q[4]`, convert quaternion to the **body x-axis**, and
call `YLZ.energy()` on those coordinates.

Source: `projects/vivarium/ylz.py` (potential + integrator), `_ylz_run.py` (driver + shape
classification). Shape is classified from the full gyration eigenvalue spectrum, since `ev3/ev1`
alone cannot separate a flat sheet from a tube -- both are near zero.
