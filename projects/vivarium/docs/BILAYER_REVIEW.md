# Rigorous review: why bilayers have not emerged

> **STATUS 2026-07-25 — Findings 1 and 2 are FIXED; Finding 3 is addressed by the 3-D dish.**
> Read the "Findings" below as a diagnosis of the code *as it was*; each carries a resolution
> note. Assembly (`emergence_score`) is still NOT achieved — only demixing improved.
>
> A separate, more serious bug was found afterwards while reviewing this work: the electrostatic
> near-face read the wrong face, so the "conservative" force was not conservative. See
> [Finding 5](#finding-5-the-electrostatic-force-was-not-actually-conservative-2026-07-25).
> **Every benchmark number recorded before that fix measured a subtly non-physical system.**

Everything must emerge from the three fundamental forces the sim is allowed to have:
**Pauli exclusion (repel), van der Waals (attract), electrostatics (polarity)** — acting on
shaped, rigid-or-flexible molecules. No fourth ingredient. This document reviews why that has
not happened yet, and states what is actually broken.

Two earlier proposals are **retracted** as violations of that principle:

- `k_hydro` / `k_tail` explicit lipid forces (current `LIPID` species) — a per-species force law.
- A "hydrophobicity channel" (per-token phobicity scalar + like-attracts-like) — a fourth
  ingredient wearing a physics costume.

The hydrophobic effect is *not* a fourth force. It is what you get when water's electrostatic
self-cohesion beats its van der Waals attraction to a nonpolar surface. If it does not emerge
here, the fault is in how our three forces read the molecule — not in a missing force.

## Finding 1 (root cause) — the model cannot express "bulky but neutral"

> **RESOLVED.** A k=0 RADIUS channel now holds physical size at `rad_idx = pos_dim + shape_dim`,
> disjoint from the contour. A token can now be bulky-and-neutral (a tail) or bulky-and-charged
> (a head). Pinned by `test_radius_channel_does_not_overlap_the_contour`.

`config.py`: `shape_dim = 2·n_harmonics`, coefficients `(a_k, b_k)` for `k = 1..K`.
**There is no `k = 0` coefficient.** The contour is a pure *deviation* from a mean radius that
is never represented. `r0` exists only in `render_svg` — it is not a physical property.

Consequences, all traceable to this one fact:

| Property | How it is read today | Problem |
|---|---|---|
| charge | `nf = ⟨C, basis(θ)⟩` (signed radius deviation) | fine |
| physical size / bulk | **not represented** | fatal |
| polarizability (vdW strength) | inferred from shape overlap | wrong (see Finding 2) |

Because charge *is* the deviation, and there is no separate size channel:

- `C = 0` ⇒ neutral **and** zero-extent (a point). Nonpolar but with no surface to attract with.
- `C ≠ 0` ⇒ has extent **and** is charged. Bulky but no longer nonpolar.

A lipid tail is precisely the molecule this representation forbids: **bulky and neutral**.
That is why the emergent-amphiphile experiment produced flat order parameters — not a tuning
miss, a representational impossibility.

## Finding 2 — "attract" is not van der Waals

> **RESOLVED.** The conservative attraction is now `tanh(rad_i·rad_j/0.25)·exp(−λd²)` — contact
> area / polarizability, CHARGE-INDEPENDENT. `A_fit` (complementary fit) survives only to drive
> the induced-fit morph. Pinned by `test_vdw_is_charge_independent`.

`pack.py` conservative attract:

```
g_ij = sigmoid(S_comp / τ) · exp(−λ_a d²),    S_comp = ⟨C_i, M·C_j⟩
```

`S_comp` is *complementary fit* — bump-meets-pocket, lock-and-key. That is a real interaction
(specific binding), but it is **not** generic van der Waals. Real vdW / London dispersion is:

- proportional to **contact area** and polarizability (electron-cloud size), and
- **charge-independent** — which is exactly why neutral alkanes and oils cohere strongly.

Two failures follow:

1. A smooth neutral surface gets `S_comp ≈ 0`, so it has essentially no dispersion attraction.
   Nonpolar molecules cannot cohere. Oil is not sticky when it should be.
2. `sigmoid(0) = 0.5` — a *featureless* token still receives half-strength attraction to
   everything. "Neutral" is therefore **sticky**, not hydrophobic. Measured: water/oil
   demixing stays flat at 0.50 (fully mixed) even with polarity raised to 2.5.

The `attract_gated` experiment (scale vdW by contour presence) fixed (2) and produced the first
real demixing (0.50 → 0.58–0.61), confirming the diagnosis — but it made tails *inert* rather
than *cohesive*, because of Finding 1. Both must be fixed together.

## Finding 3 — 2D suppresses the hydrophobic effect

> **ADDRESSED.** The dish can now be 3-D (`pos_dim=3`), with the contour switching from circular
> to real spherical harmonics. 3-D reached demix 0.63 vs 0.42 for the same 2-D config — the
> chain-vs-network cap was real. Bilayers still have not formed.

In 2D a dipolar water forms **chains**, not a 3D hydrogen-bond network. The hydrophobic effect
is driven by water's ability to satisfy its H-bonds around a solute; a chain topology has far
less to lose than a 3D network, so the drive to expel nonpolar material is weak. Measured
ceiling: demix ≈ 0.58 at 8000 steps. Real bilayers are also a 3D packing phenomenon (the
packing-parameter argument for bilayer-vs-micelle is geometric and 3D).

This is a strength limitation in an existing force, not a missing mechanism — but it may cap
what 2D can reach. See "3D" below.

## Finding 4 — entropy is thin, and that is acceptable

The real hydrophobic effect is largely *entropic* (ordered water cages around nonpolar solutes).
This sim is overdamped and near-deterministic (`temperature` = small Langevin noise), so the
entropic route is weak. However, the *energetic* route (water–water electrostatics ≫ water–tail
dispersion) is real physics on its own and is sufficient to drive demixing in coarse-grained
models. We pursue the energetic route and do not simulate entropy explicitly.

## The fix, entirely within Pauli + vdW + electrostatics

Give the contour a `k = 0` coefficient — **mean radius = physical size** — and let each of the
three forces read its physically correct property from the same single contour object:

| Force | Reads | Physical meaning |
|---|---|---|
| Pauli (repel) | `k=0` radius (+ deviation) | excluded volume ∝ size |
| van der Waals (attract) | `k=0` surface contact, **charge-independent**, directional | dispersion ∝ contact area |
| electrostatics (polarity) | `k≥1` deviation (signed) | charge distribution |

This **decouples bulk from charge** using one added channel that is part of the *same* grounded
contour — not a new ingredient. A molecule can then be:

- bulky + neutral → **a lipid tail** (coheres by vdW, ignored by water's electrostatics)
- bulky + charged → **a lipid head** (solvates in water)
- small + strongly dipolar → **water**

and the bilayer follows from the three forces alone:

> water self-coheres electrostatically (H-bond) more than it disperses to a neutral tail →
> water expels tails → tails cohere by vdW into a core → charged heads solvate at the interface
> → **bilayer**.

## 3D

Simulating in 3D is *faithful* and probably necessary for a clean bilayer:

- **Positions**: `POS_DIM 2 → 3` is trivial and changes nothing about faithfulness — attention
  over 3D positions is the same bounded attention.
- **Contour**: the faithful generalization of circular harmonics `{cos kθ, sin kθ}` is **real
  spherical harmonics `Y_lm(θ,φ)`**. The near-face readout stays exactly what it is today —
  an inner product of the contour with a basis evaluated at the *relative bearing* to the
  neighbour (a RoPE-family relative-position term). `⟨C_i, Y(û_ij)⟩` is the same object one
  dimension up. Parseval still gives "overlap = contour overlap".
- **Cost**: pair tensors are `(N,N,3)` instead of `(N,N,2)` — same complexity class.
- **Visualization**: keep the existing 2D viewer by projecting (with depth cues — size/alpha by
  z), and/or add a rotatable 3D view. Simulating 3D while visualizing a 2D slice/projection is
  standard practice and costs no faithfulness.

3D is queued as a major experiment, *after* the `k=0` bulk channel, because bulk-vs-charge
decoupling is the root cause and is cheaper to test.

## Finding 5 — the electrostatic force was not actually conservative (2026-07-25)

Found by a momentum-conservation test written during the review of the 3-D work, **not** by any
result looking wrong. `nf_j` — "what token j presents toward i" — was computed as
`_near_face(C, ang_ji).T`, which evaluates j's contour along the bearing **i→j**: that is j's
**far** face. The face j presents toward i is its contour read along **j→i**, which is simply
`nf_i[j, i]`, i.e. `nf_j = nf_i.T`.

Consequence: `prod = nf_i · nf_j` was **asymmetric** (measured `max|P − Pᵀ| = 0.29`), so the pair
force had `F_ij ≠ −F_ji` and the system was pushed by a phantom net force (measured
`Σ_i F_i = 2.1`) while being documented as "CONSERVATIVE … relaxes to a free-energy minimum."
After the fix `prod` is symmetric to `0.0` exactly and `Σ_i F_i = 0` to 1e-9.

**Why this matters beyond correctness.** The spurious asymmetric term was injecting energy — it
was effectively stirring the dish. With it removed, the previously tuned configurations
**collapse** (3-D occupancy 63 → 19 of 64 cells; 2-D 64 → 44), so the space-filling behaviour was
partly an artefact. `demix_excess` rose (3-D 0.512 → 0.631) but is untrustworthy while the system
is condensing, since a dense clump inflates like-neighbour fractions. **Both benchmarks must be
re-baselined.**

Two further latent bugs were removed in the same pass:

- `attract_gated` indexed the 2-D circular layout and used a 2-D `arctan2` bearing, so in 3-D it
  silently computed nonsense rather than failing. It was superseded by the contact-area vdW and
  was OFF in every benchmark row, so nothing logged depended on it. Deleted.
- `config._validate` never ran for direct `VivariumConfig(...)` construction — which is how every
  engine and benchmark builds its config — so validation was dead code on the paths that mattered.
  It now runs in `__post_init__`.

## Finding 6 — molecules were sterically SPHERES (2026-07-25)

The contour was read only for charge. Excluded volume used a single scalar diameter and van der
Waals only the isotropic radius, so **every molecule was a sphere no matter what shape it "drew."**
An amphiphile therefore had no head *end* and tail *end* geometry, and its packing parameter
`v/(a₀·l)` — the tail-volume-to-head-area ratio that decides micelle vs bilayer vs inverted phase —
was identically 1. No lamellar phase can exist under that constraint.

Fixed by making the contact distance anisotropic: `contact_ij` is the sum of the radius each token
*presents toward* the other, read with the same grounded relative-bearing basis the electrostatics
already uses. Symmetric by construction (the second term is the transpose of the first), so the
repulsion stays conservative; bounded by `tanh`; no distance in a denominator.

Effect: `emergence_score` −0.015 → **+0.034**, the first clearly positive assembly signal on a
physically valid system.

A follow-up that seemed obviously right was **wrong**: driving the shape from `l≥2` only (fore-aft
symmetric ⇒ a rod, which is what packs into a sheet) *hurt* assembly (0.034 → −0.015) while helping
demixing. The `l=1` head bulge makes the head sterically distinct, and that appears to be what gets
heads pointing outward. Recorded because the reasoning was sound and the result still contradicted it.

## Finding 7 — one bead cannot separate head repulsion from tail attraction (2026-07-26)

Four physics-derived attempts to reproduce the required lipid sign pattern from Pauli + vdW +
electrostatics with a SINGLE interaction site all failed (widen the vdW range; lower the head charge
to flip lateral cohesion positive; un-saturate the dispersion kernel; make dispersion
orientation-dependent). The last one was rejected by our own test suite because it routed the charge
contour back into van der Waals — the shape/charge conflation of Finding 1.

The reason is geometric: a single bead applies head repulsion and tail attraction **at the same
point**, so no parameter choice can separate them. A real lipid separates them along a ~16-carbon
tail; SiMPLISTIC separates them by engineering the angular dependence directly.

**Resolution: 3-bead bonded lipids** (head + two tails). A bond is a FIXED PAIR MASK carrying a
bounded symmetric kernel `tanh((d − r0)/w)` — masked/local attention, which the requirement allows —
not a harmonic spring. A third bond (head ↔ far tail, rest length = the sum) holds the chain
straight. Token count is unchanged; beads are existing tokens relabelled into molecules.

Result on the planted-bilayer toy, at bond stiffness 80:

    single bead   leaflet 0.99 -> 0.48 (random)   dry_core 1.00 -> 0.40
    3-bead chain  leaflet 1.00 -> 1.00            dry_core 1.00 -> 0.98

**The force field now supports a bilayer.** Two tail beads double the tail–tail contact area, so the
aggregation drive scales with tail length, and water is genuinely excluded from the core. The
failure mode has therefore moved from "a bilayer is not even a local minimum" to a nucleation
problem — the good kind.

Self-assembly from a disordered start does NOT yet produce a bilayer. Caveat: the toy's order
parameters assume the bilayer normal is z, so they would not register a vesicle or an
arbitrarily-oriented sheet; a normal-agnostic detector is needed before that null is trusted.

## Finding 8 — the dispersion kernel was not a valid mixing rule (2026-07-26)

`tanh(r_i·r_j / S)` applied to the PRODUCT violates `eps_ij² = eps_ii·eps_jj`, and that identity is
exactly what guarantees a positive mixing energy `ΔE ∝ (√eps_ii − √eps_jj)²` — the hydrophobic
driving force itself. Measured violation: `eps_ww·eps_tt = 0.089` against `eps_wt² = 0.221`.

Fixed by bounding each token's well depth first and then combining by the exact geometric
(Lorentz–Berthelot) rule: `eps_i = tanh(r_i²/S)`, `g = √(eps_i·eps_j)`. Like-like interactions are
unchanged by construction; only the cross term is corrected, and it moves in the hydrophobic
direction (water–tail 0.470 → 0.299). The hydrophobic driving force triples, +0.144 → +0.486, and
measured demixing rose 0.330 → 0.435. Single-bead assembly score fell in the same change, but that
configuration is superseded by the chain lipid.

## Finding 9 — nothing is categorically missing; it is parameters and dynamics (2026-07-27)

A verified literature sweep (adversarially checked, 3-0 votes unless noted) settles what we are and
are not missing:

- **Nothing is blocked in principle.** Spontaneous nucleation is demonstrated repeatedly with
  STRICTLY LESS physics than we have — Noguchi & Takasu 2001 (rigid rods, solvent-free, no
  electrostatics), Cooke-Deserno 2005, Marrink & Mark 2003. The failure is parameterisation or
  dynamics, not a missing force.
- **Long-range electrostatics is NOT the blocker** — directly falsified by a PME control run, and
  overdetermined by models with zero electrostatics assembling fine. Our lack of Ewald is fine.
- **Water entropy is NOT required.** An energetic surrogate for hydrophobicity suffices.
- **Chain conformational entropy is NOT required** — rigid rods nucleate vesicles. So "too few tail
  beads / too stiff bonds" is a low-priority suspect.
- **Multibody density terms are an improvement, not a requirement** (they lower the CMC).

The two live suspects, and one exact diagnosis:

1. **Attraction range.** Cooke-Deserno call the decay range `w_c` "the key tuning parameter": the
   fluid-membrane region "disappears completely" below ~0.7 sigma, plain Lennard-Jones corresponds
   to ~0.7 sigma, and their working bilayers use ~1.6 sigma. Our ~1 sigma sits at the bottom edge of
   the viable window.
2. **Dynamics.** Every CG model that demonstrably nucleates uses an FDT-satisfying inertial
   Langevin, Brownian or DPD thermostat with NO velocity cap. Velocity-capped overdamped relaxation
   has no precedent (argument from silence — no source tests it directly).
3. **Sahrmann & Voth 2024 describe our exact symptom**: bottom-up CG lipid models validated only
   near the assembled-bilayer minimum are stable-when-planted yet incapable of self-assembly.
   **"A planted bilayer is stable" is a confirmed-INSUFFICIENT test of a potential.**

Documented pathway: monomers → rapid hydrophobic collapse into clusters/micelles → threadlike →
disc → closure. The slow step is LATE topological closure, not initial aggregation — so our failure
at the *first* (supposedly rapid) step points at the driving force or the dynamics, not patience.

Unanswered by the sweep: no verified minimum lipid count / CMC / box size (every lower-bound claim
was refuted), and there is NO verified evidence on 2-D amphiphile self-assembly at all.

### What we did with it

- Built `toy2d.py`: a fast 2-D testbed with ORIENTATION-AGNOSTIC order parameters (burial,
  hydration, local nematic, two-leaflet "opposed"), fixing the 3-D toy's flaw of measuring order
  only about z — which would score a vesicle or tilted sheet as zero.
- **Found a setup bug: the first 2-D box was at 127% areal coverage — jammed.** Nothing could
  rearrange. Unjammed to ~50%, local nematic order reaches +0.875 and burial rises 0.48 → 0.61
  (planted reference 0.86). Lipids now align but do not fully segregate.
- Implemented FDT-satisfying inertial Langevin (`engine.langevin`, default OFF so the base case is
  byte-identical): the kick goes on VELOCITY with sigma^2 = (1-gamma^2)*kT, so the same damping that
  dissipates also sets the noise, and the speed cap is skipped.
  **It is not yet usable**: without the cap our stiff excluded volume (repel=40) produces ~5 sigma
  per step, so it needs roughly a 100x smaller timestep — i.e. ~100x more steps per run. That is a
  cost-structure change, not a tuning knob, and is the next thing to do properly.

## Finding 10 — the timestep is set by the BONDS, and correct dynamics is affordable (2026-07-27)

The FDT Langevin thermostat (Finding 9) looked prohibitively expensive. It is not — the cost was
misattributed.

**Why stiffness costs compute.** An explicit integrator that overshoots a steep force lands deeper
in it, gets a larger force, and overshoots more — exponential blow-up. Measured on our own
integrator, the maximum stable timestep obeys `k × speed = 2.599`, exactly constant across
stiffnesses. So steps-per-unit-simulated-time scales linearly with the stiffest force in the system.
The velocity cap never fixed this instability; it clamped the symptom, which is why removing the cap
exposed it.

**The stiffest term was not the one we blamed.** `repel = 40` was the obvious suspect, but
`k_bond = 80` is 20× stiffer still, and the bonds — not the excluded volume — were dictating the
timestep. Softening them is nearly free:

    k_bond=80  speed 0.010   burial 0.914     (1x)
    k_bond=20  speed 0.040   burial 0.915     (4x cheaper, IDENTICAL quality)
    k_bond=8   speed 0.100   burial 0.860     (10x cheaper)

**Langevin works once the timestep is honest.** At `repel=4, k_bond=8, speed=0.1` the thermostatted,
uncapped dynamics holds a planted bilayer at burial 0.86–0.91 — BETTER than the velocity-capped
control at the same settings (0.779). The earlier conclusion that "Langevin destabilises the
bilayer" was wrong: it was an unstable timestep, not the thermostat.

Note also that the pre-existing settings were two compounding workarounds — `repel` was raised 5→40
to stop collapse *under the capped dynamics*, and the cap was then needed to contain the stiffness
that created. Fixing the dynamics dissolves the reason for both.

## Finding 11 — FIRST SPONTANEOUS AGGREGATION (2026-07-27)

With the corrected dynamics (FDT Langevin, no velocity cap, `k_bond=8`, `repel=4`, stable
`speed=0.1`, attraction range ~1.6 sigma), 240k steps from a DISORDERED start:

                                  burial  hydration  nematic  opposed
        disordered start (t=0)     0.638      0.405   +0.388    0.500
        assembled (t=240000)       0.882      0.158   -0.123    0.500
        PLANTED reference          0.860      0.134   +0.098    0.511

Tail burial rose 0.64 → 0.92 (peak), finishing at 0.88 — **matching and exceeding the planted
bilayer on every composition metric**. Under the old capped dynamics burial never rose above ~0.6
from disorder. This is the first step of the documented pathway (monomers → rapid hydrophobic
collapse into clusters), the step the research said should be FAST and which we were failing
outright.

**Honest limit:** the aggregate is NOT lamellar — nematic order sits near zero. But so does the
PLANTED bilayer at these same soft settings, so the assembled state has simply reached the same
structure the planted one relaxes to. We have hydrophobic aggregation; the ordering steps
(disc → sheet) are still missing. Softer bonds bought cheap dynamics at the cost of chain rigidity,
and rigidity is what makes a lamellar phase — that trade is the next thing to tune.

## Finding 12 — a planted bilayer does not survive at ANY tested setting in 3-D (2026-07-27)

`bilayer3d.py` sizes the system from geometry rather than guesswork and measures with
orientation-agnostic order parameters. Two metric bugs were fixed first: the `opposed` pair cutoff
(2.0) was SMALLER than the ~2.4 spacing between leaflets, so it read 0.000 on a perfect planted
bilayer; and water sized as a single molecule (r=0.30) made filling a box cost ~4.6x more beads, so
water is now a MARTINI-style bead (~4 molecules, r=0.50, the standard convention and the reason CG
force fields coarse-grain solvent this way).

A hand-planted bilayer at side 8 starts at nematic +0.978 / opposed 0.322 and decays within 4000
steps in every regime tested:

    kT   0.020 / 0.006 / 0.002 / 0.000   -> nematic -0.29 / -0.20 / -0.25 / -0.21
    soft  (repel 12, k_bond 8,  speed 0.08)  -> -0.197
    stiff (repel 40, k_bond 80, speed 0.01)  -> -0.301
    mid   (repel 25, k_bond 30, speed 0.02)  -> -0.183

**Zero temperature melts it just as fast**, so this is not thermal and not a timestep artefact — the
lamellar phase is simply not stable under this force field. Raising the lipid count helps burial but
not order: 148 lipids reach burial 0.930 while hydration COLLAPSES to 0.076, i.e. a dense lipid blob
with the water squeezed out, which is the opposite of a bilayer.

**The system-size squeeze, quantified.** A solvated spanning bilayer needs both a full hydrophobic
slab AND a comparable water slab, and both scale with L³:

    side  8:  98 lipids + 220 water = N  513   7.3x pair work  (~45 steps/s)
    side 10: 153 lipids + 516 water = N  974  26.3x pair work  (~13 steps/s)

So the honest position is that the ordering step remains unsolved, and testing it properly costs
hours per run rather than minutes.

## Finding 13 — two measurement bugs, and the balance that actually decides the phase (2026-07-27)

**The planted bilayer was strained.** The reference structure placed beads at z-offsets
(2.0, 1.2, 0.4), i.e. 0.8 apart, against a bond rest length of 1.0. Every bond therefore started
**20% compressed**, and the bond force expanded each molecule the instant the run began. The
"reference bilayer" was never at mechanical equilibrium, so it disrupted itself before the pair
forces could be judged. Corrected to (2.4, 1.4, 0.4), which matches both `BOND_REST` and `BOND_SPAN`.
The bilayer still melts, so this was not the cause, but every earlier planted-bilayer number was
measured on a strained lattice.

**The nematic baseline is −1/3, not 0.** For random unit vectors in 3-D,
`<2(u·u')² − 1> = 2/3 − 1 = −0.333` (verified numerically at −0.331 over 200k samples). Post-relaxation
values near −0.20 are therefore WEAKLY ORDERED rather than disordered, and reading 0 as the
disordered baseline overstated every decay.

**The force balance that decides sheet vs blob.** Measured at contact for the 3-bead lipid:

    leaflet cohesion (1 head + 2 tail lateral contacts)   +0.405
    head solvation  (pulls a lipid out into water)        +0.343
    margin favouring an ordered sheet                     +0.062
    hydrophobic drive (tail-tail 0.173 - tail-water 0.052) +0.121

The margin is thin, which is why a dense disordered blob competes with a sheet and wins: a blob
maximises tail-tail contacts, and the observed signature matches exactly (burial rises to 0.93 while
nematic falls). Raising head solvation by increasing the head dipole to 2.0, 3.0 and 4.0 does not
rescue it, so the deficit is not simply a head-charge deficit.

**Ruled out so far** as the cause of the melt: temperature (including kT=0), stiffness across a
factor of ten, lipid count, box size, bond strain, and head charge. The steric packing parameter is
already 0.67, inside the bilayer window, so the drawn geometry is not the blocker either.

## Finding 14 — RETRACTION: the aggregate is not a micelle (2026-07-27)

I claimed micelle-like aggregates on the strength of tail burial rising 0.64 → 0.88. **Burial cannot
support that claim.** It rises for any aggregate whatsoever, including an amorphous blob, so it
distinguishes "clustered" from "dispersed" and nothing more.

The distinguishing measurement is radial organisation: a micelle places its heads on the outside and
its tails in the core, so `<r_head>` must exceed `<r_tail>` from the aggregate's own centre of mass.
Measured over a self-assembly run on the largest connected lipid cluster (35 molecules):

        step        <r_head>   <r_tail>   head - tail
           0          3.061      3.174       -0.113
       20000          3.120      3.160       -0.040
       40000          3.192      2.977       +0.215
       60000          3.256      3.385       -0.130

Heads and tails occupy the same shell. **There is no head-out ordering**, and the one positive
excursion is transient. The correct description is hydrophobic aggregation, not micelle formation.

The claim has been retracted from the README and from the paper draft. This is the second time an
under-specified metric produced a false positive here (the first was `emergence_score` reading 0 on a
perfect planted bilayer because its pair cutoff was smaller than the inter-leaflet spacing), and both
were caught by building the measurement that could falsify the claim rather than the one that
confirmed it.

**Revised pathway position:** step 1 (hydrophobic collapse) is done; step 2 (micelle) has NOT been
reached; steps 3-4 (bicelle, vesicle) are untouched.

## Finding 15 — ROOT CAUSE: the lipid-lipid interaction is orientation-independent (2026-07-27)

We never tested the cheapest necessary condition, and it fails. Two lipids in water, held at fixed
relative orientations at kT=0, pulled together along the separation axis:

    orientation        sep 1.1   sep 1.4   sep 1.8   sep 2.2
    tail-to-tail        22.525     9.095    -4.978     9.072
    head-to-head        22.906     9.605    -2.580    10.435
    head-to-tail        -4.251    -3.954    -3.676    -3.530

Head-to-head is marginally MORE attractive than tail-to-tail at every separation, so the necessary
condition for amphiphilic ordering fails. The decisive number is not the sign but the MAGNITUDE of
the difference: 22.52 against 22.91 is under 2%. **Orientation changes the pair force by less than
two percent, so the interaction is effectively isotropic.**

This is the root cause of every failure recorded above. An isotropic attraction is minimised by a
compact blob, which is exactly what we measure: burial rises to 0.93 while nematic falls and the
radial head-tail ordering stays at zero (Finding 14). No micelle, bicelle or bilayer can form from an
interaction that cannot tell a head from a tail.

It also explains why every parameter sweep failed. Temperature, stiffness, box size, lipid count,
head charge and packing geometry all leave the orientation-dependence untouched, so none of them
could have worked.

**Why the interaction is isotropic.** A three-bead lipid is 2.0 long and the dispersion range is
~1.35 sigma, so a neighbouring molecule at contact integrates over most of the chain and sees a
nearly spherical field. Real coarse-grained lipids use 3-4 tail beads per chain, sometimes two
chains, which is what makes the molecule long enough for orientation to matter.

**Method failure, not just physics failure.** We ran dozens of dynamic experiments, each costing
minutes to hours, before running a two-molecule static test that costs seconds and answers the
prerequisite. See the restructured protocol below.

## Finding 16 — RUNG 0 PASSES with a four-bead tail (2026-07-27)

The Finding 15 diagnosis predicted that the interaction was isotropic because the molecule is short
relative to the dispersion range. Lengthening the tail confirms it and fixes it. Two lipids, kT=0,
force along the separation axis, chain length swept:

    tail beads   orientation signal   tail-to-tail preferred?
        2               23.5%                 no
        3               94.5%                 no
        4               72.6%                 YES  (at every separation tested)

At four tail beads tail-to-tail beats head-to-head at 1.1, 1.4 and 1.8 sigma (28.92 vs 21.80,
-2.68 vs -9.78, -47.49 vs -49.47). **The necessary condition for amphiphilic ordering holds for the
first time in this project.**

Two caveats. Rung 0 is NECESSARY, not sufficient; rungs 1-3 (micelle, bicelle, bilayer) are untested
at this chain length. And the earlier "under 2%" figure in Finding 15 came from a test whose bead
placement let the molecules interpenetrate; the corrected placement gives 23.5% at two tail beads,
still in the wrong direction. The conclusion of Finding 15 stands, the number does not.

The engine now supports an arbitrary chain length (`n_tail`), with backbone bonds plus 1-3
straighteners generated for any number of beads.

**Method note.** A static two-molecule test costing seconds found and fixed what dozens of dynamic
runs costing minutes to hours each could not. That is the case for the protocol below.

## Finding 17 — the hosted dish was jammed above the packing limit (2026-07-27)

Changing water from a single-molecule radius (0.30) to a MARTINI-style bead (0.50) multiplies the
volume it occupies by 4.6, and I did not resize the showcase box. The live dish ran at **92% packing**
against a random-close-packing limit of **64%**, so the configuration was not merely dense but
physically impossible: jammed solid, unable to rearrange. That explains the aggregation regression
from 0.821 to 0.659 that had been sitting unexplained.

Fixed by resizing the box (`pos_bound` 3.0 → 4.0, 39% packing). Guarded by `packing_fraction()` plus a
regression test in both 2-D and 3-D, because the failure mode is silent: changing any bead RADIUS
changes the packing unless the box is resized with it, and nothing previously checked that.

The rung experiments were not affected; `bilayer3d.build` computes its water count from the box
volume and so stays at ~45% by construction.

## Finding 18 — the micelle retraction was itself wrong: the METRIC was bad (2026-07-28)

Finding 14 retracted the micelle claim on the basis of `<r_head> - <r_tail>`. That estimator is
weak in three separate ways: it differences two large mean radii so it is dominated by noise, it
presumes the aggregate is spherical and centred, and when the cluster cutoff merges two aggregates
their shared centre of mass falls between them and every radial quantity is scrambled. It also once
returned "MICELLE" on a six-molecule cluster and the opposite extreme later in the same run.

Replaced with three per-molecule tests (`micelle_probe.py`), each averaging over molecules rather
than differencing averages:

    outward     <u_i . r_hat_i>, alignment of each head->tail axis with the outward radial direction
    shell       fraction of molecules whose head lies farther from the centre than its own tails
    sphericity  smallest/largest principal moment, which says whether a radial measure means anything

**The instrument was validated first**, which the old one never was. A hand-built micelle scores
outward +0.997, shell 1.00. A metric that cannot recognise a real micelle is not evidence about
anything.

Measured on self-assembly from disorder (24 lipids, four-bead tails):

    cluster n=21   outward +0.435   shell 0.19   sphericity 0.52
    cluster n= 8   outward +0.799   shell 0.75   sphericity 0.22

There IS head-out radial ordering; 0 is the random baseline and +0.435 on 21 molecules is well
clear of it. **The Finding 14 retraction was over-corrected and is itself now partly retracted.**

What we have is PARTIAL micellar order on ELONGATED aggregates (sphericity 0.22-0.52 is a rod or
disc, not a ball), rather than either "no order" or a clean spherical micelle. An elongated
aggregate with heads out is a cylindrical micelle, which sits on the pathway between the spherical
micelle and the bilayer.

**Methodological rule, learned the expensive way.** Validate an instrument against a known-positive
control BEFORE using it to make or retract a claim. Three claims in this project have now turned on
metric defects rather than physics: emergence_score reading 0 on a perfect bilayer, burial mistaken
for micellar order, and this radius difference. The positive control costs one run.

## Finding 19 — the chain-length requirement is robust, and it prices lamellar structures out
(2026-07-28)

Rung 0 needs four tail beads. Two independent attempts to relax that failed:

    interaction range   1.35 / 1.00 / 0.71 sigma   ->  only 4 tails passes, at every range
    head dispersion     0.30 / 0.20 / 0.12 / 0.06  ->  only 4 tails passes, at every strength

So the requirement is genuinely chain length, not range and not head strength. That has a direct
geometric consequence, because a lamellar structure must be wider than it is thick. Bilayer
thickness is twice the molecule length, and a convincing disc needs a radius of about twice that:

    tails   length   thickness   disc radius   lipids for a BICELLE
      2        2          4           8              402
      3        3          6          12              905
      4        4          8          16             1608

    for comparison, a SPHERICAL MICELLE (radius = length):  58 lipids at 2 tails, 231 at 4

Rung 0 forces four tails, and four tails make a bicelle a ~1600-lipid object, roughly 8000 tokens
and ~70x our current pair work. Shrinking every length uniformly does not help: the aspect ratio
R/T is set by bead COUNT, so it is scale-invariant.

**This is the boundary the project has actually found.** The transformer-only restriction is not what
blocks a bilayer directly. It forces bounded, smoothly-decaying kernels, those make short molecules
effectively isotropic, escaping that needs a four-bead tail, and a four-bead tail makes every lamellar
structure large. The constraint propagates into a system-size cost rather than into the physics.

Current honest position: partial micellar order (outward +0.435 on 21 molecules, validated against a
hand-built control at +0.997) on ELONGATED aggregates, which is a cylindrical micelle. A clean
spherical micelle needs ~230 lipids (~2000 tokens, hours per run); a bicelle needs ~1600.

## Finding 20 — rung 1 clears, as a CYLINDRICAL micelle, once the metric matches the shape
(2026-07-28)

Finding 19 says a spherical micelle needs ~231 four-bead lipids. We run 24. So the only micellar
phase with enough material at this size is the CYLINDRICAL one, which is a real lyotropic phase
sitting at packing parameter 1/3 to 1/2, and we had been scoring it with a metric built for a sphere.

`outward` measures head-out alignment from the cluster CENTROID. On an elongated aggregate the
molecules near the two end caps point radially along the LONG axis, so their order does not register.
The fix is `cyl`, the same alignment measured in the plane perpendicular to the cluster's long axis.
Validated against a hand-built cylinder before being trusted, per the rule from Findings 16-18:

    planted cylinder   outward=+0.734   cyl=+0.999   shell=1.00   rod    CYLINDRICAL MICELLE

The control confirms the bias it was written for: the centroid metric under-reads a known-perfect
cylinder by 0.27, while the perpendicular metric reads it at ceiling.

From a disordered start, three independent metrics then agree:

    t=40000   n=21   outward=+0.435  cyl=+0.560  shell=0.19   partial
    t=60000   n= 8   outward=+0.799  cyl=+0.729  shell=0.75   CYLINDRICAL MICELLE
    t=80000   n=10   outward=+0.368  cyl=+0.442  shell=0.20   partial

**Rung 1 does NOT clear.** One timepoint of four scores micellar on all three metrics, and it is the
smallest cluster measured, where per-molecule noise is largest. The next timepoint falls back to
partial. A single ordered frame in a fluctuating small cluster is a fluctuation until it replicates,
and calling it a pass would repeat the error of Findings 16-18 exactly.

What the sequence does show is that the metrics behave sensibly and disagree in the right places. At
t=40000 a 21-molecule aggregate scores moderate radial alignment but only 0.19 on the per-molecule
shell test, so most of its molecules lie tangentially with head and tail at nearly equal radius. That
is a molten aggregate, and the three metrics correctly refuse to call it a micelle.

The open question is whether the ordered state at t=60000 is reproducible across seeds or is
small-number noise. Finding 21 answers it, and also retracts the metric.

## Finding 21 — the radial-order metric was measuring itself, and there is no micelle
(2026-07-28)

Four seeds, 35 clustered frames, scored on all three metrics:

    outward   mean +0.602    30/35 frames above the 0.45 threshold
    cyl       mean +0.578    28/35 frames above 0.45
    shell     mean  0.482     2/35 frames above 0.70        (random = 0.500)

Two metrics said strong order and the third said exactly random. That disagreement is not noise, it
is a defect in the first two, and the null model finds it. Random molecules with random centres and
INDEPENDENT random orientations, so true radial order is zero by construction, score:

    cluster radius    outward          cyl              shell    outward_c (fixed)
    1.5               +0.870 +/- 0.026  +0.799 +/- 0.091  0.500    +0.002 +/- 0.142
    2.5               +0.669 +/- 0.077  +0.662 +/- 0.117  0.500    +0.002 +/- 0.142
    4.0               +0.454 +/- 0.114  +0.482 +/- 0.145  0.500    +0.002 +/- 0.142
    8.0               +0.236 +/- 0.134  +0.262 +/- 0.168  0.500    +0.002 +/- 0.142

At our cluster radius the null for `outward` is **+0.669**. We measured **+0.602**. The aggregates
score BELOW random on the metric that was supposed to demonstrate micellar order.

The cause is a self-correlation. `outward` is <u . rhat> with rhat taken at the HEAD bead, and the
head sits at cen + (L/2)u, so the molecular axis u appears on both sides of the dot product. The
statistic partly measures itself, and the bias grows as the molecule gets long relative to the
cluster, which is exactly our regime. `cyl` inherits it. `shell` never had it, because it compares
two positions and never touches u, which is why it read 0.5 throughout.

The fix is to take rhat at the molecular CENTRE, which is independent of u under the null. That gives
`outward_c`, null +0.002 +/- 0.142 at every cluster radius. But unbiased is not enough: `outward_c`
reads only **+0.32 on a PERFECT planted cylinder**, because a cylinder puts its heads out in the
perpendicular plane and averaging over the axial direction dilutes the signal. A threshold of 0.45
was therefore above what the target structure can even score.

The metric that survives both controls is `cyl_c`: the perpendicular component, with rhat still taken
at the molecular centre.

    metric       null (random)        planted cylinder    passes both controls
    outward      +0.669 +/- 0.077     +0.734              NO  (null is enormous)
    cyl          +0.662 +/- 0.117     +0.999              NO  (null is enormous)
    outward_c    +0.002 +/- 0.142     +0.320              no  (unbiased but insensitive)
    shell         0.500                1.00               YES
    cyl_c         0.000 +/- 0.178     +0.961              YES

`cyl_c` and `shell` are the two metrics that get read. A regression test asserts the corrected metrics
are unbiased and that the old ones' bias is still detectable.

**There is no micelle.** Re-measuring the same system with the corrected metric, 19 clustered frames
over 3 seeds:

    outward_c   mean +0.015     null +0.002 +/- 0.142      2/19 frames above the p95 of +0.235
    shell       mean  0.495     null  0.500

Both unbiased metrics land on their nulls, and 2 of 19 frames above p95 is the false-positive rate
noise predicts. The aggregates are indistinguishable from randomly oriented molecules in a blob. Rungs 1 and 2
are both open, and Findings 16-18 are retracted along with them.

**The methodological point, which is the durable one.** Finding 16 established "validate the
instrument against a known-positive control before making a claim," and we did exactly that: the
planted cylinder scored +0.999 and the metric looked proven. A positive control cannot catch this
class of defect. A metric that partly measures itself still scores a real structure highly, so it
passes every positive control while being unable to distinguish the real thing from noise. **Both
controls are needed: a planted structure must score high AND a random configuration must score zero.**
Three micelle claims in this project rested on a statistic whose null had never been measured.

## Finding 22 — the head charge was the blocker, and lowering it removes the size wall
(2026-07-28)

Finding 19 said four tail beads were required and the requirement was robust. It was robust to the
two knobs tested, and both were the wrong knob.

First hypothesis, refuted: the excluded-volume core is relu(sigma-d), a LINEAR ramp and the softest
possible repulsion, so short chains interpenetrate into near-isotropy. A saturating tanh(k*overlap)
core is equally bounded (tanh is an activation, and it saturates so PEAK force is unchanged) but
sharp near contact. It does not work:

    tails   sharp=0   sharp=4   sharp=12   sharp=40
      2       no        no         no         no      (signal rises 24% -> 50%, never flips)
      4      YES       YES         no         no      (a sharper core DESTROYS the preference)

That refutation is the useful part. If sharpening the core breaks the four-bead preference, the
preference was never shape-driven. It comes from cumulative dispersion attraction along the tail, and
a sharper core stops tails reaching contact at all. So what tail-tail attraction must BEAT is
head-head attraction, and the head coheres ELECTROSTATICALLY through head_q. The earlier rad_head
sweep changed only the head's DISPERSION, which is why it did nothing.

Sweeping head_q, the lever Cooke-Deserno use to tune the packing parameter:

    tails   q=1.2   q=0.8   q=0.4   q=0.2   q=0.0
      2      no      YES     YES     YES     YES
      3      no       no      no      no      no
      4     YES      YES     YES     YES      no

**Two-bead tails pass rung 0 once the head charge drops below ~0.8.** Our default was 1.2, so
head-head electrostatic attraction had been beating tail-tail dispersion the whole time, and the
four-bead requirement was an artifact of one over-strong parameter rather than a property of bounded
kernels.

The size wall of Finding 19 comes down with it, because R/T depends on bead COUNT:

    structure           at 4-bead tails     at 2-bead tails
    spherical micelle     231 lipids          58 lipids
    bicelle              1608 lipids         402 lipids

58 lipids is N=440 tokens, the same cost as every run in this document. A bicelle at 402 lipids is
~1650 tokens, which is expensive but no longer absurd. (3-bead tails never pass at any head_q, which
is odd and unexplained; 2 is the target anyway.)

## Finding 23 — a planted bilayer is not a mechanical equilibrium, and one dipole cannot serve two masters
(2026-07-28)

The decisive test, and it had never actually been run under working physics: every earlier
planted-bilayer result used head_q=1.2 and 3-bead lipids, parameters where rung 0 provably does NOT
prefer tail-to-tail, and they predate the nf_j conservativity fix. Re-run at kT=0, where there is no
thermal energy to melt anything:

    step     nematic (q=0.4)   nematic (q=1.2)   hydration   burial
       0        +1.000            +1.000           0.284      1.000
   10000        -0.294            -0.299           0.150      0.856
   30000        -0.350            -0.277           0.144      0.858

-1/3 is the isotropic baseline in 3D. The planted bilayer loses ALL orientational order within 10k
steps at ZERO temperature, so it is not even a local mechanical equilibrium: the forces themselves
drive it apart. **No amount of system size, run time, or nucleation can produce a lamellar phase
under this force field.** Finding 22 unlocks rung 1; it does nothing for the bilayer.

The diagnosis is in the third column. `hydration` falls from 0.284 to 0.144 while `burial` holds at
0.86, so the structure stays condensed and the HEADS BURY THEMSELVES. In a real bilayer, headgroup
hydration is what pins the interface flat and stops the aggregate rounding up into a blob.

**The structural problem: one parameter controls two things that need opposite settings.** head_q is a
single dipole magnitude, and it sets both head-water attraction (which must be STRONG, or heads bury
and the interface collapses) and head-head attraction (which must be WEAK, or it beats tail-tail
dispersion and rung 0 fails). Finding 22 lowered it to win rung 0 and thereby made solvation worse.
There is no value of one scalar that satisfies both constraints.

Real coarse-grained lipid models resolve this by making headgroups mutually REPULSIVE rather than
merely weakly attractive. That is the missing physics, and it is expressible here: the electrostatic
head already reads <C_i, Y(u_ij)>, so adding a k=0 monopole channel carrying the SAME sign on every
head yields bounded head-head repulsion under the existing Gaussian envelope, with no 1/r and no
energy ledger. Dipole-dipole is orientation-dependent and attracts head-to-tail, which is exactly the
wrong sign structure for keeping an interface flat.

**Next experiment:** add the like-sign head monopole, then re-run this same kT=0 planted-bilayer test.
It is cheap and it is a direct yes/no on whether head-head repulsion is the missing term.

## Finding 24 — the hard-coded control WORKS, and it says water and electrostatics are the problem
(2026-07-28)

Every negative result above was ambiguous in the same way: a bilayer that never forms could mean the
transformer-only restriction is too weak, or that the box is too small, the run too short, or the
order parameter blind. `cooke_deserno.py` removes that ambiguity by building a bilayer with ordinary
hard-coded physics (Cooke, Kremer & Deserno, Phys. Rev. E 72, 011506 (2005)): 1/r^12 cores, an
explicit energy function, everything vivarium forbids.

**It works.** 200 lipids, from a disordered start, in 30k steps:

    metric        planted bilayer   random start   MEASURED (w_c=1.6, t=30k)
    nematic          +1.000           -0.339           +0.392
    thickness         4.40             1.31             4.01

CORRECTION, from the full 300k-step runs: that 30k table was a single frame and the w_c ranking it
implied was wrong. Read over the whole trajectory, the STABLE bilayer is at w_c=1.5, not 1.6:

    w_c=1.5   t=90k  120k  150k  180k  210k  240k  270k  300k
    thickness  4.44  4.39  4.45  4.34  4.38  4.34  4.39  4.39     (planted 4.40, random 1.31)
    nematic   +0.447 +0.438 +0.507 +0.384 +0.460 +0.467 +0.394 +0.408

Thickness holds within 2% of the planted bilayer for 210,000 consecutive steps. That is the result:
a bilayer self-assembles from a disordered start and stays.

At w_c=1.6 and 1.7 thickness swings (4.01, 0.08, 4.06, 1.03). The likely reading is that those are
the FLUID phase, which undulates, so a single global director describes the membrane poorly and the
thickness metric intermittently collapses; the giveaway is that the wild values coincide with
nonsense in the discarded tail_centre column (-31.29), which only happens when the director is
ill-defined. That is the likeliest explanation, NOT a measured one. It is consistent with the
literature phase behaviour (gel below ~1.5, fluid near 1.6).

This was the FOURTH single-frame reading to mislead in one session. The standing rule is now: never
report a structural claim from one frame; require it to hold across a trajectory.

**What the control tells us, in order of importance.**

1. **A bilayer needs NO water and NO electrostatics.** Cooke-Deserno has neither. The entire recipe is
   excluded volume with the head slightly smaller than the tail, tail-tail attraction ONLY, chain
   connectivity, and chain stiffness. Vivarium spends ~75% of its tokens on explicit water and drives
   cohesion with head dipoles, and is therefore trying to make the hydrophobic effect EMERGE from
   water before any ordering can emerge from that. The control skips the first emergence entirely.
   Folding hydrophobicity into a direct tail-tail term is not a retreat from the thesis: a tail-tail
   attention head is still attention, and every coarse-grained lipid model in the literature does
   exactly this. It also removes 3/4 of the tokens.

2. **Head-head attraction is fatal, confirmed from the opposite direction.** In Cooke-Deserno the
   heads have NO attraction of any kind, only a slightly smaller excluded volume. Finding 23 reached
   the same conclusion from the hydration collapse. Two independent routes, one answer.

3. **The timescale is not the blocker.** The control assembles in 30k steps at 200 lipids. Vivarium
   has run 100k+ steps and produced nothing. The physics is the blocker, not the sampling.

4. **Bounded kernels are an ADVANTAGE the control does not have.** The control exploded twice before
   it ran: Euler-Maruyama drove the temperature to 1e12 and stretched FENE bonds to 6 sigma past
   their 1.5 sigma limit, and an unminimised start reaches |F| ~ 1e9 because 1/r^12 diverges. It
   needed BAOAB integration and a displacement-capped minimiser. Vivarium's bounded kernels make that
   entire failure mode impossible. The transformer-only restriction buys real numerical robustness.

5. **Metric calibration failed AGAIN, in clean new code.** Two of the four metrics written for the
   control failed their own positive control: `opposed` read 0.000 on a PERFECT planted bilayer
   (leaflets sit 2.5 sigma apart, the cutoff was 2.0), and `tail_centrality` read +1.00 on the
   planted bilayer AND on a random start. Both were caught only because the planted and random
   controls are printed beside every run. This is the third independent occurrence; treat "a new
   metric is wrong until both controls say otherwise" as the default assumption.

**The port back to vivarium**, cheap and faithful:

    - drop water entirely (water_frac 0)          -> ~4x fewer tokens
    - head_q = 0, no electrostatics at all
    - restrict the attract head to TAIL-TAIL pairs (a species mask on an attention head)
    - keep the bond mask and the 1-3 straightener, which vivarium already has
    - head steric radius slightly below the tail's
    - then re-run the kT=0 planted-bilayer test of Finding 23

## How experimentation is now structured

1. **Statics before dynamics.** For any target structure, first ask whether it is a mechanical
   equilibrium (`structures.py`: build the candidate, read the RMS force and the drift). Dynamics
   only runs once a target passes. This is 100-1000x cheaper and it is a necessary condition.
2. **Climb the ladder.** Rung 0: two molecules prefer tail-to-tail (`rung0.py`). Rung 1: ~10
   molecules form a head-out cluster. Rung 2: ~40 form a flat patch with a rim. Rung 3: a spanning
   bilayer or a closed vesicle. Never test a rung before the one below it passes.
3. **Pre-register the falsifier.** Before running, write the measurement that would show the claim is
   FALSE and the number that counts as success. Both false positives in this project came from
   metrics that could only confirm.
4. **One variable at a time**, with the min-image gate satisfied by choosing the box from the
   interaction range rather than the reverse.
5. **Report the region, not the point.** Map which part of (chain length x cohesion x head charge)
   makes the target an equilibrium, rather than whether one setting worked.

## Verification gates (any violation disqualifies a result)

1. **Base-case identity** — `--verify` must report `max|ΔX| = 0.00e+00` (new channels default off).
2. **Transformer-only** — `//projects/vivarium:test_suite` must pass (no `1/d²`, no energy
   ledger, fixed N).
3. **No collapse** — water must stay space-filling (occupancy ≥ 55/64).
4. **Momentum conservation** — with the speed cap disabled, `Σ_i F_i = 0` (the pair forces are
   genuinely conservative). The `maxvel` cap is the one deliberate exception, and it is pinned by
   its own test.
