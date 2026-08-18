"""Render a 2-D configuration with its validated metrics printed alongside.

Used when a metric reading is doubtful: `enclosed` came back 2.96 and 19.49, both far above the bulk
density of 1.0, which a real lumen cannot be. An image settles what the structure actually is.
"""
import subprocess
import sys

import numpy as np
from bicelle2d import build
from harness import largest_cluster, measure, unwrap

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W, H = 720, 520


def render(e, title, name):
    m = measure(e)
    comp = largest_cluster(e)
    idx = e._mol[comp]
    P = unwrap(e, idx.ravel())[:, :2].reshape(len(comp), idx.shape[1], 2)
    cen = P.reshape(-1, 2).mean(0)
    wi = e._wi
    dw = e.X[wi, :2] - cen
    dw -= e.L * np.round(dw / e.L)
    sc = min((W - 80) / max(np.ptp(P[:, :, 0]), 1e-6), (H - 140) / max(np.ptp(P[:, :, 1]), 1e-6))
    sc = min(sc, 26.0)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
           f'<rect width="{W}" height="{H}" fill="#0b0e13"/>']
    for k in range(len(wi)):                        # water first, behind
        out.append(f'<circle cx="{W/2 + dw[k,0]*sc:.1f}" cy="{H/2 - dw[k,1]*sc:.1f}" r="2.2" '
                   f'fill="#38bdf8" opacity="0.35"/>')
    for i in range(len(comp)):
        for b in range(idx.shape[1]):
            px = W / 2 + (P[i, b, 0] - cen[0]) * sc
            py = H / 2 - (P[i, b, 1] - cen[1]) * sc
            col, r = ("#60a5fa", 4.5) if b == 0 else ("#f9923a", 3.6)
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{col}" opacity="0.95"/>')
    out.append(f'<text x="16" y="26" fill="#e2e8f0" font-family="monospace" font-size="15">{title}</text>')
    out.append(f'<text x="16" y="{H-56}" fill="#e2e8f0" font-family="monospace" font-size="13">'
               f'align {m["align"]:.3f}  (bilayer 1.00, micelle 0.09, vesicle 0.03, random 0.08)</text>')
    out.append(f'<text x="16" y="{H-36}" fill="#94a3b8" font-family="monospace" font-size="12">'
               f'hollow {m["hollow"]:.2f}   enclosed {m["enclosed"]:.2f} (bulk = 1.0)   '
               f'edge {m["edge"]:.2f}   aspect {m["aspect"]:.2f}</text>')
    out.append(f'<text x="16" y="{H-16}" fill="#64748b" font-family="monospace" font-size="12">'
               f'bond {m["bond_mean"]:.2f}   {len(comp)}/{len(e._mol)} lipids   '
               f'{"ADMISSIBLE" if m["ok"] else "DISQUALIFIED: " + m["why"]}   '
               f'blue=head orange=tail faint=water</text>')
    out.append('</svg>')
    fn = f"{OUT}/{name}"
    open(fn + ".svg", "w").write("".join(out))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/c2_{name}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{H+16}", f"file://{fn}.svg"], capture_output=True)
    print(f"  {name}: align={m['align']:.3f} enclosed={m['enclosed']:.2f} ok={m['ok']}", flush=True)


if __name__ == "__main__":
    for at, tag in ((1.0, "ves"), (1.5, "bil")):
        e = build(0, n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0,
                  satt=0.30, plant="clump", n_tail=2, attract=at, bond_span=2.0,
                  n_water=250, polarity=0.80, head_q=1.2, hydrophobic=0.6)
        for _ in range(6000):
            e.step()
        render(e, f"attract={at}, hydrophobic matrix ON, t=6000", f"d2_{tag}")
