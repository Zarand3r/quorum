"""Render the current ADMISSIBLE state: edge-on cross-section of the largest cluster.

Everything goes through harness.unwrap(), because an aggregate straddling the periodic boundary
renders as scattered debris if you plot raw coordinates -- the same wrapping bug that corrupted the
bond measurements. The view is the cluster's own frame: long axis horizontal, thin axis vertical, so
a lamellar structure shows heads in two rows with the tail core between them.
"""
import subprocess

import numpy as np
from bilayer3d import build
from harness import largest_cluster, measure, unwrap

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W, H = 720, 460
# The configuration the search found (iteration 37): aspect 0.189, FLATTER than the planted
# reference at 0.231, with lamellar 0.913 and bonds intact. Notably it is high cohesion (attract 1.2)
# at LOW excluded volume (repel 3.0) with a SHORT attraction range (satt 0.9) -- a corner no
# one-dimensional sweep visited, which is the whole reason for searching combinations.
KW = dict(n_lip=120, bound=5.0, kt=0.05, speed=0.002, repel=3.0, k_bond=80.0, satt=0.90,
          spol=0.90, n_tail=3, head_q=0.0, rad_head=0.0, no_water=True, aniso=0.0,
          polarity=0.0, attract=1.20, bond_span=2.0)


def render(e, title, name):
    m = measure(e)
    comp = largest_cluster(e)
    idx = e._mol[comp]
    P = unwrap(e, idx.ravel(), ref=idx[0, 0]).reshape(len(comp), idx.shape[1], 3)
    flat = P.reshape(-1, 3)
    c = flat - flat.mean(0)
    ev, evec = np.linalg.eigh(c.T @ c / len(c))
    thin, long_ax = evec[:, 0], evec[:, 2]
    x = c @ long_ax
    y = c @ thin
    sx = (W - 60) / max(x.max() - x.min(), 1e-6)
    sy = (H - 90) / max(max(y.max() - y.min(), 4.0), 1e-6)
    sc = min(sx, sy)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
           f'<rect width="{W}" height="{H}" fill="#0b0e13"/>']
    n_head = len(comp)
    for i in range(len(flat)):
        head = (i % idx.shape[1]) == 0
        px = W / 2 + x[i] * sc
        py = H / 2 - y[i] * sc
        col, r = ("#60a5fa", 5.0) if head else ("#f9923a", 4.0)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{col}" opacity="0.9"/>')
    out.append(f'<text x="16" y="28" fill="#e2e8f0" font-family="monospace" font-size="15">{title}</text>')
    out.append(f'<text x="16" y="{H-34}" fill="#94a3b8" font-family="monospace" font-size="13">'
               f'lamellar {m["lamellar"]:.3f} (random 0.50, planted 1.00)   '
               f'aspect {m["aspect"]:.2f} (random 0.85, planted 0.23)</text>')
    out.append(f'<text x="16" y="{H-14}" fill="#64748b" font-family="monospace" font-size="12">'
               f'bond {m["bond_mean"]:.2f} (rest 1.00) - molecules intact   |   '
               f'{n_head} lipids in the cluster   |   blue = head, orange = tail</text>')
    out.append('</svg>')
    fn = f"{OUT}/{name}"
    open(fn + ".svg", "w").write("".join(out))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cs_{name}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{H+16}", f"file://{fn}.svg"], capture_output=True)
    print(f"  {name}: lamellar={m['lamellar']:.3f} aspect={m['aspect']:.2f} bond={m['bond_mean']:.2f}",
          flush=True)


if __name__ == "__main__":
    render(build(seed=0, plant=True, wall_axes=(), **KW), "REFERENCE: planted bilayer (search config)", "win_planted")
    e = build(seed=0, plant=False, wall_axes=(), **KW)
    for t in range(1, 8001):
        e.step()
        if t % 4000 == 0:
            print(f"    t={t}", flush=True)
    render(e, "SEARCH BEST: self-assembled, periodic, no walls, t=8k", "win_emergent")
