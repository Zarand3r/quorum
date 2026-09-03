"""Render a gap-assay state to PNG. A closure COUNT is not believable until the ring is looked at.

Every structural claim in this project that was checked against a picture has at some point
contradicted the scalar that was supposed to confirm it, so `gap_closure.py` saves coordinates and
this draws them. 2-D, so the whole box is projected -- no slab, and none of the slab-thickness
artefacts that corrupted the 3-D renders.

Colours match _shot.py: water dark blue-grey, heads bright blue, tails orange, drawn water-first so
the amphiphile sits on top of the solvent.
"""
from __future__ import annotations

import sys

import numpy as np

from _shot import disc, write_png
from field import HEAD, TAIL, WATER

W = 620
COL = {WATER: (44, 54, 66), TAIL: (232, 138, 48), HEAD: (86, 170, 255)}
RAD = {WATER: 0.30, TAIL: 0.46, HEAD: 0.52}


def draw(npz_path, out_path, title=""):
    z = np.load(npz_path, allow_pickle=True)
    X, sp, L = z["X"], z["species"], float(z["L"])
    # RECENTRE FIRST. `_plant_ring` builds around the origin, so plotting np.mod(X, L) puts the ring
    # in the four corners of the box and it reads as four separate fragments -- the raw-coordinate
    # rendering error harness.py exists to prevent. The shift uses the CIRCULAR mean of the lipid
    # beads, which is well defined across a periodic boundary where an arithmetic mean is not.
    lip = sp != WATER
    ang = np.mod(X[lip], L) / L * 2 * np.pi
    cen = np.angle(np.exp(1j * ang).mean(axis=0)) / (2 * np.pi) * L
    X = np.mod(X - cen + L / 2.0, L)
    img = np.zeros((W, W, 3), dtype=np.uint8)
    img[:, :] = (14, 16, 20)
    s = W / L
    # water first, then tails, then heads -- structure on top of solvent
    for kind in (WATER, TAIL, HEAD):
        idx = np.where(sp == kind)[0]
        P = X[idx]
        for x, y in P:
            disc(img, x * s, (L - y) * s, RAD[kind] * s, COL[kind], 1.0)
    write_png(out_path, img)
    print(f"  {out_path}  n={len(X)} L={L:g} gap={float(z['gap']):g} closed={int(z['closed'])} {title}")


if __name__ == "__main__":
    draw(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
