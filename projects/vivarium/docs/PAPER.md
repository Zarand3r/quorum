# Vesicles from a Transformer: Emergent Bilayer Self-Assembly with Attention-Only Dynamics

**Status:** working paper, 2026-08-24. All numbers come from the run logs and the append-only
`docs/AUTONOMOUS_LOG.md`. Retracted claims stay in the text, marked, because several of them were held
for multiple days and are the most useful part of the record.

---

## Abstract

We express a coarse-grained lipid simulator entirely as a transformer and show that vesicles
self-assemble under it from a dispersed start. Every force is an unnormalised masked attention head:
the non-bonded interaction is a query-key inner product modulated by a distance function, and the
harmonic bonds are the same score-times-relative-position shape on a pair mask. One forward pass equals
one integrator step bit-for-bit, and the token channel reproduces the species interaction table to
exactly 0.0. The formulation costs what the direct integrator costs, 21.17 +- 2.42 against
20.65 +- 1.66 ms per step over five matched replicates.

Vesicles form in **2 of 18** fresh dispersed-start seeds within 10^6 steps, confirmed by an isolating
render as well as by the detector. We report three negative results that constrain the interpretation.
Line tension is **not** the driver: the tails carry `chi_TW = 0.00`, so the hydrophobic drive is absent
by construction, and a direct ring-versus-arc measurement gives lambda = +2.8 +- 2.8 eps against the
+18.31 +- 7.07 an earlier intercept fit claimed. Bending rigidity is **not measurable** here by any of
three routes. And **no dispersed-start run has ever produced two vesicles at once**, across every arm
run. Closure in this model is geometric and kinetic, not energetic.

---

## 1. The claim, and what would falsify it

Coarse-grained lipid models produce vesicles. Transformers process sequences. The claim here is that
these are the same computation, exactly rather than by analogy, and that the transformer version
produces the science result rather than merely reproducing a step.

Three things would falsify it. If the attention decomposition matched the force law only approximately,
the framing would be decorative. If the transformer path cost more per step, it would be a
curiosity rather than a formulation. If vesicles formed under the integrator but not under the
transformer, the equivalence would hold only at short horizons. Section 3 addresses the first two.
Section 4 leaves the third open, with the experiment running.

## 2. The model

The system is two-dimensional with explicit solvent. A lipid is one head bead and four tail beads in
**two branches from a single head**, which is what a real phospholipid is. Single-chain amphiphiles are
detergents: the packing parameter `P = v / (a0 * l)` has both `v` and `l` linear in tail count, so `P`
does not depend on tail length, and lengthening a linear tail from 2 to 4 to 6 never moved the phase.
Branching doubles `v` at fixed `l` and puts `P` in the bilayer band.

Interactions use a Flory-Huggins `chi` table scaling an attractive well, so `chi > 0` attracts. With
explicit water the beads feel the **exchange** energy, not the tabulated one:

```
chi_eff_ij = chi_ij + chi_WW - chi_iW - chi_jW
```

| pair | raw | effective |
|---|---|---|
| head-head | +0.20 | **-0.800** |
| head-tail | -0.25 | **-0.500** |
| tail-tail | +0.70 | **+1.200** |

The sign flip matters and cost two days of misdirected work. Raising raw `chi_HH` from 0.20 to 0.60 was
described in the log as "raising head-head repulsion" while the effective value moves from -0.800 to
-0.400, which **halves** it. The driver now prints both tables at startup.

Dynamics is velocity Verlet with an exact Ornstein-Uhlenbeck thermostat at `dt = 8e-3`, `kT = 0.45`,
`gamma = 1`.

## 3. Every force is an attention head, and the identity is exact

The non-bonded force already had attention's shape:

```
F_i = sum_j [ a(r_ij) + b(r_ij) * (q_i . k_j) ] * (x_i - x_j)
```

`a` and `b` are analytic radial functions, `q_i . k_j` is a query-key inner product read from the token
channel, and the values are **relative positions**, which is what makes the head equivariant. The
harmonic bonds and the 1-3 stiffener are the same shape restricted to a pair mask.

The token state is `(x, v, h)`. Positions and velocities are equivariant, `h` is invariant and holds the
one-hot species. `Wq` and `Wk` are the eigendecomposition factors of the `chi` table, so `q_i . k_j`
reproduces the species lookup identically rather than approximately.

### 3.1 Four assertions gate the claim

| assertion | result |
|---|---|
| heads reproduce `field.forces` on the **production** topology | **< 1e-13** relative |
| token channel `q_i . k_j` matches the `chi` table | **exactly 0.0** |
| one forward pass equals one integrator step | **bit-for-bit**, max abs diff **0.0** |
| MLP changes forces when given non-zero weights | passes |

The production-topology test matters most. Every other test builds its own bond list; this one calls
`_mixture.build`, so branched lipids and explicit water are populated exactly as a real run does. A
refactor exact on toy chains and wrong on the real topology would pass everything else.

Only **one** step is compared bit-for-bit, deliberately. Summing heads in a different order than
`field.forces` changes the last bit, and molecular dynamics amplifies that: 0 after 1 step, 1.8e-15
after 20, 4.9e-08 after 400. A multi-step tolerance would be arbitrary; the single-step identity is
exact and is the thing actually claimed.

### 3.2 The formulation is free

Five matched 400-step replicates per engine, alternating order on the same loaded machine, N = 208:

| engine | mean | sd | sem |
|---|---|---|---|
| integrator | 20.65 | 1.66 | 0.74 ms/step |
| transformer | 21.17 | 2.42 | 1.08 ms/step |

The difference is 0.52 +- 1.31 ms/step, consistent with zero. **Takeaway: expressing the dynamics as
masked attention heads costs nothing.**

### 3.3 What "transformer-only" does not cover

Three caveats travel with the claim. The attention is **unnormalised**, with no softmax, because softmax
would make each pair's contribution depend on how many other neighbours exist and would break momentum
conservation. `a(r)` and `b(r)` are **analytic**, filling the role ALiBi plays in a language model
rather than being learned; replacing them with an MLP was rejected because `well'` is sinusoidal and
both carry a `1/r` factor, so an MLP could only approximate an otherwise exact force law. And
**`W1 = W2 = 0` in every run executed**, so the MLP has contributed nothing to any result reported here.
There is no training anywhere. This is a hand-specified force field written in attention form.

A full trajectory is 1.6 x 10^6 applications of one weight-tied block. It is a single forward pass in
the sense an unrolled recurrent network is, at that depth, with a modular-wrap nonlinearity and fresh
Gaussian noise injected per layer.

## 4. Vesicles form in 2 of 18 seeds, and the picture agrees with the metric

### 4.1 Detection

Clusters come from connectivity at cut 1.4 under the minimum image. A cluster is called a vesicle when
it encloses a region **and** that region is large enough for the lipid count, `lumen >= 0.10 * n^2 / pi`,
with the call debounced at two consecutive checkpoints.

The size clause carries the discrimination. Counting **any** enclosed region across the 18 fresh seeds
gives **5/18**. Counting by the full gate gives **2/18**. The three extra seeds hold small pockets in
branched networks: sd45004 reaches lumen 122 against the 482 its 123 lipids require, a ratio of 0.253.

### 4.2 The isolating render

Whole-box frames could not settle the question. At L = 65 a 66-lipid ring is one of six structures and a
third of the frame width. We therefore isolate the largest cluster, **unwrap it across the periodic
boundary** so a boundary-crossing ring is not drawn as two arcs, and render it alone (`cluster_shot.py`).

**sd45007 at 960,000 steps is a vesicle.** A closed bilayer ring encloses a clear void, with a ribbon
tail still attached. Tails sit in the wall interior and **heads line both the outer surface and the
lumen-facing inner surface**. Largest cluster 66 lipids, lumen 460 cells, `nves = 1` for eight
consecutive checkpoints, and `perc = n` at all 49 checkpoints, so the lumen is not a periodic-wrap
artifact. A ring of the measured `R_mid = 11.16` encloses 391 cells against 460 measured.

**sd45004 at 900,000 steps is a branched network** with a small triangular gap, confirming the gate's
rejection.

### 4.3 A statistic we retract

We computed radius-from-centroid CV as a ring test and obtained **0.456 for the vesicle against 0.421
for the network**, both far above the CV well under 0.2 a ring should give. On that number we were about
to report that the gate cannot separate the two cases and that 2/18 is an artifact. The number is
correct and the inference is wrong: **the attached tail inflates the CV**, so a tailed vesicle scores
like a ribbon. **Radius CV is retracted as a ring discriminator in this system.**

**Takeaway: 2/18 stands, confirmed by picture and metric together.** Across all arms the rate is
approximately 10 in 48.

## 5. Three negative results

### 5.1 Line tension is not the driver, and the published figure was wrong

An earlier intercept fit gave lambda = +18.31 +- 7.07 eps, quoted as +40.7 +- 15.7 kT per end, implying
about 81 kT available from closure. **This is retracted.** A direct ring-versus-arc comparison at
N = 300 gives **lambda = +2.8 +- 2.8 eps, consistent with zero.**

The reason is structural, not statistical. **`chi_TW = 0.00`**: the tails are not hydrophobic, so the
exchange term that would pay for hiding an edge is absent by construction. Making the tails hydrophobic
does not fix it. That variant gives **lambda = -5.15 +- 1.49**, meaning closure becomes *less*
favourable.

An intermediate claim of 5.41 +- 1.40 eps from three paired seeds also failed at n = 9, falling to
+1.61 +- 1.67, with four of the six new seeds negative.

**Takeaway: closure in this model is geometric and kinetic. There is no energetic drive behind it.**

### 5.2 Bending rigidity is not measurable here

Three independent routes failed. The **undulation spectrum** measures its own sampling noise: per-mode
kappa spreads by 16.7x at 60 lipids and 1712x at 120, with a flat-in-q spectrum. The **critical-size
test** did not separate the sizes. The **curvature series** gives kappa = 13.84 +- 10.91 eps*sigma with
chi-squared per degree of freedom of 0.01 and a high-to-low ratio of **8.47**, failing a pre-registered
factor-of-two bar. We declined to include a span that would have passed, because adding it raises
chi-squared per degree of freedom to 1.84.

**Kappa is closed as a line of work**, per a stopping rule fixed before the last fit.

### 5.3 Multiplicity has never been observed from a dispersed start

**Zero runs, in any arm, have reached `nves >= 2` from a dispersed start.** Two simultaneous vesicles
exist only from planted or pinch-born configurations. Born-apart pairs **never merge** (8 of 8 losses
came from detector flicker at largest 52 to 52, not fusion), while pinch-born pairs re-fuse within 500
to 1500 steps. A box-size confound was tested and resolved against the box.

An earlier claim that "the model lacks a fusion barrier" is **retracted**: across ten born-apart seeds
there were zero fusion events, and what re-merges is a neck within a single membrane.

## 6. Why seeds matter is not yet answered

One seed argument fixed both the initial placement and the entire thermal noise realisation, so no
experiment could separate them. `VIVARIUM_NOISE_SEED` now overrides the noise alone, verified
bit-identical to the previous behaviour when unset.

A variance decomposition holds one factor fixed and measures the surviving spread in largest-cluster
size. **The two sampling steps disagree:**

| step | A: noise only | B: placement only | C: total |
|---|---|---|---|
| 40,000 | 5.06 | **8.54** | 8.65 |
| 80,000 | **9.73** | 7.25 | 10.50 |

`A^2 + B^2` also exceeds `C^2` at both steps (98.5 against 74.8; 147.3 against 110.3), over-explaining
the total. Both facts indicate n = 10 per arm is too small. Arms are extended to 25 seeds, with a
pre-registered stopping rule: if the decomposition remains unstable across steps, we report it as not
estimable and stop.

**One result survives both steps.** Arm A's spread is comparable to the total, not near zero.
**Fixing the initial placement does not collapse the outcome spread**, so placement alone does not
determine the result.

## 7. Method errors this project made, and the guards installed

This section exists because the errors were more instructive than most of the positive results.

| error | consequence | guard |
|---|---|---|
| Read stale `/tmp` logs from dead runs, four times | reported trends from finished experiments | `status.sh` reads `/proc/<pid>/fd/1`, live processes only |
| `_save_state` filename carries no step or run identity | relaunching five seeds destroyed the historical states their closure sizes were measured from | hazard documented at the call site; `docs/states_protected/`; `VIVARIUM_SAVE_ALL` |
| Described a raw `chi` change by its raw sign | ran a lever backwards for two ticks | driver prints raw **and** effective tables at startup |
| Sampled every 20,000 steps | merged about 3.8 closure episodes into one; closed-state lifetime median is 6,000 steps, 69% shorter than one interval | checkpoint interval is now a swept variable |
| Pre-registered thresholds against the wrong baseline | a clause could not fire as written | baselines stated numerically in the registration |
| Pre-registrations with missing branches | three outcomes occurred that no branch covered | registrations must enumerate an "other" branch |

**Takeaway: in this project the render and the metric have each flattered the other. A structural claim
now requires both, and the render must isolate the object being claimed.**

## 8. Limitations

The system is **two-dimensional**. A 2-D vesicle is a ring, and the packing arguments transfer only
loosely.

**Three-dimensional explicit solvent does not work yet** at packing fraction 0.15 to 0.35, where the
solvent is fragmented droplets rather than a liquid. Every 3-D result is therefore void.

**The MLP is inert**, `W1 = W2 = 0`, and nothing is trained.

**No result has yet been produced by the transformer path.** All results reported here come from the
integrator calling `field.forces` directly. This was discovered on 2026-08-24: a launch script omitted
`VIVARIUM_ENGINE=transformer`, and the six-seed arm committed two days earlier as the transformer
emergence arm had been running the integrator. Six matched transformer seeds are now running against
six integrator seeds as a control. The equivalence is proven per step; **it is not yet demonstrated
across a full emergent trajectory.**

## 9. What would change the conclusion

**Making the tails hydrophobic** by setting `chi_TW < 0` would supply the missing drive. Measured
in isolation it makes closure worse (lambda = -5.15 +- 1.49), so it must be paired with a compensating
change rather than applied alone.

**Working in three dimensions** requires first fixing the solvent, which is the largest single blocker.

**Training the MLP** would make the architecture claim substantive rather than structural.

## 10. Reproduction

```
bazel test //projects/vivarium:test_suite          # 157.6 s, 1 of 1 PASSED

# one emergent run, dispersed start
VIVARIUM_CHI_HT=-0.25 VIVARIUM_CHI_WW=0.50 VIVARIUM_CHECKPOINT_EVERY=20000 \
  ./bazel-bin/projects/vivarium/_mixture 1600000 2 160 0.0 65 0.45 0.55 random 45007

# the same run with the dynamics as a transformer forward pass
VIVARIUM_ENGINE=transformer ...same arguments...

# isolate and unwrap the largest cluster
python3 projects/vivarium/cluster_shot.py <state.npz> out.png
```

Arguments are `steps d n_lip frac_short L kT phi plant seed`. `VIVARIUM_NOISE_SEED` overrides the
thermal noise independently of placement.

**Log column map:** 1 step, 2 E/lip, 3 largest, 4 R_mid, 11 lumen_c, 12 nenc, 13 perc, 19 nves.
