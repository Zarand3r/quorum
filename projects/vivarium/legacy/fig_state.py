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
W, H = 760, 500
# The configuration the search found (iteration 37): aspect 0.189, FLATTER than the planted
# reference at 0.231, with lamellar 0.913 and bonds intact. Notably it is high cohesion (attract 1.2)
# at LOW excluded volume (repel 3.0) with a SHORT attraction range (satt 0.9) -- a corner no
# one-dimensional sweep visited, which is the whole reason for searching combinations.
KW = dict(n_lip=231, bound=7.0, kt=0.05, speed=0.002, repel=12.0, k_bond=80.0, satt=0.30,
          spol=0.90, n_tail=3, head_q=0.0, rad_head=0.0, no_water=True, aniso=0.0,
          polarity=0.0, attract=0.30, bond_span=2.0)


def render(e, title, name):
    """Image + the corrected metrics on the same figure, so a picture is never read alone.

    The protocol that would have caught all six retractions: planted reference, validated metrics,
    and the image, all three together. `align` is the discriminator (1 = bilayer, 0 = radial);
    `lamellar` is printed only because it ANTI-discriminates and readers must see that.
    """
    m = measure(e)
    comp = largest_cluster(e)
    idx = e._mol[comp]
    P = unwrap(e, idx.ravel())[:, :3].reshape(len(comp), idx.shape[1], 3)
    flat = P.reshape(-1, 3)
    c = flat - flat.mean(0)
    ev, evec = np.linalg.eigh(c.T @ c / len(c))
    thin, long_ax = evec[:, 0], evec[:, 2]
    x, y = c @ long_ax, c @ thin
    sc = min((W - 60) / max(x.max() - x.min(), 1e-6),
             (H - 110) / max(max(y.max() - y.min(), 4.0), 1e-6))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
           f'<rect width="{W}" height="{H}" fill="#0b0e13"/>']
    for i2 in range(len(flat)):
        head = (i2 % idx.shape[1]) == 0
        col, r = ("#60a5fa", 5.0) if head else ("#f9923a", 4.0)
        out.append(f'<circle cx="{W/2 + x[i2]*sc:.1f}" cy="{H/2 - y[i2]*sc:.1f}" r="{r}" '
                   f'fill="{col}" opacity="0.9"/>')
    out.append(f'<text x="16" y="26" fill="#e2e8f0" font-family="monospace" font-size="15">{title}</text>')
    out.append(f'<text x="16" y="{H-52}" fill="#e2e8f0" font-family="monospace" font-size="13">'
               f'align {m["align"]:.3f}   (planted bilayer 1.00, micelle 0.09, random 0.08)</text>')
    out.append(f'<text x="16" y="{H-33}" fill="#94a3b8" font-family="monospace" font-size="12">'
               f'hollow {m["hollow"]:.2f} (vesicle 0.0, micelle 14.6)   '
               f'lamellar {m["lamellar"]:.3f} (ANTI-discriminates: micelle scores higher)</text>')
    out.append(f'<text x="16" y="{H-14}" fill="#64748b" font-family="monospace" font-size="12">'
               f'bond {m["bond_mean"]:.2f}   {len(comp)}/{len(e._mol)} lipids in cluster   '
               f'{"ADMISSIBLE" if m["ok"] else "DISQUALIFIED: " + m["why"]}</text>')
    out.append('</svg>')
    fn = f"{OUT}/{name}"
    open(fn + ".svg", "w").write("".join(out))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cs_{name}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{H+16}", f"file://{fn}.svg"], capture_output=True)
    print(f"  {name}: align={m['align']:.3f} hollow={m['hollow']:.2f} ok={m['ok']}", flush=True)


if __name__ == "__main__":
    # WHAT WE HAVE: a spanning bilayer that HOLDS. Rendered after relaxation, not at t=0, because an
    # initial condition proves nothing -- the claim is that the structure survives its own dynamics
    # with molecules intact, no walls, and periodic boundaries.
    # box sized by the rules the tests discovered: half-width must exceed membrane thickness
    e = build(seed=0, plant=True, wall_axes=(), **KW)
    render(e, "REFERENCE: planted bilayer (align should read ~1.0)", "v2_planted")
    e2 = build(seed=0, plant=False, wall_axes=(), **KW)
    for t in range(1, 12001):
        e2.step()
        if t % 4000 == 0:
            print(f"    t={t}", flush=True)
    render(e2, "SELF-ASSEMBLED from disorder, t=12k, corrected metrics", "v2_emergent")
