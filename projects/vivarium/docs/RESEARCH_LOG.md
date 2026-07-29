# Vivarium research log

Append-only. Newest entry at the TOP. Every entry states what was run, what came back, and what it
changed. Claims that were later retracted stay in the log with the retraction attached, because the
retractions are the most useful part of this file.

`docs/BILAYER_REVIEW.md` holds the narrative findings (1-24). This file is the audit trail: what was
executed, in what order, and which conclusions are currently live.

## Status board

| rung | target | status |
|---|---|---|
| 0 | two lipids prefer tail-to-tail | PASSES, at 2-bead tails once head_q < 0.8 (F22) |
| 1 | micelle (radial head-out order) | FAILS, no radial order once the metric is unbiased (F21) |
| 2 | bicelle | not attempted |
| 3 | bilayer | OPEN. Every prior "melts at kT=0" result is VOID (see 2026-07-28c) |

## Live methodological rules

1. A metric is wrong until BOTH controls agree: a planted structure scores high AND a random
   configuration scores at the null. A positive control alone cannot catch a self-correlated
   statistic (F21). Three metrics have failed this in three separate places.
2. No structural claim from a single frame. It must hold across a trajectory (F24 correction).
3. At kT=0 a planted structure must not GAIN kinetic energy. If |v| grows, the integrator is broken
   and no conclusion about stability is admissible (2026-07-28c).
4. Sweep the parameter that drives the MECHANISM, not the nearest available knob (F22: range and
   head dispersion were both wrong knobs; head electrostatics was the lever).

---

## 2026-07-28c — the planted bilayer never melted; vivarium was exploding

**Ran.** Diagnostic on the planted bilayer at kT=0, tracking bond length, 1-3 span, mean speed.

**Got.**

    t=0     bond=1.000  r13=2.000  |v|=0.0000  nematic=+1.000
    t=200   bond=3.075  r13=3.593  |v|=11.5370 nematic=-0.343
    t=10000 bond=2.659  r13=3.483  |v|=12.0562 nematic=-0.315

At ZERO temperature the velocity must stay at zero. It reached 11.5 within 200 steps and bonds
stretched 3x past their rest length. This is a numerical blowup, not a phase instability.

**Changed.** RETRACTS Finding 23 ("a planted bilayer is not a mechanical equilibrium") and every
earlier planted-bilayer melting result. They all measured an exploding integrator. The mechanism
Finding 23 proposed (one dipole serving two masters) is unsupported by that evidence; it may still be
true, but nothing here shows it.

Notably this is the SAME failure that hit the Cooke-Deserno control, which needed BAOAB integration
and a displacement-capped minimiser. The difference: the control announced itself with T=1e12, while
vivarium's bounded kernels produced a quieter blowup that looked exactly like melting.

## 2026-07-28b — the hard-coded control works (F24)

**Ran.** `cooke_deserno.py`, solvent-free 3-bead lipids, 200 lipids, 300k steps, w_c in {1.5,1.6,1.7}.

**Got.** A stable bilayer at w_c=1.5: thickness 4.34-4.45 against planted 4.40 and random 1.31, held
for 210k consecutive steps. Initial report of "w_c=1.6 best" was a single-frame artifact, corrected.

**Changed.** Proves a bilayer is reachable in this box, on this timescale, under calibrated metrics.
Vivarium's negatives are therefore about vivarium, not about the harness.

## 2026-07-28a — the micelle metric measured itself (F21)

**Ran.** Null model: random centres, INDEPENDENT random orientations, scored by the same estimator.

**Got.** `outward` null = +0.669 at our cluster radius; we had measured +0.602, i.e. BELOW noise.
Cause: r-hat taken at the HEAD, whose position is cen + (L/2)u, so u sits on both sides of the dot
product. Fixed metric `cyl_c`: null 0.000 +/- 0.178, planted micelle +0.961.

**Changed.** Retracted three micelle claims. No radial order exists in the aggregates.
