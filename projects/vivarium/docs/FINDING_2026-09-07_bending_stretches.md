# The bending "fix" inflates the molecule; it does not stiffen it

**Verified independently 2026-09-07** — analytically and against the shipped `Field`.

## The defect

The 1-3 stiffener and the 1-2 bonds share a spring constant (`field.py:563`,
`k_bend = k_bond * bend_frac`, `bend_frac` default 1.0). For a straight 3-bead chain with bond length
`b`, the energy is

    E(b) = k (b-1)^2 + (k/2) (2b - r0)^2      ->      b* = (2 + 2 r0) / 6

| `bend_r0` | predicted `b*` | measured on the shipped Field | molecule length |
|---|---|---|---|
| 2.0 (the default) | 1.0000 | **1.0179** | 2.0 sigma |
| **4.0 (the "fix")** | **1.6667** | **1.6654** | **3.33 sigma** |

`b*` is independent of `k`. **Setting `bend_r0 = 4.0` stretches every bond by 67%.**

## Why Cooke-Deserno can do this and we cannot: FENE

Cooke's bonds are **FENE** -- they diverge at `R_inf = 1.5 sigma` and are effectively inextensible.
A pre-stretched 1-3 spring therefore has nowhere to go but *straighten the chain*, which is the entire
point of the pre-stress. Its stiffener sits in permanent tension against a bond that cannot yield.

Our bonds are **harmonic and infinitely extensible**. The same stiffener does not straighten the
molecule; it inflates it. The mechanism the fix was copied from does not transfer, and
`docs/DEEP_RESEARCH_2026-08-31.md` had flagged the gap without resolving it: *"The literature does NOT
answer FENE-vs-harmonic for membrane (as opposed to numerical) stability."* It does here, and the
answer is that FENE is what makes a pre-stretched stiffener a bending term rather than a stretching one.

## Consequence 1: the headline 3-D thickness claim compares two different molecules

`bilayer_metrics.thickness` is head-sheet separation, so it scales with molecule length. On an ideal
flat bilayer built at each bond length:

| bond | molecule length | `thickness` reads |
|---|---|---|
| 1.0000 | 2.00 | 5.00 |
| **1.6654** | **3.33** | **7.66** |

The Amendment-3 closure run measured **4.14** and reported it as *"103% of reference (4.05)"*. But
4.05 is the ORACLE's value, for the oracle's ~1.93 sigma molecule, while those runs used
`bend_r0 = 4.0` and therefore a **3.33 sigma** molecule, whose proper bilayer reads **7.66**.

**4.14 is 54% of its own molecule's bilayer, not 103% of anything.** That is what heavy interdigitation
or strong tilt looks like. Gate B's "min thickness 2.87 (holds)" is 37% on the same basis.

## Consequence 2: the k_theta sweep held the deformation exactly constant

Amendment 4 swept `k_theta` in {10, 20, 33} to test bending stiffness as a closure lever. Since
`b* = (2 + 2 r0)/6` is independent of `k`, **every arm had the identical 67% stretch**. The sweep
varied stiffness while holding the deformation fixed, so it could not have separated the two.

## What this does NOT overturn

**The 2-D emergent vesicle stands.** No committed file sets `VIVARIUM_BEND_R0`, so every 2-D result on
disk -- including the confirmed seed-509 vesicle -- ran at `bend_r0 = 2.0`, i.e. with a molecule at its
natural 1.02 bond length and **near-zero harmonic bending stiffness**. That is worth stating positively:
**2-D vesicle formation does not require chain bending stiffness.** The defect is confined to the
configurations that set `bend_r0 = 4.0`, which are the 3-D ones.

## The fix

Replace the harmonic 1-2 bond with FENE, or cap it, so the stiffener straightens rather than stretches.
Then re-measure: the 3-D "membranes now work" result needs re-deriving with a molecule of the intended
length, and the thickness reference must be computed for the molecule actually in the box.
