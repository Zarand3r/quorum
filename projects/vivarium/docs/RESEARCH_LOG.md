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

## 2026-07-28d — porting the Cooke-Deserno recipe, one difference at a time

Working hypothesis: the control (`cooke_deserno.py`) makes a bilayer, so porting its recipe into
vivarium should too. Each run below removes ONE remaining difference and re-tests the planted bilayer
at kT=0. Everything is solvent-free with head_q=0 and rad_head=0.05, which zeroes head cohesion while
leaving head EXCLUDED VOLUME intact (eps = tanh(rad^2/0.25), so rad 0.05 -> eps 0.01 vs tail 0.999).

| # | difference removed | result | verdict |
|---|---|---|---|
| 1 | direct port (no water, no electrostatics) | nematic +1.000 -> -0.315 | melts |
| 2 | + steric overlap fixed (2.5,1.5,0.5) | +1.000 -> -0.255 | melts; overlap was NOT the cause |
| 3 | + attraction range matched to CD (satt 0.30 = 2.77 sigma vs CD 2.62) | melts | range was not it |
| 4 | + isotropic beads (aniso 0.95 -> 0.0) | +1.000 -> -0.424, PLATEAUS | no longer exploding |
| 5 | + box sized so faces do not attract across PBC (bound 5.0, 231 lipids) | +0.984 -> -0.439 | still collapses |
| 6 | + rigid-rod chain (bond_span > 2*BOND_REST) | running | - |

**Bugs found and fixed along the way**, each of which invalidated earlier results:

- *Steric clash in the planted bilayer.* Offsets (2.4,1.4,0.4) put opposing leaflet tails 0.8 apart
  against a contact distance of 1.0. Fixed to (2.5,1.5,0.5), generalised to any chain length,
  verified at 0.000 overlap. Did NOT stop the melting, which is how the next bug surfaced.
- *The integrator was exploding.* See 2026-07-28c. At speed 0.08, |v| reached 11.5 at kT=0 and bonds
  stretched 3x. Reducing the timestep to 0.005 stops it: the metrics now PLATEAU instead of running
  away, which is what makes runs 4-6 admissible evidence at all.
- *aniso=0.95 by default.* Contact distance is half*(1+0.95*nf_i) + half*(1+0.95*nf_j), so it swings
  over [0.05, 1.95] rather than sitting at 1.0, stretching bonded pairs well past BOND_REST.
  Cooke-Deserno beads are spheres; aniso=0.0 reproduces that.
- *The box was too thin.* At bound 3.9 the vacuum gap is 2.8 against an attraction range of 2.77, so
  the two faces of the bilayer attracted each other ACROSS the periodic boundary. That run also had
  min-image margin 0.0104, over the 0.01 gate, so it was inadmissible regardless.

**Open at this point.** With overlap, integrator, anisotropy and box all corrected, the planted
bilayer still collapses to a condensed disordered blob (cells 49/64 -> 33/64, nematic below the -1/3
isotropic baseline, i.e. actively anti-aligned). The remaining known difference from the control is
CHAIN RIGIDITY: Cooke-Deserno sets the 1-3 rest length to 4 sigma when the chain can only reach
~1.9 sigma, so the spring is permanently stretched and the lipid is a rigid rod (measured at 98% of
maximum extension). Vivarium's BOND_SPAN=2.0 is exactly the straight length, so a straight chain
feels zero tension. `bond_span` is now tunable; run 6 sweeps it.

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
