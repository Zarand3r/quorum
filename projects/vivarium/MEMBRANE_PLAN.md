> **SUPERSEDED (2026-07-25)** — by the three-fundamental-forces approach in
> [`docs/BILAYER_REVIEW.md`](docs/BILAYER_REVIEW.md): everything must emerge from **Pauli exclusion
> + van der Waals + electrostatics** only, with the **k=0 radius channel** (bulk separated from
> charge) and **contact-area, charge-independent vdW**. The explicit per-species lipid force laws
> (`k_hydro` / `k_tail`, the `LIPID` rod) are **retracted**. Kept for the record.

# Membrane self-assembly — working plan (Path A: emergent, no dictated bonds)

**Goal:** amphiphilic tokens **self-assemble into a bilayer / membrane** from local *laws only* —
no dictated bonds, no multi-bead molecules. Success declared by the user's eye; a **membrane metric**
(built and validated first) provides trustworthy corroboration.

## Hard requirements
- **Transformer-only** — interaction = attention (content + relative-bearing bias) + structured
  linear readouts + normalization. No hand force kernels beyond what `pack` already established, no
  ledgers, no global terms.
- **No dictated binding** — we specify *laws* (anisotropic affinity = the hydrophobic effect) and
  *reagents* (assign species at init = "what's in the beaker"). We never specify which token binds
  which, nor any fixed intramolecular bond. Membrane = emergent product.
- **Fixed N**, **measure-don't-reward** (the metric never feeds the update; tuning a physical knob
  to find a regime is allowed).

## The law (single-token amphiphile, hydrophobic effect)
Each token: position `p`, and (lipids only) an **orientation** `o` (unit 2-vector) — a
*grounded, dynamic* head↔tail axis. Species (water / lipid) is a **protected channel** set at init.

Anisotropic hydrophobicity presented by `i` toward neighbour `j` (bearing `r̂_ij`):
- water: `φ_i(j) = −1` (hydrophilic, isotropic)
- lipid: `φ_i(j) = tanh(β · o_i·r̂_ij)` (+1 toward tail `+o`, −1 toward head)

Pair affinity `a_ij = φ_i(j)·φ_j(i)` ∈ [−1,1]: tail–tail → +1 (attract), tail–water → −1 (repel),
head–water → +1 (attract), water–water → +1. **This is the hydrophobic effect**, and it drives
tails-together / heads-to-water → micelle/bilayer.

Dynamics (all attention-weighted aggregation over k-NN, like `pack`):
- **position:** `F_i = Σ_j a_ij · r̂_ij` (attract if a>0, repel if a<0) + soft steric repel; momentum,
  velocity cap, torus wrap.
- **orientation (torque):** rotate `o_i` toward `Σ_j φ_j(i)·r̂_ij` (point tail toward hydrophobic
  neighbours, away from water); renormalize.

Transformer-faithful framing: `a_ij` is an attention score bilinear in per-token orientation
*queries* and relative *bearing* (a RoPE/relative-position-attention-family variant); motion/torque
are attention-weighted sums of relative vectors.

## The metric (Phase 0 — build & validate FIRST, against the eye)
- **H (hydrophobic shielding)** — mean over lipids of the lipid-fraction of the tail-side
  neighbourhood. `H→1` = tails buried = *assembled*. THE "did it self-assemble" signal.
- **sheetness** — largest lipid cluster's position-covariance aspect ratio: micelle ≈ 1, bilayer
  ribbon ≫ 1. Separates "membrane" from "ball".
- **(stretch) closure** — a bilayer loop enclosing water = vesicle.
Validated on hand-placed fixtures (bilayer / micelle / mixed / separated) so the numbers provably
match what the eye sees before we trust them to tune.

## Phases
0. Metric + fixtures (trust first). 1. Engine (species + hydrophobic law + orientation). 2. Sweep
(β, water:lipid ratio, ranges, torque gain) → maximise H, then push sheetness. 3. Report + host.

## Honest risk
Micelles are the robust first outcome; a true **bilayer** is the narrow "edge-of-assembly" regime
(the lipid *packing parameter*: head/tail balance). Expect several tuning passes. "Micelles" is a
real partial win; "bilayer ribbon" is the target; "vesicle" is the stretch.

## Findings (2026-07-21)

**Result: amphiphilic tokens self-assemble from a random soup into a single orientationally-ordered,
one-particle-thick membrane band spanning the box** — director order `S≈1.0`, sheet aspect `≈12`,
`clusters→1`, water excluded. Emerges from a purely local anisotropic affinity LAW (relative-position
attention in per-token orientation + bearing); **no dictated bonds, fixed N, transformer-faithful.**
See `membrane_timelapse.png` (random → nucleate → merge → one band). Showcase config is the default in
`membrane.py` / `render_membrane.py`; reproduce with `bazel run //projects/vivarium:membrane -- --probe`.

**The path there — four ingredients, each a physical law, discovered by iteration:**
1. **Hydrophobic effect done right.** Affinity must attract ONLY hydrophobic (tail) patches
   (`a = h_i·h_j`, `h∈[0,1]`); the first attempt let hydrophilic surfaces attract too, collapsing
   everything into thick blobs. Hydrophilic-neutral is what lets tails bury into a THIN sheet.
2. **Anisotropic packing (Yuan+2010).** Attraction favoured side-by-side (bond ⊥ normal) + parallel
   normals → tile a leaflet, not a chain. Gives the correct local motif (`S=0.997`, visible
   side-by-side parallel pairs) but fragments into many frozen patches.
3. **Thermostat + weak isotropic cohesion.** Kinetically-trapped patches don't coalesce; an annealed
   thermal kick (`temp`, quenched to 0) + a soft long-range lipid pull (`gc`) let them merge into one
   domain. Standard self-assembly annealing.
4. **Rod-shaped steric (the token IS a shape).** Isotropic (disk) steric fills the interior → a round
   raft. Making the excluded volume a ROD (long along the normal, `kappa`) forbids end-on stacking, so
   lipids can only pack side-by-side → forced one-particle-thick → the extended band.

**Honest limitation.** In this **2D single-bead** model the equilibrium ordered domain is a nematic
band/raft — the correct membrane *packing motif* and unambiguous self-assembly, but NOT the iconic
closed **bilayer/vesicle** (two leaflets tail-to-tail enclosing water). The signed-vs-unsigned test
confirms order is real; the tail-to-tail inter-leaflet term (`gi`) is implemented but a clean closed
bilayer needs a genuinely **shaped token** (Gay-Berne ellipsoid / 2-bead lipid — still one token,
squarely the grounded-contour idea) or **3D**. That is the documented next step, and `kappa` is the
first move toward it.

**Metric trust.** `metrics_membrane.measure` now also returns director order `S` (unsigned `|o_i·o_j|`,
so both antiparallel leaflets count) and side-by-side fraction — both validated on hand-built fixtures
(`test_order_parameter_matches_eye`). As with H/sheetness, the numbers provably match what the eye sees.
