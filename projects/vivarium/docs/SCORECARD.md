# Vivarium scorecard — where we are, with binary criteria

Every stage has a PASS/FAIL test against a validated metric and a planted reference, not a
judgement call. Values are the last measured; the command to re-measure is given. Metric bands come
from `references.py` (planted, solvated, relaxed before reading).

## Metric bands (the rulers)

| metric | bilayer | micelle | collapse | what it answers |
|---|---|---|---|---|
| `splay` (2-D) | 0.00 – 0.21 | 0.47 – 0.63 | — | is the local order lamellar or radial? |
| `splay` (3-D) | 0.00 | 0.59 – 0.76 | — | same, calibrated separately |
| `packing` | 0.71 – 1.00 | 0.44 – 0.68 | < 0.35 | does matter occupy space? |
| `align` | ~1.0 | 0.08 – 0.18 | ambiguous 0.5–0.8 | global nematic order (NOT sufficient alone) |
| `spanning` | ~1.0 | low | — | does the aggregate wrap the periodic box? |

`splay` is the discriminator. `align` alone cannot separate a ribbon from a dense pile, which is
what made three claims wrong before it existed.

## Stages

| # | stage | criterion | 2-D | 3-D |
|---|---|---|---|---|
| 0 | tail-to-tail preference | two lipids associate tails-in | **PASS** | untested |
| 1 | **micelle from disorder** | `splay` in micelle band, `packing` > 0.35, dispersed start | **PASS** — splay 0.527, packing 0.441 vs reference 0.436 | **FAIL** — splay 0.90–0.95, disordered |
| 2 | **finite bilayer patch** | `splay` < 0.30, stable over 100k+ steps | **PASS** — splay 0.253, held t=20k→150k | not reached |
| 3 | **spanning bilayer** | `splay` < 0.30 AND `spanning` > 0.8 AND `packing` > 0.35, simultaneously | **FAIL** — best is either/or: (splay 0.25, span 0.27) or (span 0.82, align 0.11) | **FAIL** — planted one melts, splay 0.000 → 0.824 |
| 4 | vesicle | `enclosed` > 0.02, `edge` ~ 0, sealed | not started | not started |

**2-D: 2 of 4 stages. 3-D: 0 of 4.**

## What blocks each

**Stage 3 in 2-D** — the two levers pull apart. Low lipid fraction gives bilayer order in finite
patches (splay 0.25, spanning 0.27); high fraction gives spanning without order (spanning 0.82,
align 0.11). Success is the overlap, and phi 0.50–0.60 is unsampled. This is a two-parameter search
with a binary criterion, which is a tractable shape of problem.

**Stage 1 in 3-D** — blocked by a BUG, not by physics. See below.

## Known defect blocking 3-D (2026-08-01)

`_contact_distance` discards per-species radius when `aniso > 0`:

    base = (self.repel_contact if self.sigma is None
            else self.sigma[:, None] + self.sigma[None, :])
    if self.aniso <= 0.0:
        return base                       # 2-D path (aniso=0): sigma IS used
    half = 0.5 * self.repel_contact       # 3-D path (aniso=0.95): sigma DISCARDED
    return half * (1.0 + self.aniso * nf) + half * (1.0 + self.aniso * nf.T)

Verified directly: `head_sigma` 0.5 and 1.0 produce IDENTICAL contact matrices at aniso=0.95 while
`sigma` itself differs. So every 3-D run has had water, heads and tails at the same steric radius.

The packing parameter P = v/(a0*l) is precisely a head-area to tail-volume ratio, so the 3-D model
has been missing the property its phase behaviour depends on. **Every 3-D result to date measures a
different molecule than the 2-D results do**, which makes the 2-D vs 3-D comparison invalid as run.

## Cost wall (why 3-D is barely explored)

Solvent fills the box, so N ~ L^3, and forces are O(N^2): cost ~ L^6.

    bound    water     N     s/step   20k steps
      4.5      482    626      0.09      0.5 h
      7.0     2178   2358      1.26      7.0 h
      8.0     3250   3520      2.81     15.6 h
     11.0     8962   9151     19.02    105.7 h   <- matches the 2-D box that works

The contact term is short-ranged (`overlap` is exactly 0 beyond ~1.95 = repel_contact*(1+aniso)) yet
is computed densely for all pairs. Exploiting that is EXACT and changes the scaling from L^6 to ~L^3.
Not yet done.

## Re-measuring

    bazel test //projects/vivarium:test_suite     # 105 tests: metric truth + discrimination
