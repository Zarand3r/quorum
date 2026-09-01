# Reviewer handoff — vivarium, 2026-08-31

**Ask:** we can now build membranes and cannot close them. One measured quantity has refused to move
across every intervention. We would like a second opinion on whether the model *can* close a vesicle,
and if so what is missing.

---

## 1. The objective

Can a lipid vesicle self-assemble in a simulator where every force is a transformer attention
operation — each molecule a token, each step a forward pass? Constraint: nothing may be supplied that
contains the answer. Spontaneous curvature (a term that tells the membrane to bend) is refused, because
a vesicle that forms because we told it to bend has not emerged.

Three target behaviours: **emerge**, **fuse**, **divide**.

## 2. What is established

**The transformer formulation is exact and free.** Forces match the ordinary force law to 1e-13, one
forward pass equals one integrator step bit-for-bit, and it costs no measurable time (21.17 ± 2.42 vs
20.65 ± 1.66 ms/step). This is not in question.

**2-D: a vesicle emerges, rarely.** 2 of 18 fresh dispersed seeds, render-confirmed. Closure is
controlled by the ribbon's end-to-end gap (5/5 at 3.4 sigma, 1/10 at 10.1 sigma), not by curvature.

**3-D membranes now work — this is new as of today.** The cause of every prior 3-D failure was that
lipids had **zero harmonic bending stiffness**. The 1-3 "stiffener" rested at exactly the straight
chain's own geometric length, so with `r13 = 2b cos(d/2) ~ 2b - b d^2/4` the energy is
`(K b^2/32) d^4` — purely quartic, second derivative zero at d = 0. Verified on our own potential:
`V/d^4 = 0.9375` constant, `V/d^2 -> 0.0004` at d = 0.02. Cooke-Deserno's rest length of 4 sigma is a
deliberate pre-stress that makes the same spring quadratic with `k_theta = k sigma^2`.

With that one number changed:

| | k_theta = 0 | k_theta = 33 |
|---|---|---|
| planted planar bilayer, min thickness | 0.65 (dissolves; traces reach 0.15) | **2.87 (holds)** |
| self-assembly from random start, mean thickness | 1.72 | **3.41** |
| closure run, N = 1600, mean thickness | — | **4.14** |

Reference bilayer 4.05–4.40; random gas 1.31. The closure run reached **103%** of reference, 3 of 6
seeds at or above it, self-assembled from a random start. Self-assembly A/B was a perfect 3v3
separation, exact one-sided p = 0.050.

## 3. The blocker

**`hollow` does not move.** It is the share of tail beads nearer the aggregate centre than the median
head: 0.000 for a shell, 0.573 for a flat sheet, 0.987 for a solid ball.

| configuration | membrane quality | hollow |
|---|---|---|
| broken bending, N=200 planted spheres | none | 0.995 |
| k_theta = 100, planted spheres | — | 0.652 |
| assembly N=1000, broken bending | poor (1.72) | 0.505 |
| assembly N=1000, bending fixed | good (3.41) | 0.500 |
| closure N=1600, bending fixed | **reference (4.14)** | 0.512 |
| H4 k_theta = 10 and 20 (in progress) | degraded (2.2–3.2) | 0.46–0.54 |

Across a ~40x range of membrane quality, a 3x range of bending stiffness, three lipid counts, four box
sizes and two densities, `hollow` has stayed at **0.49 ± 0.03**. In the current run, 46 checkpoints
give min 0.46, median 0.49, max 0.541. The vesicle threshold is 0.25. It has never approached it.

**Closure is not downstream of membrane stability.** Fixing the membrane was decisive for membranes and
brought closure not one step closer.

## 4. Ruled out, with evidence

- **Head area** — swept 0.6–1.8 sigma, 39 runs, no effect on closure (and the sphere-scan confound is
  noted below).
- **Temperature** — 0.3–1.3 eps.
- **Attraction width** — w_c 0.6–1.8 sigma; our operating point is inside Cooke's fluid band.
- **Excluded-volume stiffness** — core height 37.8–1000; interpenetration repairs monotonically
  (nn/contact 0.30 -> 0.95) with no effect on closure.
- **Density** — packing 0.034–0.101; correlation with membrane consolidation is **-0.30**, i.e. the
  opposite of the prediction. NOTE: measured under the broken bending term, so it should be retested.
- **Bounded soft core** — exonerated by direct precedent: Revalee, Laradji & Sunil Kumar (JCP 128,
  035102, 2008) self-assemble solvent-free bilayers from 3-bead lipids with a bounded quadratic core,
  harmonic bonds and a single bead size. Their `U_max/kT ~ 33`; ours is 29–126.
- **FENE bonds** — not required (Laradji uses harmonic).
- **Head/tail size asymmetry** — not required (Laradji uses one bead size).
- **Bending stiffness (as a closure lever)** — H4 in progress and looking negative; k_theta 10, 20, 33
  all give hollow ~0.50 while thickness varies 2.2–4.14.

## 5. The specific question for a reviewer

In a solvent-free model, line tension at a membrane edge arises **only** from tails at the rim losing
tail-tail contacts. There is no water for them to be exposed to. Our chemistry is `cooke_chi`: one
attraction, tail-tail, `chi_TT = 1.0`; heads carry no attractive term at all.

**Is that edge penalty large enough to drive closure, and how would we measure it directly?**

`R_c = 2 kappa / lambda`. We can vary `kappa` (done — no effect on `hollow`). We have never measured
`lambda` in 3-D, and the project's three previous attempts to measure it in 2-D all failed
(`lambda = +2.8 ± 2.8 eps`, consistent with zero; `kappa` defeated three independent routes).

Concretely:
1. Is `hollow` at ~0.50 with a reference-quality membrane the expected reading for a **flat sheet that
   simply has no reason to curl**, or does it indicate something structurally wrong?
2. What is the cheapest direct measurement of line tension in a solvent-free CG bilayer? Is the
   standard route (a planted ribbon / half-membrane with two free edges, measuring the pressure-tensor
   anisotropy) sound here?
3. Given `chi_TT` is the *only* attraction, is there a principled way to raise edge cost **without**
   importing spontaneous curvature — i.e. without violating the constraint in §1?
4. Should we accept that a 1600-lipid patch is simply below `R_c` and go to N = 5000–10000, or is that
   throwing compute at a structural problem?

## 6. Calibration — how much to trust the above

This session produced **five measurement defects**, all of the same shape: a metric that could not
distinguish success from the failure mode actually present.

1. `n_enclosed` is a **2-D** detector (`np.zeros((n,n))`, 4-connectivity). It reads 0 on a genuinely
   hollow 3-D vesicle. 39 runs were scored against it before this was caught.
2. `frac_largest` scores a collapsed globule identically to a vesicle. Caught by rendering.
3. `core_fraction` scores a healthy flat bilayer (0.3755) identically to a blob, and is
   *anti-correlated* with solidity on real states.
4. A gate reported "AC-2 satisfied" when the control arm had **never been run** (rate defaulted to 0).
5. An A/B passed its parameter through `os.environ` while workers were threads in one process; both
   arms silently got the same value and the results were bit-identical.

`bilayer_metrics.py` (thickness / hollow / anisotropy) is validated against four synthetic controls it
must **separate** — vesicle, sheet, blob, gas — and against the Cooke-Deserno oracle at N = 200, where
it correctly reads a bilayer sheet of thickness 4.05. It is the only instrument here we would defend.

Four hypotheses were proposed and withdrawn during the session: gel phase, interpenetration, dilution,
and "a 3-D vesicle is stable in this engine". Each was refuted by its own pre-registered test.

## 7. Reproduction

    bazel test //projects/vivarium:test_suite        # 240 tests
    python phase_diagram.py --probe                  # instrument validation
    python bilayer_metrics.py                        # four-control separation check

Specs and outcomes: `specs/2026-08-30_vesicle_feasible_geometry.md` (H3 + amendments 1–4),
`specs/2026-08-28_head_area_*.md` (H1, H2, both negative, both with errata).
Results: `docs/results/*.tsv`. Narrative: `RESEARCH_LOG.md`. Summary: `SUMMARY.md`.
Literature: `docs/DEEP_RESEARCH_2026-08-31.md`.
