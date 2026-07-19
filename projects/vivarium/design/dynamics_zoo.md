# Dynamics zoo — drives, combining/breaking, and what stays "transformer only"

A catalogue of mechanisms for making the vivarium dish do more than swirl, each with the math,
its biological faithfulness, and whether it stays **transformer-only** (attention + MLP + norms +
structured/learned linear layers + architecture mods — *not* external geometric rules, energy
ledgers, or population controllers). Written 2026-07-19 while exploring past the skew-rotation
default.

## 0. Why skew rotation is the floor, not the ceiling

The hosted sim avoids collapse with a **skew term** `X·J` (`J = −Jᵀ`) and **non-reciprocal
attention** `A + β(A−Aᵀ)`. Both are *antisymmetric operators* — the Lie algebra of rotation — so
they give the mathematically-minimal non-settling motion: **rotation**. It's linear, imposed
uniformly, and conservative (orthogonal, energy-preserving). Biology is none of those:
**nonlinear, emergent from interaction, and dissipative.** The mechanisms below fix exactly those
three properties. See also [`potential_flux.md`](potential_flux.md) (`ẋ = −D∇Φ + J`; skew is the
linear `J`), [`dock_and_morph.md`](dock_and_morph.md), and the thermolife paper §2 (grounding).

## 1. Alternative drives (replace/augment the skew)

Ordered by biological faithfulness. "TX-only" = stays transformer-only.

### Reaction–diffusion (Turing / Gray–Scott) — TX-only ✅ (most native)
```
∂u/∂t = D_u ∇²u + f(u,v)     ∂v/∂t = D_v ∇²v + g(u,v)   (D_v ≫ D_u; f,g nonlinear)
```
Nonlinear autocatalysis + **differential diffusion** → spots, stripes, chemical waves,
self-replicating blobs (animal coats, BZ reaction, morphogenesis). **Maps almost exactly onto the
block:** attention *is* diffusion (a graph-Laplacian smoothing `A·X − X` over neighbours), the
**MLP is the nonlinear reaction**. The one new ingredient is **per-channel diffusion rates**
(activator slow, inhibitor fast) — a structured architecture choice, still transformer-only. This
is the first one we're trying.

### Excitatory–inhibitory (Wilson–Cowan / neural fields) — TX-only ✅
```
du/dt = −u + σ(w_ee·u − w_ie·v + I)     dv/dt = −v + σ(w_ei·u − w_ii·v)
```
E excites I, I suppresses E, through a **saturating nonlinearity** σ. Oscillation, traveling
waves, multistability *emerge* from the interaction. Implemented as **two attention heads**
(short-range excitatory / long-range inhibitory) + a sigmoid. The canonical biological
pattern-former; subsumes reaction-diffusion.

### Excitable (FitzHugh–Nagumo) — borderline ⚠️
```
dv/dt = v − v³/3 − w + I     dw/dt = ε(v + a − b·w)
```
Fast cubic excitation + a **slow recovery variable** → threshold-triggered *spikes* and traveling
*pulses* with a refractory period (action potentials, calcium/cAMP waves, quorum pulses). The most
faithful to how cells actually signal. Needs a two-timescale gated channel — a neural-net
primitive (gated attention/SSMs) but stretches "vanilla transformer."

### Dissipative / metabolic (Prigogine) — NOT TX-only ❌
```
dx/dt = −∇Φ + source − sink   (non-equilibrium steady state via throughput)
```
Life stays alive by *dissipating* energy, not rotating. Requires an explicit energy variable +
injection + consumption + a conservation ledger — external bookkeeping (the economy sim,
thermolife `eco/`). Most thermodynamically faithful, but outside the transformer.

### Lotka–Volterra / predator–prey — borderline ⚠️
```
dx/dt = x(α − βy)     dy/dt = y(δx − γ)
```
Oscillation *emergent from the nonlinear `xy` interaction* (eating), not imposed. The bilinear
coupling is attention-native; "populations that grow/shrink" want extra state.

## 2. Combining into larger shapes / breaking apart

Currently impossible: fixed N, separate point-blobs, no adhesion-as-a-unit, no birth/death.

| Ingredient | Effect | TX-only? |
|---|---|---|
| **Type-conditioned adhesion** | strong short-range attraction by type/shape → clusters that move as a unit (Particle-Life "cells", self-assembly) | ✅ if via **attention** (types = channels, adhesion = content-based attention); ❌ if a hand-coded type-force matrix |
| **Metaball / field rendering** | draw the union of nearby contours as *one* outline → clusters *look* like a larger shape | ✅ it's *rendering* (read-only, orthogonal to the dynamics) |
| **Instability-driven breaking** (E–I / excitable) | clusters that form *and dissolve* rhythmically (slime-mold streaming) | ✅ (E–I) / ⚠️ (excitable) |
| **Division / birth–death** | one shape literally becomes two; population grows (economy sim's `e_div`/death) | ❌ **variable N = external population controller** |

## 3. The transformer-only boundary (the through-line)

What breaks "transformer only" is anything that **adds state or machinery beyond a fixed set of
token embeddings**:
- an **energy ledger** (metabolism), or
- a **variable token count** (division/population).

Everything expressible as *attention + nonlinearity on a fixed set of tokens* stays pure — and
that covers a lot: all the richer **drives** (reaction-diffusion, E–I → waves, patterns,
multistability) and **adhesive combining** (type attention + metaball viewing). The one thing you
**cannot** get purely is **literal division/replication** (and metabolism), because those need
state the transformer doesn't have.

> **A transformer can make a fixed set of things pattern, move, cluster, and dissolve — it cannot
> make *more* of them.**

## 4. The morph weakness (why shapes look static now)

Not broken (grounding is correct: contour `C = z·W_c`), but weak because: **LayerNorm damps the
shape channels** (they contract toward a fixed configuration while un-normalized positions
wander); **only 3 harmonics** (6 numbers → simple blobs); and the **skew *rotates* the shape
rather than deforming it**. Fixes (all TX-only): more harmonics, a stronger/less-LayerNorm'd shape
drive, and applying an RD/E–I *reaction* to the shape channels — literally the "reaction" of
morphogenesis.

## 5. Plan

Try in order (all transformer-only): **(1) reaction–diffusion** [now], (2) E–I two-head attention,
(3) type-conditioned adhesion + metaball rendering. Each added as a live knob alongside the skew,
so the dish can be slid between regimes. Division/metabolism are deliberately out of scope (they'd
break "transformer only") unless we consciously choose to add a controller.
