# Vivarium research log

Append-only. Newest entry at the TOP. Every entry states what was run, what came back, and what it
changed. Claims that were later retracted stay in the log with the retraction attached, because the
retractions are the most useful part of this file.

`docs/BILAYER_REVIEW.md` holds the narrative findings (1-24). This file is the audit trail: what was
executed, in what order, and which conclusions are currently live.

## Where this stands right now (2026-08-01, end of session)

**THE CENTRAL FINDING: we built a DETERGENT, not a lipid.**

In nature a phospholipid bilayer does not spontaneously break into micelles -- it is one of the most
stable structures in biology. A membrane dissolving into micelles happens when you add DETERGENT
(Triton X-100, SDS, octyl glucoside); that is the standard laboratory method for solubilising
membranes, and the product is mixed micelles. Fragmenting into micelles is what a detergent does and
what a lipid does not.

Every observation here is consistent with that, and each had previously been read as a failure:

    observation                        read as failure        read as DETERGENT
    self-assembly gives micelles       wrong phase            CORRECT for P < 1/3
    planted bilayer fragments          unstable, needs tuning CORRECT -- detergents solubilise
    preferred aggregation number ~12   odd plateau            CORRECT -- micelles have a set size
    finite ribbons, never spanning     nearly there           CORRECT -- mixed-micelle regime

So the melting is not a kinetic problem, a parameter problem or an annealing problem: it is the
thermodynamically correct behaviour of the molecule that was built. No amount of longer runs or
better annealing changes it, which is exactly why every kinetic intervention tried this session
plateaued. The fix is MOLECULAR GEOMETRY -- raising the packing parameter P = v/(a0*l) out of the
detergent range (< 1/3) into the bilayer range (1/2 to 1).

**Achieved and verified:**

  STAGE 1, MICELLES. Self-assembled from a FULLY DISPERSED random start -- no concentration and no
  order supplied -- and verified against a purpose-built solvated reference:

      structure                packing   solvation   align    bond
      planted micelle (ref)      0.436        1.24   0.175   1.013
      SELF-ASSEMBLED             0.441        1.42   0.078   1.015
      genuine collapse           0.150          --   0.630      --

  Indistinguishable from the reference, with better solvation. Molecules intact, transformer-only
  constraint held.

  STAGE 2, BILAYER RIBBONS (finite). The dispersed run equilibrates into five aggregates of ~12-20
  lipids holding align ~0.73, unchanged from t=20k to t=150k. Rendered at true bead radius, several
  are ELONGATED with a head-tail-tail-head cross-section: finite bilayer patches coexisting with
  round micelles. packing 0.502 sits between the micelle reference (0.436) and the bilayer reference
  (0.713), as a mixture should.

**Not achieved:** a SPANNING bilayer. The patches stay finite, and a planted spanning bilayer
dissolves. No vesicle.

**The levers, tested:**

    head_sigma (steric a0)   NO EFFECT, and it drives collapse at 0.5. a0 here is set
                             ELECTROSTATICALLY, not sterically, so this shrank the wrong term.
    n_tail=4 branched        OVERSHOOTS. Four tail beads per head puts P > 1, past the bilayer
                             window into INVERTED curvature; still micellar from a dispersed start
                             despite retaining more order on the PLANTED screen.
    force magnitude          NO EFFECT. Scaling every force with the timestep is a rescaling of
                             TIME; only force-relative-to-kT moves, and lowering effective
                             temperature freezes a glass rather than ordering it.
    head_q (electrostatic)   UNDER TEST. This is the term that actually sets effective a0.

**Reading protocol, non-negotiable.** A structural claim needs an image AND validated metrics AND the
reference on the same axes. The ribbon result is why: align 0.73 fits a ribbon AND a dense pile, and
packing 0.452 sits a hair above the micelle floor of 0.436, so the numbers alone are ambiguous in
both directions. The layering in the image is not. Render at TRUE bead radius (sigma) -- a fixed
pixel radius makes an interpenetrating pile look cleanly resolved, which is how a collapse passed for
a structure.

**Sampling:** read runs at t >= 20000. Aggregate count first RISES as spurious contacts from random
placement break apart and real micelles form, then FALLS as they fuse. Every run in this project
before 2026-08-01 stopped at t=6000, inside the fragmentation phase, before any of the ordering is
visible.

**Instruments added this session:** `packing` (lipid-to-lipid excluded volume), `solvation` (the
solvent half, split out), and `references.py` (solvated planted structures). Seventeen measurement
defects found. 104 tests pass.

## Status board

| rung | target | status |
|---|---|---|
| 0 | two lipids prefer tail-to-tail | PASSES, at 2-bead tails once head_q < 0.8 (F22) |
| 1 | micelle (radial head-out order) | **ACHIEVED AND VERIFIED** (2026-08-01m/n). Self-assembles from a FULLY DISPERSED start; matches a purpose-built solvated reference on packing, bond and align. |
| 2 | bicelle / finite bilayer patch | **PARTIAL, EMERGENT** (2026-08-01p). Finite ribbons with head-tail-tail-head layering appear from disorder and persist 130k steps at align ~0.73, coexisting with micelles. Note this is a SINGLE-species ribbon; the earlier "a true bicelle is two-component" finding concerns the rim-stabilised disc, which is a different object. |
| 3 | spanning bilayer | **NOT ACHIEVED.** Exists only when planted, and a planted one dissolves into micelles -- the detergent signature. Blocked on molecular geometry (P), not on kinetics. |
| 4 | vesicle | NOT STARTED. Requires a stable bilayer first. |

## Live methodological rules

-6. A BICELLE CANNOT BE VERIFIED WITHOUT EXPLICIT SOLVENT. `edge` is defined by tail-water contact, so
   with no water it returns NaN and the rim -- the feature that makes a disc finite -- is unmeasurable.
   Any solvent-free run is incapable of demonstrating a bicelle whatever else it computes.
   `edge` is also SOLVENT-DENSITY dependent, so it must be read RELATIVE to a control, never against
   an absolute threshold: the same planted bicelle reads 0.03 in dilute solvent and higher in dense.
   What is invariant is the ordering, finite disc > spanning sheet.

-5. `lamellar` ANTI-DISCRIMINATES and must never be read alone. It asks whether a head sits farther
   out than its own tails, which is true of ANY heads-out structure, and it scores a MICELLE (0.967)
   ABOVE a BILAYER (0.889). Use `align`, the nematic order of the lipid axes: bilayer 1.00, micelle
   0.09, vesicle 0.03, random 0.08. Together they CLASSIFY:
       lamellar high + align LOW  -> micelle (radial order)
       lamellar high + align HIGH -> bilayer (lamellar order)
       lamellar low               -> disordered
   Every "lamellar 0.8-0.97, partial order" claim in this project's history is consistent with a
   micelle, i.e. was evidence AGAINST a membrane.

-3. "PLANT IT AND CHECK IT READS SUCCESS" IS NOT ENOUGH. A metric that returns success for everything
   passes that test, and `lamellar` really does read 1.000 on a collapsed droplet. Plant EVERY
   candidate and require DISCRIMINATION: bilayer vs micelle is separated only by `aspect`, and micelle
   vs vesicle only by `hollow`, since both are round with heads out. A search ranking on `aspect`
   alone would discard a vesicle as a droplet -- the very structure being hunted.
   Also: a test that has never failed is not evidence. Verify each one catches the bug it was written
   for by reintroducing that bug.

-4. A REFERENCE STRUCTURE MUST FIT ITS BOX, AND THE BOX HAS TWO SEPARATE REQUIREMENTS.
   * Spanning bilayer: half-width must EXCEED the membrane thickness, or minimum image folds the two
     leaflets together and a flat bilayer measures as round (measured: aspect 0.98).
   * Finite structure: unwrapping from a single reference bead needs DIAMETER < L/2, or the far side
     wraps onto the near side (measured: a hollow vesicle read as filled, hollow 2.6).
   Lateral spacing is a third, independent constraint: too large a box and the lipids never touch at
   all ("no aggregate").

-2. A MIXING RULE CANNOT EXPRESS HYDROPHOBICITY. Geometric (Lorentz-Berthelot) mixing pins the cross
   term at eps_ij = sqrt(eps_i * eps_j), and the contrast (eps_ii + eps_jj)/2 - eps_ij is >= 0 by
   AM-GM, LARGEST when one species is weak. So the only demixing available is "oil is sticky": tails
   clump while water, having little self-attraction, freely permeates them. The real hydrophobic
   effect is the opposite -- water coheres and SQUEEZES tails out -- and needs eps_tw BELOW the
   geometric mean, which the rule forbids. Every CG lipid force field uses a species-pair MATRIX for
   this reason. This is why `edge` sat at 1.00 through every sweep.

-1. TARGET THE RIGHT STRUCTURE. A LINEAR head-tail-tail chain is a single-tailed SURFACTANT, and
   single-tailed surfactants form MICELLES in nature. Months of "why won't it form a bilayer" was
   asking the wrong molecule to do something real chemistry says it cannot. Real phospholipids are
   DOUBLE-TAILED (`branched=True`). Separately, a flat spanning bilayer is an MD idealisation; what a
   finite amount of lipid forms in water is a VESICLE, which unlike a bicelle has no rim to pay for.

0. CHECK THE MOLECULE FIRST. Every order parameter is computed from head/tail POSITIONS, so if the
   lipid itself is deformed the metric describes nothing. `bond_span=6.0` stretched bonds to 2.4x
   their rest length and was used in EVERY 4-bead-tail run, so those geometries were wrong. Print
   bond length and 1-3 span alongside any structural claim. span=2.0 keeps them intact
   (bond 1.01 +/- 0.01, r13 2.00).

1. A metric is wrong until BOTH controls agree: a planted structure scores high AND a random
   configuration scores at the null. A positive control alone cannot catch a self-correlated
   statistic (F21). Three metrics have failed this in three separate places.
2. No structural claim from a single frame. It must hold across a trajectory (F24 correction).
3. At kT=0 a planted structure must not GAIN kinetic energy. If |v| grows, the integrator is broken
   and no conclusion about stability is admissible (2026-07-28c).
4. Sweep the parameter that drives the MECHANISM, not the nearest available knob (F22: range and
   head dispersion were both wrong knobs; head electrostatics was the lever).

---

## 2026-08-01t — 3-D has no per-species steric radius. Every 3-D result measures a different molecule

Found while reading the force path for a performance refactor, then verified directly.

    aniso=0.95   head_sigma 0.5 vs 1.0  ->  contact matrices IDENTICAL   (sigma itself differs)

`_contact_distance` computes `base` from per-species sigma and then DISCARDS it whenever aniso > 0:

    base = (self.repel_contact if self.sigma is None
            else self.sigma[:, None] + self.sigma[None, :])
    if self.aniso <= 0.0:
        return base                       # 2-D path (bicelle2d, aniso=0): sigma IS used
    half = 0.5 * self.repel_contact       # 3-D path (bilayer3d, aniso=0.95): sigma DISCARDED
    return half * (1.0 + self.aniso * nf) + half * (1.0 + self.aniso * nf.T)

So in every 3-D run, water, heads and tails have had the SAME steric radius. The packing parameter
P = v/(a0*l) is a head-area to tail-volume ratio, so the 3-D model has been missing the single
property its phase behaviour depends on.

**Consequences, which reach back over the whole 3-D line:**

  - The 2-D vs 3-D comparison is INVALID as run. It was never one variable (dimensionality); the
    molecules differed too. The 2026-08-01s conclusion that "2-D may not transfer" is not supported
    by the runs that were used to reach it.
  - A `head_sigma` sweep in 3-D would be a no-op, and would have read as "head size does not matter"
    -- the same null the 2-D sweep produced for a different reason.
  - The melting 3-D planted bilayer was measured on a molecule with no head/tail asymmetry, so it
    says nothing about whether a proper lipid holds a bilayer in 3-D.

`base` being computed and never used is the tell: this reads as a bug rather than a decision to let
the anisotropic contour supersede sigma. Not yet fixed -- fixing it changes 3-D physics, so it wants
its own change with the base case re-verified.

**Cost wall, quantified.** Solvent fills the box so N ~ L^3, and forces are O(N^2), giving cost ~ L^6:

    bound=4.5   N= 626    0.09 s/step     20k steps =   0.5 h
    bound=7.0   N=2358    1.26 s/step     20k steps =   7.0 h
    bound=8.0   N=3520    2.81 s/step     20k steps =  15.6 h
    bound=11.0  N=9151   19.02 s/step     20k steps = 105.7 h   <- the 2-D box that works

This is why 3-D is barely explored: not a choice, a cost wall. The contact term is short-ranged --
`overlap` is exactly zero beyond repel_contact*(1+aniso) ~ 1.95, and only ~2% of pairs are within it
at liquid density -- yet an (N,N,tK) basis is built for every pair. Exploiting that is EXACT and takes
the scaling from L^6 to ~L^3.

**Performance, done:** the spherical-harmonic pair basis was being built TWICE per step from
identical inputs (via _contact_distance and again in _extra_force) at ~25% of step time. Now shared
through a slot that step() clears on both ends, so nothing survives a step and callers outside step()
always recompute. Verified BYTE-IDENTICAL over 200 steps (max |diff| = 0.000e+00) for 1.08x -- real,
but smaller than the 1.15x predicted, and reported as measured.

Adds `docs/SCORECARD.md`: binary PASS/FAIL criteria per stage against the calibrated metric bands.
Current state is 2 of 4 stages in 2-D, 0 of 4 in 3-D.

## 2026-08-01s — first 3-D check: PRELIMINARY and NOT controlled. Read the caveats before the numbers

Ran the 3-D transfer question early because it is the one whose answer could invalidate the most.

**First attempt was INVALID and is retracted.** speed=0.02 at k_bond=30 gives displacement/step of
0.02*30/0.7 = 0.86, seventeen times the DISP_MAX of 0.05 -- a stability limit derived earlier in this
same session and then violated by carrying a timestep over from a different configuration without
re-checking the product. Every bond read 1.70 against a rest length of 1.0. The probe now ASSERTS the
stability product at build time so this cannot recur silently.

Rerun at speed=0.001 (bonds 1.028-1.037, ok=True):

    structure                            splay   align
    planted 3-D bilayer (t=0)            0.000   1.000
    planted 3-D bilayer (relaxed 2k)     0.727   0.188
    3-D self-assembly t=5000             0.914   0.143
    3-D self-assembly t=20000            0.722   0.183
    2-D self-assembly, for contrast      0.253   0.813

**What is trustworthy here:** the planted 3-D bilayer decays against ITSELF, splay 0.000 -> 0.727 and
align 1.000 -> 0.188. That comparison needs no external calibration, and it says the lamellar phase
is not stable in 3-D at these parameters.

**What is NOT trustworthy, and must be fixed before anything else is concluded:**

  1. THE COMPARISON IS UNCONTROLLED. The 3-D run differs from the 2-D one in concentration, in
     satt/spol, and in water fraction. Several variables changed at once -- the exact error this log
     documents repeatedly.
  2. `splay` IS NOT CALIBRATED IN 3-D. Its expected value 2*pi/n is a CIRCLE result; a 3-D micelle
     fans over a SPHERE, so the micelle band is unknown. Reading 0.72 as "micelle" is reasoning by
     analogy from an unvalidated reference, which is the mistake made four times today.
  3. THE 3-D PLANTED BILAYER IS NOT AT CONTACT. It measures packing 1.360, i.e. its lipids sit BEYOND
     contact spacing, so it is not a properly built reference either.

So the 2-D result is not yet shown to fail in 3-D; it is shown to be unmeasured in 3-D.

**Terminology, because it caused a real confusion.** "2-D bilayer" in the membrane literature means a
lipid bilayer whose SHAPE is a flat sheet -- a 2-D surface embedded in 3-D space, e.g. a supported
lipid bilayer on mica. The molecules, the water and the tails are all fully 3-D. THIS PROJECT's 2-D
runs are different: pos_dim=2, so the entire universe is a plane and a "bilayer" is a double ROW, a
1-D line of material in a 2-D world. Supported lipid bilayers do not validate 2-spatial-dimension
simulation; they are 3-D physics, and are what a 3-D run is supposed to PRODUCE.

**Physical reasons to expect 2-D not to transfer** (reasoning, not literature -- the session's web
search budget was exhausted, so this is unverified):

  EDGE DIMENSIONALITY. A finite 3-D patch has a 1-D rim costing 2*pi*R*gamma, growing with size. The
  same patch in 2-D has TWO ENDPOINTS, a 0-D edge whose cost is CONSTANT however long the ribbon. The
  competition between finite patches and closed vesicles is therefore not the same problem, and
  R_crit = (4*kappa_c + 2*kappa_bar)/gamma is a 3-D result with no direct 2-D analogue.

  PACKING THRESHOLDS ARE 3-D. P < 1/3 micelle, 1/2..1 bilayer come from sphere/cylinder/plane
  geometry. A 2-D "micelle" is a disc and a 2-D "bilayer" a double row; the numbers do not carry over,
  and they were applied to 2-D runs repeatedly today without that being flagged.

  MERMIN-WAGNER. Long-range order for continuous symmetries is destroyed by fluctuations in 2-D, so a
  2-D system is more fluctuation-dominated and an extended ordered phase may not be stable at all.

Independent corroboration of the EDGE argument (via the user, from Gemini, on supported bilayers):
free-standing lipid patches have high edge energy from exposed tails at the borders, and free
membranes prefer to close into vesicles to hide them; flat bilayers in the laboratory require a solid
substrate plus a thin water cushion. That supports the rim/closure reasoning and adds a design option
this project has not used -- a SUBSTRATE (the codebase already has `wall_axes`) is the physical way to
stabilise a flat bilayer, alongside the periodic box.

**Next, in this order:** build 3-D references properly (solvated, lipid count derived from the box,
relaxed before reading), calibrate `splay` and `packing` against them, and only then run a CONTROLLED
2-D vs 3-D comparison with one variable changed. Start from what already works in 2-D -- the micelle.

## 2026-08-01r — `splay`: the bilayer ribbons are REAL, measured rather than eyeballed

Every stage-2 claim so far rested on my reading of a render, which is the weakest evidence in a
project that has found seventeen measurement defects. So the discriminator got built.

`splay` is the median angle between a lipid's axis and its SAME-LEAFLET neighbours' axes. Curvature
is the actual difference between a bilayer and a micelle, and this measures it LOCALLY: same-leaflet
neighbours are parallel in a bilayer (-> 0) and fan by ~2*pi/n in a micelle of n lipids. Same-leaflet
is defined by u_i . u_j > 0, since opposing leaflets are antiparallel and including them would report
~pi for a perfect bilayer -- the structure's own signature mistaken for disorder.

Calibrated against both references, and it matches the geometric prediction:

    structure                    splay   predicted 2*pi/n   align
    planted bilayer (t=0)        0.000               0.00   1.000
    planted bilayer (relaxed)    0.207               0.00   0.883
    planted micelle n=12         0.571               0.52   0.000
    micelle n=12 relaxed         0.631               0.52   0.056
    planted micelle n=20         0.471               0.31   0.000

Bilayers 0.00-0.21, micelles 0.47-0.63, with an empty gap. Then the runs:

    run                                  splay   align   packing   call
    four-micelle figure (clump, t=6k)    0.527   0.078     0.441   micelle
    dispersed, t=20k                     0.253   0.813     0.502   BILAYER

**The ribbons are real.** splay 0.253 sits beside the relaxed planted bilayer at 0.207 and nowhere
near the micelle band. The visual reading was right, and it is now independent of the visual reading.
The four-micelle figure reads 0.527, confirming micelles a third time and by a third method.

`align` alone could not have done this: it reads 0.813 for the ribbons and 0.078 for the micelles,
but 0.5-0.8 is exactly where a dense pile also lands. `splay` is local, scale-free, and its expected
value is derivable from geometry rather than fitted.

**Concentration sweep** (fixed box, dispersed, t=20k) -- `spanning` is the fraction of the periodic
axis the largest aggregate covers, binned on wrapped coordinates rather than taken as an extent,
because an aggregate that WRAPS reports a span larger than the box:

    phi_lipid   n_lip   spanning   cluster   align   packing
         0.43      63       0.27      0.29   0.813     0.502
         0.65     110       0.82      0.50   0.113     0.503
         0.83     160       0.50      0.36   0.114     0.365

Spanning peaks at phi ~0.65 and DEGRADES beyond it, with packing falling to 0.365 near the floor. The
two levers currently pull apart: low concentration gives bilayer order in finite patches (align 0.81,
splay 0.25), high concentration gives spanning without order (span 0.82, align 0.11). The target is
the overlap, and finding it is the next experiment.

Box size is a weaker version of the same lever: shrinking the half-width 8 -> 5 raised spanning
0.38 -> 0.60 and produced the only admissible row, but it bottoms out because the membrane is ~5
thick and a box under ~10 wide lets the bilayer feel its own periodic image.

## 2026-08-01q — the diagnosis: we built a DETERGENT, not a lipid

Prompted by the right question: in nature, do bilayers melt into multiple micelles?

They do not. A phospholipid bilayer is among the most stable structures in biology. A membrane
dissolving into micelles is what happens when DETERGENT is added -- Triton X-100, SDS, octyl
glucoside -- and it is the standard laboratory method for solubilising membranes, yielding mixed
micelles. Fragmenting into micelles is what a detergent does and what a lipid does not.

(Keep the vocabulary straight: "melting" in membrane biophysics means the gel to liquid-crystalline
CHAIN transition at Tm, where tails disorder and the bilayer REMAINS a bilayer. Our runs do not do
that. They fragment into five separate aggregates, which is dissolution.)

**So the planted bilayer's failure identifies the MOLECULE, not the parameters.** Every observation
lines up, and each had been read as a failure to be tuned away:

    observation                        read as failure          read as DETERGENT
    self-assembly gives micelles       wrong phase              CORRECT for P < 1/3
    planted bilayer fragments          unstable, needs tuning   CORRECT -- detergents solubilise
    preferred aggregation number ~12   odd plateau              CORRECT -- micelles have a set size
    finite ribbons, never spanning     nearly there             CORRECT -- mixed-micelle regime

This retroactively explains why EVERY kinetic intervention plateaued: annealing, longer runs, force
scaling, bond stiffness, temperature. A thermodynamic constraint viewed from inside a parameter
search looks exactly like a series of plateaus, and I read each plateau as a reason to try the next
parameter instead of as evidence about the molecule.

The consequence is that the search space was wrong, not merely badly sampled. The fix is molecular
geometry: raise P = v/(a0*l) from the detergent range (< 1/3) into the bilayer range (1/2 to 1).

Head-charge sweep, dispersed start, t=20000 (a0 is set electrostatically here, so this is the term
that matters -- steric head_sigma had no effect):

    head_q   polarity   aggregates   largest   align   packing
       1.2       0.80            5        18   0.813     0.502
       0.6       0.80            6        20   0.579     0.552

Lowering the charge alone does NOT consolidate the aggregates -- still fragmented, and align falls.
So effective a0 is not reducible by charge alone at this tail volume, and P has to be raised from the
v side and the a0 side together: a TWO-bead double tail (n_tail=2 branched, not the n_tail=4 that
overshot into P > 1) at reduced head charge is the untested combination.

## 2026-08-01p — BILAYER RIBBONS EMERGE. Stage 2, finite rather than spanning

The single-tailed dispersed run equilibrates into a real phase, and the image says what it is.

    step    aggregates  largest  mean size   align   packing
      6000           8       15        7.4   0.530     0.673
     20000           5       18       12.2   0.813     0.502
     60000           5       20       12.6   0.721     0.457
    150000           5       20       12.6   0.734     0.452

Steady from t=20k to t=150k: five aggregates of ~12-20 lipids holding nematic order ~0.73 over 130k
steps. That is a phase, not a transient.

**Rendered, several aggregates are ELONGATED with a head-tail-tail-head cross-section** -- blue heads
along both edges, orange tails through the middle. Those are bilayer ribbons: finite bilayer patches,
i.e. bicelles, coexisting with round micelles. `packing` 0.502 sits between the micelle reference
(0.436) and the bilayer reference (0.713), exactly as a mixture should.

This is the first membrane-like structure this project has produced from disorder. It is stage 2 and
NOT stage 3: the patches are finite, and no spanning bilayer has formed.

Why the metric alone could never have said so. align 0.73 is consistent with BOTH a ribbon and a
dense pile, and packing 0.452 sits a hair above the micelle floor of 0.436. The two numbers together
are ambiguous; the layering in the image is not. This is the case the standing protocol was written
for -- image AND validated metrics AND reference on the same axes -- and here the image carried it.

**Two corrections from this round:**

The double tail OVERSHOT. n_tail=4 branched gives four tail beads per head, so tails are far wider
than the head: P > 1, past the bilayer window into INVERTED curvature. It plateaued at align 0.24 and
stayed micellar from a dispersed start, despite retaining more order on the PLANTED screen (51% vs
28%). Doubling v was right; quadrupling it is not.

And a0 is not steric. A single-tailed lipid here is geometrically a cylinder yet micellizes, because
head_q=1.2 at polarity=0.80 inflates the EFFECTIVE head area electrostatically. That is why shrinking
head_sigma did nothing -- it shrank the wrong term -- and it makes the head charge, not the head
size, the lever for pushing these ribbons toward a spanning bilayer.

## 2026-08-01o — the double tail stabilises the bilayer, and micelles DO coarsen into lamellar order

Two results, both pointing the same way.

**Stability screen, planted spanning bilayer, order retained:**

    lipid            t=500   t=2000   t=6000
    single tail        88%      68%      28%
    DOUBLE tail        93%      76%      51%

Nearly double the retention at comparable packing (0.401 vs 0.484). Adding a second tail doubles v at
fixed a0 and l, moving P = v/(a0*l) from the micelle range (<1/3) into the bilayer range (1/2..1),
and the lamellar phase measurably stabilises. Nature's architecture, reproduced.

Shrinking the head instead does NOT work, and the earlier "smaller heads do not help" is confirmed
with working instruments: head_sigma 1.0 melts cleanly (28% retained, packing 0.484) while 0.7 and
0.5 COLLAPSE (packing 0.347 and 0.289, below the 0.35 floor) with `align` rising as they do -- the
anticorrelation signature. a0 is not the lever; the second tail is.

**Coarsening, from a FULLY DISPERSED start:**

    step    aggregates  largest  mean size   align   packing
       0             5       31       10.6   0.267     0.626
    2000             4       30       14.5   0.331     0.825
    6000             8       15        7.4   0.530     0.673
   20000             5       18       12.2   0.813     0.502

Two phases, and the first one masks the second. Aggregates first go UP (5 -> 8) as spurious contacts
from random placement break apart and real micelles form at a preferred aggregation number ~7. Then
they FUSE: 8 -> 5, mean size 7.4 -> 12.2, largest 15 -> 18. And `align` climbs to 0.813 at admissible
packing, where micelles score 0.09-0.18.

That is the classic surfactant progression -- sphere -> rod -> lamellar -- appearing on its own from
disorder. The micelle phase is not a dead end, and reading the run at t=6000 (as every previous run
did) samples it during the fragmentation phase, before any of this is visible.

## 2026-08-01n — MICELLES EMERGE, including from a fully dispersed start

    start                  packing   align   largest cluster   verdict
    clump (as published)     0.441   0.078              98%    OK
    DISPERSED (random)       0.673   0.530              24%    "fragmented"

`plant="clump"` was never a planted micelle: the code places lipids at RANDOM positions inside a disc
with RANDOM orientations, supplying concentration and nothing else. So the tails-in/heads-out
organisation and the split into discrete aggregates were already emergent in the published figure.

From a fully DISPERSED start -- neither concentration nor order given -- roughly eight micelles form
anyway, and pack BETTER (0.673 vs 0.441, since smaller aggregates compress less). Self-assembly is
complete, not partial.

**The "fragmented" verdict is a metric artifact and a real bug for this phase.** MIN_CLUSTER_FRAC
demands that one aggregate hold 60% of the lipids, which is correct for a bilayer or a vesicle and
WRONG for a micelle phase, where many small aggregates is the right answer. The guard is
bilayer-shaped, in exactly the way MIN_PACKING was bilayer-shaped. Same lesson twice in one day: a
threshold calibrated on one phase silently condemns the others.

**Stage 1 of the vesicle pathway is done and verified.** Hydrophobic collapse produces micelles from
disorder, against a reference, with intact molecules.

## 2026-08-01m — THE MICELLES WERE REAL. The gate was calibrated on the wrong structure

Built the solvated references that never existed, and they settle the question against me.

    structure                          packing   solv   align    bond
    spanning bilayer, planted at contact 1.000   0.64   1.000   1.000
    spanning bilayer, relaxed            0.713   0.92   0.678   1.009
    MICELLE, planted                     0.683   0.56   0.000   1.000
    MICELLE, relaxed                     0.436   1.24   0.175   1.013
    THE FOUR-MICELLE FIGURE              0.441   1.42   0.078   1.015
    genuine collapse                     0.150     --   0.630      --

**The figure is indistinguishable from a purpose-built planted micelle** on packing (0.441 vs 0.436),
bond (1.015 vs 1.013) and align (both near zero, i.e. radial rather than lamellar), and its solvation
is BETTER (1.42 vs 1.24: solvent further out of the core). Those aggregates are micelles. Both of my
verdicts on them -- first "collapsed", then "undetermined" -- were wrong.

**Why the instrument was wrong, and it is a general lesson.** A micelle CANNOT reach a bilayer's
packing by geometry: its lipids converge radially, so the inner tail beads sit closer than contact by
construction. That is the packing parameter appearing as a floor on the metric. MIN_PACKING = 0.70
was fitted to the bilayer alone, so it rejected the other structure by definition -- a threshold
calibrated on ONE shape silently condemns every shape that packs differently. Gate is now 0.35,
derived to sit below the tightest legitimate structure (micelle 0.436) and well above true collapse
(0.150).

Two tooling fixes underneath this:

  `packing` is now LIPID-TO-LIPID. Counting solvent as a neighbour measured solvation, not
  structure, and in a solvated box the nearest bead to a lipid is nearly always water -- a bilayer
  planted at exact contact read 0.637 instead of 1.000.

  `solvation` split out as its own diagnostic, since "does the membrane interpenetrate itself" and
  "is solvent jammed into it" are different questions that one number conflated. It RISES as
  planted solvent relaxes out (0.64 -> 0.92 for the bilayer), which is also the check that a
  reference has been relaxed before it is read.

New module `references.py` holds the solvated builders and enforces the two rules this project keeps
relearning: the LIPID COUNT FOLLOWS THE BOX (a spanning bilayer needs box_width/contact per leaflet;
63 across a width of 22 is 0.71 spacing, over-crowded by construction), and a reference must be
RELAXED before it is read.

104 tests pass. **Stage 1 -- hydrophobic collapse into micelles -- is achieved and now verified
against a reference.**

## 2026-08-01l — defect #17: `packing` is confounded by explicit water, so the collapse verdicts are not reliable

Prompted by re-examining the four-micelle figure (fig2d, attract=1.0, t=6000), which I had dismissed
as a collapse. That dismissal was wrong twice over.

**First error: wrong parameters.** I demonstrated collapse at attract=2.0 / repel=12 (ratio 6) and
generalised it to a figure made at attract=1.0 (ratio 12). The collapse threshold sits BETWEEN those,
so the demonstration says nothing about the figure.

**Second error: miscalibrated instrument.** A 2-D bilayer planted at exact contact spacing, with the
lipid count derived from the box (22 columns per leaflet at contact = 44 lipids, not the 63 I first
planted across the same width at 0.71 spacing):

    step   packing   align
       0     0.637   1.000    <- PERFECT planted bilayer reads 0.637, not 1.0
     500     0.690   0.883    <- after the randomly-placed water relaxes
    2000     0.672   0.678
    6000     0.482   0.275    <- melted

`packing` takes each lipid's distance to the nearest bead of ANY species. With 250 randomly-placed
waters the nearest bead is usually WATER, so the metric reports solvent proximity rather than lipid
spacing. The 3-D planted bilayer scored a clean 1.000 only because that reference has no solvent.

So MIN_PACKING = 0.70 is too strict for solvated 2-D -- a healthy solvated bilayer sits at ~0.69 and
fails its own gate. Every "collapsed" verdict on a solvated 2-D run is therefore unreliable as
stated, including the repel sweep used to void the earlier micelle results. The figure's 0.441 is
still below the MELTED bilayer's 0.482, so it is not vindicated either; it is undetermined.

**One result survives, because `align` is not affected by the water confound:** a planted bilayer
MELTS at the figure's parameters, align 1.00 -> 0.275 over 6000 steps. Those parameters do not
support a stable lamellar phase. That is the stability screen doing its job.

**The recurring failure, now four instances deep:** treating a freshly built reference as ground
truth without checking it fits its own box -- bilayer, micelle, vesicle, and now my own control. It
is rule one of MEASUREMENT_DISCIPLINE.md, violated repeatedly since writing it. What is missing for
the micelle question specifically is a SOLVATED planted micelle reference; none exists, so the
figure cannot be judged at all right now.

## 2026-08-01k — RETRACTION of 01j's mechanism: uniform force scaling is a time rescaling

01j read the scale 1 -> 4 gain (align 0.082 -> 0.225) as evidence that absolute force scale buys
order. Scaling further with k_bond scaled to match kills that reading:

    scale  repel  attr  k_bond   pack   bad   align
        4    192     8     240   0.78  0.00   0.111
       16    768    32     960   0.76  0.00   0.116

Fixing the bond ceiling worked -- scale 16 is fully valid now, zero bad bonds. But a further 4x in
every force moves align by 0.005. Order PLATEAUS.

Dimensionally it had to. Scaling every force by s while scaling the timestep by 1/s is a rescaling of
TIME; the trajectory is unchanged. The only quantity that genuinely moves is force relative to kT,
i.e. effective temperature, and lowering it does not order the system -- it freezes it into a
disordered glass.

So the 01j gain was NOT from absolute scale. It was from k_bond staying at 60 while the other forces
went to 192, i.e. a SOFT bond relative to its surroundings. Stiffening it to 240 at the same scale
halved the order, 0.225 -> 0.111. Flexibility is what lets lipids rearrange into a lamellar packing;
force magnitude is not.

    scale 4, k_bond  60   align 0.225   bad 0.01   <- best valid config so far
    scale 4, k_bond 240   align 0.111   bad 0.00

That reframes the problem as KINETIC rather than energetic. The forces are strong enough; the system
cannot explore its way to the ordered state. Which makes temperature and bond flexibility the knobs
worth sweeping, not force magnitude.

## 2026-08-01j — order CAN be bought without collapse: scale both forces at fixed ratio

The first increase in order in this project that is not an artifact of collapse.

Collapse is set by the attract/repel RATIO; ordering is set by cohesion against kT. Those are
different knobs, so both forces were scaled together at the ratio that holds (1/24) with kT fixed,
and the timestep scaled as 1/force to keep the stability product speed*force constant.

    scale  repel  attr  k_bond   pack   bad   align   verdict
        1     48     2      60   0.80  0.00   0.082   OK
        4    192     8      60   0.80  0.01   0.225   OK
       16    768    32      60   0.82  0.30   0.063   molecule deformed

Packing stays pinned at 0.80 while `align` rises 2.7x. Every earlier rise in `align` came with
collapse -- this one does not, so it is measuring lipid organisation rather than pile density.

Two things this settles. Bounded kernels are NOT immediately fatal: the crowding hypothesis was
wrong (the collapse threshold is identical at phi 0.71 and phi 0.34, so it is the force ratio and not
density), but the ratio is not a dead end either, because absolute scale is a free parameter once the
ratio is held.

scale 16 fails on BONDS, not collapse -- packing is a healthy 0.82 while 30% of bonds deform. repel
and attract went to 768/32 and k_bond was left at 60, so the saturating bond lost to external force.
That is the same ceiling mechanism as 2026-08-01f, and it says k_bond is not an independent knob: it
has to scale with whatever load the other forces impose.

Still far from a membrane. align 0.225 against 1.00 for a planted bilayer.

## 2026-08-01i — the micelles were collapses. Every structural result in the 2-D line is void

Re-ran the repel sweep under the packing guard, because every earlier row was scored by a harness
that could not see collapse.

    repel   packing   bond    bad   align   cluster   verdict
        3      0.09  0.980   0.00   0.691      0.70   collapsed
        6      0.12  1.008   0.00   0.458      1.00   collapsed
       12      0.15  1.028   0.00   0.635      1.00   collapsed
       24      0.45  1.012   0.00   0.045      0.98   collapsed
       48      0.82  1.019   0.00   0.108      0.98   OK

**repel 12 is the setting every earlier 2-D run used, and it sits at 0.15 of contact -- sevenfold
interpenetration.** The micelles seen in screenshots, orange tail core with blue heads, were collapsed
piles. A collapse and a micelle are indistinguishable from OUTSIDE; the difference is interior
density, which nothing measured. Rendering at TRUE bead radius (sigma) rather than a cosmetic marker
size makes it obvious at a glance: 189 beads of diameter 1.0 inside a span of 3.9, fused into a solid
disc.

**Note the anticorrelation.** Every high-`align` row is collapsed and the one admissible row has
almost no order. `align` was tracking COLLAPSE, not lipid organisation -- denser piles score higher.
So the apparent progress across this whole line of work was an artifact, and the ranking it induced
actively drove the search toward collapse.

What survives at repel 48, the first sterically valid aggregate here: tails segregate from solvent
and heads sit at the interface, so hydrophobic aggregation is REAL. But span 23.3 exceeds the box
width of 22 with cluster_frac 0.98, i.e. an amorphous PERCOLATING network rather than a finite
aggregate. No micelle, no bilayer, no vesicle.

Two things follow for the parameters. Excluded volume has to be far stronger than anything used so
far -- repel 48, not 12. And attraction was tuned against collapsed runs, so `attract` 2.0 against
repel 48 is a different balance entirely and has to be re-tuned from scratch, now against a guard
that cannot be gamed by piling up.

## 2026-08-01h — the packing guard immediately condemned the reference structures it was added to check

`packing` was added to catch a collapsed RUN. Turned on the planted references, it rejected most of
them, and every rejection was a real defect that had been calibrating the metrics all along.

    reference               before   cause
    micelle                   0.32   all 60 tail ENDS on one shell of radius 0.6
    solvated filled sphere    0.04   same, at radius 0.5
    vesicle                   0.63   leaflets split in HALF, so the inner shell is crammed
    3-D planted bilayer       1.000   already correct -- lipids sit exactly at contact

Four distinct root causes, three of them geometric and one statistical:

**1. Shells cannot hold a filled core.** A shell of n points at radius r spaces them ~2r*sqrt(pi/n)
apart, so the INNERMOST shell caps the aggregation number. Enlarging it until it is legal empties the
core and turns a micelle into a small vesicle -- `hollow` then read 0.00 for both.

**2. This lipid cannot form a micelle at all.** Packing parameter P = v/(a0*l) = 1.05/(1.0*2.0) =
0.52, which is the BILAYER range; micelles need P < 1/3. The planted micelle was never a structure
this molecule could make. The reference is now an honest uniformly-filled droplet, which is all the
`hollow` / `enclosed` contrast ever needed, and a real micelle reference would require a different
molecule (one tail, or a wider head).

**3. Vesicle leaflets must split by AREA, not in half.** n_inner/n_outer = (r_inner/r_outer)^2. Real
vesicles carry the same constraint, which is why their leaflets hold different lipid counts.

**4. `_sphere_dirs` sampled normalised Gaussians, i.e. Poisson-random points.** Poisson points CLUMP:
median nearest-neighbour distance is 2r*sqrt(ln2/n) against 2r*sqrt(pi/n) for an even arrangement, a
factor of 2.1 closer. This defeated every geometric fix -- the shells stayed at 0.59 of contact
whatever radii or leaflet split were chosen, because the clumping was in the SAMPLING. Replaced with
a Fibonacci spiral, with a separate `_random_dirs` kept for the null reference, where clumping is the
point. Two corollaries, each of which cost a test: a contiguous SLICE of one spiral is a band over a
pole, not a shell, so each leaflet needs its own spiral; and two spirals of n/2 both cover the whole
sphere, handing out directions in near-coincident PAIRS, so a filled ball needs a single spiral of n.

All 103 tests pass. The cluster-cutoff window was re-measured rather than assumed after the geometry
changed, and gap=3.2 still separates correctly (cutoff 1.6 -> 0.33) while catching the known-bad
cutoff (2.2 -> 1.00).

This closes the long-standing task "fix planted bilayer steric overlap": the 3-D planted bilayer was
in fact already correct at exactly 1.000, and the overlap was in the micelle and vesicle instead.

## 2026-08-01g — RETRACTION of 2026-08-01f's structural claim, and defect #16: nothing checked that matter occupies space

The k_bond finding in 2026-08-01f stands: raising the force ceiling while holding speed * k_bond
fixed does keep bonds intact, and that mechanism is real. **The structural claim built on it does
not.** Calling that run "the first admissible ordered structure" was wrong, and the render is what
caught it.

    lipid beads       189
    raw extent x/y    2.18 x 2.33      -> area ~5
    area needed       148              -> 30x over-packed

189 beads inside a 2.2-unit blob. The aggregate had collapsed THROUGH ITSELF, and measure() returned
ok=True, lamellar 1.00, cluster_frac 1.00, align 0.53 on it.

**Defect #16, and the worst class so far: the harness had no excluded-volume check at all.** Every
existing guard is structurally blind to interpenetration.

    bond_stats   reads INTRAMOLECULAR distances, so 63 molecules stacked on one point each
                 report a flawless bond of 1.0
    lamellar     computed from DIRECTIONS, which stay well defined at any density
    align        same
    cluster_frac a collapsed pile is maximally connected, so this reads 1.00 -- its BEST value

So "zero deformed bonds" was true and irrelevant. Lowering repel 12 -> 6 is what let attraction win;
the repel 3 row was very likely the same collapse, which is exactly why its bonds read COMPRESSED
(0.943) rather than stretched. That number was visible at the time and I read it as a curiosity
instead of as the signature it was.

Fix: `packing(e)` -- median nearest NON-BONDED neighbour distance over the derived contact distance,
gated at MIN_PACKING and checked BEFORE every shape metric, since a collapsed pile scores perfectly
on all of them. Bonded pairs are excluded because a bond legitimately sits inside contact.

The methodological lesson, which is the same one this project keeps paying for: a metric suite
assembled by fixing defects one at a time only ever guards the failures it has already seen. Fifteen
defects in, nothing had asked whether the configuration was admissible as MATTER before asking what
SHAPE it was. Physical admissibility is a precondition, not another metric alongside the rest.

## 2026-08-01f — SOLVED: a saturating bond needs a higher force ceiling, not a stiffer spring

First admissible ordered structure with explicit water in this project.

    k_bond   speed    product   bond    max   frac>1.25   align
        20  0.0006      0.012  1.019   1.38        0.06   0.537
        60  0.0002      0.012  1.008   1.15        0.00   0.458

The damage was never bulk pressure. At repel 6 the MEAN bond (1.019) was better than the no-water
baseline (1.027) while order was fully retained, and at repel 3 the mean fell to 0.943 -- most bonds
COMPRESSED -- yet 13% still exceeded 1.25. That is bimodal: soft cores let a bead thread through a
neighbouring molecule and drag its bond long behind it. The failure is a TAIL, not a squeeze.

A tail is exactly what a SATURATING force produces. The transformer-only constraint means the bond is
an attention kernel with a bounded maximum force; once steric push exceeds that bound the bond
stretches freely and nothing pulls it back. Raising k_bond earlier appeared to make things worse only
because it broke the integrator -- displacement per step is speed * k_bond / (1 - momentum), and
k_bond = 100 at unchanged speed blew through the 0.05 stability limit. Raising the ceiling WHILE
holding the product fixed was never tested until now.

    k_bond 60, speed 0.0002, repel 6, water 250   ->   frac>1.25 = 0.00, align 0.458

Zero deformed bonds, max bond 1.15 (against 1.05 for a relaxed planted bilayer and a 1.25 gate), with
lamellar order retained. The no-water baseline scores align 0.042, i.e. random, so the order is real
and solvent-driven.

Working parameter set for the vesicle attempt: k_bond 60, speed 0.0002, repel 6, bond_span 2.0,
n_water 250, hydrophobic 0.6. Step counts must scale as 1/speed to reach the same physical time.

## 2026-08-01e — water is BOTH the source of lamellar order and the cause of bond damage

**Isolated by elimination**, after the bond threshold was first calibrated against a known-good
structure: a relaxed planted bilayer keeps EVERY bond under 1.05 (p99 = 1.050, frac>1.25 = 0.00), so
the 1.25 threshold is generous and runs exceeding it are genuinely deforming.

Ruled out one at a time, each by a run rather than an argument:

    the species-pair matrix   deforms without it too
    the electrostatic head    10-12% deformed at polarity 0.80, 0.30 AND 0.00
    the timestep              3x stability margin, still deforms
    bond stiffness            WORSE when raised (100 -> 100% of bonds over the limit)

**The cause is explicit water**, and the isolation is clean:

    2-D, NO water, clump start    bond 1.027  frac>1.25 0.00   align 0.042
    2-D, water 250, clump start   bond 1.061  frac>1.25 0.07   align 0.529
    2-D, water 120, clump start   bond 1.045  frac>1.25 0.05   align 0.346

Polarity looked exonerating only because water was still present when polarity was zeroed -- clearing
one variable while another stayed did not clear the pair.

**The trade-off is the finding.** Water is REQUIRED for lamellar order: without it align is 0.042,
i.e. random. With it, align reaches 0.529. But solvent multiplies the neighbours around each lipid
bead, and summed steric pressure then exceeds what a SATURATING bond kernel can resist -- the
mechanism from 2026-07-28f, now with the culprit identified. Halving the water halves the damage and
also halves the order.

That is the real shape of the problem: the same solvent that drives stage 1 also breaks the molecule,
and a bounded bond force cannot be strengthened out of it (raising k_bond makes it worse). The lever
that reduces pressure WITHOUT removing water is the excluded-volume strength.

## 2026-08-01d — bicelle vs vesicle: Finding 25 was right, and I retracted it wrongly

**Two sources used the same word for different things.**
* A TRUE BICELLE is a two-component equilibrium phase: long-chain lipid plus a short-chain detergent
  (DMPC/DHPC) that caps the rim. Vesicles are the usual STARTING material -- adding detergent cracks
  them into discs, and diluting the detergent lets the discs reseal into vesicles.
* A transient DISC-LIKE INTERMEDIATE in single-component CG self-assembly is a kinetic structure, not
  a thermodynamic phase, and is loosely called "bicelle-like".

**Our own control already said so.** Cooke-Deserno, given one lipid species and a finite aggregate,
made a ROD rather than a disc. Finding 25 concluded from that "a bicelle needs a second, rim-capping
species" -- which matches the literature -- and I RETRACTED it when the vesicle-pathway description
arrived. The retraction was the error, not the finding.

**Consequence: target the VESICLE, not the bicelle.** A vesicle is what a single phospholipid forms in
water, needs no detergent, and is now fully verifiable:

    align     ~0.03 radial (validated: bilayer 1.00, micelle 0.09, vesicle 0.03, random 0.08)
    hollow    ~0.00 empty core, guarded to spherical aggregates
    enclosed  ~0.55 lumen at bulk solvent density; a filled micelle reads 0.00

A bicelle remains reachable later, but only by adding a SECOND species, which is a modelling change
rather than a parameter sweep.

**Not independently sourced:** the web-search budget was exhausted, so this rests on background
knowledge plus our own control experiment, which agree.

## 2026-08-01c — can the tooling verify a BICELLE? Not until now

**Asked directly, and the audit found the gap.** Verifying a bicelle needs three things: lamellar
order, a flat disc shape, and a RIM. The suite covered bilayer, micelle, vesicle and random -- none of
which has a rim -- so the one structure the project is hunting had never been planted, and `edge`, the
rim metric, had never been validated against a known answer.

**Added a planted bicelle and a spanning-bilayer-with-solvent control.** Building them surfaced three
things:

1. `edge` WORKS. A periodic spanning sheet has no edges and reads near zero; a finite disc reads
   higher. That ordering is the test, and it now passes.
2. `edge` is UNDEFINED without solvent (NaN), so a bicelle cannot be demonstrated in any solvent-free
   run. This is a hard constraint on experiment design, not just on tests.
3. `edge` scales with SOLVENT DENSITY, so it must be compared to a control rather than a fixed
   threshold: the same planted bicelle read 0.032 in dilute solvent.

**Also corrected a bad reference of my own:** the first planted "bicelle" had radius 5 and thickness 5,
a squat cylinder that scored aspect 0.46, barely flatter than a sphere. A real bicelle has radius
several times its thickness; rebuilt at R=9 with 500 lipids.

**Verdict: the tooling can now verify a bicelle**, provided the run has explicit solvent and a control
to compare `edge` against. 99 tests pass.

## 2026-08-01b — adversarial tool audit: three more bugs, and the discriminator we never had

**Asked to deep dive for remaining tooling bugs.** Attacked each tool with cases it had never seen.
All three attacks succeeded.

    A  unwrap() on a structure wider than L/2   true span 8.0 -> reported 9.79      BROKEN
    B  lamellar on a planted SPHERE             0.967, with near-degenerate          BROKEN
                                                eigenvalues so the "thin axis"
                                                is arbitrary noise
    C  aspect on the SAME membrane, two boxes   0.245 at bound=6, 0.109 at bound=9   MEASURES THE BOX

C invalidates every cross-box `aspect` comparison in this project. B explains why `lamellar` read 1.0
on droplets: it was never measuring lamellar order.

**Fixes.**
* `unwrap` now walks the molecule graph by BFS, unwrapping each molecule against an ALREADY-UNWRAPPED
  neighbour, which has no size limit. Note a genuine limitation recorded honestly: for a structure
  that PERCOLATES the periodic box, unwrapping is mathematically ill-defined and BFS unrolls it
  arbitrarily.
* `align`: nematic order S of the lipid axes, computed from INTRAMOLECULAR minimum-image vectors so
  it needs no unwrapping and is valid for spanning and finite structures alike. This is the
  discriminator the project never had.

      structure   align    lamellar   hollow
      bilayer     1.000    0.889      n/a (guarded)
      micelle     0.086    0.967      14.56
      vesicle     0.033    0.489       0.00
      random      0.084    0.477       5.21

* `thick_mol`: thickness along the director in molecule lengths, independent of the box.
* `hollow` guarded to roughly spherical aggregates only -- core-vs-shell is a radial decomposition and
  read 22.27 on a planted slab, which is meaningless.
* The RENDERER now unwraps through the same BFS, so an image can no longer show a coherent aggregate
  as scattered debris.

**Re-examination with the corrected instruments.** Planted bilayer align 0.994; self-assembled
solvent-free align 0.084, i.e. the random value. NO PRIOR STRUCTURAL CLAIM SURVIVES. What stands is
that vivarium HOLDS a planted membrane; it does not FORM one.

## 2026-08-01a — the tools were wrong, and known-answer tests found it

**Question asked: are you judging by screenshots or by the raw tensors, and are the tools correct?**
Almost entirely by scalars, and no. Images were consulted maybe five times all session and EVERY time
contradicted the scalar: a "SLAB" that was a droplet, an "aspect 0.189" that was a 23-lipid fragment,
a "ring" that was a filled blob. Each time I went back to optimising scalars.

**Tool audit.** `make_figures.frame()` rendered RAW WRAPPED coordinates, so several images sent
earlier could show an aggregate as scattered debris purely from wrapping. `fig_state.py` was correct.
Orientation arrays had never been inspected directly at all. Fixed the renderer; added
`inspect_raw.py`, which prints head-position histograms, per-lipid tilt and the leaflet split, and
validates itself against a planted bilayer.

**Then a real process failure.** `py_test(test_suite)` had been silently DELETED from BUILD.bazel by
one of my scripted edits at 93b8449. Two "85 tests pass" claims were therefore vacuous: the grep
matched nothing and I read empty output as success. Restored.

**Bugs the known-answer tests caught, none of which inspection had found:**

1. `largest_cluster` connected molecules by their MIDDLE bead, ~5 apart across a bilayer, so it split
   every bilayer into leaflets. cluster_frac read 0.50 and MIN_CLUSTER_FRAC=0.60 DISQUALIFIED a
   perfect bilayer as "fragmented". Many of today's "fragmented" rejections were plausibly membranes.
   Now connects on any bead pair, since the leaflets meet tail to tail ~1 apart.
2. The planted bilayer control at bound=5 with 4-bead tails spans 9 of a 10 box: its head layers sat
   1.0 apart through the wrap. The reference itself was invalid.
3. A planted VESICLE read as flat (aspect 0.39) and FILLED (hollow 2.6) because its diameter exceeded
   L/2 and the far side wrapped onto the near side.
4. A spanning bilayer read as ROUND (aspect 0.98) because the box half-width was under the membrane
   thickness, so minimum image folded the leaflets together.

**Now in place:** `tests/test_metric_truth.py` and `tests/test_structure_discrimination.py`, 96 tests
passing, pinning what the metrics MEAN rather than what they currently output. Verified they can fail
by reintroducing the clustering bug (3 tests tripped) and restoring it.

**Consequence.** No structural conclusion from the preceding day survives: the scalars sat downstream
of a cluster detector that could not see a bilayer, references that did not fit their boxes, and a
renderer that did not unwrap.

## 2026-07-31c — the mixing rule was the blocker; species-pair matrix implemented

**Question asked: is it working, or should we pivot?** Pivot, and the reason is structural rather
than a tuning failure.

Vivarium mixed dispersion geometrically. Computing the hydrophobic contrast across the whole range of
water strengths:

    rad_water   eps_ww   eps_tt   eps_tw = sqrt      contrast
    0.15        0.090    0.994    0.299              +0.243
    0.40        0.565    0.994    0.749              +0.030
    0.60        0.894    0.994    0.942              +0.001
    0.85        0.994    0.994    0.994              +0.000

By AM-GM the contrast is non-negative and largest when water is WEAK, so a mixing rule offers exactly
one demixing mechanism: "oil is sticky". Tails clump because they attract each other, while water has
little reason to leave and permeates the aggregate. That is a weak analogue of the hydrophobic effect
and it is why every wet-core reading persisted.

The real stage-1 driver needs water to cohere strongly AND couple weakly to tails, i.e. eps_tw below
the geometric mean. A mixing rule cannot produce a negative deviation by construction.

**Implemented `eps_pair`**, an (n_species, n_species) well-depth matrix replacing the mixing rule.
Defaults to None so the base case stays byte-identical. It remains inside the transformer-only
requirement: a species-pair coefficient is a bilinear form on species embeddings, a structured linear
op of the same shape as an attention bias, still bounded and still symmetric so forces stay
conservative.

    water-water   tunable (the hydrogen-bond analogue)
    tail-tail     1.00
    tail-water    0.02   <- FAR below the geometric mean; impossible under a mixing rule
    head-water    0.60   <- heads are hydrophilic
    head-head     0.10   <- heads must not cohere

**Note on verification:** the claim that CG force fields use interaction matrices rather than mixing
rules is from background knowledge; the session's web-search budget was exhausted, so it is not
independently sourced here.

## 2026-07-31b — auditing against the physics: our water is nearly an ideal gas

**Prompted by "are we overcomplicating or on the wrong path".** Yes, on both counts, and the audit is
worth recording because it caught a first-principles error a nine-parameter search could not.

**The stage-1 driver is water preferring ITSELF.** Water cannot hydrogen-bond to a tail, so it cages
it, and aggregation releases that structured water for a favourable entropy change. The hydrophobic
effect is therefore powered by water-water attraction. Ours:

    tail-tail    eps 0.994
    tail-water   eps 0.299
    water-water  eps 0.090      <- the hydrogen-bond analogue

Our water is nearly an ideal gas. Solvating a tail costs almost nothing, so there is barely a
hydrophobic effect to collapse the aggregate -- exactly what `edge` = 1.00 (wet cores) had been
reporting for hours while I searched packing parameters instead.

**One axis, from the physics, beat nine chosen by me.** Sweeping water self-attraction:

    water_dipole   lamellar   aspect   verdict
      0.8            0.967     0.815   partial
      2.5            0.933     0.307   RIBBON (2-D bicelle)   <- first unbiased ribbon verdict
      5.0            0.900     0.438   partial
      9.0            0.967     0.476   partial

Water self-attraction is the FLATNESS lever, and 2.5 is a clear optimum.

**Why `edge` stays at 1.00 is geometric, not thermodynamic.** At tails=4 the membrane measures
thick = 2.61, so tips sit ~1.3 from each face, inside the 1.2 water-contact range: they physically
cannot be dry. Lengthening the arms thickens it (thick 4.7-6.4) but ORDERING DEGRADES
(lamellar 0.93 -> 0.70) and edge stays 1.00, which means water crosses through defects rather than
the sheet being too thin.

**Standing correction to method.** A nine-dimensional random search over parameters was the wrong
instrument for a question the physics answers directly. The 60-config and 120-config searches produced
one usable number between them; a four-point sweep chosen from the stage-1 mechanism produced the
first ribbon.

## 2026-07-31a — explicit water restored; cohesion sets a real flat-vs-dry trade-off

**Why solvent-free was fatal, not merely expensive.** The literature pathway is
dispersion -> bicelle -> cup -> sealed vesicle, and every step is driven by hydrophobic edges
minimising contact with WATER. A vesicle is by definition a shell ENCLOSING water. Solvent-free gives
line tension gamma = 0, so R_crit = (4*kappa_c + 2*kappa_bar)/gamma is INFINITE and closure cannot
happen at any size; there is also nothing to enclose. The droplets were the correct answer to the
model being run, and the earlier "a bicelle needs two species" conclusion was wrong -- bicelles form
spontaneously as kinetic intermediates once water is present.

**Two bugs this exposed, both of which invalidated the earlier branched test.**
- `_build_chains` built branched TOPOLOGY while the drivers still strung beads along a LINE, so arm
  2's first bead started 3 units from the head it is bonded to. Every branched run in 2-D and 3-D
  began with torn bonds.
- `harness.bond_stats` walked mol[:,k] -> mol[:,k+1], which on a branched lipid steps from arm 1's tip
  to arm 2's base -- beads that are not bonded. It reported 25% breakage on a perfect molecule. It now
  reads the engine's bond list.

**`edge`: the quantity the pathway actually trades.** Fraction of lipids whose DEEPEST tail bead
touches water, i.e. L_edge in G_edge = 2*pi*R*gamma. Counting any wet tail bead saturated at 1.00 even
at perfect lamellar order, because a 4-bead branched lipid gives a membrane ~4 thick and a 1.4 contact
range reaches the midline from both faces. Stage 2 has edge > 0, stage 4 has edge -> 0.

**Result: cohesion sets a genuine trade-off** (2-D, 40 lipids, explicit water, branched):

    attract    lamellar   aspect   edge    reading
      0.3        0.600     0.765   1.00    disordered
      5.0        0.975     0.332   1.00    FLAT but fully wet: no hydrophobic core
     14.0        0.875     0.900   0.25    DRY CORE but round: a droplet
     25.0        0.650     0.880   0.23    dry core, rounder still

Flatness and a dry core are both reachable, but so far never together. This is the competition the
thermodynamics predicts -- line tension against bending -- appearing directly in our own numbers, and
it is the first time the pathway has been visible rather than inferred.

**Corrected en route:** at N=40 the ribbon interior is already 95% of the molecules, so the wet core is
a DENSITY problem, not a length problem. Scaling the lipid count is therefore the wrong lever.

## 2026-07-30b — nature's architecture implemented; the packing parameter still does not select a phase

**First principles, prompted by the right question: what have we actually been searching for?**
`aspect` rewards a flat spanning sheet, which is the standard MD idealisation of a lamellar phase. But
a finite amount of lipid in water forms a VESICLE, and a vesicle has NO RIM -- so it avoids the exact
edge-energy penalty that killed the bicelle in both vivarium and the control. The metric was also
blind to it: a vesicle is spherical, so `aspect` ~ 1 and `lamellar` high, which is a droplet's
signature. A vesicle would have been DISCARDED by the 60-config search as a droplet.

**And the deeper miss.** A linear head-tail-tail-tail chain is a SINGLE-TAILED surfactant. Single-
tailed surfactants form micelles; that is textbook. The droplets this project kept producing were the
CORRECT physics for the molecule being simulated. Real phospholipids have TWO tails branching from one
head, which doubles v at fixed a0 and moves P = v/(a0*l) from the micelle regime into the bilayer one.

**Implemented** `branched=True`: two arms from the head, verified by bond topology (head degree 2 vs 1
for the linear chain). Base case still byte-identical.

**Result: it does not help.**

    2-D, 100 lipids, 4 tail beads, from a compact clump   (random 0.520/0.720, planted ribbon 1.000/0.093)
    linear                          lamellar 0.690  aspect 0.785
    branched, head 1.0              lamellar 0.620  aspect 0.903
    branched, head 1.4 / 1.8 / 2.2  lamellar 0.62-0.69  aspect 0.765-0.802
    branched, head 0.8 / 0.5 / 0.3  lamellar 0.58-0.62  aspect 0.753-0.900

**Measured a0 instead of assuming it**, which corrected a wrong prediction of mine:

    head_sigma   predicted spacing   MEASURED   ratio
    1.0          1.00                1.999      1.00
    1.4          1.40                2.336      1.17
    1.8          1.80                2.604      1.30
    2.2          2.20                2.883      1.44

The head claims area SUB-LINEARLY (asking 2.2x delivers 1.44x), and at head_sigma=1.0 the spacing is
already 2.0, so effective a0 is ~4x nominal. Recomputing P with measured areas, every LARGER head was
pushing deeper into the micelle regime -- the opposite of what I had swept for. Sweeping smaller heads
across the corrected window did not help either.

**Conclusion.** The packing parameter, which is the mechanism nature uses to select lamellar over
micellar, does not operate in this model: P was varied across 0.24 to 0.89 by two independent routes
and the phase never changed. The reference model agrees that finite bilayers are hard -- Cooke-Deserno
given a finite aggregate in a large box also made a ROD, and only produces a bilayer when the periodic
box is sized to force one. Spontaneous vesicle formation needs thousands of lipids and long times,
which is why the MD literature almost always STARTS from a planted bilayer.

## 2026-07-30a — a validated harness, and the first admissible structural result

**The bug behind three wrong diagnoses.** `molecule_ok` measured bond lengths with RAW subtraction, no
minimum image, so any bonded pair straddling the periodic boundary read as enormous -- it reported
13.3 in a box of 10, which is geometrically impossible and which I did not question. Measured
correctly:

    config                         bond (rest 1.0)    fraction > 1.25
    span=2.0, repel=12             1.01 - 1.02        0.00   PERFECTLY INTACT
    span=6.0 (the retracted SLAB)  1.76 - 3.38        1.00   genuinely stretched

So the SLAB retraction was RIGHT, but the three diagnoses after it were all wrong: there was no
steric-pressure envelope problem and no timestep problem. `span=2.0` keeps molecules perfect at
repel=12. The ONLY real defect was bond_span=6.0.

**`harness.py`: one chokepoint.** `unwrap()` and `delta()` are the only places a periodic difference
is taken, and everything geometric goes through them. Any sample with a deformed molecule
(bond > 1.25) or an overshooting integrator (> 0.05/step) is DISQUALIFIED rather than interpreted.
Bonds are measured over EVERY backbone bond, shape PER CLUSTER, and both controls print every run.

Calibration: planted 1.000 / 0.231, random 0.498 / 0.839, and span=6.0 correctly REFUSED.

The harness immediately caught a bug of my own: the first driver sampled displacement across a
6000-step interval and compared it to a per-step bound, disqualifying every healthy run.

**First admissible result** (bond 1.02, disp <= 0.001, status ok throughout):

    run                            lamellar (null 0.50)   aspect (null 0.85)
    planted bilayer, relaxed       0.991 -> 0.870         0.23 -> 0.43   stable 24k steps
    self-assembly, slit            0.494 -> 0.818         0.87 -> 0.48   stable
    self-assembly, PBC (no walls)  0.506 -> 0.818         0.85 -> 0.55   stable

**Two findings.** The WALL DEPENDENCE IS GONE: pure periodic matches the slit, so that caveat was an
artifact of the stretched lipid rather than a real requirement. And both starting points CONVERGE --
the planted bilayer decays to 0.87/0.43 while disorder rises to 0.82/0.55. Meeting from opposite
directions is what equilibrium looks like, and it is far stronger evidence than either run alone.

**Honest limit.** This is not a clean bilayer: aspect settles near 0.5 against a planted 0.23, so the
aggregate is markedly flatter than a droplet but well short of a slab. It is a partially ordered
lamellar aggregate, and it is the first structural claim in this project that survives its own
admissibility checks.

## 2026-07-29g — RETRACTION: the slab was an artifact of the stretched lipid

**Ran.** The three claims that had been measured at bond_span=6.0, redone at span=2.0, with bond
length and 1-3 span now printed on EVERY line (rule 0), and span=6.0 alongside for a direct contrast.

    config                      bond (rest 1.0)   L2/L3   shape   lamellar
    span 6.0 (the old "best")        4.12          0.87    SLAB     0.965
    span 2.0, slit                   2.14          0.14    rod      0.805
    span 2.0, pure PBC               2.10          0.14    rod      0.810
    span 2.0, planted bilayer        1.49          0.09    rod      0.814

**The only configuration that produces a slab is the one whose lipids are stretched to 4x their rest
length** -- a ~7-long floppy string rather than a 3-bead rod. Long strings layer readily, which is
presumably why it looked so good. RETRACTING the L2/L3 0.87 "SLAB" result and, with it, the claim that
4-bead tails give lamellar order. The head_sigma sweep of 2026-07-29d rested on the same stretched
molecule and is void too.

**Second problem, found by the new instrumentation.** span=2.0 does NOT keep lipids intact at 3-D
density either: bonds still reach 1.4-2.1. In 2-D at lower density span=2.0 held perfectly
(1.01 +/- 0.01), so this is density-dependent and is Finding 2026-07-28f's mechanism again -- steric
pressure is a SUM over ~12 neighbours at repel=12, about 43 in total, against a bond force that
SATURATES at k_bond=40. The bond loses.

**Consequence for the whole project.** No admissible bilayer result currently stands. What survives is
the micelle (rung 1), the stable planted 2-D bicelle, and the finding that the droplet is the
equilibrium phase. Everything lamellar in 3-D was measured on a deformed molecule.

**Running:** k_bond 150 and 400 at span 2.0, which should let the bond win the force balance. Until a
run shows bond ~1.0 SUSTAINED, no 3-D structural claim is admissible.

## 2026-07-29f — the droplet is the PHASE, not a trap; and bond_span=6.0 was stretching every lipid

**Ran, in 2-D from a compact disordered clump** (which separates "can dispersed molecules find each
other", ordinary diffusion, from "can molecules already together ORDER"): lipid count past the
droplet head-packing limit, a hard excluded-volume core, per-cluster shape, annealing, and finally the
molecular geometry itself.

**Everything says droplet.**

    lipid count   N=60/100/150, all past the limit where heads no longer fit
                  on a droplet perimeter (12*pi ~ 38)          aspect 0.76-0.82  round
    hard core     repel_sharp 0 / 4 / 12 / 40                  aspect 0.76-0.93  round
    per-cluster   ONE cluster, per-cluster aspect == global     the metric was sound
    annealing     kT 0.10 / 0.25 / 0.60 -> 0.005               aspect 0.77-0.86  round

Annealing failing is the informative one: annealing escapes KINETIC traps, so the droplet is not a
trap, it is the preferred phase. The planted ribbon (aspect 0.33, lamellar 0.92, holds 20k steps) is
therefore metastable, and nothing reaches it from a disordered clump.

**Then the bug that matters most.** Checking the molecule, which nothing above had done:

    bond_span   bond (rest 1.0)   r13 (straight 2.0)   verdict
      2.0       1.01 +/- 0.01     2.00                 INTACT, perfectly straight
      2.2       1.07 +/- 0.01     2.14                 intact
      2.5       1.17 +/- 0.01     2.34                 intact
      3.0       1.34 +/- 0.02     2.67                 STRETCHED
      6.0       2.37 +/- 0.42     4.46                 STRETCHED 2.4x

`bond_span=6.0` was used in EVERY 4-bead-tail experiment, in 2-D and 3-D. Those lipids were 2.4x
longer and far floppier than intended, so the 3-D results that looked best -- lamellar 0.965,
L2/L3 0.87, "SLAB" -- were measured on the wrong molecule. The mechanism is the one from 2026-07-28f:
the straightener wants 6.0, the chain can only reach 2.0, and both tanh kernels saturate at the same
amplitude so they cancel and the chain extends with no restoring force.

**Important:** fixing it does NOT change the phase. At span=2.0 with a perfectly rigid rod the
aggregate is still a round droplet (aspect 0.762). So the stretch was a real bug but not the cause.

**Next:** re-run the 4-bead-tail 3-D experiments at span=2.0. Longer tails were the one lever that
demonstrably helped (L2/L3 0.87 vs 0.44-0.58), and that measurement has to be repeated on an intact
molecule before it can be believed.

## 2026-07-29e — the box was the limit, not the physics (2-D bicelle is stable)

**Prompted by the observation** that the environment might be too confining and lipids were piling at
the box edges. That turned out to be right, twice over.

**Bug in my own experiment first.** The planted 2-D row laid `n_lip/2` lipids across the FULL box
whatever the count, so 30 lipids in a box of 12 started at 0.4 spacing against a contact distance of
1.0 -- 60% over-compressed from step one. It collapsed instantly and I nearly recorded that as the
ribbon being unstable. Sized correctly, a SPANNING 2-D bilayer is stable and gets flatter with room:

    box 12   lamellar 1.000  aspect 0.205
    box 18   lamellar 1.000  aspect 0.141
    box 24   lamellar 1.000  aspect 0.088

**Then the bicelle proper:** a FINITE ribbon (36 lipids, `--spanfrac 0.5`, empty box around it) in
progressively larger boxes.

    box   aspect 0 -> 5k -> 10k -> 15k -> 20k        lamellar   outcome
     24   0.217  0.661  0.615  0.549  0.546            0.722    curls into a droplet
     32   0.122  0.385  0.520  0.529  0.539            0.889    curls
     44   0.097  0.305  0.336  0.331  0.352            0.917    HOLDS as a ribbon

In the large box it PLATEAUS rather than continuing to curl. Against a random null of aspect 0.62 /
lamellar 0.583 and a planted 0.097 / 1.000, the relaxed state sits far closer to the ribbon. The small
boxes curl because the ribbon is confined and interacting with its own periodic images.

**Metric warning found here.** `lamellar` reads 1.000 on a COLLAPSED droplet, identical to the planted
ribbon, because a filled blob with heads on its perimeter satisfies "head farther out than its own
tails" perfectly. Only `aspect` separates ribbon from droplet. A radial profile confirmed the collapsed
state has tails all the way to r=0.25, so it is filled, not a closed ring -- I had briefly read it as a
2-D vesicle, which was wrong.

**Status.** A 2-D bicelle is STABLE given room. Self-assembly of one from disorder is untested, and
that is the remaining question: stability and nucleation are separate, and nucleation is what has
failed everywhere in 3-D.

## 2026-07-29d — longer tails help, smaller heads do not, and the slab needs the WALLS

**Ran.** 4-bead tails, head_sigma in {1.0, 0.70, 0.55, 0.40}, self-assembly from disorder, under BOTH
boundary conditions so they are directly comparable.

**Got.**

    4-bead tails        pure periodic                with slit (walls on z)
    head 1.0            lamellar 0.537  L2/L3 0.77   lamellar 0.965  L2/L3 0.87  SLAB
    head 0.70           lamellar 0.810  L2/L3 0.42   lamellar 0.935  L2/L3 0.82  SLAB
    head 0.55           lamellar 0.740  L2/L3 0.51   -
    head 0.40           lamellar 0.524  L2/L3 0.59   lamellar 0.896  L2/L3 0.74  SLAB

**1. Longer tails help.** 4-bead tails reach L2/L3 0.87 against 0.44-0.58 for 2-bead. This is the
packing-parameter prediction (P = v/(a0*l)) confirmed: more tail volume raises P toward lamellar.

**2. Smaller heads do NOT help.** With the slit, lamellar falls monotonically as the head shrinks:
0.965 (head 1.0) -> 0.935 (0.70) -> 0.896 (0.40). The packing-parameter argument predicts the
opposite, so that lever is spent and the prediction is wrong here. Plausibly because in a
SOLVENT-FREE model the head's only job is steric spreading -- there is no water to hide from -- so
shrinking it removes the lateral pressure that holds a leaflet apart.

**3. THE SLAB REQUIRES THE WALLS.** Under pure periodic boundaries there is no slab at any head size.
Every bilayer-like result in this project depends on `--slit`, which is the one component whose
transformer-only faithfulness is contestable (it applies a force from a token's ABSOLUTE position,
defensible only as a position-wise feed-forward layer, and it breaks translation invariance and
momentum conservation). A slit also CONFINES lipids to a slab-shaped region, so it may simply be
templating the membrane rather than letting it emerge. Treat the slab as wall-assisted until a
periodic run reproduces it.

**Metric note.** head 1.0 under PBC scores "SLAB" on shape while lamellar reads 0.537, i.e. the 0.5
null: a slab-SHAPED blob with no head-out order. Neither metric alone is sufficient, which is why
both print on every run.

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
