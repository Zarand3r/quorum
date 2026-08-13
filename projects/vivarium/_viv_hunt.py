"""Hunt for a vesicle in the real Vivarium: hydration x curvature, with the metrics that decide it.

Established so far, at 20k steps from a clumped start:
  * 4 waters/lipid  -> heads outward 0.42 (INVERTED, a reverse micelle: the water-poor phase)
  * 10 waters/lipid -> heads outward 0.65 (majority correct), solvent homogeneity 2.28 -> 1.64

Hydration is the variable that un-inverts the structure, so the hunt continues there. Curvature is
swept alongside because closure needs both: heads on the outside AND a preferred splay.

A vesicle here means all four of:
  heads outward near 1, an enclosed water pocket well above bulk, the aggregate not fragmented,
  and the harness's own admissibility gate passing (no interpenetration).
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster, measure

BASE = dict(n_lip=63, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
            n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6)
DENSITY = 439.0 / 22.0 ** 2


def head_outward(e, comp):
    mol = e._mol[comp]
    P = e.X[:, :e.pd]
    head, tailc = P[mol[:, 0]], P[mol[:, 1:]].mean(axis=1)
    u = head - tailc
    u -= e.L * np.round(u / e.L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    cen = P[mol.ravel()].mean(axis=0)
    rel = head - cen
    rel -= e.L * np.round(rel / e.L)
    r = np.linalg.norm(rel, axis=1)
    ok = r > 1e-9
    return float((np.einsum("ic,ic->i", u[ok], rel[ok] / r[ok][:, None]) > 0).mean())


def solvent_homogeneity(e, cells=6):
    w = e.X[e._wi, :e.pd]
    idx = (w / e.L * cells).astype(int) % cells
    flat = (idx * (cells ** np.arange(e.pd)[::-1])).sum(axis=1)
    n = np.bincount(flat, minlength=cells ** e.pd).astype(float)
    return float(n.std() / max(n.mean(), 1e-9))


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    wpl = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    curvs = [float(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "0.15,0.30,0.45").split(",")]

    nw = wpl * BASE["n_lip"]
    N = 3 * BASE["n_lip"] + nw
    bound = (N / DENSITY) ** 0.5 / 2.0
    print(f"{wpl} waters/lipid  n_water={nw}  N={N}  bound={bound:.1f}  steps={steps}", flush=True)
    print(f"{'curv':>6}{'headOut':>9}{'largest':>9}{'enclosed':>10}{'align':>8}"
          f"{'homog':>8}   verdict", flush=True)
    for cv in curvs:
        e = build(0, plant="clump", attract=1.5, n_water=nw, bound=bound, **BASE)
        e.curvature = cv
        for _ in range(steps):
            e.step()
        comp = largest_cluster(e)
        m = measure(e)
        ho = head_outward(e, comp)
        name = f"vivh_w{wpl:02d}_c{int(round(cv*100)):03d}"
        render(e, f"VIVARIUM {wpl} w/lipid, curvature {cv}, t={steps}", name)
        print(f"{cv:>6.2f}{ho:>9.2f}{len(comp):>6}/63{m['enclosed']:>10.2f}{m['align']:>8.3f}"
              f"{solvent_homogeneity(e):>8.2f}   {'OK' if m['ok'] else m['why'][:28]}", flush=True)
