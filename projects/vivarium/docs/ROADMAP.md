# vivarium — consolidated roadmap

*The single list of experiments and their results. Updated 2026-09-10. Supersedes `ROADMAP_V2.md` and
`ROADMAP_RESET.md`. Referenced from [`../SUMMARY.md`](../SUMMARY.md).*

Every row has a registered spec in `specs/` and an append-only result file in `docs/results/`.
Verdicts are what the pre-registered gate returned, not an interpretation of it.

---

## 1. Foundation — DONE

| # | experiment | result | verdict |
|---|---|---|---|
| F1 | Is the transformer formulation exact? | forces match `field.forces` to **1.4e-16**; one forward pass vs `Inertial.step` **exactly 0.0**; token-channel `q·k` vs the χ table **0.000e+00** over 30 186 pairs | **PASS** |
| F2 | Does it cost anything? | 21.17 ± 2.42 vs 20.65 ± 1.66 ms/step | **free** |
| F3 | Chain-bending defect | 1-3 stiffener at rest length 2σ gives **zero** harmonic stiffness (V/δ⁴ = 0.9375 constant, V/δ² → 0.0004) | defect confirmed |

**Caveat on F1:** the bit-exact *step* identity was measured on 120 beads in L = 12 with hand-built
linear chains — **not** the production topology. Only the *force* identity was checked at 2 959 beads.

---

## 2. The 2-D vesicle — DONE, verified

| # | experiment | result | verdict |
|---|---|---|---|
| V1 | Does a vesicle emerge from a scattered start? | **seed 509, step 500 000**: `vesicle_call` True, dilations `[1,1,1,1]`, lumen ratio 0.136, 56-lipid cluster, held 22 consecutive checkpoints | **YES — render-confirmed** |
| V2 | Is it reproducible? | re-running seed 509 reproduced closure at the same step | **YES** |
| V3 | How does it form? | cluster **constant at 56 lipids** for 100 k steps before *and* after closure | **ends meeting, not curving** |
| V4 | Historical replication | 2/18 historically; **0/44** in recent runs under the strict gate | see §6 — criterion changed |

Config: `N=160, L=65, kT=0.45, φ=0.55`, full six-affinity chemistry, `plant="random"`.
Shipped as `docs/controls/emergent_vesicle_sd509_s500000.npz`, served at `/vivarium`.

---

## 3. Reducing the chemistry — DONE, with a cost

Registered: `specs/2026-09-02_knob_ladder_2d.md`. Endpoint changed from the 11% self-assembly rate to
the **gap dose-response** (30× cheaper, graded).

| # | rung | closure (3.4σ) | far (10.1σ) | verdict |
|---|---|---|---|---|
| GATE I | instrument reproduces the published dose-response | **10/10** | **2/10**, p = 0.0004 | **PASS** |
| L1 | `chi_HT` removed | 9/10 | 0/10 | **PASS — decoration** |
| L1c | + head size 0.95 | 10/10 | 0/10 | pass, but no credit (L1 already passed) |
| L2 | `chi_HH` removed | 8/10 | 0/10 | **PASS — decoration** |
| L3 | `chi_HW` removed | 8/10 | 0/10 | **PASS on closure**, but persistence 18/20 → **10/20**, p = 0.0069 |
| L4 | `chi_TW` | — | — | **VACUOUS** — already 0.00; the honest knob count is **five**, not six |
| L5 | `chi_WW` removed | 7/10 | 0/10 | **PASS — decoration** |
| L6a | Flory–Huggins solvent-averaged, water removed | 16/20 | 4/20 | **PASS** — restores what L3 lost (p = 0.048 vs L3; p = 0.33 vs having the knob) |
| L6b | Cooke: `chi_TT` only + head size | **19/20** closure, **17/20** persistence | 4/20, p = 1.1e-6 | **PASS** |

**Headline:** five affinities plus explicit solvent → **one affinity plus one size ratio**, with
production no better on closure (p = 0.67) or persistence (p = 0.59).

**Two corrections, both recorded:**
- On the *strict* gate, 6B is **11/20 against 18/20** (p = 0.0155) — the only arm where `vesicle_call`
  diverges from persistence. "No loss" is withdrawn.
- 6B's `chi_TT = 1.00` is an unregistered hand-picked constant, and `sigma_head` was retired at L1 then
  silently reinstated at L6b.

---

## 4. Emergence under the reduced chemistry — FAILED

| # | experiment | result | verdict |
|---|---|---|---|
| E1 (H7) | reduced chemistry, dispersed start, n=20 | **0/20** vesicles, 0/20 enclosure, largest 78/160 | **FAIL** |
| E2 (H8) | production vs reduced, contemporaneous, dense checkpoints | production **13/20** enclosure vs reduced **2/20**, p = 0.00039; both **0/20** strict | **the reduction costs assembly** |
| E3 (H10) | does lowering N raise the rate? (spanning hypothesis) | N=50 **0/12**, N=80 **0/12**, N=116 0/12, N=160 1/32 — rate **rises** with N | **FAIL — all three predictions backwards** |

E3's registered outcome-4 applies: the limit is **minimum viable vesicle size**, not the box. At N=50
the largest aggregate reaches only 17.8 lipids.

---

## 5. Why won't a membrane bend? — SEVEN NULLS

The flat-planted-ribbon protocol. Every entry is a measured null with the membrane intact.

| # | candidate | result |
|---|---|---|
| B1 | `chi_TW` (line tension) | λ = +2.8 ± 2.8 ε — **null with power** |
| B2 | `chi_HH` | 0/5 at two values, 10 runs |
| B3 | lipid shape (2-tail) | dissolves to micelles |
| B4 | imposed leaflet **thickness** asymmetry | 0/5, intact, render straight |
| B5 | imposed leaflet **area** asymmetry | 0/5, intact |
| B6 | **MLP affinity channel** (χ from coordination) | **0/12 vs 0/12**, p = 1.0 |
| B7 | **MLP shape channel** (σ_head from head-only coordination) | **0/12 vs 0/12**, p = 1.0 |

**B1–B5 are symmetric pair terms** and `RESULTS.md` explains them structurally: a pair potential cannot
express a difference between leaflets. **B6 and B7 are not pair terms**, so that explanation no longer
covers the data. The obstruction is narrower and more specific than "pair potentials are insufficient".

---

## 6. Instruments — the recurring failure mode

Twenty-five defects on record, **all instruments or harness, none physics**.

| # | instrument | status |
|---|---|---|
| I1 | `n_enclosed` (2-D) | validated; reads **0 on every 3-D control** — 39 3-D runs were scored against it |
| I2 | `_lumen3d.n_enclosed_3d` | **NEW, validated** — shell→1, ball→0, gas→0, slab→0, two shells→**2** |
| I3 | `vesicle_call` | normalisation fixed (cluster, not whole system). Re-scored 151 states: **0 verdict flips**, 149/151 blocked by clause 1 |
| I4 | `phase.py` gel/fluid/gas | validated (deep freeze→gel, Cooke point→fluid, boil→gas) |
| I5 | `curl.aspect` | validated — flat 0.0024, arc 0.504, ring 1.000 |
| I6 | `_sasa.exposure` | validated incl. an analytic case (2/3 exactly) |
| I7 | gradient gate (F = −∇U) | **~2e-08** for every modulator configuration |
| I8 | cross-path gate (field vs transformer) | **0.000e+00** at every configuration |

**The open question this creates:** the historical "2 of 18" used **gate 1 only**; gate 2 (lumen size)
was added later and rejects *every* saved 2-D state. The two successful runs were overwritten on disk.
So it is **unverifiable, not refuted**. Deciding which gate defines a vesicle is a judgement call, not
a measurement — it is the top item in the reviewer handoff.

---

## 7. Retracted

| what | why |
|---|---|
| gel/fluid explanation of the assembly gap | `phase.py` hardcoded one chemistry; production was never measured. Measured properly **both read retention 0.776 — both gel**. At matched T\*, production still wins (p = 0.0036): **chemistry, not phase** |
| ladder "no loss" headline | 6B is 11/20 vs 18/20 on the strict gate |
| 3-D bending fix | `bend_r0 = 4.0` **stretches bonds 67%** (b\* = (2+2r₀)/6) rather than stiffening. Cooke gets away with it only via **FENE** (inextensible). The "103% of reference" thickness compared a 3.33σ molecule to a yardstick for a 1.93σ one — it is **54%** |
| H5 enclosure signal | 4/6 vs 0/6 became **4/12 vs 4/12**, p = 0.667 |
| spanning hypothesis | E3, all predictions backwards |

---

## 8. Performance (measured condensed, not dispersed)

| configuration | beads | ms/step | 1e6 steps |
|---|---|---|---|
| 2-D production | 2 959 | **3.40** | 0.94 h |
| 2-D solvent-free | 800 | 1.08 | 0.30 h |
| 3-D solvent-free N=1000 | 5 000 | **97.4** | 27 h |
| 3-D oracle (Cooke–Deserno) | 5 000 | **265.8** | 73.8 h |

3-D costs **~29×** more per run than 2-D. Our engine is **20× faster than the reference
implementation**, which is why the oracle head-to-head remains this project's one unevaluated
registered gate. `np.add.at` → `bincount` gave a bit-identical **16–23%**.

---

## 9. What comes next

**Ordered by value, with cost.**

1. **Raise the 2-D emergence rate.** Only ~1 in 32 succeeds, which is too rare to gate anything. The
   one validated coordinate is the ribbon's **end-to-end gap** (5/5 at 3.4σ, 1/10 at 10.1σ). Untested
   prediction from E2/E3: the successful seed made a **small** aggregate (85 vs a median of 132), so
   *many small aggregates should beat one large one*. Cheap: an N-and-density sweep at 2-D cost.
2. **Decide which gate defines a vesicle** (§6). No further run can settle it; it needs a judgement.
   Blocks any claim about the historical result.
3. **Explore the rest of the MLP.** Only the simplest form has been tried — an *instantaneous scalar
   function of a coordination count*. `polar_pack` does three further things, none tested here:
   - **induced fit** — shape adapts to *which* neighbours you are bound to (`A_fit` attention),
     not merely how many. The lipid analogue is hydrophobic matching.
   - **history-dependent state** — its shape channel evolves through residual + LayerNorm, so it has
     a relaxation time. Ours is memoryless. Doing this properly needs an **extended Lagrangian**
     (internal coordinate with its own kinetic term) or the energy ledger is lost.
   - **explicit rigidity** — an elastic restoring pull toward a rest shape, with `morph` as the
     flexibility fighting it. Ours has no independent stiffness.
   Note B6/B7 first: the two simplest channels are already null, so this is refinement of a mechanism
   not yet shown to work.
4. **Rebuild 3-D on inextensible bonds (FENE)** before spending compute there. Its bending result is
   retracted and everything downstream of it needs re-deriving. ~29× the 2-D cost.
5. **Run the oracle head-to-head** (AC-2, registered and never evaluated). 73.8 h/seed.
6. ~~Quarantine `bicelle2d` and `bilayer3d`~~ — **WITHDRAWN 2026-09-11, the premise was wrong.**
   They are not dead legacy stacks, they are **system builders**: `bicelle2d.build` constructs the
   `--lipid2d` viewer mode in `server.py:436`, and four tests (`test_physics_invariants`,
   `test_metric_truth`, `test_slider_ranges`, `test_polar3d`) use them to build systems for
   invariant checks. They have no dynamics of their own — 0 energy and 0 force functions — so calling
   them "simulation stacks" was a miscount on my part. Moving them breaks the test suite and the
   viewer.

   The underlying duplication problem is still real (`def plant` in 18 files, `def build` in 15,
   `def step` in 12, and two force paths that once disagreed silently). But it needs a proper
   consolidation, not a file move, and it is no longer a cheap item.

**Not started:** fusion and division. Neither has ever been observed.
