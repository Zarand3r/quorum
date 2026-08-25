# Performance: deferred work, ordered by measured payoff

**Status: NOT STARTED, deliberately.** Correctness comes first. Every item below changes either the
trajectory statistics or the numerical guarantees the project's verification rests on, so none of it
should land until the physics questions are settled. This file exists so the analysis is not re-derived
later.

**Do not start here.** Start at Section 5, which argues that raw speed is the wrong lever for the
bottleneck this project actually has.

---

## 0. The measurement everything below rests on

One production step, N = 160 lipids in L = 65, unloaded, numpy float64:

```
beads 2959    water 2159 (73%)    lipid beads 800
neighbour pairs 30,421      dense would be 4,376,361
   water-water   18,336 (60%)
   water-lipid    8,854 (29%)
   lipid-lipid    3,231 (11%)   <- the only interaction we measure anything from
forces()  5.42 ms       _pairs()  1.23 ms
```

**The Verlet neighbour list already works**, cutting 4.38M candidate pairs to 30,421, a factor of 144.
`field.py` builds it with a skin and a cell-list rebuild, and `check_neighbor_list` gates it against a
dense reference path. **Do not "add a neighbour list."** It is there.

**89% of the pair work involves water.** That is the finding that orders this list.

Engine cost is the same either way, so none of this is a transformer tax: 5 matched 400-step replicates
gave integrator **20.65 +- 1.66** and transformer **21.17 +- 2.42** ms/step under load.

---

## 1. Go solvent-free. Roughly 9x, and the machinery already exists.

`solvent_averaged_chi` is already implemented in `field.py`, and the effective table it produces is the
one the paper says the beads actually feel:

```
chi_eff_ij = chi_ij + chi_WW - chi_iW - chi_jW
```

Dropping explicit water and running on `chi_eff` reduces the pair list from **30,421 to about 3,231**.
This is the Cooke-Deserno solvent-free model, which the project already cites as its reference.

**Why it is better justified here than usual:** `chi_TW = 0.00`, so the tails are indifferent to water.
In this parameterisation the explicit solvent is close to dead weight, which is also why the line
tension is about zero.

**What it costs:** every water-mediated effect disappears, including the lumen osmotics that
`VIVARIUM_LUMEN_FILL` just used to produce a dumbbell. **A solvent-free build cannot run the fission
experiment**, so this is not a free swap. The driver already supports `phi = 0`.

---

## 2. Batch seeds on a GPU. The largest available win, and the one the architecture is shaped for.

Dense attention over 2,959 tokens is a 4.4M-entry score matrix, which is small by transformer standards.
**On a GPU the neighbour list stops being necessary at all** and dense masked attention is simpler and
faster than the sparse path.

**The real win is the batch dimension.** Formation is rare, 2 of 18 seeds, so the science needs seeds
more than it needs single-run speed. In the attention formulation seeds are a leading batch dimension,
so 128 seeds run in one batched forward pass. **Sequential seed count is the binding constraint on every
statistical claim in this project**, including the 0/5-against-4/15 that is currently under-powered.

Port target: numpy to torch or JAX. The head decomposition in `transformer.py` maps directly.

**What it costs:** float32 by default (see Section 3), and a second implementation to keep in sync with
the reference path.

---

## 3. float32. About 2x on memory bandwidth.

The force law does not need 64-bit.

**What it costs:** `test_one_forward_pass_is_one_integrator_step_exactly` asserts
`np.abs(Xa - Xb).max() == 0.0`. That assertion **cannot survive** a dtype change and would have to be
restated as a tolerance, which weakens the strongest correctness guarantee the project has. Do this only
together with Section 2, and keep a float64 reference path for the gate.

---

## 4. Multiple timestepping (RESPA). Roughly 2-4x, nearly free.

`dt = 8e-3` is capped by stiff bond vibration, while the expensive non-bonded forces are soft and vary
slowly. Update non-bonded every 2-4 inner steps and bonded every step.

**What it costs:** trajectories change, so the 23,587-line log's numbers stop being directly comparable.

---

## 5. Raw speed is the wrong lever. Read this before doing any of the above.

**Closure is a rare event.** Runs wait 600,000 to 1,000,000 steps and 16 of 18 seeds never close at all.
**A 100x speedup still leaves you sampling a rare event, just faster.**

**The project already owns a validated reaction coordinate**, which most projects never get: the
**end-to-end gap**. Section 5 of `PAPER.md` establishes that a 6x change in gap moves the closed fraction
from 0.000 to 0.512, while length and radius move it 1.46x and the wrong way respectively.

**Bias along the gap instead of waiting.** Umbrella sampling or metadynamics along the end-to-end gap
returns the **free-energy profile of closure directly**, for a fraction of the compute. It also delivers
the two numbers three separate measurement routes failed to produce: **the line tension and the closure
barrier height**. Replica exchange across a kT ladder is the alternative, and it is another batch
dimension that composes with Section 2.

**This is the highest-value item in this file.** Sections 1 to 4 make the same experiment cheaper.
Section 5 changes which experiment you run.

---

## 6. Learned propagator. Flagged as speculative; do not reach for it early.

`W1 = W2 = 0` in every run ever executed, so the MLP has contributed nothing to any result. Training it
as a multi-step propagator is the honest destination of "transformer-only."

**What it costs:** the exactness on which the entire verification rests. Every correctness claim in this
project reduces to "the heads reproduce `field.forces` to 1e-13 and one pass equals one step bit-for-bit."
A learned propagator has neither property. **Do not do this until the physics is settled and there is a
fixed benchmark it can be scored against.**

---

## 7. Re-baselining protocol, required for items 1, 4, 5 and 6

All four change trajectory statistics, so **no number in `AUTONOMOUS_LOG.md` stays comparable across
them.** Any of them must reproduce a known result before its output is trusted.

**The cheapest validation is the gap dose-response**, since it is the project's strongest and most
replicated measurement: planted arcs at n = 80 must give closed fractions of **0.000 / 0.027 / 0.350** at
gaps of 26.7 / 14.1 / 4.2 sigma. A build that fails to reproduce that curve is wrong, whatever its
speed.

Second gate: `bazel test //projects/vivarium:test_suite` must stay green, or its weakened assertions must
be stated explicitly (see Section 3).
