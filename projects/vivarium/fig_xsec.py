"""Edge-on CROSS-SECTION of the membrane, the standard way a bilayer is shown.

A 3-D view of a dense slab is unreadable. Taking a thin slice in y and plotting (x, z) shows the
leaflets directly: a BILAYER has TWO head layers with the tail core between them, a MONOLAYER has
one. This also settles the thickness question -- the self-assembled slab measured L1/L3 = 0.17,
implying ~4.1 thick, where a 4-bead-tail bilayer should be ~9.
"""
import subprocess

import numpy as np
from bilayer3d import build, lamellar, shape

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W, H = 620, 420
KW = dict(n_lip=231, bound=5.0, kt=0.02, speed=0.005, repel=12.0, k_bond=40.0, satt=0.30,
          spol=0.90, n_tail=4, head_q=0.0, rad_head=0.0, no_water=True, aniso=0.0,
          polarity=0.0, attract=0.30, bond_span=6.0, wall_axes=(2,))


def xsec(e, title, name, slab=1.2):
    mol = e._mol
    B = e.cfg.pos_bound
    sel = np.abs(e.X[:, 1]) < slab                       # thin slice in y
    heads = set(mol[:, 0].tolist())
    sx, sz = (W - 60) / (2 * B), (H - 70) / (2 * B)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
           f'<rect width="{W}" height="{H}" fill="#0b0e13"/>']
    for i in np.where(sel)[0]:
        x = 30 + (e.X[i, 0] + B) * sx
        z = H - 40 - (e.X[i, 2] + B) * sz
        head = i in heads
        col, r = ("#60a5fa", 5.5) if head else ("#f9923a", 4.5)
        out.append(f'<circle cx="{x:.1f}" cy="{z:.1f}" r="{r}" fill="{col}" opacity="0.92"/>')
    a1, a2 = shape(e)
    hz = e.X[mol[:, 0], 2]
    thick = float(hz[hz > hz.mean()].mean() - hz[hz < hz.mean()].mean())
    out.append(f'<text x="16" y="26" fill="#e2e8f0" font-family="monospace" font-size="15">{title}</text>')
    out.append(f'<text x="16" y="{H-12}" fill="#94a3b8" font-family="monospace" font-size="13">'
               f'lamellar {lamellar(e):.3f}   head-layer separation {thick:.1f}   L1/L3 {a1:.2f}  '
               f'blue = head, orange = tail</text>')
    out.append('</svg>')
    fn = f"{OUT}/{name}"
    open(fn + ".svg", "w").write("".join(out))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cx_{name}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{H+16}", f"file://{fn}.svg"], capture_output=True)

    # density profile along z: TWO head peaks = bilayer, ONE = monolayer
    tz = e.X[mol[:, 1:].ravel(), 2]
    bins = np.linspace(-B, B, 25)
    ch, _ = np.histogram(hz, bins=bins); ct, _ = np.histogram(tz, bins=bins)
    mx = max(ch.max(), ct.max(), 1)
    print(f"\n  {title}   lamellar={lamellar(e):.3f}  head-layer sep={thick:.1f}")
    for i in range(len(ch)):
        z = 0.5 * (bins[i] + bins[i + 1])
        print(f"   z={z:+5.1f}  {'#'*int(24*ch[i]/mx):<26}{'*'*int(24*ct[i]/mx)}", flush=True)


if __name__ == "__main__":
    xsec(build(seed=0, plant=True, **KW), "PLANTED reference (4-bead tails)", "xsec_planted")
    e = build(seed=0, plant=False, **KW)
    for t in range(1, 10001):
        e.step()
    xsec(e, "SELF-ASSEMBLED from disorder, t=10k", "xsec_emergent")
