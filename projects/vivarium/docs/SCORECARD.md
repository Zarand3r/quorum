# Vivarium scorecard — where we are, with binary criteria

Every stage has a PASS/FAIL test against a validated metric and a planted reference, not a
judgement call. Values are the last measured; the command to re-measure is given. Metric bands come
from `references.py` (planted, solvated, relaxed before reading).

## Metric bands (the rulers)

| metric | bilayer | micelle | collapse | what it answers |
|---|---|---|---|---|
| `splay` (2-D) | 0.00 – 0.21 | 0.47 – 0.63 | — | is the local order lamellar or radial? |
| `splay` (3-D) | 0.00 | 0.59 – 0.76 | — | same, calibrated separately |
| `head_enrich` | 1.34 (n/a for a slab) | **3.0** = max | ~1.0 | are tails buried and heads outside? |
| `packing` | 0.71 – 1.00 | 0.44 – 0.68 | < 0.35 | does matter occupy space? |
| `align` | ~1.0 | 0.08 – 0.18 | ambiguous 0.5–0.8 | global nematic order (NOT sufficient alone) |
| `spanning` | ~1.0 | low | — | does the aggregate wrap the periodic box? |

`head_enrich` is the MICELLE criterion and `splay` the LAMELLAR one, and they answer different
questions. `splay` conflates "wrong structure" with "right structure, patchy surface" -- a
self-assembled 3-D aggregate read splay 0.807, nearer the random null than the micelle band, and was
called disordered, while its cross-section showed a proper tail core with heads outside and
`head_enrich` read 3.00, the theoretical maximum. Radial enrichment is meaningless for a SLAB, so
`head_enrich` applies to compact aggregates only.

`splay` is the discriminator for lamellar order. `align` alone cannot separate a ribbon from a dense pile, which is
what made three claims wrong before it existed.

### Null controls (a positive control alone validates nothing)

| metric | bilayer | micelle | RANDOM null |
|---|---|---|---|
| `splay` 2-D | 0.00 – 0.21 | 0.52 | **0.60 – 0.70** |
| `splay` 3-D | 0.000 | 0.605 | **1.103** |
| `packing` | 0.78 – 1.00 | 0.51 | **0.77 – 0.80** |
| `solvation` | 0.64 – 0.79 | 0.95 | 0.63 – 0.65 |

**`packing` reads HIGH for random dispersed lipids** -- higher than a real micelle -- because
unaggregated molecules are simply far apart. It is a FLOOR check that catches collapse; a high value
is NOT evidence of structure, and must never be quoted as if it were.

`splay` separates all three in both dimensionalities, which is why it is the discriminator: the
2-D ribbons at 0.253 sit beside the relaxed planted bilayer (0.207) and far from micelle and random
alike.

## Stages

| # | stage | criterion | 2-D | 3-D |
|---|---|---|---|---|
| 0 | tail-to-tail preference | two lipids associate tails-in | **PASS** | untested |
| 1 | **micelle from disorder** | heads enriched on the surface (`head_enrich` -> 3.0) + tails buried | **PASS** — splay 0.527, packing 0.441 vs reference 0.436 | **PASS** — head_enrich **3.00**, equal to the planted reference and the theoretical max; splay 0.807 vs 0.605 means a rougher surface, not a different structure |
| 2 | **finite bilayer patch** | `splay` < 0.30, stable over 100k+ steps | **PASS** — splay 0.253, held t=20k→150k | not reached |
| 3 | **spanning bilayer** | `splay` < 0.30 AND `spanning` > 0.8 AND `packing` > 0.35, simultaneously | **PHASE IS STABLE** at repel 24: a planted bilayer holds and ORDERS (splay 0.197 → 0.098, packing 0.87). Self-assembly not yet there — one aggregate, 64–68% spanning, splay 0.61. A KINETIC problem now, not thermodynamic. | **FAIL** — with packing held at 0.90 (repel 96) a planted bilayer melts at every head_sigma from 0.5 to 1.4; genuinely unstable, not a collapse artifact |
| 4 | vesicle | **`encloses` > 0.02** — topological partition; planted loops read 0.030–0.032, sheets/droplets/random 0.001–0.009 | not started | not started |

**2-D: 2 of 4 stages, with stage 3's PHASE proven stable. 3-D: 1 of 4.**

Both dimensionalities are maintained. 2-D is the near-term target because its lamellar phase EXISTS
(a planted bilayer holds at splay 0.071, packing 0.95) so only kinetics remain; 3-D's genuinely melts
at every head size once packing is enforced, so it needs a different MOLECULE -- branched tails,
never yet run in 3-D.

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

## Running experiments (read this before launching anything)

Scratch probes are NOT committed. Add a `py_binary(name = "_probe", srcs = ["_probe.py"], main =
"_probe.py", data = [":configs"], imports = ["."], deps = [":vivarium"])` to BUILD.bazel while you
need one and REMOVE IT with the file. A target left behind pointing at a deleted source breaks
`bazel build //projects/vivarium/...` while `bazel test //projects/vivarium:test_suite` keeps
passing, so the tests stay green and the build does not -- which is how a broken tree reached main.
Check the BUILD, not only the tests, before calling a state a checkpoint.


    OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 bazel run //projects/vivarium:_probe

Two measured traps, both of which silently cost ~1.5x:

  THREADS. numpy defaults to one thread per core (32 here) and this workload is elementwise over
  (N,N,3) and (N,N,8) arrays, which numpy does NOT thread -- so the pool never helps and its
  synchronisation costs real time:

      OMP_NUM_THREADS=1     60.4 ms/step
      OMP_NUM_THREADS=4     59.0 ms/step   <- use this
      OMP_NUM_THREADS=16    80.3 ms/step   <- 33% SLOWER

  ORPHANS. Background runs survive the shell that launched them. Six accumulated in one session, some
  for 3+ hours, and contention alone moved the same benchmark from 60 to 89 ms/step. `pkill -f` on a
  pattern is NOT safe here: the pattern matches the killing shell's own command line, so it kills
  itself and nothing else. Kill by PID:

      for p in $(pgrep -f "vivarium/_probe"); do kill -9 $p; done

## Re-measuring

    bazel test //projects/vivarium:test_suite     # 105 tests: metric truth + discrimination
