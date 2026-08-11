"""Measure the two numbers that size a vesicle: membrane thickness d and area per amphiphile a.

A vesicle needs an outer radius R > d, or there is no lumen and the object is a solid micelle. The
amphiphile count then follows from the area of two concentric leaflets. Both numbers come from the
box-spanning slab we already have, where the geometry is unambiguous.
"""
import sys
import numpy as np

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


def geom(tag, nbins=60):
    z = np.load(f"{ST}/{tag}.npz")
    x, sp, L = z["x"], z["species"], float(z["L"])
    nb, nh, n = int(z["nb"]), int(z.get("nh", 1)), int(z["n_amph"])
    dim = x.shape[1]
    var, ax = -1, 0
    for a in range(dim):
        h, _ = np.histogram(x[sp != 0][:, a], bins=nbins, range=(0, L))
        if h.var() > var:
            var, ax = h.var(), a
    ht, _ = np.histogram(x[sp == 2][:, ax], bins=nbins, range=(0, L))
    hh, _ = np.histogram(x[sp == 1][:, ax], bins=nbins, range=(0, L))
    ht = np.roll(ht, nbins // 2 - int(np.argmax(ht)))
    hh = np.roll(hh, nbins // 2 - int(np.argmax(ht[nbins // 2 - 1:nbins // 2 + 2]) * 0))
    hh = np.roll(hh, nbins // 2 - int(np.argmax(ht)) - (nbins // 2 - int(np.argmax(ht))) + 0)
    # re-roll heads with the SAME shift applied to tails
    z2 = np.load(f"{ST}/{tag}.npz")
    hh, _ = np.histogram(z2["x"][z2["species"] == 1][:, ax], bins=nbins, range=(0, L))
    shift = nbins // 2 - int(np.argmax(np.histogram(z2["x"][z2["species"] == 2][:, ax],
                                                    bins=nbins, range=(0, L))[0]))
    hh, ht = np.roll(hh, shift), np.roll(ht * 0 + np.roll(ht, 0), 0)
    ht = np.roll(np.histogram(z2["x"][z2["species"] == 2][:, ax], bins=nbins, range=(0, L))[0], shift)
    bw = L / nbins
    # tail core width at half max; head-to-head distance between the two flanking head peaks
    half = ht.max() / 2.0
    core = float((ht > half).sum() * bw)
    c = nbins // 2
    lpk = int(np.argmax(hh[:c])); rpk = c + int(np.argmax(hh[c:]))
    h2h = float((rpk - lpk) * bw)
    area = 2.0 * L ** 2 / n if dim == 3 else 2.0 * L / n
    print(f"{tag}")
    print(f"  box L={L:.2f}  n_amph={n}  beads/amph={nb} (nh={nh})")
    print(f"  tail-core width (FWHM)      d_core = {core:.2f} rc")
    print(f"  head-peak to head-peak      d      = {h2h:.2f} rc   <- membrane thickness")
    print(f"  area per amphiphile         a      = {area:.2f} rc^2")
    print()
    print(f"  a vesicle needs outer radius R > d = {h2h:.1f}; amphiphiles = 4*pi*(R^2+(R-d)^2)/a")
    for R in (h2h * 1.2, h2h * 1.5, h2h * 1.8):
        inner = max(R - h2h, 0.0)
        namph = 4 * np.pi * (R ** 2 + inner ** 2) / area
        Lbox = 3.5 * R          # dilute enough that a box-spanning lamella costs MORE lipids
        Npart = 3.0 * Lbox ** 3
        print(f"    R={R:5.1f}  lumen r={inner:4.1f}  n_amph={namph:6.0f}  "
              f"box L>={Lbox:5.1f}  N_particles={Npart:8.0f}")


for t in sys.argv[1:]:
    geom(t)
