import numpy as np
from _linetension import plant
from field import Field
from integrate import Inertial
from _regime import largest_frac

kT, n_tail, n_lip, L, phi = 0.45, 2, 120, 60.0, 0.55
n_water = int(round(phi * L * L / (np.pi * 0.25))) - (1 + n_tail) * n_lip
X, species, bonds, mol = plant(n_lip, n_tail, L, True, n_water, seed=0)
f = Field(species, bonds, L)
ig = Inertial(f, kT, 8e-3, seed=400)
print(f"spanning bilayer, {n_lip} lipids, L={L}, kT={kT}, {n_water} water")
print(f"{'step':>8}{'y spread':>11}{'largest':>10}{'thickness':>11}")
for t in range(60001):
    X = ig.step(X)
    if t % 15000 == 0:
        P = X[mol].mean(axis=1)
        head, tail = X[mol[:, 0]], X[mol[:, 1:]].mean(axis=1)
        up = head[:, 1] > tail[:, 1]
        th = float(head[up][:, 1].mean() - head[~up][:, 1].mean()) if up.any() and (~up).any() else float('nan')
        print(f"{t:>8}{float(P[:,1].std()):>11.2f}{largest_frac(X, mol, L):>10.2f}{th:>11.2f}")
