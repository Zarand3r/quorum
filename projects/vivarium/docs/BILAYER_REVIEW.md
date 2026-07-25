# Rigorous review: why bilayers have not emerged

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

## Verification gates (any violation disqualifies a result)

1. **Base-case identity** — `--verify` must report `max|ΔX| = 0.00e+00` (new channels default off).
2. **Transformer-only** — `//projects/vivarium:test_suite` must pass (no `1/d²`, no energy
   ledger, fixed N).
3. **No collapse** — water must stay space-filling (occupancy ≥ 55/64).
