# Reviewer prompt: bending rigidity is unmeasurable here, and it is the last unknown

**Date:** 2026-08-19. Worktree `/home/rbao/quorum-thermolife`, branch `autoresearch/bilayer-emergence`.
Self-contained. **One question, in §4.**

This is raised under a stuck criterion agreed in advance: *two consecutive attempts at the same
measurement failing for instrument reasons*. The undulation spectrum has now failed twice, and the
second attempt — on a membrane twice the size — was worse than the first.

---

## 1. Why kappa is the last unknown

Closure of a finite 2-D bilayer ribbon trades a constant against a size-dependent term:

    edge saved   = 2 * lambda                        (independent of ribbon length)
    bending paid = pi * kappa / R,   R = L_c / 2pi   (falls as the ribbon grows)

**lambda is measured and solid.** From a flat finite ribbon against a flat SPANNING (periodic,
therefore end-free) ribbon at identical N, density and temperature, 5 seeds, 20000 steps each:

| | E |
|---|---|
| spanning, no ends | -2115.13 +- 6.04 |
| finite, two ends | -2078.50 +- 12.79 |
| **lambda** | **+18.31 +- 7.07 eps = +40.7 +- 15.7 kT per end** |

Positive at 2.6 sigma. Both arms flat, so bending contributes to neither. Closure therefore has
about **81 kT** to gain, and is favoured whenever **kappa < ~150 kT**. Real membranes are 10-30 kT.

**CORRECTION (2026-08-19), and it changes what this document should have asked.** The comparison
above -- "real membranes are 10-30 kT" -- is dimensionally void. In 2-D,
`E = (kappa/2) integral (u'')^2 dx` gives `[kappa] = energy * LENGTH`; in 3-D,
`E = (kappa/2) integral (2H)^2 dA` gives `[kappa] = energy`. An energy*length cannot be compared with
an energy, so no statement of the form "our kappa is enormous / ordinary versus real membranes" was
ever meaningful, and all of them are withdrawn.

The critical-size logic is unaffected, since it balances two 2-D energies against each other and is
self-consistent. It has since been run and DID find a threshold: planted arcs unroll at N = 70 and
retain a lumen at N = 120, 200 and 300, with shell CV falling monotonically 0.370 / 0.353 / 0.218 /
0.194. From `2*lambda = pi*kappa/R` at the threshold this gives **kappa ~ 90 eps*sigma** (bracketed
65-111), which is the first bending-rigidity estimate in this project.

So question 3 below is now answered by our own data, and the remaining questions are about method.

## 2. What was tried, and how it failed

Thermal undulations of a flat spanning bilayer, midplane height u(x) binned along the membrane,
fitting `<|u_q|^2> = kT / (kappa q^4 L)`.

**Attempt 1**, 60 lipids, L = 30, 12 bins, 4 modes. Reported slope 19.8, R^2 = 0.961, kappa = 0.7 kT.
Retracted: extracting kappa mode by mode gives 10.42 / 2.78 / 0.62 / 0.74 kT — a 16.7x spread. R^2
passed because a linear fit of `1/<|u_q|^2>` against q^4 spanning 2.5 decades in x is dominated by its
single largest point. R^2 is a poor test of a power law.

**Attempt 2**, 120 lipids, L = 60, 24 bins, 6 modes, 399 samples. Per-mode gate (spread < 2x) added.

| mode | q | `<\|u_q\|^2>` | kappa |
|---|---|---|---|
| 1 | 0.105 | 0.282 | 491.9 kT |
| 2 | 0.209 | 0.547 | 15.8 kT |
| 3 | 0.314 | 0.830 | 2.1 kT |
| 4 | 0.419 | 0.479 | 1.1 kT |
| 5 | 0.524 | 0.772 | 0.3 kT |
| 6 | 0.628 | 0.255 | 0.4 kT |

Spread **1712x**. The diagnosis is in the raw column: `<|u_q|^2>` is FLAT in q across a sixfold range,
where q^-4 would fall by 1296x. A flat spectrum is white noise — the estimator is measuring its own
sampling error. With 120 lipids in 24 bins each bin mean carries the scatter of five lipids.

Doubling the membrane made it worse, which is the part we find most informative and least understood.

## 3. The system

2-D coarse-grained amphiphile, explicit solvent. Pair energy
`U_ij = eps [ core(r/sigma) + well(r/sigma) * chi_ij ]`, one energy scale, one length scale, symmetric
3x3 `chi` over (head, tail, water); no orientation term anywhere. Chains carry 1-2 and 1-3 harmonic
bonds. Inertial Langevin, dt = 8e-3, validated against the overdamped ensemble over 5 seeds per rung.
Forces are `-dU/dX` to 1.2e-07. The membrane is FLUID at this state point (kT = 0.45, two tails):
neighbour retention 0.42, against 0.80-0.93 in the gel at kT = 0.17.

## 4. The question

**How should we measure kappa for a 2-D bilayer of ~100 lipids, given that the undulation spectrum is
swamped by finite-N sampling noise?**

Specifically:

1. **Is undulation analysis simply inapplicable at this size**, and if so is there a rule of thumb for
   the minimum lipids-per-mode needed before the spectrum rises above the sampling floor? We would
   rather know the requirement than keep doubling.
2. **Is there a better estimator at small N** — buckling a ribbon of fixed contour length between
   fixed ends and reading the force; the tilt/splay fluctuation route; a constrained-curvature
   thermodynamic integration; something else?
3. **Or should we not measure kappa at all?** Our fallback is a CRITICAL-SIZE experiment: sweep
   planted arc length (70/120/200/300 lipids) and find the threshold where arcs stop unrolling and
   start closing; at threshold `pi*kappa/R = 2*lambda` yields kappa with no spectrum. It costs four
   long runs. Is that sound, and is the threshold sharp enough to locate with four points?
4. **Does a flat `<|u_q|^2>` indicate anything beyond sampling noise** — a membrane with no coherent
   bending mode at all, which would itself be the answer?

## 5. Context that may matter

All three closure attempts used ~70 lipids and every one saw the arc EXPAND rather than close: at
kT = 0.17 it sat open, at 0.55 it tore in two (70 -> 38 lipids), at 0.45 it unrolled into a shallow
band. If the critical size exceeds 70, all three were run below threshold and say nothing about the
model — which we should have computed before spending them.

Separately, a ring-versus-arc energy comparison at matched conditions returned `-0 +- 81 kT` over 5
seeds: an error bar larger than the effect. Recorded as blind, not as zero.

## 6. Standing caveat

This project has withdrawn roughly fifteen results and the large majority were measurement or protocol
artefacts rather than physics — false HOLLOW verdicts from a centroid lumen detector, "bilayers" that
were interpenetrating piles, a conservativity audit that measured step displacement instead of force,
a closure metric that scored any blob as closed, a render slab that turned a hollow shell into a
filled ball, a 3-D solvent that was never a liquid, MSD-as-fluidity contaminated by rigid-body
rotation, and now two kappa attempts. Treat every number here as provisional unless it has a control
or a render behind it. `lambda` in §1 has both.
