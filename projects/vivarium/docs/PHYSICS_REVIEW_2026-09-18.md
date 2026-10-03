# Critical review of the active vivarium

The active dish is a **coarse-grained molecular dynamics model with an exact attention-shaped force
decomposition**. It is not currently a reaction–diffusion model, a trained transformer, or a live
contour-morphing network. Its conservative force calculation is well tested. **Full adherence to the
older strict transformer-only contract is not established.** These are separate conclusions.

Reviewed against `SUMMARY.md`, the consolidated `ROADMAP.md`, `manifest.py`,
`design/HARD_REQUIREMENT.md`, `field.py`, `transformer.py`, `manybody.py`, `_mixture.py`,
`integrate.py`, `vesicle.py`, and the architecture and physical-realism tests. The hosted audit
changes control/observation behavior, not the production interaction equations or MLP wiring.

## What actually runs

The hosted production system has 160 branched, five-bead lipids and 2,159 water beads in a periodic
2-D box of side 65. **A bead is a token; a lipid is five tokens.** The step is velocity Verlet with
independent Ornstein–Uhlenbeck friction/noise. Fixed species affinities, a bounded overlap potential,
a cosine attractive well, harmonic bonds, and 1–3 distance springs determine the forces.

`VivariumTransformer.attention` independently assembles the same conservative forces as
`Field.forces`. Both read the effective species chemistry through `Field._env`, whose
`content_pairs` actually computes the query–key inner product of **fixed species factors** on the
neighbour pairs. Thus query–key arithmetic is not absent from production, despite older handoff
wording about reading the table directly. The separate hidden token channel and the transformer's
own `q()`/`k()` projections do **not** determine the production force. `forward` does not
invoke `mlp`. The optional coordination-dependent affinity and size modulators are off in ordinary
production, including the recorded vesicle.

## What the physical tests prove, and what they do not

The checks for analytic pair derivatives, Newton's third law, numerical energy gradients,
translation/rotation invariance, thermostat-off energy conservation, equipartition, and independent
force-path agreement are meaningful. Agreement means that the implementation computes its stated
model. It does **not** establish that this model quantitatively reproduces water, lipids, membrane
elasticity, or biological kinetics.

The energy-gradient checks are numerical tolerances on sampled configurations, not a proof that no
configuration can fail. In particular the overlap potential `height*(1-r/sigma)^2` has a radial cusp
at exact coincidence: a Cartesian gradient direction is undefined there. The `max(r,1e-12)` guards
choose a numerical convention, rather than making the potential globally smooth.

Independent Langevin friction and noise exchange momentum with a bath. They are legitimate for
sampling a coarse-grained thermal system, but they do not conserve the fluid's local momentum or
reproduce solvent hydrodynamics. **Zero net conservative force does not establish momentum
conservation of the full stochastic step.** Compare with momentum-conserving pairwise stochastic
models such as [Español's DPD formulation](https://arxiv.org/abs/cond-mat/9706217).

## Transformer-only: there is a real unresolved boundary

The older hard requirement allows local attention, position-wise MLPs, norms/residuals, and
structured linear maps. Its kernel amendment specifically describes bounded content weights,
Gaussian/RBF distance kernels, and no raw division by distance. The active force heads instead use
analytic derivatives with `1/r` factors, a cosine well, Hookean springs, and an angle-gradient
calculation. The old enforcement grep principally checks archived `pack`/`pure`/`polar` code.
The active physical-realism tests check correctness of equations, **not compliance with that entire
older operation whitelist**.

For example, a non-bonded contribution is

```
F_i = sum_j [ -(eps/sigma) * (core'(r/sigma) + chi_ij*well'(r/sigma)) / r ] * (x_i-x_j)
```

This has a local scalar score and a relative-position value, a defensible generalized kernel-message
form. But its score diverges as `r -> 0` even when the force magnitude stays bounded. Bounded energy,
bounded force, and bounded attention weight are **three different conditions**. Springs likewise
do not have globally bounded force. Calling a calculation an `AttentionHead` does not settle these
issues: almost any central pair force can be written as score times relative displacement.

The newer summary accepts analytic physical kernels and composed passes for three-body terms. That
is broader than the old kernel amendment. This conflict needs an explicit architectural resolution,
not an inference that the old document is satisfied. In particular:

- Make the adaptive token-channel query/key path load-bearing if adaptive internal state is part
  of the claim. The fixed species-factor inner product already runs; its equality to an interaction
  table does not establish that changing `transformer.h` can change the interaction.
- State precisely which analytic radial features and multi-pass geometric operations are permitted.
  Review the complete step, including thermostat and periodic-coordinate handling, rather than just
  its interaction sum.
- Enforce that specification on ACTIVE modules. Preserve the independent physical-gradient gates.

The strict expected-failure `test_mlp_is_live_not_decorative` records that changing `h` changes no
force. If that wiring changes, its XPASS fails the suite until this audit is revisited. The audit
does not weaken it or turn a physical-formulation result into a stronger wiring claim.

An energy **function** is not a metabolic **ledger**. Evaluating `U(X)` for a gradient check does not
introduce energy tokens, resource injection, or consumption dynamics forbidden by the old contract.
Conversely, an absent energy function does not make bath temperature meaningless: driven Langevin
systems can have a well-defined bath temperature without equilibrium detailed balance. What is lost
is an equilibrium-potential interpretation, not every thermodynamic concept.

## Does reaction–diffusion require an MLP?

An MLP is **allowed**, not mandatory. In a reaction–diffusion discretization the two useful roles are

```
du_i/dt = sum_j w_ij D (u_j-u_i) + f(u_i)
          local diffusion           local reaction
```

Attention can implement the graph diffusion term. A position-wise MLP can implement or approximate
the local nonlinear reaction `f`; an explicit admissible local nonlinearity can do so too. A Turing
mechanism additionally needs the right kinetic stability and transport parameters. In the classical
case, a homogeneous reaction equilibrium is stable without diffusion but unstable to certain spatial
perturbations with diffusion. **Adding an MLP alone proves none of that.** See
[Turing's original reaction–diffusion analysis](https://groups.csail.mit.edu/mac/projects/amorphous/6.978/papers/turing-chemical-basis.pdf).

The current lipid system is not simply `A*u-u`. Attractive/repulsive, species-dependent mechanical
forces move interacting particles. It already contains nonlinear dynamics and can demix and assemble
without a reaction network. The statement in `manybody.py` that an absent MLP makes this system
"pure diffusion" and unable to break symmetry is wrong. Published coarse-grained lipid models
assemble fluid bilayers without an MLP: [Cooke, Kremer & Deserno](https://arxiv.org/abs/cond-mat/0502418).

Morphology also has two meanings here. A molecule can change **conformation** through bead motion
under fixed conservative forces. A token can change an independent **shape representation** through
a local network. The former already runs; the latter currently does not.

`ShapeMLP` is a fixed scalar sigmoid constitutive relation; `ManyBodyMLP` is a fixed rational response.
Neither has the implemented multilayer network its name suggests. A sigmoid relation could be
implemented as a fixed affine/sigmoid neuron, but giving it more layers is not automatically better
physics. Their valuable feature is the conservative many-body construction: their configuration
dependence is accompanied by the full chain-rule force.

For a genuine shape network, put its output inside the energy and differentiate through its input
descriptor. If an internal shape state evolves independently, give it a specified energy and
consistent dynamics/dissipation. Updating `h` arbitrarily each tick and then changing pair affinities
can perform unaccounted work, even if each instantaneous pair force is reciprocal. Symmetry alone
is insufficient. LayerNorm and arbitrary clipping also require physical justification when applied
to physical state.

## Fidelity gaps and corrections to the roadmap's interpretation

- **2-D scope:** this establishes a closed bilayer curve, not a volumetric 3-D membrane bubble.
- **Chain stiffness:** zero harmonic coefficient of a quartic spring is not zero thermal rigidity.
  The roadmap correctly retracts the stronger claim. Isolated-chain stiffness is also not the
  membrane's bending modulus. The new harmonic angle term is implemented but off; its strength
  calibration is indeterminate. Do not enable it as a hosted control fix.
- **Bond extension:** harmonic bonds are a coarse-graining choice, not automatically a coding bug.
  FENE is common, but its divergence at maximum extension conflicts with a global bounded-kernel
  constraint. Any replacement needs an explicit compatible model and new validation.
- **Electrostatics:** no explicit electrostatic interaction runs here. That leaves part of the stated
  research objective unmet, but not every successful generic membrane model needs explicit charges.
  Zwitterionic phospholipid heads are not simply net positive charges. A screened head–head repulsion
  is a modelling hypothesis, not automatically a faithful completion of the chemistry.
- **Solvent:** relative pair affinities alone do not quantify the hydrophobic effect or water's
  equation of state. Use matched solvent, transfer-free-energy, and mixture controls under the actual
  hosted parameters. Reordering coefficients is not a substitute for these measurements.
- **Size selection:** growth of the largest cluster with total lipid count suggests coarsening, but
  it does not prove that long-range repulsion is the missing mechanism. A vesicle need not have one
  intrinsic preferred radius: lipid amount, lumen volume, tension, and curvature energetics can set
  its size. The proposed electrostatic experiment has a falsifier; retain it as a hypothesis.
- **Closure:** small end gap is a predictor, not an established cause. The reported near-zero rim
  energy and unresolved membrane modulus leave the mechanism open. Thermal fluctuation-assisted
  closure is not inherently unphysical, but rare closures do not establish the natural closure law.

The current detector also contains choices despite the summary's "no free parameters" wording:
bead connectivity 1.4, minimum aggregate size 8, a dilation ladder, and a bilayer band 0.20–0.80.
These may be useful robustness choices, but should be reported and tested for sensitivity. The live
code scores closure with a bilayer veto; some summary prose still describes a product of two scores.
Do not reinterpret old rates under a revised detector without an explicit rescore.

## Recommendation

Keep the molecular and reaction–diffusion questions distinct. For this dish, prioritize a
load-bearing token/interaction path with an energy-consistent state model, one explicit ACTIVE
architecture contract, and measured membrane elasticity/solvent behavior. Introduce a reaction MLP
only when there is a reaction or internal-shape law to model and an instrument that can show it acts.
Do not add a decorative network to make a checklist green, or sacrifice conservative physics to
make the network appear live.

The follow-up design backlog and required acceptance gates are recorded in
[`MLP_FUTURE_WORK.md`](MLP_FUTURE_WORK.md).
