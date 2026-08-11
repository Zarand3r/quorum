"""What does a HEALTHY membrane read once it is thermalized? The missing baseline.

Every `bilayer_frac` pole quoted so far -- planted flat bilayer 0.967, planted R=9 vesicle 0.878 --
is measured at t=0 on a perfect lattice at effectively zero orientational noise. A real membrane at
kT=1 fluctuates, so it must read lower even when nothing is wrong with it. Without this baseline the
planted-vesicle decay (R=7.5: 0.541 -> 0.179 over 6000 steps) cannot be attributed: it is either
genuine instability or ordinary thermalization, and the two are indistinguishable from the vesicle
run alone.

So: run a planted FLAT bilayer, which we independently believe is a stable phase for this chemistry
(the box-spanning slab exists, holds temperature, and is laterally fluid), through the same number of
steps with the same readout. Its thermalized value is the ceiling any curved structure is competing
against.

The intactness fraction is reported alongside, because a membrane that fell apart also produces a
low bilayer_frac and the two must not be confused.
"""

import sys

import numpy as np

from _fluidity import plant_slab, intact
from _pairing import bilayer_frac
from _sl_model import NB, NH, A


def run(steps, n_per_leaf=64, k_ang=15.0, seed=1):
    d, n_amph, pitch = plant_slab(n_per_leaf, k_ang, A, seed)
    b0 = np.arange(n_amph) * NB
    print(f"planted FLAT bilayer, n_amph={n_amph}, L={d.L:.2f}, k_ang={k_ang}")
    print(f"{'step':>7}{'bil_frac':>10}{'paired':>8}{'flat':>7}{'intact':>8}{'T':>7}", flush=True)
    for t in range(steps + 1):
        if t % max(steps // 8, 1) == 0:
            f, pa, fl = bilayer_frac(d.x, d.L, b0, NB, NH)
            print(f"{t:>7}{f:>10.3f}{pa:>8.3f}{fl:>7.3f}{intact(d, n_amph):>8.2f}"
                  f"{d.temperature():>7.3f}", flush=True)
            if t in (0, steps):
                np.savez_compressed(
                    f"/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/"
                    f"flat_therm_t{t}.npz",
                    x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=NH)
        d.step()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 6000)
