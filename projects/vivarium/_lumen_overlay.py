"""Draw the DETECTED lumen under the beads, so render and metric cannot flatter each other.

Every structural dispute in this project came from comparing a number computed on one thing with a
picture of another. This puts both on one canvas: RED = the grid cells the gate calls enclosed
interior, drawn beneath the beads of the very cluster the gate ran on.
"""
import sys, glob, re
sys.path.insert(0, "/home/rbao/quorum-thermolife/projects/vivarium")
import numpy as np
from collections import deque
from _shot import write_png, disc
from _lumen_field import _interior_mask, _mol_centroids

HEAD, TAIL, WATER = 0, 1, 2
sd, step = sys.argv[1], sys.argv[2]   # usage: _lumen_overlay <seed> <zero-padded-step>
f = glob.glob(f"docs/hits/*ht-0.25*sd{sd}_s{step}.npz")[0]
z = np.load(f, allow_pickle=True)
X = z["X"]; mols = [np.asarray(m, dtype=int) for m in z["mols"]]; L = float(z["L"]); sp = z["species"]

cen = _mol_centroids(X, mols, L); d = cen[:, None, :] - cen[None, :, :]; d -= L*np.round(d/L)
near = np.linalg.norm(d, axis=2) < 8.0; seen = np.zeros(len(mols), bool); best = []
for s in range(len(mols)):
    if seen[s]: continue
    comp, q = [s], deque([s]); seen[s] = True
    while q:
        i = q.popleft()
        for j in np.flatnonzero(near[i]):
            if seen[j]: continue
            dd = X[mols[i]][:, None, :] - X[mols[j]][None, :, :]; dd -= L*np.round(dd/L)
            if np.linalg.norm(dd, axis=2).min() < 1.4:
                seen[j] = True; comp.append(j); q.append(j)
    if len(comp) > len(best): best = comp
sub = [mols[i] for i in best]

# CRITICAL: _interior_mask unwraps the cluster and recentres it on L/2. The mask therefore lives in
# a DIFFERENT frame from X. Drawing beads at X%L against that mask compares two different pictures --
# the exact class of error this overlay exists to prevent. Rebuild the same transform for the beads.
from _lumen_field import unwrap_cluster
_P = unwrap_cluster(X, sub, L)
if _P is None: _P = np.asarray(X[np.concatenate(sub)])
_shift = -_P.mean(axis=0) + L/2.0
Xd = (X + _shift) % L
Pd = (_P + _shift) % L
interior = _interior_mask(X, sub, L, 0.5, 1.0)
n = interior.shape[0]; vis = np.zeros_like(interior); keep = np.zeros_like(interior)
for i in range(n):
    for j in range(n):
        if not interior[i, j] or vis[i, j]: continue
        st = [(i, j)]; vis[i, j] = True; cells = []
        while st:
            a, b = st.pop(); cells.append((a, b))
            for da, db in ((1,0),(-1,0),(0,1),(0,-1)):
                p, q2 = a+da, b+db
                if 0 <= p < n and 0 <= q2 < n and interior[p, q2] and not vis[p, q2]:
                    vis[p, q2] = True; st.append((p, q2))
        if len(cells) >= 40:
            for a, b in cells: keep[a, b] = True

S = 900; img = np.zeros((S, S, 3), np.uint8); img[:, :] = (13, 17, 23)
ys, xs = np.nonzero(keep)                      # cell (i,j) -> x=i*0.5, y=j*0.5
for cx, cy in zip(ys, xs):
    px0 = int(cx*0.5/L*S); py0 = int(cy*0.5/L*S)
    px1 = max(px0+1, int((cx*0.5+0.5)/L*S)); py1 = max(py0+1, int((cy*0.5+0.5)/L*S))
    img[S-1-np.clip(np.arange(py0,py1),0,S-1)[:,None], np.clip(np.arange(px0,px1),0,S-1)[None,:]] = (140, 34, 38)

beads = np.concatenate(sub); other = np.setdiff1d(np.arange(len(X)), beads)
def put(idx, rgb, r, src=None):
    for p in (src if src is not None else Xd[idx]):
        disc(img, p[0] % L/L*S, S-1-(p[1] % L/L*S), r, rgb, 1.0)
put(other, (51, 64, 84), 1.6)
put(None, (255, 152, 64), 3.2, src=Pd[sp[beads] == TAIL])
put(None, (77, 181, 255), 4.2, src=Pd[sp[beads] == HEAD])
out = f"docs/images/LUMEN_OVERLAY_sd{sd}_s{step}.png"
write_png(out, img)
print(f"{out}  lipids={len(best)}  lumen_cells={int(keep.sum())}")
