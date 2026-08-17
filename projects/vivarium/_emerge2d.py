"""Do vesicles EMERGE in 2-D -- and do they come and go rather than last forever?

REFRAMED CRITERION
    Demanding that a hand-planted vesicle survive indefinitely is stricter than the field requires.
    Simulated vesicles are long-lived METASTABLE states, and a population that forms, persists for a
    while and occasionally dissolves is a result rather than a failure. Planted-stability is also a
    confounded diagnostic: three separate planting artefacts turned up while chasing it in 3-D
    (leaflet split by area rather than volume, an unfilled lumen, and a solvent too dilute to
    pressurise one).

    So this measures the thing actually wanted: starting from DISPERSED lipids, with nothing planted,
    how often does a closed ring with a lumen exist at all? The readout is the fraction of checkpoints
    classified HOLLOW over a long run, plus the largest aggregate, not the state at the final step.

HYPOTHESIS     above some concentration a closed ring appears transiently, so the HOLLOW fraction is
               greater than zero even if no single ring lasts to the end.
FALSIFICATION  if HOLLOW is never reported at any checkpoint at any concentration, 2-D closure does
               not occur by nucleation in this model, and the branched-network phase is the whole
               story.

Concentration is the swept variable because it sets which morphology is affordable: a spanning stripe
costs about 2L lipids, so at fixed L a ring can only win below that, while too few lipids simply never
nucleate. The earlier failure -- largest aggregate 6-12 of 70 after 100000 steps -- was at the dilute
end of exactly this trade-off.
"""

import sys

import numpy as np

from _mixture import build, geometry, largest_cluster, shot
from field import Field
from ring_assay import classify


class View:
    def __init__(self, X, mol, wi, L, pd):
        self.X, self._mol, self._wi, self.L, self.pd = X, mol, wi, L, pd


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 400000
    n_lip = int(sys.argv[2]) if len(sys.argv) > 2 else 70
    L = float(sys.argv[3]) if len(sys.argv) > 3 else 28.0
    kT = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35
    phi, d, n_tail = 0.55, 2, 4

    n_water = int(round(phi * L ** 2 / (np.pi * 0.25))) - (1 + n_tail) * n_lip
    if n_water < 0:
        raise ValueError(f"L={L} too small for {n_lip} lipids at packing fraction {phi}")
    X, species, bonds, mols, wi, chains = build(0, n_lip, n_water, L, d, plant="random")
    mol = np.array([m for m in mols])
    f = Field(species, bonds, L)
    gamma, dt = 1.0, 2e-4
    rng = np.random.default_rng(1)
    amp = np.sqrt(2.0 * kT * dt / gamma)

    print(f"EMERGENCE 2-D: {n_lip} lipids (1 head + {n_tail} tails) + {n_water} water, L={L}, "
          f"kT={kT}, dispersed start, {steps} steps", flush=True)
    print(f"a spanning stripe costs about {2 * L:.0f} lipids, so a ring is affordable "
          f"{'BELOW' if n_lip < 2 * L else 'ABOVE -- stripe wins'} this count", flush=True)
    print(f"{'step':>8}{'E/lip':>9}{'largest':>9}{'R_mid':>7}{'shellCV':>9}{'lumenW':>8}   verdict",
          flush=True)
    every = max(steps // 40, 1)
    hollow = 0
    checks = 0
    for t in range(steps + 1):
        X += (f.forces(X) / gamma) * dt + amp * rng.normal(size=X.shape)
        X -= L * np.round(X / L)
        if t % every == 0:
            v, dd = classify(View(X, mol, wi, L, 2))
            g = geometry(X, mols, wi, chains, L, d)
            checks += 1
            hollow += (v == "HOLLOW")
            print(f"{t:>8}{f.energy(X) / n_lip:>9.2f}{largest_cluster(X, mols, L):>9}"
                  f"{g['R_mid']:>7.2f}{g['shell_cv']:>9.3f}{g['lumen_w']:>8}   {v}", flush=True)
            shot(X, species, L, f"em2d_N{n_lip}_L{int(L)}_s{t:07d}")
    print(f"\nHOLLOW at {hollow} of {checks} checkpoints ({100.0 * hollow / checks:.0f}%)", flush=True)
