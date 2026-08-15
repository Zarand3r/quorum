"""Is the SOLVENT significant, or was the vacuum collapse just a density artefact?

Earlier vacuum runs used bound=8.0 with 63 lipids and no water: lipid density 0.738. The hydrated
runs used bound=11.0 with 250 water: lipid density 0.390. So vacuum packed the lipids 1.9x more
tightly, and the collapse seen there cannot be attributed to the absence of solvent.

This holds LIPID density fixed at the hydrated value and varies only whether solvent is present.

HYPOTHESIS     the solvent is doing real work -- at matched lipid density, hydrated aggregates stay
               spaced while vacuum ones collapse.
FALSIFICATION  if vacuum at matched lipid density behaves like the hydrated case, the earlier vacuum
               collapse was purely a density artefact and solvent is not the relevant variable.
"""
import sys
import numpy as np
from bicelle2d import build
from fig2d import render, largest_cluster, measure

LIPID_RHO = 3 * 63 / 22.0 ** 2      # 0.390, the hydrated configuration's lipid density
BASE = dict(n_lip=63, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
            n_tail=2, bond_span=2.0, polarity=0.80, head_q=1.2, hydrophobic=0.6, attract=1.5)


def nn_frac(e, thresh=0.5):
    """Fraction of lipid beads with a non-bonded neighbour inside half contact -- the collapse test
    the harness itself uses."""
    P = e.X[e._mol.ravel(), :e.pd]
    d = P[:, None, :] - P[None, :, :]
    d -= e.L * np.round(d / e.L)
    r = np.linalg.norm(d, axis=2)
    np.fill_diagonal(r, np.inf)
    return float((r.min(axis=1) < thresh).mean())


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    bound = (3 * 63 / LIPID_RHO) ** 0.5 / 2.0        # same lipid density in both arms
    print(f"MATCHED LIPID DENSITY {LIPID_RHO:.3f} (bound={bound:.1f}) -- solvent is the only variable")
    print(f"{'arm':>10}{'nW':>6}{'largest':>9}{'nn<0.5':>9}{'align':>8}   verdict", flush=True)
    for label, nw in (("vacuum", 0), ("hydrated", 250)):
        e = build(0, plant="clump", n_water=nw, bound=bound, **BASE)
        e.curvature = 0.0
        for _ in range(steps):
            e.step()
        m = measure(e)
        render(e, f"{label}, matched lipid density, t={steps}", f"solv_{label}")
        print(f"{label:>10}{nw:>6}{len(largest_cluster(e)):>6}/63{nn_frac(e):>9.2f}"
              f"{m['align']:>8.3f}   {'OK' if m['ok'] else m['why'][:34]}", flush=True)
