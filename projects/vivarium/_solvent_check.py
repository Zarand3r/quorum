"""Is the solvent actually collapsing under curvature, or is the render zooming?

fig2d.render auto-scales on the lipid cluster and minimum-images the water, so a compact aggregate
zooms in and can make a uniform solvent look like separated clumps. This measures the solvent
directly: cell-occupancy homogeneity (std/mean over a grid), where a healthy dispersed solvent stays
near the value of a random arrangement and a collapsing one grows without bound.
"""
import numpy as np
from bicelle2d import build

BASE = dict(n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
            satt=0.30, n_tail=2, bond_span=2.0, n_water=250,
            polarity=0.80, head_q=1.2, hydrophobic=0.6)


def homogeneity(e, cells=6):
    w = e.X[e._wi, :e.pd]
    idx = (w / e.L * cells).astype(int) % cells
    flat = (idx * (cells ** np.arange(e.pd)[::-1])).sum(axis=1)
    n = np.bincount(flat, minlength=cells ** e.pd).astype(float)
    return float(n.std() / max(n.mean(), 1e-9))


rng = np.random.default_rng(0)
print("random-null homogeneity for 250 points on a 6x6 grid:")
nulls = []
for _ in range(20):
    f = rng.integers(0, 36, 250)
    n = np.bincount(f, minlength=36).astype(float)
    nulls.append(n.std() / n.mean())
print(f"  {np.mean(nulls):.3f} +/- {np.std(nulls):.3f}\n")

print(f"{'curvature':>10}{'homogeneity':>13}{'largest agg':>13}")
for cv in (0.0, 0.15, 0.30):
    e = build(0, plant=False, attract=1.0, **BASE)
    e.curvature = cv
    for _ in range(20000):
        e.step()
    from fig2d import largest_cluster
    print(f"{cv:>10.2f}{homogeneity(e):>13.3f}{len(largest_cluster(e)):>13d}", flush=True)
