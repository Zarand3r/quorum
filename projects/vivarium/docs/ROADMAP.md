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
| V3 | How does it form? | cluster **constant at 56 lipids** for 100 k steps before *and* after closure | **ends meeting** — see the correction below |
| V4 | Historical replication | 2/18 historically; **0/44** in recent runs under the strict gate | see §6 — criterion changed |

| V5 | Second and third vesicles (H11) | N=56 sd904 (lasso, ratio 0.196) and **N=112 sd903 — a clean ring, 35/112 lipids, ratio 0.454** | **YES — both render-checked** |

**Correction 2026-09-13 — "ends meeting, NOT curving" is a false dichotomy.** In 2-D a sheet's rim *is*
its two ends; a ribbon cannot bring its ends together without curving. The two descriptions name the
same event. The real question is what drives it, and the literature answer is a competition between
edge line tension λ (favours closing, grows with rim length) and bending rigidity κ (resists, and is
size-independent), giving a critical radius `R_c = 2κ/λ` above which closure wins — the criterion this
project already recorded in `docs/REVIEWER_HANDOFF_2026-08-31.md`.

**Neither side of that criterion is pinned here.** λ was measured directly, ring against arc at N=300,
time-averaged over the plateau: **+2.8 ± 2.8 ε, consistent with zero** — and `field.py` draws the
conclusion in its own comment, *"with no cost to an exposed edge there is no drive to close one, which
is why every arc in this project has unrolled."* κ is recorded in `docs/RESULTS.md` as **"not
measurable by any of three routes"**.

So closure here is **not demonstrably the natural mechanism**. It is consistent with two floppy ends
meeting by chance, which would explain both the ~1-in-20 rate and why end-to-end gap is the one
coordinate that predicts closure. **Measuring κ is what would settle it, and it has never been done.**
One caveat against over-reading this: λ ≈ 0 is not obviously a defect — the ribbon's ends appear to
self-cap with heads (which is why tip-counting metrics failed on a closed ring), and real bicelle rims
are also partly capped, which is what makes bicelles metastable rather than spontaneously closing.

Config: production chemistry, `plant="random"`, `bend_r0=2.0` (no bending stiffness).
**Every confirmed vesicle, with the exact command to reproduce it, is recorded in
[`SUCCESSES.md`](SUCCESSES.md)** — written because the original was lost for want of exactly that.

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
| E4 (H11) | does system size raise the rate, at FIXED density? | N=56 **1/20**, N=80 **0/20**, N=112 **2/20**, N=160 **1/20**; mean largest 55→104 | **FAIL — rate flat over a 1.9× range of aggregate size** |
| E5 (H12) | density at fixed N | **WITHDRAWN before running** — acts through the same mediator (aggregate size) that E4 just swept with no effect |

E3's registered outcome-4 applies: the limit is **minimum viable vesicle size**, not the box. At N=50
the largest aggregate reaches only 17.8 lipids.

---

## 5. Why won't a membrane bend? — SIX NULLS, five of them clean (was seven; two withdrawn, one replaced)

The flat-planted-ribbon protocol. Every entry is a measured null with the membrane intact.

| # | candidate | result |
|---|---|---|
| B1 | `chi_TW` (line tension) | λ = +2.8 ± 2.8 ε — **null with power** |
| B2 | `chi_HH` | 0/5 at two values, 10 runs |
| B3 | lipid shape (2-tail) | dissolves to micelles |
| B4 | imposed leaflet **thickness** asymmetry | 0/5, intact, render straight |
| B5 | imposed leaflet **area** asymmetry | 0/5, intact |
| ~~B6~~ | ~~MLP affinity channel~~ | **WITHDRAWN — the term was a constant, see below** |
| ~~B7~~ | ~~MLP shape channel~~ | **WITHDRAWN — same defect** |
| B6′ | *uniformly* 24% larger heads (what B7 actually ran) | **0/12 vs 0/12**, p = 1.0 |

**B1–B5 are symmetric pair terms** and `RESULTS.md` explains them structurally: a pair potential cannot
express a difference between leaflets. **G5 is the sixth null and is NOT a pair term**, so that
explanation does not cover it — but G5 is also **not a clean test**: the term destroyed the membrane
before it could bend it (0/24 intact), so "would it bend a sheet that stayed whole?" is unanswered.
Item 2 of §9 is the experiment that would answer it.

### Why B6 and B7 were withdrawn — a free parameter that stopped matching its own derivation

Both MLP channels divide their descriptor by `n_ref = 6.0`, registered as "the close-packed 2-D
coordination number (geometry), not a fit". Two errors, compounding:

- The descriptor is a sum of **smooth kernel weights**, not a neighbour count. At the head-head spacing
  of a flat bilayer (2.05σ) the kernel returns **0.107**, so two neighbours score 0.21, not 2.
- A 2-D leaflet is a **line**, so a head has **two** in-leaflet head neighbours, not six. And the
  descriptor was narrowed from all-lipid to head-only on 2026-09-09 to fix the feedback sign;
  `n_ref` was never re-derived after that change.

Measured through `Field.coordination` — the same code the force reads — head coordination is **0.207**
in a flat bilayer against an `n_ref` of 6.0. The shape channel's bracket is therefore `1.2414` for
every head in every state, with a **0.4% spread**: a uniform 24% head inflation, not a modulation. The
outer-minus-inner wedge on a ring, which *is* the mechanism, was **+0.10%**; at a derived `n_ref` the
same ring gives **+3.77%**.

B7 did test something and it is kept as B6′: *a uniform 24% head enlargement does not curl a flat
ribbon*. That is not the registered mechanism, which remains **untested**, not refuted.

**Decision 2026-09-11 (user): the many-body term is kept for physical realism regardless of what G5
returns.** It is the EAM / many-body-DPD class of term and the packing-parameter mechanism real lipids
use; before it, no force in the model could depend on a molecule's environment. G5 therefore decides
whether it is switched ON by default and at what `amp`, **not** whether it stays in the code. Two
conditions: off by default while `amp` is underived, and any positive reported as "with a
curvature-capable term present".

### G5 witness — the term WORKS. It turns the bilayer into micelles. (1 seed/arm, 2026-09-11)

Rendered and measured while the 12-seed sweep runs. One seed per arm, so this is a direction, not a
rate — but the direction is unambiguous and it is the textbook one.

| arm | step | clusters | roundness | heads outside tails | largest | reads as |
|---|---|---|---|---|---|---|
| amp 0.0 | 125 k | **1** | 0.013 | +0.327 | 56/56 | ribbon, intact throughout |
| amp 1.0 | 75 k | **4** | **0.446** | +0.496 | 22/56 | **micelles** |
| amp 4.0 | 75 k | **4** | **0.349** | +0.571 | 26/56 | micelles |

(a planted flat ribbon reads roundness 0.002; a disc reads 1.0. Heads stay on the outside in every
case, so the pieces are correctly-organised amphiphile aggregates, not damage.)

**This is the packing parameter doing exactly what lipid physics says it should.** `P = v/(a₀·l)`:
raise the head area `a₀` and `P` falls; below about 1/3 the stable phase is a micelle, not a bilayer.
The term raises head area, and the bilayer becomes micelles. **The shape channel is not inert and not
wrong — it moves the one geometric lever that sets curvature, in the direction the theory predicts.**

**Why it still will not curl, diagnosed.** The planter builds the ribbon at 2.0500 σ against a relaxed
1.7651 σ, so the term reads the starting membrane as under-crowded and inflates *every* head at step 0
— measured mean `sigma_head` 1.094 / 1.360 / 1.631 / 1.898 at amp 0.25 / 1.0 / 2.0 / 4.0. That
**global** inflation is first-order and lowers `P` everywhere. The **leaflet asymmetry** that produces
curvature is second-order, and it is swamped. The term changes the phase before it can bend the phase
it started in.

**The registered gate will therefore FAIL, through G5b.** That clause — curl counts only if the
largest aggregate still holds ≥ 90 % of the lipids — was registered on 2026-09-11 before any data
precisely so that "it curled" could not be claimed for a cloud of micelles, which is isotropic and
scores a high `aspect` for the opposite of the reason we care about. It is doing its job.

**Under R9 this is a success, not a failure.** The term is physically correct, it moves the right
lever, and it makes vesicles *less* likely at every amplitude tested. That is reported as a result.

**Follow-up to register (a new experiment, not an amendment): plant at the relaxed spacing.** Build the
ribbon at 1.7651 σ so the term starts neutral, isolating the second-order leaflet asymmetry from the
first-order global inflation. This is not tuning a parameter to pass a gate — it corrects an initial
condition that is 16 % more dilute than the model's own equilibrium, which under R9 is a fidelity
defect in its own right and belongs in §5b regardless of what it does to the curl rate.

### G5 — FINAL: fails to curl at every amplitude run; destroys the membrane, dose-dependently

*Session handoff: [`HANDOFF_2026-09-12.md`](HANDOFF_2026-09-12.md).*

| amp | σ_head at t=0 | **curled AND intact** | intact | mean largest | p vs off (intact) |
|---|---|---|---|---|---|
| 0.0 (off) | 1.000 | 0/12 | **12/12** | 56 | — |
| 0.25 | 1.094 | **0/12** | 2/12 | 38.8 | 3.4e-05 |
| 1.0 | 1.360 | **0/12** | 0/12 | 19.2 | 3.7e-07 |
| 2.0 | 1.631 | **0/12** | 0/12 | 21.8 | 3.7e-07 |
| 4.0 | 1.898 | **NOT RUN** | — | — | — |

The off arm's `largest_final` reads −1 in the TSV — that column did not exist when those rows were
written and was back-filled as "not measured" rather than invented; its intactness comes from the
render and from a witness run that held 56/56 through 150 000 steps.

**Gate verdict at every completed amp: `curled AND intact ≥ 6/12` → 0/12. FAILS.**

Two findings, the second far stronger than the one gated on: the shape channel **does not bend a flat
ribbon**, and it **destroys membranes dose-dependently** — pooled p = 8.0e-10, mean largest aggregate
falling 56 → 38.8 → 19.2 as σ_head rises. Under R9 that is a success and is reported as one.

**Amp 4.0 is NOT RUN, not null.** Resume: `curl.py --scales 4.0 --n-ref 0.3335 --seeds 12 --seed0 800
--workers 12` (dedups on `(scale, n_ref, seed)`; use 12 workers, see §5c).

### G5 — earlier partial verdict, amps 1.0 and 2.0 (2026-09-12)

The gate's output, verbatim:

```
amp 1.0 (n_ref 0.3335): on 0/12 vs off 0/12, Fisher p = 1.0000
  G4 gate (on>=6/12 AND off<=1/12 AND p<=0.05): False
amp 2.0 (n_ref 0.3335): on 0/12 vs off 0/12, Fisher p = 1.0000
  G4 gate (on>=6/12 AND off<=1/12 AND p<=0.05): False
```

| arm | curled (raw) | **curled AND intact** | intact | mean largest_final |
|---|---|---|---|---|
| off (amp 0) | 0/12 | 0/12 | **12/12** | 56 |
| amp 1.0 | 0/12 | **0/12** | **0/12** | 19.2 / 56 |
| amp 2.0 | 1/12 | **0/12** | **0/12** | 21.8 / 56 |

**Two findings, and the second is far stronger than the first.**

1. **The curl gate FAILS.** 0/12 at both amps, p = 1.0000. The shape channel does not bend a flat
   ribbon.
2. **The shape channel destroys membranes, with near-certainty.** Intact 12/12 in the off arm against
   **0/24** across both MLP cells — **Fisher one-sided p = 8.0e-10**. Every single MLP run fragmented.
   This effect was not what the experiment was gated on; it is what the experiment found.

The one raw `curled=1` is sd801 below — three micelles, excluded by the intactness clause.

**Under R9 this is a success and is reported as one.** The term is physically correct, it moves the
packing parameter, and the phase it selects is the micelle. That makes vesicles *less* likely, which
is the case R9 was written for.

**Amps 0.25 and 4.0 — sequenced, both expected to complete.** At 24-way both remaining cells would
have sat ~80 % complete at the session deadline, so the pool was killed by explicit PID (workers then
parent, 24 rows verified preserved) and relaunched on amp 0.25 alone. Measuring the relaunch then
showed **12 workers out-throughputs 24 by 1.53×** (§5c) — the box has 16 physical cores, not 32 — so
each cell takes ~1 h rather than the 3.3 h assumed. Amp 4.0 is chained to start when 0.25 lands.
Whichever does not finish is reported as **NOT RUN**, never as a null.

### G5 — the control earned its keep. `aspect = 0.5997` on three micelles. (2026-09-12)

One run in the ladder crossed the curl threshold:

```
mlp  amp 2.0  n_ref 0.3335  sd 801   aspect0 0.0024  aspect_max 0.5997   curled=1  intact=0
```

`aspect` 0.5997 against a 0.45 threshold — a clear pass on the metric the experiment was built around.
The saved state, rendered (`docs/figures/g5_CURLED_sd801.png`):

| | |
|---|---|
| separate lipid aggregates | **4** (110, 100, 60, 10 beads) |
| one intact ribbon would be | ~280 beads in **one** cluster |
| mean roundness of the aggregates | **0.478** (ribbon 0.002, disc 1.0) |
| what it is | **three round micelles, heads out** |

**It did not curl. It fell apart into micelles, and a scattered set of blobs is isotropic.** Without
the `intact` clause — registered 2026-09-11, before any data, as the criterion the experiment could
fail by winning — this row would have entered the record as the project's first membrane curl, on a
protocol with five standing nulls. It is the clearest demonstration in this project that a validated
metric can pass for the wrong reason, and the reason it was caught is that the clause existed before
the number did.

Every one of the first 21 rows reads `intact=0`, `largest_final` 14–26 of 56.

### G5 — the shape channel, actually tested. Registered 2026-09-11, RUNNING

| | |
|---|---|
| `n_ref` | **0.3335**, measured on a relaxed flat ribbon (6 seeds, 100 k steps, modulator off) |
| response | `sigma = sigma0 * 2/(1 + exp(-2*amp*(1 - n/n_ref)))` — the linear law made smooth and bounded, so the clamp cannot break the energy ledger at large `amp` |
| arms | `amp ∈ {0.25, 1.0, 2.0, 4.0}`, 12 seeds each (800-811), 300 k steps, paired against the existing 0/12 off arm |
| gate | curled **and intact** ≥ 6/12, off ≤ 1/12, Fisher p ≤ 0.05, at **any** amp |
| control | `intact` = largest aggregate holds ≥ 90% of lipids. **Curl that appears only where the ribbon fragments FAILS the gate** — the criterion this can fail by winning |

Guards added so this fails loudly next time: `n_ref` has no default on either modulator;
`manybody.assert_calibrated` raises when the descriptor's mean is >4× from `n_ref`, and `curl.py`
calls it at step 0; `Field.coordination(X)` exposes the descriptor the force reads;
`tests/test_manybody.py` pins all of it, including that `n_ref = 6.0` is rejected. See
`specs/2026-09-07_mlp_many_body.md` Amendment 4.

---

## 5a. What came across from `polar_pack`, and what did not

The two stacks were compared and deliberately combined (2026-09-07 onward). `polar_pack` is
transformer-only and expressive but has **no energy ledger**; vivarium has the ledger. The transfer was
of an *idea*, gated at every step.

**Transferred — the mechanism.** polar_pack's MLP does not modulate interaction strength, it modulates
**shape**: "induced-fit morph — the block updates the shape channels, so an agent deforms its contour to
fit its binding partners." In lipid physics shape is exactly what sets curvature, through `P = v/(a₀·l)`.
That became `manybody.ShapeMLP`, and it is the live MLP in this project.

**The gates it passed, all registered before the data:**

| gate | result |
|---|---|
| G1 — `field.forces` vs `transformer.attention`, every MLP scale | **0.000e+00** |
| G2 — flat bilayer must show NO leaflet asymmetry (cannot manufacture curvature) | **0.0000 exactly** |
| G3 — curved ring must show one (mechanism engages) | **+0.1179** |
| F = −∇U with the many-body term, central differences | **1.07e-06**, the truncation floor, flat in MLP strength |
| 2026-09-12 — does it move the packing parameter? | **yes**: bilayer → micelles, p = 8.0e-10 |

**Not transferred, deliberately.** *Softmax*: row-stochastic weights give `w_ij ≠ w_ji`, so Newton's
third law fails and force becomes intensive — polar_pack can afford it because it has no ledger, and we
cannot. *The electrostatic head*: non-conservative as built (Finding 5) and softmax-based; see §5b D1.

**What it has not delivered: a curl or a vesicle.** The mechanism is sound and verified; the outcome is
still null.

---

## 5b. Fidelity audit — where the model is NOT what nature does

Added 2026-09-11 under R9. Every entry is a known departure, with how it was established. **Fixing
these is not conditional on them helping.** Ordered by how much they bear on the vesicle question.

| # | departure from nature | established by | deliberate? |
|---|---|---|---|
| D1 | **No electrostatics *in the vivarium stack*.** Real lipid heads are zwitterionic or charged; head–head repulsion is long-ranged next to the vdW well and sets head area, hence the packing parameter. | grep: no coulomb / yukawa / debye / ewald / charge term in `field.py`, `transformer.py`, `_mixture.py`. Every term is cut at `rc = 2.5σ` — `_core` zero beyond `s=1`, `_well` zero beyond `rc`. | **No — an omission.** But **not untried**: see the note below. |
| D2 | **Chains have zero bending rigidity.** Real acyl chains resist bending; Cooke–Deserno keep the 1-3 stiffener permanently stretched (rest 4σ) precisely to straighten them. | F3: stiffener at rest length 2σ gives `V/δ² → 0.0004`. | **No — believed present, measured absent.** The `bend_r0=4.0` fix stretched bonds 67% and was retracted. |
| D3 | **Two dimensions.** | by construction | **Yes** — ~29× cost in 3-D. |
| D4 | **No hydrodynamics.** A membrane's undulation relaxation and fission dynamics are set by solvent hydrodynamics. A per-particle thermostat destroys them. | `integrate.py:75-76` — `v = c1*v + sqrt(kT/m*(1-c1²))·normal(size=X.shape)`: independent friction and noise per particle, so momentum is **not** conserved. DPD's pairwise thermostat conserves it. | **No — inherited, never chosen.** |
| D5 | **Harmonic bonds, no maximum extension.** Under strong forces molecules stretch without limit. | `field.py` `k_bond`/`r_bond`, harmonic | **No — inherited.** FENE is the standard CG choice for exactly this. |
| D6 | **`amp` is a free parameter.** | declared in the spec | **No.** `n_ref` is now derived and measured; `amp` should be too — from a hydration-shell compressibility or an area-per-lipid response. |
| D7 | **Head-size response bounded at 2σ₀.** A bound is physical (a hydration shell has a maximum thickness); the *value* 2 is not. | chosen 2026-09-11 for numerical safety, to remove a clamp that broke `F = −∇U` | **Partly** — existence justified, magnitude arbitrary. |
| D8 | **Bounded repulsive core**, finite at full overlap (37.8ε) rather than divergent. | `_core = height·(1−s)²` | **Yes** — documented, and standard in CG/DPD. The one entry here that is defensible as-is. |
| D9 | **The flat-ribbon planter builds 16 % more dilute than equilibrium**: head spacing 2.0500 σ against a relaxed 1.7651 σ (6 seeds, 100 k steps, modulator off). Every environment-dependent term therefore reads the starting membrane as under-crowded. | measured 2026-09-11 while deriving `n_ref`; the source is a hard-coded default, `_mixture._plant_flat_ribbon(..., gap=1.05, ...)`, against a measured equilibrium of 0.883 per lipid. Its docstring justifies the ribbon being FINITE, and says nothing about the spacing value. | **No — a picked constant.** "Derive constants from the configuration; do not pick them", in one literal. It is why the G5 arms micellise from step 0. |

**D1 has been attempted before, in the other stack — read this before re-attempting it.**
`polar_pack.py` carries an electrostatic head: a bounded, bearing-aware attention on near-face charges
`nf_i(j) = ⟨C_i, basis(θ_{i→j})⟩`, deliberately **not** a `1/d²` Coulomb kernel. Two things happened to
it, both recorded in `docs/BILAYER_REVIEW.md`:

- **Finding 5 (2026-07-25): it was not conservative.** `nf_j` was read along the wrong bearing, so
  `prod` was asymmetric (`max|P − Pᵀ| = 0.29`), giving `F_ij ≠ −F_ji` and a phantom net force
  `Σ F_i = 2.1` — while being documented as "CONSERVATIVE … relaxes to a free-energy minimum". Found by
  a momentum test, **not** by any result looking wrong. After the fix the tuned configurations
  **collapsed** (3-D occupancy 63 → 19 of 64 cells), so the prior space-filling behaviour was partly
  the spurious term stirring the dish.
- **It never produced emergence.** On the frozen benchmark the best `emergence_score` is the
  **baseline, +0.0057**; every row since is negative (2-D −0.0367; 3-D −0.0179 to −0.0703). `demix`
  improved (0.061 → 0.101 in 2-D, 0.512 in 3-D) — the hydrophobic effect works, assembly does not.

So electrostatics is **not** an untried idea. What is untried is electrostatics **inside an energy
ledger**: polar_pack's head is row-stochastic softmax, which fails R3 by construction, and its one
implementation was non-conservative for three months without anyone noticing. Any vivarium version must
carry a momentum test and a gradient gate from the first commit.

**The size-selection argument below is what is new, and it stands on its own data.** Largest aggregate against system size, from the emergence runs:

| N | runs | mean largest | **max** | mean/N |
|---|---|---|---|---|
| 56 | 20 | 55.2 | **56** | 0.99 |
| 80 | 32 | 57.7 | **80** | 0.72 |
| 112 | 20 | 89.8 | **112** | 0.80 |
| 160 | 52 | 120.2 | **160** | 0.75 |

`max largest = N` exactly at every N — nothing stops an aggregate swallowing the whole system. **There
is no selected size**: that is bulk coarsening, not pattern formation. It is what a single interaction
range predicts, and it explains how vesicles are lost here — `SUCCESSES.md` records vesicle #1
"later grew to 85 by accretion, which added appendages and no lumen", and the cleanest ring on record
is a *minority* of the lipids (35 of 112) while the 56-of-56 one renders as a lasso. A vesicle is a
finite size-selected object and this model selects no size.

The equilibrium analogue of a Turing pattern is **SALR** — short-range attraction, long-range
repulsion — which gives micro-phase separation at a selected size that stops coarsening. The
long-range repulsion is D1. **Falsifier:** add a screened-Coulomb head–head term with Debye length
> `rc` and the largest aggregate must *saturate* with N instead of tracking it. If it still tracks N,
this diagnosis is wrong. To be registered before running.

---

## 5c. Harness throughput — 24 workers is SLOWER than 12

Measured 2026-09-12, mid-sweep, on the identical 300 000-step run:

| workers | s/run | throughput |
|---|---|---|
| 24 | 11 662 | 0.00206 runs/s |
| **12** | ~3 720 | **0.00323 runs/s** |

**12-way is 1.53× the throughput of 24-way while using half the workers.** The box is an AMD Ryzen 9
9950X3D — **16 physical cores, 2 threads each, 32 logical**. `nproc` reports 32, and the harness default
of 24 workers oversubscribes the physical cores; the extra processes cost more in contention than they
add in parallelism. G5's first wave therefore ran at ~65 % of achievable throughput for three hours.

This is the fourth cost-model error on record in this project (see §8). The rule that keeps being
relearned: **measure one run at the concurrency you intend to use, before planning around it.**

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
| I7 | the **test suite itself** | **RED since 2026-09-09**, `1 failed / 253 passed`, unnoticed for two days because it was not run — see below |
| I7 | gradient gate (F = −∇U) | **~2e-08** for every modulator configuration |
| I8 | cross-path gate (field vs transformer) | **0.000e+00** at every configuration |

**The open question this creates:** the historical "2 of 18" used **gate 1 only**; gate 2 (lumen size)
was added later and rejects *every* saved 2-D state. The two successful runs were overwritten on disk.
So it is **unverifiable, not refuted**. Deciding which gate defines a vesicle is a judgement call, not
a measurement — it is the top item in the reviewer handoff.

---

### I7 — the suite went red and nobody noticed, for two days

`bazel test //projects/vivarium:test_suite` → **1 failed, 253 passed, 633 s**. The failure:

```
tests/test_transformer.py::test_mlp_is_live_not_decorative
  assert np.abs(F_after - F_before).max() > 1e-6, "MLP changed h but not the forces"
  AssertionError: assert np.float64(0.0) > 1e-06
```

`_score_nonbonded` reads χ from `field._env`. `q()` and `k()` have **no caller outside the tests**, so
there is no path from the token channel `h` to the force law: an MLP that updates `h` changes nothing.

**Introduced by `decf88c5` (2026-09-09)** — the commit that fixed *two force paths computing different
physics*, which had already voided 24 runs and 48 CPU-hours. The fix was right; it silently cost this.

What is and is not affected:

- **Not affected: every number measured to date.** `test_qk_equals_the_chi_table` still pins
  `q·k == content_pairs` to 1e-12, so the two routes agree numerically. The formulation claim
  ("every force is a masked attention head whose `q·k` is the χ table") stands.
- **Affected: the wiring claim.** A per-token channel cannot influence interactions. The live MLP is
  the many-body modulator in `field` (`ShapeMLP`/`ManyBodyMLP`), which reaches the forces through
  `_env`; the token-channel MLP (`W1`/`W2`) does not, and `transformer.forward` never calls `mlp()`.
  The 2026-09-07 spec flagged the adjacent version of this as "a claim-vs-code gap" and it was never
  closed.

**Not fixed here, deliberately.** The two candidate fixes are not cleanups:

1. route χ from `q·k` — restores the wiring, but changes production trajectories at the
   eigendecomposition round-trip level (~1e-12, which over 300 000 chaotic steps is total divergence),
   so every stored result would need re-deriving and the golden tests re-baselining;
2. accept that the token channel is not the live MLP and rewrite the test to assert what is true.

Both change what the project claims. Recorded for review; **weakening the test to get green is not an
option**.

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

*Updated 2026-09-13. **Ordered by value.** This list got LONGER over 2026-09-11/12: one item closed,
the fidelity audit (§5b) opened four substantive ones. That is normal for research and is stated
rather than hidden.*

### Closed this session

- **The MLP's simplest channel is now actually tested.** Was item 3 below, previously untestable
  because both earlier attempts ran against a broken constant. G5: fails to curl at amps 0.25 / 1.0 /
  2.0, destroys the membrane dose-dependently (p = 8.0e-10). See §5.

### Open, in order

1. **Settle the token-channel decision** (`HANDOFF_2026-09-12.md` §1). Blocks the push and defines
   what the project claims. Needs a person, not a run. **Note it is also a prerequisite for item 4** —
   induced fit and history-dependent state both require the channel to reach the forces.
2. **Plant the ribbon at the spacing the model settles at** (D9). 1.7651 σ, not the hand-picked 2.05.
   The shape term currently wrecks the sheet before it can bend it because the starting sheet reads as
   16 % under-crowded; this isolates the second-order leaflet asymmetry from the first-order global
   inflation. **The single cheapest experiment most likely to move the bending question**, and under R9
   a fidelity fix worth doing regardless. ~1 h at 12-way.
3. **Raise the 2-D emergence rate.** Still ~1–2 in 20. Three *geometric* levers failed (E3, E4, E5).
   The strongest candidate is **D1, long-range head–head repulsion**: `max largest aggregate = N`
   exactly at N = 56, 80, 112, 160, so the model selects **no size** — bulk coarsening, which is what a
   single interaction range predicts. A vesicle is a finite size-selected object. **Falsifier:** add a
   screened-Coulomb head–head term with Debye length > `rc`; largest must *saturate* with N rather than
   track it. **Read §5b D1 first** — polar_pack already tried an electrostatic head, it was
   non-conservative for three months undetected, and it never produced emergence. A vivarium version
   needs a momentum test and a gradient gate from the first commit, not added later.
4. **The rest of the MLP** — none of these tested, and all three need item 1 first:
   - **induced fit** — shape adapts to *which* neighbours, not how many. The current descriptor is a
     rotationally-invariant count, so it cannot tell a molecule which *side* it is crowded on — and
     one-sidedness is what curvature is. A first-moment (vector) descriptor would; it stays zero on a
     flat symmetric bilayer by symmetry, so it passes the no-smuggling null.
   - **history-dependent state** — needs an extended Lagrangian or the energy ledger is lost.
   - **explicit rigidity** — an elastic pull toward a rest shape.
5. **Finish the registered ladder: amp 4.0.** NOT RUN, not null. `curl.py --scales 4.0 --n-ref 0.3335
   --seeds 12 --seed0 800 --workers 12`. ~1 h.
6. **Fix the fidelity defects that are not experiments** (§5b): D2 chains have zero bending rigidity
   (needs FENE + a proper stiffener), D4 no hydrodynamics (needs a pairwise DPD thermostat), D5
   harmonic bonds. Under R9 these are owed regardless of what they do to the vesicle rate.
7. **Build a validated leaflet splitter** — by lipid axis, not head radius. Needed to say *why* any
   curl happens; the radius-based attempt failed its controls (2026-09-11) and was withdrawn.
8. **Decide which gate defines a vesicle** (§6). No run can settle it. Blocks any claim about the
   historical 2/18.
9. **Rebuild 3-D on inextensible bonds (FENE).** Its bending result is retracted and everything
   downstream needs re-deriving. ~29× the 2-D cost.
10. **Run the oracle head-to-head** (AC-2, registered, never evaluated). 73.8 h/seed.
11. **Consolidation.** `def plant` in 18 files, `def build` in 15, `def step` in 12, and two force
    paths that once disagreed silently. Real work, not a file move — ~~quarantining `bicelle2d` /
    `bilayer3d`~~ was **WITHDRAWN 2026-09-11**: they are live builders for the viewer (`server.py:436`)
    and four tests, not dead legacy. That was a miscount on my part.

**Not started:** fusion and division. Neither has ever been observed.

**The objective itself is not met.** A 2-D vesicle emerges rarely; the stated goal is a self-assembled
bilayer in 3-D from excluded volume + van der Waals + electrostatics, and of those three the model has
the first two.
