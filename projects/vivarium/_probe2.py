"""The synthesis: DOUBLE-TAILED lipid (which stabilises lamellar order) from a FULLY DISPERSED start,
run long enough to pass the fragmentation phase (every previous run stopped at t=6000, inside it).
Renders at checkpoints so the structure is seen, not inferred.
"""
import subprocess
import numpy as np
from bicelle2d import build
from harness import bond_stats, measure, unwrap, _periodic_axes

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
W = 520
KW = dict(n_lip=40, bound=11.0, kt=0.02, speed=0.001, repel=12.0, k_bond=30.0, satt=0.30,
          n_tail=4, branched=True, attract=1.0, bond_span=2.0, n_water=250, polarity=0.80,
          head_q=1.2, hydrophobic=0.6)

def aggregates(e):
    mol, sig = e._mol, e.sigma
    cutoff = 1.6 * float(2.0 * np.median(sig))
    P = e.X[mol.ravel(), :e.pd]
    d = P[:, None, :] - P[None, :, :]
    free = _periodic_axes(e)
    d[:, :, free] -= e.L * np.round(d[:, :, free] / e.L)
    near = np.linalg.norm(d, axis=2) < cutoff
    nb = mol.shape[1]
    m = near.reshape(len(mol), nb, len(mol), nb).any(axis=(1, 3))
    seen, sizes = set(), []
    for s in range(len(mol)):
        if s in seen: continue
        stack, c = [s], 0
        seen.add(s)
        while stack:
            u = stack.pop(); c += 1
            for v in np.where(m[u])[0]:
                if v not in seen:
                    seen.add(v); stack.append(v)
        sizes.append(c)
    return sorted(sizes, reverse=True)

def shoot(e, tag, title, sub):
    B = e.cfg.pos_bound; sc = (W * 0.42) / B; c = W / 2
    P = unwrap(e, np.arange(len(e.X)))[:, :2]
    P = P - P[e.species != 0].mean(0)
    sp, sig = e.species, e.sigma
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}">'
         f'<rect width="{W}" height="{W}" fill="#0b0e13"/>']
    for i in np.where(sp == 0)[0]:
        o.append(f'<circle cx="{c+P[i,0]*sc:.1f}" cy="{c-P[i,1]*sc:.1f}" r="{sig[i]*sc:.1f}"'
                 f' fill="#1e3a5f" opacity="0.26"/>')
    for i in np.where(sp != 0)[0]:
        col = "#38bdf8" if int(sp[i]) == 5 else "#fb923c"
        o.append(f'<circle cx="{c+P[i,0]*sc:.1f}" cy="{c-P[i,1]*sc:.1f}" r="{sig[i]*sc:.1f}"'
                 f' fill="{col}" opacity="0.72" stroke="#0b0e13" stroke-width="0.5"/>')
    o.append(f'<rect x="0" y="{W-42}" width="{W}" height="42" fill="#0b0e13" opacity="0.92"/>'
             f'<text x="9" y="{W-25}" fill="#e2e8f0" font-family="monospace" font-size="12">{title}</text>'
             f'<text x="9" y="{W-8}" fill="#94a3b8" font-family="monospace" font-size="11">{sub}</text></svg>')
    fn = f"{OUT}/{tag}"
    open(fn + ".svg", "w").write("".join(o))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{tag}", f"--screenshot={fn}.png",
                    f"--window-size={W+16},{W+16}", f"file://{fn}.svg"], capture_output=True)

e = build(7, plant=False, **KW)
print(f"  {'step':>8}{'n_agg':>7}{'largest':>9}{'align':>7}{'pack':>7}{'bond':>7}  verdict", flush=True)
for t in (6000, 20000, 60000, 150000, 300000):
    while getattr(e, "_t", 0) < t:
        e.step(); e._t = getattr(e, "_t", 0) + 1
    sz = aggregates(e); big = [s for s in sz if s >= 3]
    m = measure(e); mean, _, frac = bond_stats(e)
    print(f"  {t:>8}{len(big):>7}{sz[0]:>9}{m['align']:>7.3f}{m['packing']:>7.3f}{mean:>7.3f}"
          f"  {'OK' if m['ok'] else m['why'][:24]}", flush=True)
    shoot(e, f"dbl_{t}", f"DOUBLE-TAILED, dispersed start, t={t}",
          f"aggregates {len(big)}  largest {sz[0]}  align {m['align']:.3f}  "
          f"packing {m['packing']:.3f}  bond {mean:.3f}")
