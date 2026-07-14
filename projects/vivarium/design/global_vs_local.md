# Global vs local rules — can a global thermodynamics rule give Game-of-Life life?

> **The question (user's):** Game of Life uses a *local* update rule. Can we get the
> same emergent, interacting, never-settling dynamics from a **global thermodynamics
> rule** instead — or is a local rule the *only* way?

Short answer: **local is not the only way — but "global vs local" is largely a false
dichotomy.** The properties that actually matter are **finite-range interaction** and
**far-from-equilibrium**, and a *global* thermodynamic rule can have both. A global
energy with local terms and a local update rule are often *the same object* seen two
ways. What genuinely *fails* is (i) truly global **all-to-all/mean-field** coupling and
(ii) pure **equilibrium** energy minimization — and, tellingly, those are exactly the
two collapse modes this project keeps running into.

---

## 1. The duality: a global energy with local terms *is* a local rule

Take a global energy `E(x) = Σ_i U(x_i) + Σ_{i~j} V(x_i, x_j)` where `i~j` means *near
neighbors only*. Gradient-descend it:

```
dx_i/dt = −∂E/∂x_i = −U'(x_i) − Σ_{j~i} ∂V/∂x_i
```

Because `E`'s couplings are local, `∂E/∂x_i` depends **only on i's neighbors** — the
"global rule" (descend `E`) *is* a local update rule. This is not a coincidence; it's
how most of physics works:

- **Ising / spin glasses:** global `E = −Σ_{i~j} J_ij s_i s_j`; local spin flips;
  domains, phase transitions, pattern formation.
- **Cahn–Hilliard, Swift–Hohenberg, reaction–diffusion as gradient flows:** global free-
  energy functional with local gradient terms → spinodal/Turing patterns.
- **Hopfield nets / Boltzmann machines:** global energy; **local** update (each unit
  uses its local field); emergent attractors. Boltzmann *learning* is also local
  (`Δw_ij ∝ ⟨s_i s_j⟩_data − ⟨s_i s_j⟩_model`).

So "is a local rule the only way?" — no: **a global thermodynamic functional whose
interactions are finite-range produces a local rule automatically.** They are dual
descriptions, related by `dynamics = −∇(energy)`.

## 2. What actually kills the emergence — and it's not "being global"

**(a) All-to-all / mean-field coupling.** If every element instantly affects every
other (infinite interaction range), there is no bounded propagation speed, no spatial
structure, no gliders, no Turing patterns. Mean-field systems synchronize or
homogenize. **This is precisely the global-softmax-attention collapse** the thermolife
HK study measured, and the "infinite diffusion rate" that forbids Turing patterns.
Locality here means **finite interaction range**, and it is genuinely necessary — but a
*global energy* can be finite-range (Ising is), so this is not an argument for a local
*rule*, it's an argument against *infinite-range* interaction.

**(b) Pure equilibrium minimization.** A rule that just descends a fixed energy
**converges** — it settles into the minimum (Hopfield → an attractor and stops). That
is the *opposite* of "never settling." Game of Life and life are **non-equilibrium**:
driven, dissipative, perpetually in flux. So a naive "global thermodynamics = minimize
free energy" rule gives you death-by-convergence, the same failure as a global training
loss that finds its optimum.

## 3. What a *global* rule needs to stay alive: non-equilibrium

To never converge, a global thermodynamic rule must be **far from equilibrium** — one
of:

- **Driven / dissipative (Prigogine's dissipative structures):** sustain order by
  continuous energy/matter throughput. Convection cells, BZ reaction, life. Globally
  thermodynamic, never settling — because of *flux*, not because of locality. (This is
  the "gentle drift / energy input" ingredient — D7.)
- **Non-gradient (rotational) dynamics:** by the Helmholtz decomposition any flow is
  `f = −∇E + (rotational part)`. The rotational part is **not** the gradient of any
  potential, so it produces **limit cycles / perpetual orbits** — never a fixed point.
  This is exactly the skew-symmetric oscillator term the morph needed. A global rule can
  include it; then "energy" alone doesn't govern the dynamics.
- **Maximum entropy production / non-equilibrium variational principles:** proposed
  global principles selecting *steady states with ongoing flux* rather than static
  minima. (Less rigorously established — flag as speculative.)

So: **global + finite-range + non-equilibrium can, in principle, reproduce the
emergence.** It's the *equilibrium* and the *mean-field* assumptions that break it,
not globality per se.

## 4. The punchline: our chosen local rule is a global thermodynamic principle in disguise

We picked **predictive plasticity** (each bacterium reduces its surprise about its
neighbors). That is the **local implementation of a global variational principle** —
the **Free-Energy Principle** (variational free energy = surprise + complexity;
predictive coding is its local message-passing process theory). Minimizing a *global*
variational free energy **decomposes into local prediction-error updates** exactly
because the free energy factorizes over local (Markov-blanket) terms.

So for vivarium the two framings are the *same coin*:

| Global (thermodynamic) view | Local (rule) view |
|---|---|
| minimize variational **free energy** `F = surprise + complexity` | each bacterium does **predictive-error** plasticity |
| energy factorizes over local Markov blankets | updates use only neighbors |
| driven off-equilibrium by the **drift** → non-equilibrium steady state | never fully predicts → never converges |

The global rule and the local rule are **dual**, joined by the free energy having local
structure. Locality is not the *only* way; it's the *efficient, biological* way to
implement a finite-range, non-equilibrium global principle.

## 5. Answer, sharpened

- **Is a local rule the only way?** No. A **global thermodynamic rule works iff** it is
  **(a) finite-range** (not mean-field) and **(b) non-equilibrium** (driven and/or
  non-gradient). Under those conditions it *is* a local rule, by duality.
- **What can't work:** truly **all-to-all/mean-field** coupling (homogenizes → collapse)
  or pure **equilibrium minimization** (settles → dead). These are the project's two
  recurring failure modes, now named thermodynamically.
- **The real necessary conditions** are therefore *finite interaction range* + *far from
  equilibrium* — **not** "local vs global." "Local rule" is one (biological, efficient)
  encoding of exactly that.

## 6. Experimental program (vivarium M3)

Make it empirical, not rhetorical. Build **two update engines over the same substrate,
same measured-aliveness harness**:

1. **Local engine:** predictive-plasticity, per-tick, neighbor-only (the M1/M2 default).
2. **Global engine:** a **non-equilibrium energy-based** rule — a global functional
   `F` with *finite-range* interaction terms, evolved by (gradient flow of `F`) **+ a
   non-gradient/driven term** (the drift) so it doesn't just minimize. Same locality of
   *interaction*, but the update is written as "descend/flow the global `F`."

Then **measure**: do they land in the same aliveness / pattern regime? Predictions from
§4: with matched finite range + matched drive, **yes** (they're dual); strip the drive
→ the global engine *converges* (dies) while the local predictive one, being
continually surprised, keeps moving; make either **mean-field** → both collapse.

That experiment turns the philosophical question into a **binary, honest result** —
which is the whole point of building it.

## 7. Open sub-questions to keep

- Is there a *global* rule that is genuinely **non-decomposable** into local updates yet
  still pattern-forms? (Long-range-but-not-mean-field kernels; power-law interactions.)
- Does the drive have to be **external** (drift) or can a purely **internal**
  non-gradient term (rotational/oscillatory) sustain aliveness with *no* environment —
  and is that still "thermodynamic"? (Ties back to the (a)/(b) intrinsic-vs-external
  discussion in the main thread.)
