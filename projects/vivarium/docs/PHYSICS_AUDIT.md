# Physics audit: new field vs pre-oracle engine vs the YLZ oracle

**Date:** 2026-08-17. Read from source: `field.py`, `pack.py`, `polar_pack.py`, `ylz.py`, `bilipid.py`.

The question is not which model is nicer but which is FAITHFUL. Where the three disagree, the audit
asks what a coarse-grained lipid force field is required to have, and records who has it.

---

## 1. Side by side

| | pre-oracle `pack.py` | new `field.py` | oracle `ylz.py` / `bilipid.py` |
|---|---|---|---|
| defined by | forces, assembled by hand | **one scalar energy**, forces = `-dU/dX` | one scalar energy, analytic gradient |
| gradient checked | no `energy` method exists | **1.5e-07** | 1.2e-08 |
| excluded volume | `clip(contact - r, 0)`, optional `tanh` | quadratic in overlap, bounded | bounded `k(rmin-r)^2`, or divergent `r^-4` |
| core is | ORIENTATION-DEPENDENT (contour) | isotropic, one `sigma` | isotropic, one `sigma` |
| attraction | Gaussian envelope used AS the force | cosine well, min at contact | `-eps cos(...)^{2 zeta}`, min at `rmin` |
| chemistry | species `eps_pair` matrix | species `chi` matrix, factored as `q.k` | none needed (implicit solvent) |
| solvent | explicit water | explicit water | **implicit** |
| orientation term | `nematic` (u.u)^2 | **none, deliberately** | full `a = q + beta p - beta^2` |
| chain bonds | 1-2 harmonic **and 1-3** (`bend_frac`) | **1-2 harmonic only** | 1-2 harmonic only |
| thermostat | OU, `sigma^2 = (1-gamma^2) kT` | overdamped Brownian, `sqrt(2 kT dt/gamma)` | exact OU |

The first three rows are where the new field is clearly better: it has an energy, its forces are that
energy's gradient to 1.5e-07, and its core is isotropic rather than depending on a learned contour.
The last two rows are where it is clearly WORSE, and they are the subject of this audit.

## 2. Defect 1 -- the lipid has no bending stiffness at all (SEVERE)

`polar_pack.py` builds **1-3 bonds** at `bend_frac = 1.0` of `k_bond`, i.e. the pre-oracle lipid has an
explicit tail stiffness. `field.py` builds only consecutive 1-2 bonds:

    bonds = [[idx[b], idx[b + 1]] for b in range(t)]

so its tail is a FREELY JOINTED chain with zero persistence length. No coarse-grained membrane model
works this way. Cooke-Deserno, MARTINI and every relative include an angle or 1-3 term, because a
membrane's bending rigidity `kappa` comes from exactly two places: chain stiffness, and
orientation-dependent interactions.

**`field.py` has neither.** The orientation term was deliberately omitted so spontaneous curvature
could not be imported, and the chain term was omitted by oversight. A membrane with `kappa ~ 0` cannot
hold a curved shape -- it crumples -- which is what the 3-D vesicle did: shell CV rose 0.136 -> 0.282
while staying connected, i.e. the shell stayed intact and lost its SHAPE. That is the signature of
missing bending rigidity, not of a collapsed aggregate.

This is the most likely single cause of every 3-D failure, and it predicts the 2-D survival too: a
2-D ring is a curve whose "bending" is resisted by in-plane packing, so it needs far less `kappa`.

## 3. Defect 2 -- bonded pairs are not excluded from non-bonded forces (MODERATE)

`field.py` builds its neighbour list over all pairs within the cutoff and adds bonds on top, with no
exclusion list. So a bonded 1-2 tail pair feels the harmonic bond AND the full `chi_TT = 1.0`
attractive well. Standard practice excludes 1-2 (often 1-3) neighbours from the non-bonded term
precisely because that interaction is already represented by the bond.

Consequence: an extra attraction along the backbone that shortens and stiffens the chain in an
uncontrolled way, and makes the measured `a` and `d` in `_sizing3d` not quite the intended lipid's.

## 4. Defect 3 -- the chemistry matrix inverts the hydrophobic effect (MODERATE)

`field.py` uses `chi_TT = 1.00`, `chi_WW = 0.40`, `chi_TW = 0.00`.

Demixing is fine: `chi_TW = 0 < (chi_TT + chi_WW)/2 = 0.70`, so the exchange parameter is positive and
tails and water separate. But the ORDERING is backwards. In real coarse-grained force fields water is
the strongest cohesive species -- MARTINI water-water sits above alkane-alkane -- because the
hydrophobic effect is driven by water's self-attraction squeezing oil out, not by oil being sticky.

This project already documented that exact error. `pack.py` carries a comment saying geometric mixing
"CANNOT express hydrophobicity" because it only offers "oil is sticky ... which is why `edge` stayed at
1.00 (wet cores)", and `polar_pack.py` states the intended ordering: "water-water is held by
electrostatics, oil-oil by dispersion, and water gains little from wetting a nonpolar surface".
`field.py` then reintroduced the inverted ordering in a new form.

Consequence: a weakly cohesive solvent exerts little lateral pressure on the membrane and provides
little osmotic support to a lumen -- which is the same failure the 3-D lumen showed.

## 5. Defect 4 -- we have been running twice as hot as the oracle (MODERATE)

Both models put the attractive well at depth `eps` and use a bounded core, so the two dimensionless
ratios that govern behaviour are directly comparable:

| ratio | oracle (`bilipid.py`) | new field |
|---|---|---|
| core height / kT | 30 / 0.1724 = **174** | 60 / 0.35 = **171** |
| well depth / kT | 1.0 / 0.1724 = **5.80** | 1.0 / 0.35 = **2.86** |

The cores match almost exactly. The COHESION does not: relative to thermal energy our well is half as
deep. Aggregation and coarsening depend on this ratio roughly exponentially, so a factor of two is
large, and it matches what was observed -- lipids that condense into many small aggregates and never
ripen into one, at every concentration tried.

## 6. What is faithful

Worth stating, because most of the physics is sound.

* Forces are the gradient of a scalar (1.5e-07), so no energy/force inconsistency is possible. The
  pre-oracle engine has no energy function at all and assembles forces by hand.
* Newton's third law holds pairwise; net force is zero to 1e-9.
* The thermostat satisfies fluctuation-dissipation in all three models.
* Rotation and translation invariance under the periodic box are tested.
* The core is bounded, isotropic and one length scale, matching the oracle's bounded variant.
* Excluded volume is real: beads sit at 0.95-0.99 of contact, against 0.15-0.36 before.
* The species matrix is the right mechanism for hydrophobicity (MARTINI does the same); only its
  VALUES are wrong, per defect 3.
* The measured area per lipid, 1.36-1.40 sigma^2, is close to the oracle's 1.50 -- so the lipid is
  dimensionally sane even with the defects above.

## 7. What the oracle has that we deliberately do not

The YLZ orientation term. It is what gives that model its bending rigidity AND its spontaneous
curvature, through one parameter `beta` whose optimum sits at `sin(theta*) = -beta`. Measured here:
`beta = 0` gives 0 vesicles in 1.5M steps, `beta = 0.15` gives 3-4.

Omitting it is the right call for a bottom-up model, since importing it imports the answer. But the
omission has a consequence that was not thought through: **it removed one of the only two sources of
bending rigidity, and defect 1 removed the other.** The fix is not to restore `beta` -- it is to
restore chain stiffness, which is a property of the MOLECULE rather than a preferred curvature of the
membrane, and which every serious coarse-grained lipid model has.

## 8. Fixes, in priority order

1. **Add 1-3 bonds (or an angle potential) to the chain.** Restores `kappa` from molecular geometry
   with no preferred curvature. This is the one that plausibly changes the result.
2. **Exclude 1-2 pairs from the non-bonded term.**
3. **Reorder `chi` so water is the most cohesive species**, keeping the demixing condition satisfied.
4. **Run at the oracle's reduced temperature**, `kT/eps ~ 0.17`, or deepen the well to match.

1 and 2 change the molecule, so `_sizing3d` must be re-measured after them and every sizing derived
from it recomputed.
