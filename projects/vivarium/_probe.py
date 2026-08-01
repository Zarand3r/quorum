"""Render the equilibrated single-tailed dispersed system. It holds align 0.73 with 5 finite
aggregates from t=20k to t=150k, which is either short BILAYER RIBBONS (lipids aligned across a
short axis -- stage 2) or dense piles. packing 0.452 sits just above the micelle floor of 0.436, so
the number cannot decide it. The image can.
"""
import subprocess
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure, unwrap

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W = 560
FIG = dict(n_lip=63, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
           n_tail=2, attract=1.0, bond_span=2.0, n_water=250, polarity=0.80, head_q=1.2,
           hydrophobic=0.6)

e = build(7, plant=False, **FIG)
for t in (20000, 60000):
    while getattr(e, "_t", 0) < t:
        e.step(); e._t = getattr(e, "_t", 0) + 1
    m = measure(e); mean, _, frac = bond_stats(e)
    B = e.cfg.pos_bound; sc = (W * 0.42) / B; c = W / 2
    P = unwrap(e, np.arange(len(e.X)))[:, :2]; P = P - P[e.species != 0].mean(0)
    sp, sig = e.species, e.sigma
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}">'
         f'<rect width="{W}" height="{W}" fill="#0b0e13"/>']
    for i in np.where(sp == 0)[0]:
        o.append(f'<circle cx="{c+P[i,0]*sc:.1f}" cy="{c-P[i,1]*sc:.1f}" r="{sig[i]*sc:.1f}"'
                 f' fill="#1e3a5f" opacity="0.24"/>')
    nb = len(e._mol) * (e._mol.shape[1] - 1)
    for a, b in zip(e._bond_i[:nb], e._bond_j[:nb]):
        if np.abs(P[b] - P[a]).max() > B: continue
        o.append(f'<line x1="{c+P[a,0]*sc:.1f}" y1="{c-P[a,1]*sc:.1f}" x2="{c+P[b,0]*sc:.1f}"'
                 f' y2="{c-P[b,1]*sc:.1f}" stroke="#e2e8f0" stroke-width="0.9" opacity="0.5"/>')
    for i in np.where(sp != 0)[0]:
        col = "#38bdf8" if int(sp[i]) == 5 else "#fb923c"
        o.append(f'<circle cx="{c+P[i,0]*sc:.1f}" cy="{c-P[i,1]*sc:.1f}" r="{sig[i]*sc:.1f}"'
                 f' fill="{col}" opacity="0.74" stroke="#0b0e13" stroke-width="0.5"/>')
    o.append(f'<rect x="0" y="{W-42}" width="{W}" height="42" fill="#0b0e13" opacity="0.92"/>'
             f'<text x="9" y="{W-25}" fill="#e2e8f0" font-family="monospace" font-size="12">'
             f'SINGLE-TAILED, dispersed start, t={t}</text>'
             f'<text x="9" y="{W-8}" fill="#94a3b8" font-family="monospace" font-size="11">'
             f'align {m["align"]:.3f}   packing {m["packing"]:.3f}   bond {mean:.3f}   '
             f'micelle ref 0.436 / bilayer ref 0.713</text></svg>')
    fn = f"{OUT}/single_{t}"
    open(fn + ".svg", "w").write("".join(o))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_s{t}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{W+16}", f"file://{fn}.svg"], capture_output=True)
    print(f"  t={t}  align {m['align']:.3f}  packing {m['packing']:.3f}  -> {fn}.png", flush=True)
