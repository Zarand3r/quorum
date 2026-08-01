"""Is the solvent-free aggregate genuinely HOLLOW, or is `hollow` being fooled?

hollow=0.05 sits at the planted-vesicle value (0.00), far from the planted micelle (14.56). Before
believing it, look at the raw radial distribution: a shell has tails in a band with an empty middle;
a filled micelle has tails all the way to r=0.
"""
import numpy as np
from bilayer3d import build
from harness import largest_cluster, measure, unwrap

e = build(seed=0, plant=False, n_lip=231, bound=7.0, kt=0.02, speed=0.002, repel=12.0,
          k_bond=40.0, satt=0.30, spol=0.90, n_tail=4, head_q=0.0, rad_head=0.0,
          no_water=True, aniso=0.0, polarity=0.0, attract=0.30, bond_span=2.0, wall_axes=())
for _ in range(12000):
    e.step()
m = measure(e)
comp = largest_cluster(e)
idx = e._mol[comp]
P = unwrap(e, idx.ravel())[:, :3].reshape(len(comp), idx.shape[1], 3)
cen = P.reshape(-1, 3).mean(0)
rh = np.linalg.norm(P[:, 0] - cen, axis=1)
rt = np.linalg.norm(P[:, 1:].reshape(-1, 3) - cen, axis=1)
print(f"  align={m['align']:.3f} lamellar={m['lamellar']:.3f} hollow={m['hollow']:.3f} "
      f"aspect={m['aspect']:.2f} n={m['n_cluster']}/{len(e._mol)} ok={m['ok']}")
bins = np.linspace(0, max(rt.max(), rh.max()) * 1.02, 16)
ch, _ = np.histogram(rh, bins=bins)
ct, _ = np.histogram(rt, bins=bins)
mx = max(ch.max(), ct.max(), 1)
print(f"  {'radius':>7}  {'HEAD':<22} {'TAIL'}")
for i in range(len(ch)):
    r = 0.5 * (bins[i] + bins[i + 1])
    print(f"  {r:>7.2f}  {'#' * int(20 * ch[i] / mx):<22} {'*' * int(20 * ct[i] / mx)}")
print(f"\n  tails inside r=1.5: {(rt < 1.5).sum()}   (a sealed shell should have ~0)")
