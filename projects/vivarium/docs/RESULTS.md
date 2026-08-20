# Emergent vesicle in a 2-D transformer-only lipid model

**Claim.** A closed, water-filled bilayer vesicle self-assembles from a dispersed random start,
persists under fresh thermal noise, and passes a two-gate criterion calibrated against known
structures. Nothing was planted at any point in its lineage.

**It formed by ends meeting, not by curvature.** That distinction is the main scientific content
here, and it is measured, not assumed.

![emergent vesicle](figures/01_emergent_vesicle_persistence_sd21.png)

---

## The criterion

A single enclosure count is not sufficient — a branched network with an incidental pocket passes it.
`vesicle_call()` requires both:

1. **`n_enclosed == 1` at every dilation in bead 1.0–3.0.** The count is dilation-sensitive, so only a
   call stable across the knob is reportable.
2. **The lumen must be the right SIZE for the lipid count.** A closed vesicle of *n* lipids has contour
   *n*, so *R = n/2π* and interior *πR²*. Threshold 0.10.

Calibration, every entry verified against its render:

| structure | lumen / expected | verdict |
|---|---|---|
| planted vesicle, N = 120 | 0.876 | vesicle |
| planted ring, N = 300 | 0.882 | vesicle |
| implicit arc, N = 80, closed | 0.295 | vesicle (irregular) |
| **emergent candidate** | **0.269–0.292** | **vesicle** |
| emergent branched network | 0.028 | not a vesicle |
| branched network, later reading | 0.010–0.044 | not a vesicle |

Gate 2 exists because the original pre-registered criterion had only gate 1, and a 160-lipid branched
network passed it. The render caught that; the metric did not.

## The result

Lineage: random dispersed start → N = 160, L = 65 → continued twice. No planting anywhere.

| | |
|---|---|
| largest cluster | **160/160** lipids |
| percolating | no |
| core depth | 1.430–1.440 |
| `n_enclosed` @ bead 1.0/1.5/2.0/3.0 | 1, 1, 1, 1 |
| lumen ratio | 0.269–0.292 |

**Persistence** — 5 fresh thermal seeds, 200 000 steps, read at the end:

| seed | largest | vesicle_call | ratio |
|---|---|---|---|
| 20 | 159 | True | 0.272 |
| 21 | 160 | True | 0.285 |
| 22 | 160 | True | 0.281 |
| 23 | 123 | True — **fragmented, excluded** | 0.454 |
| 24 | 160 | False (opened) | — |

**3/5 intact and True**, against a bar of ≥3/5 fixed before the run. The source trajectory
independently held its closure for a further 400 000 steps (2.4 M total, ratio 0.292).

## Why it closed: encounter, not curvature

**This force field cannot curve a flat bilayer.** Every candidate source was tested on the same
planted-flat-ribbon protocol, and every one is a measured null with the membrane intact:

| candidate | result |
|---|---|
| χ_TW (tail–water) | null **with power**: λ = +2.8 ± 2.8 vs −5.2 ± 4.2 ε |
| χ_HH (head–head) | 0/5 at two values, 10 runs |
| lipid shape (2-tail) | dissolves to micelles, largest 7–11 of 80 |
| leaflet **thickness** asymmetry (4/6 tails) | 0/5, intact, render straight |
| leaflet **area** asymmetry (split 0.58, ratio 1.35) | 0/5, intact |

The reason is structural: χ terms are symmetric pair interactions, and spontaneous curvature is by
definition a difference between the two leaflets.

Closure instead happens when two ends of a ribbon meet. That route is quantified — planted arcs at
fixed N = 300, varying only the end-gap:

| end-gap | closed |
|---|---|
| 2.4 σ (N = 80) | 5/5, all by step 5 000 |
| 3.0 σ | 5/5 |
| 6.0 σ | 3/5 |
| 9.0 σ | 2/5 |

A rate that falls steeply with gap, with **no hard capture radius** — even 9 σ closes given time. The
emergent vesicle is this process at work: a long meandering ribbon whose ends found each other.

![flat stays flat](figures/04_flat_bilayer_does_not_curl.png)

*A planted flat bilayer after 200 000 steps with imposed 4/6-tail leaflet asymmetry: still straight,
fully intact. 0/5 closed.*

## Limits

- **It is a vesicle with appendages.** A stub and corner fragments belong to the same cluster, joined
  through the periodic boundary. That is why the ratio is ~0.28 rather than the ~0.88 of a planted
  vesicle: appendage lipids count in the expectation and contribute no lumen.
- **It is 2-D.** Nothing transfers to 3-D, where explicit solvent at φ 0.15–0.35 is still fragmented
  droplets rather than a liquid.
- **The formation rate is unmeasured.** One occurrence in five emergence seeds. A 10-seed measurement
  is in flight; until it reports, this is "observed once", not "reproducible at rate X".

## Reproducing

```bash
bazel build //projects/vivarium:_mixture
# dispersed start, N=160 in L=65
OMP_NUM_THREADS=1 VIVARIUM_CHI_HT=-0.25 VIVARIUM_CHI_WW=0.50 \
  bazel-bin/projects/vivarium/_mixture 1600000 2 160 0.0 65.0 0.45 0.55 random <seed>
```

Score any saved state with `vesicle_call()` in `_lumen_field.py`. The frozen candidate is
`docs/states/vesicle_candidate_frozen.npz`.

Full chronology, including every retraction, is in [AUTONOMOUS_LOG.md](AUTONOMOUS_LOG.md).
