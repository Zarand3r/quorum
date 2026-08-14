"""Vivarium lipids in VACUUM: remove the solvent confound before adding it back properly.

Motivation. Every hydrated run here has a clustered solvent -- homogeneity 1.47 to 4.29 against a
random-point null of 0.38 -- so the lipids sit in an emulsion of water droplets rather than in a
continuous phase. "Waters per lipid" was therefore never a clean variable, which is consistent with
the non-monotonic result 0.42 -> 0.65 -> 0.12 for heads outward at 4, 10 and 20 waters per lipid.

Vacuum removes the confound. It is also the regime the two reference models actually work in: YLZ
and the two-species `bilipid` are both solvent-free, and both produce vesicles. What holds heads
outward there is not solvation but the orientation term plus head-head electrostatic repulsion,
both of which Vivarium already has (polarity 0.80, head_q 1.2).

Cheap as well: N = 189 rather than 439-2079, so a case runs in minutes instead of hours, which makes
a two-sided curvature sweep affordable -- and the sign is exactly what is in question.
"""

import sys

import numpy as np

from bicelle2d import build
from fig2d import render, largest_cluster, measure

BASE = dict(n_lip=63, bound=8.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
            satt=0.30, n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6)


def head_outward(e, comp):
    """1.0 = heads face away from the aggregate centre (normal); 0.0 = inverted."""
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


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    curvs = [float(v) for v in
             (sys.argv[2] if len(sys.argv) > 2 else "-0.45,-0.30,-0.15,0.0,0.15,0.30,0.45").split(",")]
    print(f"VACUUM (no solvent), 63 lipids, N=189, steps={steps}", flush=True)
    print(f"{'curv':>7}{'headOut':>9}{'largest':>9}{'enclosed':>10}{'align':>8}   verdict", flush=True)
    for cv in curvs:
        e = build(0, plant="clump", attract=1.5, n_water=0, **BASE)
        e.curvature = cv
        for _ in range(steps):
            e.step()
        comp = largest_cluster(e)
        m = measure(e)
        tag = f"vac_c{'m' if cv < 0 else 'p'}{abs(int(round(cv*100))):03d}"
        render(e, f"VACUUM curvature {cv:+.2f}, t={steps}", tag)
        print(f"{cv:>+7.2f}{head_outward(e, comp):>9.2f}{len(comp):>6}/63"
              f"{m['enclosed']:>10.2f}{m['align']:>8.3f}   {'OK' if m['ok'] else m['why'][:30]}",
              flush=True)
