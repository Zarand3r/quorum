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
from _ylz_run import clusters_unwrapped, shape

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


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
            P, nb, nc = clusters_unwrapped(c, s.L, cut=1.8)
            if nb >= 8:
                R, cv, ho, e2, e3, sh = shape(P)
                # recover which molecules are in that cluster, for the head-orientation check
                d = c[:, None, :] - c[None, :, :]
                d -= s.L * np.round(d / s.L)
                adj = np.linalg.norm(d, axis=2) < 1.8
                np.fill_diagonal(adj, False)
                seen = np.zeros(len(c), bool)
                best = None
                for k in range(len(c)):
                    if seen[k]:
                        continue
                    stack, comp = [k], []
                    seen[k] = True
                    while stack:
                        q = stack.pop()
                        comp.append(q)
                        for m in np.flatnonzero(adj[q]):
                            if not seen[m]:
                                seen[m] = True
                                stack.append(m)
                    if best is None or len(comp) > len(best):
                        best = comp
                sel = np.array(best)
                ho_frac = head_outward(s, P, u[sel], P.mean(axis=0))
            else:
                R = cv = ho = e2 = e3 = 0.0
                sh, ho_frac = "dispersed", float("nan")
            print(f"{t:>9}{s.energy()/s.n_mol:>10.3f}{s.temperature():>7.3f}{nc:>6}{nb:>9}"
                  f"{R:>7.2f}{cv:>9.3f}{ho:>8.3f}{e2:>6.2f}{e3:>6.2f}{ho_frac:>9.2f}   {sh}",
                  flush=True)
            x, sp = s.positions_species()
            np.savez_compressed(f"{ST}/{tag}.npz", x=x, species=sp, L=s.L,
                                n_amph=s.n_mol, nb=2, nh=1)
        s.step()
