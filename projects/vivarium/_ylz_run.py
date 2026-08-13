"""M1 verification: does OUR engine reproduce the vesicle that stock LAMMPS produced?

Same potential (gradient-checked in ylz.py), same published parameters, same sizing rule that M0
established: the particle count must be unable to afford either a box-spanning sheet (L^2/a) or a
spanning tube (2 pi r L / a), leaving closure as the only edgeless option. With the measured area
per particle a = 1.50 sigma^2, N=300 in L=25 forbids both (sheet 417, tube 367).

Shape is classified from the full eigenvalue SPECTRUM of the gyration tensor, not from a single
ratio: ev3/ev1 alone cannot separate a flat sheet from a tube because both are near zero. Four
states earlier in this project were mislabelled tubes for exactly that reason.

    sphere / shell   ev2/ev1 ~ 1, ev3/ev1 ~ 1
    flat sheet       ev2/ev1 ~ 1, ev3/ev1 ~ 0
    tube             ev2/ev1 ~ 0, ev3/ev1 ~ 0
"""

import sys
from collections import deque

import numpy as np

from ylz import YLZ

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


def clusters_unwrapped(x, L, cut=1.6):
    """Largest connected cluster, unwrapped through its own contact graph."""
    n = len(x)
    d = x[:, None, :] - x[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    lab = -np.ones(n, int)
    c = 0
    for s in range(n):
        if lab[s] >= 0:
            continue
        q = deque([s])
        lab[s] = c
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = c
                    q.append(j)
        c += 1
    sizes = np.bincount(lab)
    big = int(sizes.argmax())
    sel = np.flatnonzero(lab == big)
    pos = np.full((n, 3), np.nan)
    root = sel[0]
    pos[root] = x[root]
    q = deque([root])
    while q:
        i = q.popleft()
        for j in np.flatnonzero(adj[i]):
            if np.isnan(pos[j, 0]):
                o = x[j] - x[i]
                o -= L * np.round(o / L)
                pos[j] = pos[i] + o
                q.append(j)
    return pos[sel], int(sizes[big]), len(sizes)


def shape(P):
    ctr = P.mean(axis=0)
    d = P - ctr
    r = np.linalg.norm(d, axis=1)
    ev = np.sort(np.linalg.eigvalsh(np.cov(d.T)))[::-1]
    e2, e3 = ev[1] / ev[0], ev[2] / ev[0]
    cv = r.std() / max(r.mean(), 1e-9)
    hollow = float((r < 0.5 * r.mean()).mean())
    if e3 > 0.45 and cv < 0.25 and hollow < 0.08:
        s = "VESICLE (hollow sphere)"
    elif e3 > 0.45:
        s = "compact blob"
    elif e2 > 0.45:
        s = "flat sheet/disc"
    else:
        s = "tube/elongated"
    return r.mean(), cv, hollow, e2, e3, s


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    L = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    steps = int(sys.argv[3]) if len(sys.argv) > 3 else 400000
    beta = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1
    tag = sys.argv[5] if len(sys.argv) > 5 else f"ourylz_N{N}_b{beta}"
    bounded = len(sys.argv) > 6 and sys.argv[6] != "div"
    contact = float(sys.argv[6]) if bounded else 3.0

    s = YLZ(N, L, beta=beta, seed=1, bounded_core=bounded, contact=contact)
    a = 1.50
    print(f"our-engine YLZ: N={N} L={L} beta={beta} core={f'bounded@{contact:g}eps' if bounded else 'r^-4'}  "
          f"(sheet needs {L*L/a:.0f}, tube needs {2*np.pi*3.5*L/a:.0f})", flush=True)
    print(f"{'step':>8}{'E/particle':>12}{'T':>7}{'clus':>6}{'largest':>9}{'R':>7}"
          f"{'shellCV':>9}{'hollow':>8}{'e2':>6}{'e3':>6}   shape", flush=True)
    every = max(steps // 10, 1)
    for t in range(steps + 1):
        if t % every == 0:
            P, nb, nc = clusters_unwrapped(s.x, s.L)
            R, cv, ho, e2, e3, sh = shape(P) if nb >= 8 else (0, 0, 0, 0, 0, "dispersed")
            print(f"{t:>8}{s.energy()/s.n:>12.3f}{s.temperature():>7.3f}{nc:>6}{nb:>9}"
                  f"{R:>7.2f}{cv:>9.3f}{ho:>8.3f}{e2:>6.2f}{e3:>6.2f}   {sh}", flush=True)
            np.savez_compressed(f"{ST}/{tag}.npz", x=s.x, species=np.full(s.n, 2, int),
                                L=s.L, n_amph=s.n, nb=1, nh=0)
        s.step()
