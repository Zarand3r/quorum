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
| 2 | bicelle | BLOCKED BY PHYSICS, not by vivarium: a single-species lipid cannot form a stable flat disc. The Cooke-Deserno control fails it too (2026-07-29c). Needs a second, rim-capping species |
| 3 | bilayer | PLANTED BILAYER IS STABLE. lamellar 1.000 held 16k steps at kT=0, null 0.463. Self-assembly from disorder under test (2026-07-29b) |

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

## 2026-07-29c — a bicelle needs TWO species; the control fails it as well

**Ran.** Two tracks in parallel. (a) vivarium, 2-bead tails, lipid count walked past the micelle cap
(a micelle's radius is capped at one molecule length, so ~58 lipids at 2 tails; beyond that the
excess MUST take another phase). (b) `cooke_deserno.py`, the control that demonstrably makes
bilayers, given a finite lipid count in a box far larger than they can span, which is the condition
under which a free-floating disc or vesicle would appear.

**Got.**

    vivarium (2-bead tails, box 14)        lamellar  L1/L3  L2/L3  shape
      60 lipids  (1x micelle cap)            0.250   0.12   0.64
     150 lipids  (2.6x)                      0.833   0.38   0.58
     250 lipids  (4.3x)                      0.816   0.15   0.44   rod
     350 lipids  (6.0x)                      0.700   0.12   0.48

    Cooke-Deserno control, 200 lipids, big box
     t=50000    L1/L3 0.41  L2/L3 0.69
     t=100000   L1/L3 0.36  L2/L3 0.60
     t=150000   L1/L3 0.09  L2/L3 0.12    <- a ROD, not a disc

**The control fails the same way vivarium does.** Cooke-Deserno makes bilayers reliably, and given a
finite lipid count it still relaxes to a cylinder rather than a flat disc. So this is not a vivarium
defect, it is the physics of a SINGLE-SPECIES lipid: a finite flat disc has a high-energy rim where
tails are exposed to solvent, and the aggregate escapes that rim either by elongating into a cylinder
or by closing into a vesicle. Real bicelles are two-component for exactly this reason -- a long-chain
lipid forms the flat face and a short-chain detergent caps the rim (DMPC/DHPC is the standard pair).

**Consequence.** Rung 2 as written is unreachable with one species, in vivarium or in any faithful
model. It needs a SECOND species with a shorter tail that preferentially sits at the rim. Vivarium
already carries multiple species, so this is a configuration change rather than new physics.

**Also worth noting:** running the control alongside is what made this diagnosable at all. Without
it, a rod in vivarium reads as another vivarium failure rather than as correct physics.

## 2026-07-29b — the bilayer was stable the whole time; `nematic` was the wrong observable

**Ran.** Stopped adding scalars and plotted the DENSITY PROFILE along the membrane normal.

**Got.** After 8000 steps at kT=0 the tails form a single core centred at z=0 and the heads are
DEPLETED from the middle and pushed outside it, out to +/-4.8. Tails inside, heads outside, which is
the defining architecture of a bilayer. The membrane is thicker and more diffuse than planted, but
it is unmistakably lamellar. `nematic` read +0.020 for this.

**Why nematic was wrong.** It measures AXIS ALIGNMENT between neighbouring lipids. A FLUID membrane
splays and tilts its lipids while keeping heads out and tails in, so nematic decays toward 0 while
the organisation is untouched. Reading nematic alone reports a healthy fluid bilayer as a failure.
That is what it had been doing for most of a day.

**New metric, calibrated against both controls before use.** `lamellar` = fraction of lipids whose
HEAD is farther from the midplane than its OWN tails. Per-molecule, so tilt and diffuseness do not
touch it.

    planted bilayer   lamellar 0.996     nematic +0.984
    disordered start  lamellar 0.463     nematic -0.338      (null is 0.5)

    relaxation at kT=0:
    t=0      lamellar 0.996   nematic +0.984
    t=2000   lamellar 1.000   nematic +0.064
    t=8000   lamellar 1.000   nematic +0.020
    t=16000  lamellar 1.000   nematic +0.000

**THE PLANTED BILAYER IS STABLE.** Every lipid keeps its head outside its own tails for 16000 steps
at zero temperature. Finding 23 was wrong twice: the integrator was exploding, AND the observable was
measuring the wrong thing.

**Still open:** whether a bilayer EMERGES from a disordered start. Running.

**Negative results from this round, so they are not retried:** raising bond stiffness does not help
(k_bond 40/100/250 all plateau); raising cohesion actively hurts (attract 1..30 all drive nematic to
the isotropic -0.33); weakening the straightener collapses the membrane.

## 2026-07-29a — bond stiffness is not the fix; `opposed` characterised; cohesion never swept

**Ran.** k_bond in {40, 100, 250} against span in {2.0, 6.0}, planted bilayer at kT=0.

**Got.**

    k_bond    span=2.0            span=6.0
    40        -0.427  33/64       +0.025  55/64
    100       -0.101  28/64       +0.001  54/64
    250       -0.254  41/64       -0.314  50/64

Raising the bond amplitude does NOT rescue the bilayer. Best remains nematic ~ +0.02 against a
planted +0.984, so the sheet still loses essentially all orientational order. The 2026-07-28f
hypothesis (steric pressure out-guns the bond) is real as a mechanism but is not the binding
constraint.

**Useful structure in the failure.** The planted bilayer occupies 49/64 cells. At span=2.0 the system
falls to 33/64, which is COLLAPSE; at span=6.0 it rises to 55/64, which is DISPERSAL. We are
overshooting in both directions, and the membrane is not being held together in either.

**Metric characterisation, not a bug.** `opposed` reads 0.123 on a PERFECT planted bilayer and 0.275
on a RANDOM start, so it is INVERTED and weak. Widening the cutoff does not help and my first
diagnosis of an off-by-cutoff error was wrong: within a leaflet each lipid has ~42 neighbours inside
the cutoff against only ~4 across the midplane, so in-plane parallel pairs dominate the mean by an
order of magnitude. Read `nematic` as the discriminator (planted +0.984, random -0.339) and treat a
LOW `opposed` as weak corroboration only. Documented in the source next to the cutoff.

**Gap this exposed.** `attract`, the vdW cohesion amplitude, has NEVER been swept: it is hardcoded at
0.30 against repel=12, a 1:40 ratio. That is the term that has to hold a membrane together, and
collapse-versus-dispersal is exactly what an ill-set cohesion/repulsion balance looks like. Now
wired as `--attract` and being swept over {0.3, 1, 3, 10, 30} x span {2.0, 6.0}.

## 2026-07-28f — the lipids are being torn apart; the bond force is out-gunned by steric pressure

**Ran.** Tracked the MOLECULE rather than the aggregate during a planted-bilayer relaxation at kT=0.
Every orientational metric is computed from the lipid axis, so if the lipid itself deforms the metric
is noise, and nothing above had checked.

**Got.**

    span=2.0   bond (rest 1.0)   r13 (straight 2.0)   tilt    |v|      nematic
    t=0        1.01 +/- 0.20     2.02                  0.3deg  0.0000   +0.984
    t=2000     2.10 +/- 2.65     2.86                 56.4deg  0.0254   -0.441

Bonds stretch to 2.1 with a standard deviation of 2.65, so some are enormously stretched, while |v|
stays at 0.025. This is not an explosion: the molecules are being pulled apart quasi-statically.

**Mechanism.** The bond kernel is `k_bond * tanh((d-r0)/w)`, which SATURATES at k_bond = 8. The
steric repulsion is a SUM over neighbours at repel = 12, and a bead in a dense bilayer has ~12 of
them. The aggregate steric pressure therefore exceeds the maximum force a bond can ever exert, and
the chain is ripped open. Cooke-Deserno cannot hit this because its FENE bond DIVERGES: no pressure
can break it. Vivarium is not allowed to diverge, so the only equivalent is a bond amplitude that
beats the aggregate pressure, which means k_bond >> repel * n_neighbours rather than k_bond = 8.

**Also corrects 2026-07-28e.** Weakening the straightener (`bend_frac` < 1) was the WRONG move: a
full 3x3 sweep of span x bend_frac all collapsed (nematic -0.42 to -0.44, cells 32-36) versus
nematic +0.015 and cells 58/64 at bend_frac = 1.0. The saturation-cancellation argument was
theoretically reasonable and empirically backwards. The straightener's saturating tension is what
holds the bilayer open, and the molecule extending until sterics balance is the mechanism, not a bug.

**Performance.** Each job spawned 32 BLAS threads while effectively using ~9 cores, so three
concurrent runs drove load to 61 on a 32-core box. Measured: threading buys only 8% for a single run
(39 vs 42.3 steps/s at N=440). Sweeps now run ONE thread per job with many jobs concurrent, roughly
3x the throughput on the same hardware.

## 2026-07-28e — chain rigidity is the lever, and the two bond springs were cancelling

**Ran.** Swept the 1-3 rest length (`bond_span`) on the planted bilayer at kT=0, everything else at
the Cooke-Deserno-matched settings from 2026-07-28d.

**Got.** Monotonic, in the predicted direction:

    span   nematic   opposed   cells (collapse)
    2.0    -0.439     0.056     33/64      floppy: the sheet balls up
    3.2    -0.287     0.166     39/64
    4.2    -0.084     0.219     44/64
    6.0    +0.015     0.251     58/64      collapse essentially gone
    9.0    -0.024     0.240     54/64      past the optimum

**Then measured WHY**, by taking one step from rest and signing the displacement by leaflet so that
positive means "away from the midplane":

                     span=2.0 (floppy)   span=6.0 (rigid)
    head             -9.2e-05 inward     +3.96e-02 OUTWARD
    tail1            -1.29e-02           -1.29e-02
    tail2 (inner)    -4.4e-03            -4.41e-02 inward

With a floppy chain EVERYTHING moves inward: the bilayer has no mechanism to hold itself open, so it
collapses. With a rigid chain the pattern flips to heads-out / tails-in, which is exactly the force
pattern a bilayer needs. Chain rigidity is not a tuning detail, it is the mechanism.

**Bug this exposed.** The backbone bond and the 1-3 straightener shared a single `k_bond`, and both
are tanh kernels saturating at the same amplitude. Once the straightener saturates the two forces
cancel EXACTLY, so the molecule can stretch with no restoring force, which is why the rigid-chain
displacement was so large (3.3e-02 per step). Cooke-Deserno never hits this: bond stiffness 30
against bend stiffness 10, and its FENE bond DIVERGES so a bond physically cannot overstretch.
Vivarium is not allowed to diverge, so the equivalent is to make the straightener strictly weaker
than the backbone. Added per-bond stiffness (`bend_frac`); base case still byte-identical.

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
