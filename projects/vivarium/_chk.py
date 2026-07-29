import numpy as np
from bilayer3d import build, metrics

def probe(tag, **kw):
    e = build(seed=0, n_lip=142, bound=3.9, kt=0.0, speed=0.08, repel=12.0, k_bond=8.0,
              satt=0.30, spol=0.90, plant=True, n_tail=2, **kw)
    mol = e._mol
    print(f"\n--- {tag}")
    for t in (0, 200, 2000, 10000):
        if t:
            for _ in range(t - prev): e.step()
        prev = t
        b = np.linalg.norm(e.X[mol[:,0],:3]-e.X[mol[:,1],:3], axis=1)
        r13 = np.linalg.norm(e.X[mol[:,0],:3]-e.X[mol[:,2],:3], axis=1)
        z = e.X[:, 2]
        # thickness = spread of HEAD z about the two leaflet planes
        hz = e.X[mol[:,0], 2]
        thick = float(hz[hz>0].mean() - hz[hz<0].mean()) if (hz>0).any() and (hz<0).any() else 0.0
        v = float(np.linalg.norm(e.vel, axis=1).mean())
        nem = metrics(e)[2]
        print(f"  t={t:6d} bond={b.mean():.3f} r13={r13.mean():.3f}(straight=2.0) "
              f"thick={thick:5.2f} |v|={v:.4f} nematic={nem:+.3f}", flush=True)

prev = 0
probe("CD-style: no water, no electrostatics, no head dispersion",
      head_q=0.0, rad_head=0.05, no_water=True)
