# The potential–flux structure of living dynamics — and what it demands of the architecture

> **The question (theoretical biology).** Does there exist a *single scalar functional*
> whose gradient generates the effective dynamics of a living system, or does life
> irreducibly require **coupled, nonequilibrium vector fields** that cannot be reduced to
> one global objective? If the latter, future AI architectures may need to move **beyond
> explicit loss minimization during inference** and instead operate as self-organizing
> dynamical systems held **away from equilibrium**.

**Honest bottom line up front.** It is *not* a clean either/or, and the resolution is the
same shape as [`global_vs_local.md`](global_vs_local.md)'s: **a scalar can always be
*written down*, but away from equilibrium its gradient alone does not *generate* the
dynamics — the irreducible piece is a non-conservative circulating flux `J`, the signature
of broken detailed balance.** The vector-field view is the fundamental one; each famous
"scalar principle" is that scalar *for the sub-regime where its flux happens to vanish*.
This is largely **settled physics**, not an open mystery — which bounds how much a toy can
contribute (§6). Where vivarium *can* contribute is turning "non-equilibrium" from a vibe
into a **measured number** and testing whether aliveness requires it (§5).

This document is theory + deferred research program. It is **not** first-pass scope: the
core sim (M0–M2, [`../SPEC.md`](../SPEC.md)) is built first; the experiments here (§5) are
**post-core**. See [`related_work.md`](related_work.md) §3–4 for the training-route fork and
the architectural directions this motivates.

---

## 1. The mathematical core

### 1.1 Helmholtz–Hodge: a scalar always exists; the question is whether its gradient suffices

Any smooth flow decomposes into a gradient part and a divergence-free (solenoidal) part:
```
ẋ = −∇Φ(x)  +  J(x),     ∇·J is the circulating component
```
So writing down *a* scalar `Φ` is never the issue. The question is whether `J ≡ 0`.

### 1.2 The theorem that forces the issue: gradient systems cannot oscillate

For a pure gradient system `ẋ = −∇Φ`, `Φ` is a Lyapunov function: `dΦ/dt = −‖∇Φ‖² ≤ 0`.
Therefore a gradient system **monotonically descends to a fixed point** and **can have no
limit cycles, no sustained oscillation, no chaos** (standard; e.g. Strogatz, *Nonlinear
Dynamics and Chaos*, §7 & §6). Consequence: *anything* with a circadian rhythm, a cell
cycle, a metabolic or glycolytic oscillation, a heartbeat — the defining tempos of life —
**cannot** be `−∇` of any scalar whatsoever. This is not a modelling preference; it is a
theorem. It is also exactly why the sibling **morph** sim only stopped collapsing once a
*non-gradient* skew term `Ω·(x·J)` was added — empirically rediscovering that `J ≠ 0` is
mandatory for non-settling dynamics.

### 1.3 The nonequilibrium decomposition: landscape + flux

For a stochastic system `dx = b(x)dt + √(2D)dW` with stationary density `p_ss`, define the
**nonequilibrium potential** `Φ = −log p_ss`. The drift decomposes (Ao 2004; Wang et al.
2008; Qian 2006) as
```
b(x) = −D ∇Φ(x)  +  J_ss(x)/p_ss(x),
```
where `J_ss` is the **stationary probability current**. At **equilibrium** (detailed
balance) `J_ss ≡ 0`: the dynamics *are* pure gradient descent of `Φ`, and the system is
**settled — i.e. dead**. Away from equilibrium `J_ss ≠ 0`: `Φ` still exists as a *landscape*
(useful for multistability, differentiation, switching), but **its gradient does not
generate the dynamics** — the current circulates *along* level sets and is orthogonal to
`∇Φ` at steady state. Life lives in the `J_ss ≠ 0` regime, definitionally.

### 1.4 Two subtleties that strengthen "no single global scalar"

- **The split is not unique.** The Ao, Wang (steady-state/orthogonal), and Freidlin–Wentzell
  quasipotential constructions yield *different* `Φ` and `J` for the *same* dynamics. There
  is no canonical scalar to crown.
- **`Φ` may not exist globally.** In genuinely nonequilibrium, multistable systems the loop
  integral of the current is nonzero, so a smooth single-valued global `Φ` need not exist
  (only local quasipotentials do). This is the strongest form of "irreducible vector field."
- **The rigorous nonequilibrium results are relations, not variational principles.** The
  fluctuation theorems (Jarzynski 1997; Crooks 1999) are *exact equalities constraining the
  distribution of entropy production* — they do **not** hand us a scalar to extremize. At the
  exact level where nonequilibrium physics is rigorous, there is no governing potential.

---

## 2. The five candidate scalars — one decomposition at five coarse-grainings

The famous "scalar principles" are **not rivals for one throne.** Each is the valid scalar
*for the subsystem / timescale / coordinate where its flux term vanishes or is negligible*:

| Candidate | Governs | Regime where it's valid | Honest status | In our stack |
|---|---|---|---|---|
| **Gibbs / Helmholtz free energy `G`** | folding, binding, self-assembly | fast **equilibrium-seeking** subsystems (`J≈0`) | rigorous, but silent on the driven whole | the **fold** sim — docking descends a free-energy-like score and *converges*, exactly as `G` predicts |
| **Entropy production `Ṡ_tot`** | dissipation in driven systems | none universally; constraint-dependent | **weakest as a *potential*** — MEPP heuristic & disputed (Dewar), Prigogine min-EP only near-equilibrium; it is a **diagnostic, not an objective** | the *measurement* side of measure-don't-optimize |
| **Quasipotential `V(x)`** | cell states, differentiation, switching | slow collective coords of a driven system | real, but **only the gradient part** follows it; currents remain; non-unique; maybe non-smooth | the aliveness *landscape* we watch, not the generator |
| **Variational free energy `F[q]`** (FEP) | persistent self-maintaining systems | inference/belief coords | broadest proposed scalar, **but carries its own solenoidal `Q` term** (`(Γ−Q)∇`) → exemplifies the decomposition, doesn't escape it; breadth ⟷ contested falsifiability | the "predict your neighbours" objective (Route B) |
| **Fitness / long-run growth rate** | lineages | population, deterministic (mean-field) limit | a genuine **Shahshahani-metric gradient** (Sella & Hirsh 2005), but wrong *level & clock* — populations over generations, not instantaneous molecules | (out of scope — we don't do multi-generation selection in the core) |

**The unifying reading.** There is a scalar for **every subsystem you let settle**; there is
**no scalar for the whole** because *life is the coupling `J` that ferries free energy from
the driven parts to keep the relaxing parts from bottoming out.* `Φ` describes each part; `J`
is the metabolism linking them; and `J` is not `∇` of anything. This is why the honest answer
is the user's synthesis equation, not pure gradient descent:
```
ẋ = −D ∇Φ(x)  +  J(x)  +  noise
      \______/    \__/
      relaxation   metabolism-powered circulation (irreducible)
```

---

## 3. What is settled vs genuinely open

**Settled (don't overclaim novelty here):**
- Gradient systems cannot sustain oscillation/chaos (theorem, §1.2).
- Living matter **breaks detailed balance** — *measured*, not just theorized: Battle et al.
  (Science 2016) detected closed flux loops (nonzero `J`) in beating cilia and cytoskeletal
  networks. Nonzero entropy production in active biological systems is experimental fact.
- Equilibrium ⇒ pure gradient ⇒ settled; life ⇒ `J≠0`. Not controversial.

**Genuinely open / contested (where the interesting exploration is):**
- Whether any **single** nonequilibrium variational principle governs steady-state
  *selection* (MEPP and relatives are unproven and constraint-dependent).
- The **universality and falsifiability of the FEP** as *the* scalar for living/inferring
  systems (its solenoidal term and "as-if" framing are the crux of the debate; Aguilera et
  al. 2021).
- England-style **dissipation-driven adaptation** (2013; Perunov–Marsland–England 2016): does
  strong driving *statistically* push systems toward high-dissipation, hard-to-reach
  organized states? Suggestive, not established — and directly testable in a toy.
- Whether a system can be **kept alive by a purely *internal* non-gradient term** (rotational
  `J`) with **no external drive** at all, and whether that still counts as "thermodynamic"
  (ties to `global_vs_local.md` open-Q7 and the morph skew term).

---

## 4. Mapping to the architecture — why this is decision-relevant, not just elegant

The synthesis equation is *almost verbatim* what **Route B** ([`related_work.md`](related_work.md) §3)
implements as a weight-update:
```
θ̇ = −η ∇_θ L_predict        +   η ∇_θ R_anti-collapse     +   SGD noise
     \__________________/         \____________________/
     −D∇Φ  (relaxation:            J  (engineered circulation:
     descend prediction error)     variance floor / drift keeps it off-equilibrium)
```
Three consequences that turn the physics into concrete, falsifiable design claims:

1. **Route B sits on the right side of the physics** — it is literally `−D∇Φ + J` — **iff we
   keep `J`.** A pure-prediction objective is `J=0`: it descends to the "perfect prediction ⇒
   nothing changes ⇒ frozen" fixed point. This is the *same* death the fold/quasipotential
   regime predicts.
2. **`J → 0` predicts death, not merely "less interesting."** Dropping the anti-collapse term
   (Route B) or the external drift (Route A) drops the system into the gradient regime →
   settle → dead. This is now a *prediction the sim can falsify*, not a vibe.
3. **The right observable is the non-conservative component.** Aliveness should track `‖J‖` /
   entropy production / degree of broken detailed balance; a gradient-only arm should
   flatline. See §5.

Route A vs Route B, restated thermodynamically: **both must inject `J`** — Route A via an
external drift field, Route B via an anti-collapse loss term (or non-stationary data). The
morph skew term is the same `J` discovered empirically. Equilibrium Propagation (F4? — no,
F1 in `related_work.md` §4) is the option that supplies `J` while keeping strict locality.

---

## 5. Deferred research program (POST-core — do not pull into M0–M2)

Turn the philosophy into measured, binary results *after* the core sim earns (or honestly
fails to earn) aliveness. Each rides the existing measure-don't-reward harness; **none feeds
back into the update** (P3).

**E-flux1 — Measure the flux.** Instrument the running colony for the non-conservative
component: (a) **entropy production rate** via the fluctuation-theorem / Kullback estimator
on forward-vs-time-reversed trajectory probabilities; (b) **broken-detailed-balance** area
loops in coarse-grained phase space (the Battle et al. 2016 method); (c) the discrete
**probability-current** `J_ss` on a binned state space. *Deliverable:* a live `‖J‖` /
`Ṡ` readout beside the aliveness gauge.

**E-flux2 — The central correlation.** Test the sharpened claim:
> **measured aliveness > threshold ⟺ nonzero steady-state flux `‖J‖ > 0`.**
Sweep the drive (drift rate / anti-collapse weight) and plot aliveness vs `‖J‖`. Prediction:
they rise together; there is a drive threshold (the economy's `v*` analog) below which both
collapse. *Gate:* a monotone, documented relationship or an honest refutation.

**E-flux3 — `J → 0` kills it.** Ablate the circulation directly: set anti-collapse/drift to
zero (Route B) or freeze the drive (Route A). Prediction: the system relaxes to the `−D∇Φ`
fixed point and measured aliveness → 0 within a bounded window, while a matched arm with `J`
on stays alive. *Gate:* the ablation dies, the control lives — the cleanest possible
demonstration of `−D∇Φ + J`.

**E-flux4 — Gradient-only control (the global scalar arm).** Build a genuine pure-gradient
variant — descend a fixed global `Φ` (energy-based, equilibrium, no solenoidal term) over the
same substrate — and confirm it settles/dies at *every* drive setting, mirroring the fold and
the frozen economy control. This is the M3 global-vs-local experiment
([`global_vs_local.md`](global_vs_local.md) §6) upgraded with the flux lens: the question
sharpens from "do global and local rules match" to **"does the *conservative* part ever
suffice, or does aliveness strictly require the *non-conservative* flux?"**

**E-flux5 (speculative) — Intrinsic vs external `J`.** Compare aliveness sustained by a purely
*internal* rotational term (skew, no environment) vs an *external* drift, at matched `‖J‖`.
Addresses §3's open question and `global_vs_local.md` Q7.

---

## 6. Honest bound on what this can yield

A `d≈8` petri dish cannot *resolve* whether life needs coupled nonequilibrium vector fields —
the physics is largely settled (broken detailed balance is measured; gradient systems
provably can't oscillate) or rigorously open in ways a toy won't move (MEPP, FEP
universality). What vivarium can be is a **clean, watchable, instrumented instance of
`−D∇Φ + J`** in which one can *dial `J` to zero and watch measured aliveness die while measured
flux collapses*, and correlate the two ungameably. That is **demonstration with a number on
it**, not resolution — which is more than most of this discussion gets, and exactly the
project's discipline (measure, don't admire).

The one-sentence thesis (the user's, sharpened): *living systems possess local objective-like
landscapes `Φ` while fundamentally depending on metabolism-powered, non-conservative dynamics
`J` that never descend a single global scalar — and an architecture that wants to stay "alive"
during inference must therefore be a maintained-off-equilibrium flow, not a descent to a
fixed point.*

---

## 7. Relationship to the other design docs

- [`global_vs_local.md`](global_vs_local.md) — the narrower "can a global rule give
  Game-of-Life life" question; §3 there already invokes the Helmholtz rotational term. This
  doc is its rigorous thermodynamic completion; the M3 experiment there is E-flux4 here.
- [`related_work.md`](related_work.md) — §3 training routes (A/B) are the `−D∇Φ+J`
  implementation choices; §4 F1–F5 are architectural ways to supply `J` (skew term, EqProp).
- [`two_tracks.md`](two_tracks.md) — the molecular (energy, `−∇Φ`) and organism (predictive)
  tracks are the two halves of `ẋ = −D∇Φ + J` at two biological scales; E-flux4 here (§5) is
  promoted there to a first-class pair of sims.
- [`../SPEC.md`](../SPEC.md) — M3 is where E-flux4 lands; E-flux1–3 are post-M2 instrumentation.
- [`../DECISIONS.md`](../DECISIONS.md) — records the one-clock / measure-don't-reward choices
  this doc gives the thermodynamic justification for.

---

## References

*(informal; enough to locate.)*
- **Helmholtz–Hodge / gradient systems:** Strogatz, *Nonlinear Dynamics and Chaos*, §6–7.
- **Potential–flux decomposition:** Ao, *J. Phys. A* 37:L25 (2004); Wang, Xu & Wang, *PNAS*
  105:12271 (2008); Qian, *J. Phys. Chem. B* 110:15063 (2006).
- **Quasipotential / large deviations:** Freidlin & Wentzell, *Random Perturbations of
  Dynamical Systems* (Springer).
- **Fluctuation theorems:** Jarzynski, *PRL* 78:2690 (1997); Crooks, *PRE* 60:2721 (1999).
- **Broken detailed balance, measured:** Battle et al., *Science* 352:604 (2016).
- **Dissipation-driven adaptation:** England, *J. Chem. Phys.* 139:121923 (2013);
  Perunov, Marsland & England, *PRX* 6:021036 (2016).
- **Dissipative structures / entropy production:** Nicolis & Prigogine, *Self-Organization in
  Nonequilibrium Systems* (1977); Martyushev & Seleznev, *Phys. Rep.* 426:1 (2006) [MEPP review].
- **Fitness–free-energy / replicator gradient:** Sella & Hirsh, *PNAS* 102:9541 (2005);
  Shahshahani metric (Shahshahani 1979; Harper 2009).
- **Free Energy Principle & its solenoidal term:** Friston, *Nat. Rev. Neurosci.* 11:127
  (2010); Aguilera, Millidge, Tschantz & Buckley, *Phys. Life Rev.* (2021).
- **In-context learning as gradient descent (Route B tie):** von Oswald et al., ICML (2023).
