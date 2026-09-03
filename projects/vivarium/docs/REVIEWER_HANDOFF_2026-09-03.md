# Reviewer handoff — vivarium 2-D knob ladder, 2026-09-03

**Ask:** one decision, not a measurement. What should count as a 2-D vesicle? Everything below turns
on it, and no further run can settle it.

Supersedes `REVIEWER_HANDOFF_2026-08-31.md` for the 2-D track. The 3-D closure blocker described there
is unchanged and remains parked.

---

## 1. What was done

The 2-D lipid model's chemistry was six hand-set pair affinities. Each was removed or replaced, one at
a time, and scored on a pre-registered gate. Spec: `specs/2026-09-02_knob_ladder_2d.md`.

**The endpoint was changed first, and that was the enabling move.** Every prior knob test was scored
on the self-assembly vesicle rate, ~11%. At six seeds per arm that resolves nothing — the previous
rung returned 0/6 vs 0/6, the expected result for *both* arms. Two full-length runs were spent
learning this. Closure is instead controlled by the ribbon's **end-to-end gap**, the one reaction
coordinate in this project ever validated, which gives a steep dose-response and runs ~30x cheaper.

`GATE I` required the assay to reproduce the published dose-response before any rung ran. It did:

| gap | closed | published |
|---|---|---|
| 3.4 sigma | 10/10 | 5/5 |
| 10.1 sigma | 2/10 | 1/10 |

Fisher p = 0.0004. Confirmed by render, both arms.

## 2. Results

### The ladder — five real knobs, all resolved

| knob | outcome |
|---|---|
| `chi_HT = -0.25` | **decoration.** Deleted: 9/10 closure vs 10/10 |
| `chi_HH = +0.20` | **decoration.** Deleted: 8/10 |
| `chi_HW = +0.75` | **LOAD-BEARING.** Deleting it halves persistence, 18/20 -> 10/20, p = 0.0069 |
| `chi_TW = 0.00` | **vacuous.** Already at "no interaction"; never a knob. The honest count is five, not six |
| `chi_WW = +0.50` | **decoration.** Deleted: 7/10 |
| explicit solvent | **replaced.** 2799 water beads -> Flory-Huggins averaging, or dropped entirely |
| `chi_TT = 0.70` | **kept, irreducible.** Declared so before the ladder ran |

`field.py` documents `chi_HT` as "THE HEAD-TAIL CROSS TERM IS WHAT MAKES AN AMPHIPHILE". On this
endpoint it is not. The real driver is `chi_HW` against `chi_TW`.

### The reduction

Five affinities plus an explicit solvent reduce to **one affinity (`chi_TT`) plus one geometric ratio
(`sigma_head` = 0.95)**:

| | production | reduced | p |
|---|---|---|---|
| closure, 3.4 sigma | 10/10 | **19/20** | 0.667 |
| persistence | 9/10 | **17/20** | 0.593 |
| discrimination near vs far | p = 0.0004 | **p = 1.1e-6** | |

Production is not better on either endpoint.

### The one replacement that is a replacement

| persistence, near gap, n = 20 | |
|---|---|
| all water terms present | 18/20 |
| `chi_HW` deleted, nothing put back | **10/20** |
| solvent-averaged (derived, water removed) | 16/20 — p = 0.048 vs deleted |
| one affinity + head size | 17/20 — p = 0.020 vs deleted |

Deleting `chi_HW` costs persistence; integrating the solvent out **restores it to a level
indistinguishable from having the number** (p = 0.33 and p = 0.5 against the full-knob arm). This is
the project's first instance of a hand-set chemical parameter replaced by derived physics rather than
merely removed.

### And what it costs — established

The ladder ran entirely on **planted arcs**. It tests closure given a membrane. H8 tested emergence,
both arms contemporaneous, dense checkpoints, n = 20:

| arm | vesicles (strict gate) | seeds with any enclosure | mean largest aggregate |
|---|---|---|---|
| production | 0/20 | **13/20** | 131.4 / 160 |
| reduced | 0/20 | **2/20** | 78.0 / 160 |

**p = 0.000386.** So:

> The reduction **preserves the ability to close and hold** a planted vesicle and **degrades
> self-assembly**. Nucleation and closure are different problems; only closure was simplified.

## 3. The decision we need

Both arms give 0/20 on `vesicle_call` against a historical headline of **2/18**. That looks like a
reproduction failure. It probably is not one.

- `vesicle.py` already records: *"every saved 2-D production state was checked on 2026-08-27 and not
  one passes `vesicle_call`"* — five states, lumen ratios 0.021–0.070 against a 0.10 threshold.
- `vesicle_call`'s docstring: *"Gate 2 exists because the pre-registered emergence criterion had only
  gate 1, and a 160-lipid branched network passed it."*

**The 2/18 was scored on gate 1 alone.** Gate 2 was added later and rejects every 2-D state on disk.
Under a loose enclosure criterion production gives 13/20 — *more* than 2/18. Under the strict two-gate
criterion, 0/20. The old and new numbers were never measuring the same object; **2/18 vs 0/40 is not
evidence of non-reproduction.**

What it does mean: the headline 2-D result is stated against a criterion its own successor instrument
rejects, no saved state survives the current gate, and **the two successful runs are gone from disk** —
one was overwritten in place by a relaunch (`states_protected/former_sd45007_*`, filename says step
960,000, file reports 1,600,000). The result is not refuted. It is **unverifiable from the artifacts**.

**The question:** which gate defines a 2-D vesicle?

1. `n_enclosed >= 1` — production 13/20. Too loose; a branched net with an incidental pocket passes.
2. Gate 1 only, `n_enclosed == 1` stable across dilations 1.0–3.0 — what 2/18 used. Admitted a
   branched network, which is why gate 2 exists.
3. Both gates, lumen sized for the lipid count — current. Rejects every artifact this project ever
   saved, including the ones it called successes.

If (3) is right, the 2-D emergence claim should be **withdrawn** and PAPER.md rewritten. If (2) is
right, gate 2 is too strict at N = 160 and needs recalibrating — note `vesicle.py` already flags that
`vesicle_call` sizes the expected lumen from the whole system's 160 lipids while the observed cluster
was 84, and that rescaling by (84/160)^2 would put sd9302 at 0.25, well inside.

### ADDENDUM, same day — the renders push toward option (3)

The loose criterion was checked against pictures rather than left as a number, and it does not survive.

`sd313` is the strongest production seed: enclosed at 47 of 100 checkpoints with all 160 lipids in one
aggregate. Its render (`docs/figures/emerge_sd313.png`) is a **branched ribbon network with one small
incidental pocket**, lumen 161 cells against 8149 expected. `sd302` (46/100) fails the same way at
ratio 0.020.

That is precisely the failure `vesicle_call`'s own docstring records gate 2 was added to catch: *"a
160-lipid branched network passed it. The render caught that, not the metric."*

**So the 13/20 figure is not 13 near-misses. It is 13 tangled ribbons with pockets**, and gate 2 is
being correct rather than over-strict. Two consequences:

1. Option (1) is dead -- `n_enclosed >= 1` counts pockets and must not be used as an emergence
   criterion.
2. **The historical 2/18, scored on gate 1, was very likely counting the same artifact.** Gate 1 is
   stricter than option (1) but still admitted a branched network, which is why gate 2 exists at all.

This does not fully settle the question, because the `vesicle.py` concern still stands independently:
`vesicle_call` sizes the expected lumen from all 160 lipids while a real emergent vesicle may contain
only part of the system, and rescaling sd9302 by (84/160)^2 moves it from 0.070 to 0.25. That is a
genuine calibration defect in gate 2 and it needs fixing regardless of the verdict.

**Recommendation, offered not asserted:** fix gate 2 to size the lumen from the *observed cluster*
rather than the whole system, then re-score. If the emergent states still fail -- and sd313 at ratio
0.020 would fail by any rescaling -- the 2-D emergence claim should be withdrawn.

That is a judgement about what a vesicle is. It is not something another run can decide, which is why
this stops here.

## 4. Calibration — defects found this session

Six, all instrument or harness, none physics. Consistent with the nineteen already on record.

1. **The detector nearly scored the plant.** At dilation 3.0, `n_enclosed` bridges a 3.4 sigma gap by
   itself. Had `vesicle_call` (which requires stability across 1.0–3.0) been the registered endpoint,
   the near arm would have been part artifact. It was registered at bead 1.0 *before* the null control
   ran, which is the only reason the choice was not made by the data.
2. **A render showed four fragments in the box corners** — the ring is built around the origin and the
   box wraps. Believing it would have discarded a good result. Fixed by recentring on the circular mean.
3. **A schema migration silently ate 20 baseline rows** on a column-count filter. Migrated explicitly.
4. **Then it ate 28 more**, because I changed the schema *while H8 was writing*. Symptom: `--score`
   reported no production arm on a run whose log said 40/40. A width filter must fail loudly, not skip.
5. **Cost model wrong 9x** — a solo benchmark quoted for a contended sweep. Third distinct cost error
   in this project, all looking identical from outside.
6. **Threads were the wrong primitive.** The reduction dropped 2959 beads to 800, and at that array
   size numpy's GIL releases stop covering the per-step work: 16 threads gave ~2x parallelism. The
   science reduction made the harness wrong.

Also: **H5 failed its registered gate** — the 4/6 vs 0/6 enclosure signal became 4/12 vs 4/12,
p = 0.667. The baseline's 0/6 was the fluctuation. Fourth small-sample effect to evaporate here, and
the reason the endpoint was changed.

## 5. Reproduction

    python gap_closure.py --gate --seeds 10      # GATE I, the instrument gate
    python gap_closure.py --score                # the whole ladder
    python emerge_reduced.py --score             # H7 + H8, grouped by checkpoint cadence
    python bilayer_metrics.py                    # four-control separation

Specs: `specs/2026-09-02_knob_ladder_2d.md` (ladder, GATE I, amendments 1–3, all rung verdicts),
`specs/2026-09-03_H7_emergence_reduced_chemistry.md` (H7, H8), `specs/2026-09-02_H5_*.md` (H5, failed).
Results: `docs/results/gap_closure.tsv`, `docs/results/emerge_reduced.tsv`.
Renders: `docs/figures/gap_*.png`, `rung1B_*`, `rung2B_*`, `rung3B_*`, `rung6A_*`, `rung6B_*`.
States: `docs/states_gap/`, `docs/states_emerge/`.

`origin/main` is frozen at `a161f70d` by request. Nothing has been pushed.
