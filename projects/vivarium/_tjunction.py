"""P1: is bilayer branching a kinetic transient or an attractor? Plant a T junction and watch it.

The 2-D self-assembly result is a network of bilayer ribbons joined at persistent Y/T junctions
rather than a single smooth membrane that could close into a ring. Two hypotheses explain that and
they demand opposite responses:

    ribbons -> collide -> junction -> ANNEAL -> smooth membrane -> close      (kinetic intermediate)
    ribbons -> collide -> junction -> STAY / GROW                             (competing morphology)

Watching spontaneous runs cannot separate these, because a junction that forms late is
indistinguishable from one that never heals. Planting a standardised junction and measuring its fate
does separate them, and costs a fraction of a self-assembly run.

Geometry: one ribbon spans the periodic box along x, so it has NO free ends and cannot retract by
shortening; a perpendicular arm of length A0 is grafted onto it. The arm is the only thing that can
change, which makes the readout unambiguous:

    arm retracts to zero   -> junction heals, branching is a transient
    arm length constant    -> junction is arrested
    arm grows              -> branching is energetically preferred

Readout is the amphiphile count beyond the spanning ribbon's own thickness, plus the arm's furthest
extent. Both are reported because a shrinking arm that merely thickens is not the same as one that
retracts.

Chemistry is the one that produced the branching phenotype (nb=3, single head, da=15), not the
Shillcock-Lipowsky bilayer chemistry, so the answer applies to the observed failure.
"""

import sys

import numpy as np

from dpd_reference import DPD

RHO, KT, A0_REP = 3.0, 1.0, 25.0
NB, NH = 3, 1                      # 1 head + 2 tails, the 2-D ribbon amphiphile
ZS = [1.0, 0.5, 0.0]               # head outermost; head-to-head across the bilayer = 2.0


def plant(arm_len, da, L, pitch, seed, k_ang=0.0, phi=0.0):
    """Plant the ribbon (+arm), plus enough free amphiphiles to hold the target concentration.

    Concentration and box size were coupled in the first version, and that invalidated the da=15 run:
    a box big enough to stop the arm reaching the ribbon's periodic image left only phi=0.076, below
    this chemistry's CMC, so the whole planted structure dissolved into scattered small aggregates
    before any junction physics could occur. Free monomers decouple the two, letting the box be large
    while the reservoir stays above the CMC.
    """
    n_span = int(L / pitch)                       # per leaflet, spans the periodic box
    n_arm = max(int(arm_len / pitch), 1)          # per leaflet of the grafted arm
    n_struct = 2 * (n_span + n_arm)
    N = int(RHO * L * L)
    n_free = max(int(phi * N / NB) - n_struct, 0)
    n_amph = n_struct + n_free

    sp = np.zeros(N, int)
    bonds, angles = [], []
    for k in range(n_amph):
        b = k * NB
        sp[b] = 1
        sp[b + 1:b + NB] = 2
        for t in range(NB - 1):
            bonds.append((b + t, b + t + 1))
        angles.append((b, b + 1, b + 2))

    a = np.full((3, 3), A0_REP)
    a[0, 2] = a[2, 0] = A0_REP + da
    a[1, 2] = a[2, 1] = A0_REP + da
    d = DPD(N, L, kT=KT, a_matrix=a, species=sp, bonds=np.array(bonds),
            k_bond=128.0, r0=0.5, dt=0.02, seed=seed, dim=2)
    d.angles = np.array(angles)
    d.k_ang = float(k_ang)

    y0 = L / 2
    k = 0
    for leaf, sgn in ((0, +1.0), (1, -1.0)):      # spanning ribbon, normal along y
        for q in range(n_span):
            b = k * NB
            px = (q + 0.5) * pitch
            for t in range(NB):
                d.x[b + t] = np.array([px, y0 + sgn * ZS[t]]) % L
            k += 1
    x0 = L / 2
    for leaf, sgn in ((0, +1.0), (1, -1.0)):      # arm, normal along x, grafted upward in y
        for q in range(n_arm):
            b = k * NB
            py = y0 + 2.0 + (q + 0.5) * pitch
            for t in range(NB):
                d.x[b + t] = np.array([x0 + sgn * ZS[t], py]) % L
            k += 1
    for _ in range(n_free):                        # free reservoir, random position and orientation
        b = k * NB
        c = d.rng.uniform(0, L, 2)
        u = d.rng.normal(size=2)
        u /= np.linalg.norm(u)
        for t in range(NB):
            d.x[b + t] = (c + (t - 1) * 0.5 * u) % L
        k += 1
    return d, n_amph, n_span, n_arm


def arm_state(d, L, idx, base=2.0):
    """Arm extent measured against the ribbon's CURRENT position, following the original arm molecules.

    Two errors in the first version, both visible in its own output. It measured against a FIXED y0
    while the spanning ribbon undulates and drifts in y, so ribbon material counted as "arm" whenever
    the ribbon rose -- which is why the count swung 48 -> 108 -> 75 -> 106 without the structure doing
    anything so dramatic. And it counted all lipids rather than following the ones planted in the arm,
    so material exchange, which IS the healing mechanism, was invisible.

    Returns mean and max displacement of the original arm molecules from the ribbon, plus the fraction
    absorbed into the ribbon slab. Healing shows up as absorbed -> 1.
    """
    span_idx, arm_idx = idx
    b0 = np.arange(len(span_idx) + len(arm_idx)) * NB
    ymol = np.stack([d.x[b0 + t][:, 1] for t in range(NB)]).mean(axis=0)
    # circular mean of the ribbon's y, so drift across the periodic edge does not corrupt it
    ang = ymol[span_idx] / L * 2 * np.pi
    y_rib = float(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2 * np.pi) * L) % L
    dy = ymol[arm_idx] - y_rib
    dy -= L * np.round(dy / L)
    dy = np.abs(dy)
    return float(dy.mean()), float(dy.max()), float((dy < base).mean())


if __name__ == "__main__":
    steps = int(sys.argv[1])
    da = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
    arm = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    # The box must be tall enough that the arm cannot reach the ribbon's own PERIODIC IMAGE. At
    # L=24 with a 6-long arm it grew to a separation of 9.9 against a maximum possible L/2=12, i.e.
    # it eliminated its free end by wrapping -- an artifact of box size, not healing.
    L = float(sys.argv[4]) if len(sys.argv) > 4 else 40.0
    phi = float(sys.argv[5]) if len(sys.argv) > 5 else 0.20
    pitch = 0.75
    d, n_amph, n_span, n_arm = plant(arm, da, L, pitch, seed=1, phi=phi)
    idx = (np.arange(0, 2 * n_span), np.arange(2 * n_span, 2 * n_span + 2 * n_arm))
    m0, _, _ = arm_state(d, L, idx)
    print(f"planted T junction: da={da} arm={arm} L={L} phi={phi} n_amph={n_amph} "
          f"(span {2*n_span}, arm {2*n_arm}, free {n_amph - 2*(n_span+n_arm)}); "
          f"max possible separation L/2={L/2:.1f}", flush=True)
    print(f"{'step':>7}{'mean arm dy':>13}{'frac of t=0':>13}{'max dy':>9}{'absorbed':>10}"
          f"{'T':>7}   verdict", flush=True)
    for t in range(steps + 1):
        if t % max(steps // 10, 1) == 0:
            m, r, ab = arm_state(d, L, idx)
            f = m / max(m0, 1e-9)
            verdict = ("HEALED" if ab > 0.85 else
                       "retracting" if f < 0.6 else
                       "GROWING" if f > 1.4 else "ARRESTED")
            if r > 0.9 * (L / 2):
                verdict += " (WRAPPED -- box too small, artifact)"
            print(f"{t:>7}{m:>13.2f}{f:>13.2f}{r:>9.2f}{ab:>10.2f}{d.temperature():>7.3f}   "
                  f"{verdict}", flush=True)
            np.savez_compressed(
                "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states/"
                f"tjunc_da{int(da)}_arm{int(arm)}.npz",
                x=d.x, species=d.species, L=d.L, n_amph=n_amph, nb=NB, nh=NH)
        d.step()
