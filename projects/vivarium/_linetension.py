"""Line tension of a 2-D bilayer edge, measured directly rather than differenced out of two blobs.

WHY NOT THE OBVIOUS COMPARISON
    Ring versus arc at matched everything gave E(ring) - E(arc) = -0 +- 81 kT over 5 seeds: an error
    bar LARGER than the 74 kT effect it was meant to resolve. The two structures relax differently
    from seed to seed, so the difference of two large per-lipid energies is dominated by structural
    noise. Resolving 0.48 eps/lipid at that spread would need of order 80 seeds.

    So measure the CONSTANT instead. Closure is a competition between the edge energy saved and the
    bending energy paid, and the edge term can be isolated exactly:

        lambda = [ E(finite ribbon) - E(spanning ribbon) ] / 2

    with both FLAT, the same lipid count, the same density and the same temperature. Flat means no
    bending contribution on either side, so the whole difference is the two exposed ends. The spanning
    ribbon is periodic and therefore has no ends at all -- that is the control that makes this clean,
    and it is why this is a smaller and better-posed measurement than ring-versus-arc.

FALSIFICATION, STATED BEFORE THE RUN
    lambda must come out POSITIVE and resolvable at 2 sigma. An edge costs energy: tails there are
    exposed to water. If it does not, then the model does not penalise an exposed edge at all, which
    would explain every closure failure directly -- there would be nothing to gain by closing.
"""

import sys

import numpy as np

from field import Field, HEAD, TAIL, WATER
from integrate import Inertial

BOND = 1.0


def plant(n_lip, n_tail, L, spanning, n_water, seed=0):
    """Flat bilayer ribbon. `spanning` tiles the periodic box exactly, so it has NO ends."""
    rng = np.random.default_rng(seed)
    nb = 1 + n_tail
    per = n_lip // 2
    gap = L / per if spanning else 1.05
    n = n_lip * nb + n_water
    X = np.zeros((n, 2))
    species = np.empty(n, dtype=np.int64)
    mol = np.arange(n_lip * nb).reshape(n_lip, nb)
    species[mol[:, 0]] = HEAD
    species[mol[:, 1:]] = TAIL
    xs = (np.arange(per) - (per - 1) / 2.0) * gap
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        idx = mol[leaf * per:(leaf + 1) * per]
        for b in range(nb):
            off = 0.5 + (nb - 1 - b) * BOND
            X[idx[:, b], 0] = xs[:len(idx)]
            X[idx[:, b], 1] = sgn * off
    wi = np.arange(n_lip * nb, n)
    species[wi] = WATER
    X[wi] = rng.uniform(-L / 2, L / 2, size=(n_water, 2))
    X -= L * np.round(X / L)
    bonds = np.concatenate([np.stack([mol[:, b], mol[:, b + 1]], 1) for b in range(nb - 1)])
    return X, species, bonds, mol


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    n_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    kT = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
    n_tail = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    n_lip, L, phi = 60, 30.0, 0.55
    n_water = int(round(phi * L * L / (np.pi * 0.25))) - (1 + n_tail) * n_lip

    print(f"line tension, N={n_lip} lipids (1 head + {n_tail} tails), L={L}, kT={kT}, "
          f"{n_seed} seeds, {steps} steps")
    res = {}
    for spanning in (True, False):
        vals = []
        for sd in range(n_seed):
            X, species, bonds, mol = plant(n_lip, n_tail, L, spanning, n_water, seed=sd)
            f = Field(species, bonds, L)
            ig = Inertial(f, kT, 8e-3, seed=300 + sd)
            acc = []
            for t in range(steps):
                X = ig.step(X)
                if t > steps // 2 and t % 400 == 0:
                    acc.append(f.energy(X))
            vals.append(float(np.mean(acc)))
        m, e = float(np.mean(vals)), float(np.std(vals, ddof=1) / np.sqrt(n_seed))
        res["spanning" if spanning else "finite"] = (m, e)
        print(f"  {'spanning (no ends)' if spanning else 'finite (two ends)':>20}  "
              f"E {m:>10.2f} +- {e:.2f}", flush=True)

    (ms, es), (mf, ef) = res["spanning"], res["finite"]
    lam = (mf - ms) / 2.0
    sig = np.sqrt(es ** 2 + ef ** 2) / 2.0
    print(f"\nlambda = [E(finite) - E(spanning)] / 2 = {lam:+.2f} +- {sig:.2f} eps per end")
    print(f"       = {lam / kT:+.1f} +- {sig / kT:.1f} kT per end")
    if abs(lam) < 2 * sig:
        print("NOT RESOLVED at 2 sigma -- this measurement cannot see the edge cost.")
    elif lam > 0:
        print("Edge costs energy, as it must. Closure has something to gain.")
    else:
        print("EDGE IS FAVOURABLE: the model does not penalise an exposed edge, which would "
              "explain every closure failure directly.")
