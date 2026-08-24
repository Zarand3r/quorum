"""Render ONLY the largest cluster, unwrapped across the periodic boundary.

The whole-box frame cannot settle whether a 66-lipid cluster is a closed ring: at L=65 a ring of
R_mid ~ 11 is a third of the frame and sits among five other structures. This isolates it, unwraps
it so a boundary-crossing ring is not drawn as two arcs, and centres it.
"""
import sys, pathlib
import numpy as np
sys.path.insert(0, "projects/vivarium")
from _shot import write_png, disc

path, out = sys.argv[1], sys.argv[2]
z = np.load(path, allow_pickle=True)
X, species, L = z["X"], z["species"], float(z["L"])
mols = z["mols"]

# cluster on lipid beads only, cut 1.4, minimum image -- same convention as the detector
lip = np.array([i for i, s in enumerate(species) if s != 2])
P = X[lip]
n = len(P)
d = P[:, None, :] - P[None, :, :]
d -= L * np.round(d / L)
D = np.linalg.norm(d, axis=2)
adj = D < 1.4
lab = -np.ones(n, dtype=int)
c = 0
for i in range(n):
    if lab[i] >= 0:
        continue
    stack, lab[i] = [i], c
    while stack:
        j = stack.pop()
        for k in np.flatnonzero(adj[j] & (lab < 0)):
            lab[k] = c
            stack.append(k)
    c += 1
sizes = np.bincount(lab)
big = int(np.argmax(sizes))
sel = np.flatnonzero(lab == big)
print(f"{len(sizes)} clusters, largest has {len(sel)} beads")

# unwrap: BFS from a seed, placing each neighbour at its minimum image relative to the placed one
pos = np.zeros((len(sel), 2))
idx = {g: i for i, g in enumerate(sel)}
seen = np.zeros(len(sel), bool)
seen[0] = True
pos[0] = P[sel[0]]
stack = [0]
while stack:
    a = stack.pop()
    ga = sel[a]
    for gb in sel[np.flatnonzero(adj[ga][sel])]:
        b = idx[gb]
        if seen[b]:
            continue
        off = P[gb] - pos[a]
        off -= L * np.round(off / L)
        pos[b] = pos[a] + off
        seen[b] = True
        stack.append(b)
print(f"unwrapped {seen.sum()}/{len(sel)}; extent x {np.ptp(pos[:,0]):.1f} y {np.ptp(pos[:,1]):.1f} sigma")

sp = species[lip][sel]
ctr = pos.mean(0)
span = max(np.ptp(pos[:, 0]), np.ptp(pos[:, 1])) * 1.25 + 4.0
W = H = 760
img = np.zeros((H, W, 3), dtype=np.uint8)
img[:, :] = (14, 16, 22)
scale = min(W, H) * 0.92 / span
for want, rgb, rad in ((1, (232, 150, 62), 4.0), (0, (86, 160, 240), 4.8)):
    for (x, y) in (pos - ctr)[sp == want]:
        disc(img, W * 0.5 + x * scale, H * 0.5 - y * scale, rad, rgb, 1.0)
write_png(out, img)
r = np.linalg.norm(pos - ctr, axis=1)
print(f"radius from centroid: mean {r.mean():.2f} sd {r.std():.2f} min {r.min():.2f} max {r.max():.2f}"
      f"  -> CV {r.std()/r.mean():.3f}   (a closed ring is CV << 0.2; a ribbon is not)")
