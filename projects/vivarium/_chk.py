"""Track the MOLECULE, not just the aggregate. If the lipid itself is deforming, `nematic` is noise.

With bond_span=6.0 the straightener saturates against a backbone that also saturates, so the chain
can stretch without a restoring force. If bonds run far past BOND_REST the "lipid" is a long floppy
string and every orientational metric computed from its axis is meaningless.
"""
import numpy as np
from bilayer3d import build, metrics

for span, bf in ((2.0, 1.0), (6.0, 1.0)):
    e = build(seed=0, n_lip=231, bound=5.0, kt=0.0, speed=0.005, repel=12.0, k_bond=8.0,
              satt=0.30, spol=0.90, plant=True, n_tail=2, head_q=0.0, rad_head=0.0,
              no_water=True, aniso=0.0, bond_span=span, bend_frac=bf)
    mol = e._mol
    print(f"\n--- span={span} bend_frac={bf}  (BOND_REST=1.0, straight r13=2.0)")
    prev = 0
    for t in (0, 2000, 6000, 12000):
        for _ in range(t - prev):
            e.step()
        prev = t
        b = np.linalg.norm(e.X[mol[:,0],:3]-e.X[mol[:,1],:3], axis=1)
        r13 = np.linalg.norm(e.X[mol[:,0],:3]-e.X[mol[:,2],:3], axis=1)
        u = e.chain_axis()
        tilt = np.degrees(np.arccos(np.clip(np.abs(u[:, 2]), 0, 1)))   # 0 = normal to sheet
        v = float(np.linalg.norm(e.vel, axis=1).mean())
        print(f"  t={t:6d} bond={b.mean():.2f}+/-{b.std():.2f} r13={r13.mean():.2f} "
              f"tilt={tilt.mean():5.1f}deg |v|={v:.4f} nematic={metrics(e)[2]:+.3f}", flush=True)
