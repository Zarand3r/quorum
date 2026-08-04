# Research handoff: spontaneous membrane self-assembly in a bounded-kernel particle model

**For:** an agent doing literature research and physical reasoning.
**Not needed:** the codebase. This document is self-contained and deliberately free of implementation
detail. What is wanted back is physics and literature, not code.

---

## 1. What we are trying to do

Build a molecular self-assembly simulator in which **every force is an attention operation** — the
same primitive a transformer uses — and then see whether a **lipid membrane assembles itself** out of
nothing but those forces. The target sequence is the one nature takes:

    disordered amphiphiles in water
        -> micelles                    (hydrophobic collapse)
        -> finite bilayer patches      (lamellar order appears)
        -> a closed vesicle            (the patch curves and seals)

The scientific interest is whether **membrane self-assembly is reachable under a hard architectural
constraint** that ordinary molecular dynamics does not obey. If it is, a membrane becomes an emergent
property of a transformer-shaped system rather than of hand-written potentials.

### The constraint, and why it is not cosmetic

Standard MD uses divergent potentials — Lennard-Jones repulsion goes as `1/r^12`. Divergence is what
makes excluded volume *absolute*: however strong the attraction, at short range repulsion always
wins, so two atoms can never occupy the same place.

Attention kernels are **bounded**. A force built from `softmax`-weighted contributions with a
`exp(-lambda * d^2)` envelope has a **finite maximum**. This has a direct physical consequence we
have measured: pairwise repulsion is capped while attraction **sums over neighbours**, so with enough
neighbours the sum exceeds the cap and particles pass through one another. We call this collapse, and
it silently produced several false results before we could detect it.

So the project is really asking: **can a bounded-force system express the physics that a divergent
one gets for free?**

---

## 2. The model, conceptually

- **Amphiphile:** a coarse-grained molecule of one hydrophilic **head** bead and two hydrophobic
  **tail** beads, connected by bounded springs, with a stiffening term that keeps it extended.
  (Measured: the chains are fully extended, end-to-end = contour length. Floppiness is not a factor.)
- **Solvent:** explicit water beads. This is mandatory, not optional — see §3.
- **Forces, all bounded and all attention-shaped:**
  - Pauli exclusion / excluded volume (shortest range)
  - van der Waals cohesion, with species-dependent strength
  - electrostatics via a polar head
- **Both 2-D and 3-D** versions exist. In 2-D a "bilayer" is a double *row* of molecules; in 3-D it is
  a *sheet*. These turn out not to behave the same, which is itself a finding (§5).
- Periodic boundaries. Overdamped Langevin dynamics.

---

## 3. The physics we are reasoning with

### Packing parameter (Israelachvili)

The classical selector of amphiphile phase:

    P = v / (a0 * l)

with `v` the tail volume, `a0` the head cross-sectional area, `l` the tail length.

    P < 1/3       spherical micelles
    1/3 .. 1/2    cylindrical micelles
    1/2 .. 1      BILAYERS
    P > 1         inverted phases

Our molecule sits in the micellar regime, and we have reproduced the full progression by varying head
size: wide head -> micelles, narrow head -> inverted structures (tails outward, heads buried). **The
system steps over the bilayer window rather than passing through it.**

### Edge energy and closure

A finite bilayer patch exposes hydrophobic tails along its rim, costing

    G_edge = 2 * pi * R * gamma

with `gamma` the line tension. Closing the patch into a vesicle eliminates the rim but pays Helfrich
bending energy. Closure wins above a critical radius

    R_crit ~ (4 * kappa_c + 2 * kappa_bar) / gamma

This is why **bulk water yields vesicles, not flat sheets** — every biological membrane is a closed
surface, and a flat bilayer in the laboratory requires a substrate (supported bilayers) or, in
simulation, periodic boundaries that remove the rim by wrapping.

### Solvent is required

Without explicit solvent there is no hydrophobic effect, so `gamma = 0`, so `R_crit -> infinity` and
closure is impossible in principle. Any solvent-free run is incapable of demonstrating a vesicle
whatever else it computes.

### Mixing rules cannot express hydrophobicity

With Lorentz–Berthelot (geometric) mixing, the cross-interaction is `sqrt(eps_ii * eps_jj)`. By
AM–GM, the *contrast* `(eps_ii + eps_jj)/2 - sqrt(eps_ii * eps_jj) >= 0` and is largest when one
species is WEAK. A geometric mixing rule therefore cannot produce the strong self-affinity /
weak-cross-affinity structure that hydrophobicity requires. We replaced it with an explicit
species-pair interaction matrix.

---

## 4. What has been achieved (measured, with controls)

Every metric below is calibrated against **both** a planted positive control **and** a random null —
a discipline adopted after roughly twenty measurement defects, most of which were metrics that
returned "success" for everything.

| stage | 2-D | 3-D |
|---|---|---|
| micelles from disorder | **achieved** | **achieved** |
| finite bilayer patches | **achieved** | not reached |
| spanning bilayer | phase is **stable**, not self-assembled | phase is **unstable** |
| closed vesicle | phase is **stable**, not self-assembled | not reached |

Key measured facts:

- **Micelles self-assemble from a fully dispersed random start** in both dimensionalities, matching
  purpose-built planted references on packing, bond integrity, and orientational order.
- **Finite bilayer ribbons self-assemble in 2-D** and persist over 130,000 steps.
- **A planted spanning bilayer in 2-D is stable and even orders further** over time.
- **A planted vesicle in 2-D is stable and orders further** over 20,000 steps.
- **In 3-D the lamellar phase genuinely melts** at every head size once excluded volume is enforced —
  this is not a collapse artifact; it was checked with packing held healthy.

An important asymmetry: 2-D and 3-D differ, and there is a plausible reason. Each particle has ~6
neighbours in 2-D against ~12 in 3-D, so summed attraction per particle roughly doubles, and the
threshold at which bounded repulsion is overwhelmed does not transfer between dimensionalities.

---

## 5. Where we are stuck

**In 2-D, self-assembly condenses correctly but will not adopt an extended membrane geometry.**

    all lipids end in ONE connected aggregate          (yes)
    excluded volume healthy, no interpenetration       (yes)
    aggregate covers 64-73% of the box                 (need >80% to span)
    internal lamellar order plateaus                   (roughly half what a planted bilayer achieves)

The aggregate is a **compact blob with partial internal order**. It neither flattens into a spanning
sheet nor curves closed into a vesicle. Both remaining stages need the same thing, and the same blob
fails both.

Levers tried, all of which failed to move it:

- more material (worse — excess forms defects rather than filling gaps)
- stronger or weaker excluded volume (trades phase stability against assembly speed)
- **simulated annealing** (actively worse than constant temperature)
- smaller container (produced apparent spanning that turned out to be a metric artifact — in a small
  box any large aggregate covers most of the width)
- longer runs (order plateaus and stops improving)

### Our current hypothesis, which is reasoning and not measurement

For a **finite** aggregate, a compact shape has less perimeter than an extended one of equal area —
in 2-D, a disc of area 100 has perimeter ~35 against ~50 for a 5-thick ribbon. So the blob may be
genuinely *preferred*, not merely kinetically trapped, unless the molecule's geometry makes the
compact state unavailable. Our molecule forms micelles readily, so the compact state is always
available to it.

If that is right, the obstacle is thermodynamic and no kinetic intervention will help — consistent
with annealing making things worse rather than better.

### The parameter we have never varied

Our cohesive force has an envelope `exp(-lambda * d^2)`; `lambda` sets the **range** of attraction and
has been held fixed for the entire project. We have varied depth, head size, tail count, temperature,
concentration, container size and cooling schedule — **never the range**.

This looks like a serious omission, because in the canonical minimal membrane model (Cooke–Deserno,
solvent-free coarse-grained lipids) the tunable **attraction range** is precisely the parameter that
governs whether a fluid bilayer forms at all.

---

## 6. What we would most like the literature to tell us

In rough order of value:

1. **In minimal coarse-grained amphiphile models, what actually selects a bilayer over a micelle?**
   Specifically the numbers, not the rule: what ratio of attraction range to particle diameter, and
   what head:tail size ratio, are known to produce a lamellar phase? Cooke–Deserno's phase diagram in
   their range parameter would be directly usable.

2. **Can a bounded, non-divergent interaction support a lamellar phase at all?** Is there any
   published model — Gaussian-core, soft-sphere, dissipative particle dynamics, or similar — that
   forms bilayers *without* a divergent short-range repulsion? DPD is the obvious candidate since it
   uses soft, bounded repulsions; does it form membranes, and if so what does it need? This is the
   single most decisive question for the project, because a negative answer would mean the
   architectural constraint and the target are incompatible.

3. **Is "the aggregate condenses into a blob and will not flatten" a known obstacle?** How is the
   micelle -> bilayer transition actually crossed in simulations that succeed — spontaneously,
   by seeding, by composition change, or is the bilayer simply the *first* structure formed under the
   right parameters, never passing through a compact intermediate?

4. **How is a vesicle actually nucleated in simulation?** Does a patch grow and then close, or does
   closure happen at small size? What sets the crossover in practice as opposed to in the Helfrich
   formula?

5. **Does 2-D membrane self-assembly transfer to 3-D?** We have preliminary evidence it does not, but
   the underlying physics differs in ways that may be well characterised: edge dimensionality (a 3-D
   rim costs `2*pi*R*gamma` and grows with size; a 2-D "rim" is two endpoints at constant cost), and
   Mermin–Wagner fluctuations in 2-D. Is a 2-D amphiphile model considered a valid proxy for 3-D
   membranes anywhere in the literature, or is it understood to be a different problem?

6. **Aggregation number.** Is there a standard relation predicting preferred aggregate size from
   molecular geometry, which would tell us whether our aggregates are stalling at their
   thermodynamically preferred size rather than being trapped?

### Suggested searches

- `Cooke Deserno solvent-free coarse-grained lipid model tunable attraction range bilayer self-assembly`
- `dissipative particle dynamics soft repulsive potential spontaneous bilayer vesicle formation`
- `coarse-grained amphiphile phase diagram micelle cylinder bilayer packing parameter simulation`
- `minimal model spontaneous vesicle formation from micelles molecular dynamics nucleation pathway`
- `Gaussian core model / soft matter bounded potential lamellar phase`

---

## 7. Caveats on everything above

This project has found roughly **twenty measurement defects**, and in nearly every case the model was
healthier than the instruments claimed. Metrics that returned identical values for a perfect membrane
and a random gas ran for weeks before being checked against a null. Several confident structural
claims were later retracted.

So: the *measured* facts in §4 have been calibrated against positive and null controls and are
reasonably trustworthy. The *hypothesis* in §5 — that a compact blob is thermodynamically preferred —
is reasoning from a perimeter argument and has **not** been measured. Treat it as the thing most
likely to be wrong, and worth checking against the literature first.
