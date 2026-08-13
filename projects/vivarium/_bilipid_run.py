"""Self-assembly for the two-species amphiphile. Does Vivarium's head/tail representation close?

Sizing follows the rule established in M0 and confirmed in M1: with area per molecule ~1.5 sigma^2,
the molecule count must be unable to afford either a box-spanning sheet (L^2/a) or a spanning tube
(2 pi r L / a), leaving closure as the only edgeless option.

Shape is classified from the full gyration eigenvalue spectrum of the molecular CENTRES, since
ev3/ev1 alone cannot separate a flat sheet from a tube. Head-outwardness is reported alongside,
because a two-species membrane can be geometrically closed while having its heads pointing the wrong
way -- that would be a shell, but not a vesicle in any chemically meaningful sense.
"""

import sys

import numpy as np

from bilipid import BiLipid
from _ylz_run import shape

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


def all_clusters(c, L, cut=1.8, min_size=20):
    """Every cluster above min_size, unwrapped, largest first.

    Reporting only the LARGEST cluster is misleading: at 1M steps an 84-molecule vesicle was still
    present and unchanged, but an 85-molecule sheet had overtaken it by one molecule, so the run log
    printed "flat sheet/disc" and the vesicle was invisible. Structure and size are different
    questions and the driver must not conflate them.
    """
    from collections import deque
    n = len(c)
    d = c[:, None, :] - c[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    lab = -np.ones(n, int)
    k = 0
    for s0 in range(n):
        if lab[s0] >= 0:
            continue
        q = deque([s0]); lab[s0] = k
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = k; q.append(j)
        k += 1
    out = []
    for cid in np.argsort(-np.bincount(lab)):
        sel = np.flatnonzero(lab == cid)
        if len(sel) < min_size:
            continue
        pos = np.full((n, 3), np.nan)
        root = sel[0]; pos[root] = c[root]
        q = deque([root])
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if np.isnan(pos[j, 0]):
                    o = c[j] - c[i]; o -= L * np.round(o / L)
                    pos[j] = pos[i] + o; q.append(j)
        out.append((sel, pos[sel]))
    return out, int(lab.max()) + 1


def largest_cluster(c, L, cut=1.8):
    """Indices AND unwrapped positions of the largest cluster, from a single traversal.

    Returning both from one BFS is the point. An earlier version clustered twice -- once for
    positions, once for orientations -- and paired index k of one with index k of the other. The
    orderings differ, so the head-orientation check compared unrelated molecules and reported
    exactly 0.5, which reads as "chemically ambivalent" when the true value is 1.000.
    """
    from collections import deque
    n = len(c)
    d = c[:, None, :] - c[None, :, :]
    d -= L * np.round(d / L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    lab = -np.ones(n, int)
    k = 0
    for s0 in range(n):
        if lab[s0] >= 0:
            continue
        q = deque([s0]); lab[s0] = k
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = k; q.append(j)
        k += 1
    sizes = np.bincount(lab)
    sel = np.flatnonzero(lab == sizes.argmax())
    pos = np.full((n, 3), np.nan)
    root = sel[0]; pos[root] = c[root]
    q = deque([root])
    while q:
        i = q.popleft()
        for j in np.flatnonzero(adj[i]):
            if np.isnan(pos[j, 0]):
                o = c[j] - c[i]; o -= L * np.round(o / L)
                pos[j] = pos[i] + o; q.append(j)
    return sel, pos[sel], len(sizes)


def head_outward(s, sel_centres, u_sel, ctr):
    """Fraction of molecules in the shell whose head points AWAY from the aggregate centre."""
    rel = sel_centres - ctr
    n = np.linalg.norm(rel, axis=1)
    ok = n > 1e-9
    if not ok.any():
        return float("nan")
    rhat = rel[ok] / n[ok][:, None]
    return float((np.einsum("ic,ic->i", u_sel[ok], rhat) > 0).mean())


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    L = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    steps = int(sys.argv[3]) if len(sys.argv) > 3 else 3000000
    beta = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1
    tag = sys.argv[5] if len(sys.argv) > 5 else f"bilipid_N{N}"

    s = BiLipid(N, L, beta=beta, seed=1)
    a = 1.50
    print(f"TWO-SPECIES amphiphile: N={N} molecules ({2*N} beads) L={L} beta={beta} "
          f"contact={s.contact:g} eps  (sheet needs {L*L/a:.0f}, tube needs {2*np.pi*3.5*L/a:.0f})",
          flush=True)
    print(f"{'step':>9}{'E/mol':>10}{'T':>7}{'clus':>6}{'largest':>9}{'R':>7}{'shellCV':>9}"
          f"{'hollow':>8}{'e2':>6}{'e3':>6}{'headOut':>9}   shape", flush=True)
    every = max(steps // 12, 1)
    for t in range(steps + 1):
        if t % every == 0:
            c, u, _ = s.frame()
            groups, nc = all_clusters(c, s.L)
            best = None          # report the most vesicle-like cluster, not merely the biggest
            for sel, P in groups:
                R, cv, ho, e2, e3, sh = shape(P)
                hf = head_outward(s, P, u[sel], P.mean(axis=0))
                score = (sh == "VESICLE (hollow sphere)", len(sel))
                if best is None or score > best[0]:
                    best = (score, len(sel), R, cv, ho, e2, e3, hf, sh)
            if best is None:
                print(f"{t:>9}{s.energy()/s.n_mol:>10.3f}{s.temperature():>7.3f}{nc:>6}"
                      f"{0:>9}{0.0:>7.2f}{0.0:>9.3f}{0.0:>8.3f}{0.0:>6.2f}{0.0:>6.2f}"
                      f"{float('nan'):>9.2f}   dispersed", flush=True)
            else:
                _, nb, R, cv, ho, e2, e3, hf, sh = best
                nves = sum(1 for sel, P in groups if shape(P)[5] == "VESICLE (hollow sphere)")
                print(f"{t:>9}{s.energy()/s.n_mol:>10.3f}{s.temperature():>7.3f}{nc:>6}"
                      f"{nb:>9}{R:>7.2f}{cv:>9.3f}{ho:>8.3f}{e2:>6.2f}{e3:>6.2f}{hf:>9.2f}   "
                      f"{sh}  [vesicles: {nves}]", flush=True)
            x, sp = s.positions_species()
            np.savez_compressed(f"{ST}/{tag}.npz", x=x, species=sp, L=s.L,
                                n_amph=s.n_mol, nb=2, nh=1)
        s.step()
