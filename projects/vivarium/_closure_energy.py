"""Is closure still thermodynamically favoured in the FLUID regime? Ring vs arc, with error bars.

The 74 kT preference for the closed ring was measured at kT = 0.17 with FOUR-tail lipids -- i.e. in
the gel, with a lipid that is not the one now known to be fluid. It was also one seed per arm. Three
closure attempts have since failed, and in every one the arc EXPANDED and flattened rather than
closing, which is what a membrane does when its preferred curvature is flatter than the planted one.

So the question is whether the energetic preference survives the move to (kT = 0.45, two tails).

MEASURED. Planted ring and planted arc0.75 at identical N, box, density and temperature, relaxed and
then averaged over the second half of the run, repeated over independent seeds. Reported as
mean +- standard error of the per-lipid energy, and as the total difference in kT.

FALSIFICATION, STATED BEFORE THE RUN
    If E(ring) - E(arc) is not resolvably negative -- i.e. its magnitude does not exceed twice the
    combined standard error -- then closure is NOT energetically preferred for this lipid at this
    temperature, and the three failed closure attempts need no kinetic explanation at all. The
    membrane would simply prefer to stay open, and the earlier 74 kT would be a property of the gel
    phase rather than of the model.
"""

import sys

import numpy as np

from _mixture import build
from field import Field
from integrate import Inertial

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
    n_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    kT = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
    n_lip, L, phi = 70, 40.0, 0.55
    n_water = int(round(phi * L * L / (np.pi * 0.25))) - 3 * n_lip

    print(f"ring vs arc, N={n_lip} two-tail lipids, L={L}, kT={kT}, {n_seed} seeds, {steps} steps")
    out = {}
    for plant in ("ring", "arc0.75"):
        per_seed = []
        for sd in range(n_seed):
            X, species, bonds, mols, wi, chains = build(n_lip, 0, n_water, L, 2, plant=plant, seed=sd)
            f = Field(species, bonds, L)
            ig = Inertial(f, kT, 8e-3, seed=200 + sd)
            acc = []
            for t in range(steps):
                X = ig.step(X)
                if t > steps // 2 and t % 500 == 0:
                    acc.append(f.energy(X) / n_lip)
            per_seed.append(float(np.mean(acc)))
        m = float(np.mean(per_seed))
        e = float(np.std(per_seed, ddof=1) / np.sqrt(n_seed))
        out[plant] = (m, e)
        print(f"  {plant:>8}  E/lipid {m:>9.3f} +- {e:.3f}", flush=True)

    (mr, er), (ma, ea) = out["ring"], out["arc0.75"]
    diff = (mr - ma) * n_lip
    sig = np.sqrt(er ** 2 + ea ** 2) * n_lip
    print(f"\nE(ring) - E(arc) = {diff:+.1f} +- {sig:.1f} eps  =  {diff / kT:+.0f} +- {sig / kT:.0f} kT")
    resolved = abs(diff) > 2 * sig
    if not resolved:
        print("NOT RESOLVED: closure is not measurably preferred at this regime.")
    elif diff < 0:
        print("Closure IS energetically preferred; the failures are kinetic.")
    else:
        print("The OPEN state is preferred: the membrane wants to stay open, and no kinetic "
              "explanation is needed.")
