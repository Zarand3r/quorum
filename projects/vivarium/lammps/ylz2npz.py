"""Convert a solvent-free YLZ dump frame to this project's state format.

The YLZ model has no solvent and no head/tail split: every particle IS a membrane particle with an
orientation. For rendering and for the shape metrics they are all one species; the species-based
measures (paired, burial) do not apply and must not be reported for these states.
"""
import sys
import numpy as np

path, out, frame = sys.argv[1], sys.argv[2], int(sys.argv[3])
lines = open(path).readlines()
frames, i = [], 0
while i < len(lines):
    if lines[i].startswith("ITEM: TIMESTEP"):
        step = int(lines[i + 1]); nat = int(lines[i + 3])
        lo, hi = (float(v) for v in lines[i + 5].split()[:2])
        hdr = lines[i + 8].split()[2:]
        ci = [hdr.index(k) for k in ("x", "y", "z")]
        arr = np.array([[float(lines[i + 9 + k].split()[c]) for c in ci] for k in range(nat)])
        frames.append((step, hi - lo, arr))
        i += 9 + nat
    else:
        i += 1
step, L, x = frames[frame]
np.savez_compressed(out, x=np.mod(x, L), species=np.full(len(x), 2, int), L=float(L),
                    n_amph=len(x), nb=1, nh=0)
print(f"frame t={step} L={L:.2f} n={len(x)} -> {out}")
