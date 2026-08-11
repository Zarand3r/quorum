"""Transverse density profile: is the SL slab a real bilayer, or just a slab?

A bilayer has TWO head peaks flanking a tail core. A disordered slab has heads and tails overlapping.
The 2-D branched ribbons looked visually crisper than the 3-D SL slab, so the claim that the SL result
is "better" needs a number, not an impression.

Profile is taken along the axis with the strongest amphiphile density contrast (the membrane normal),
using the largest aggregate only.
"""
import sys
import numpy as np

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"

def profile(tag, nbins=40):
    z = np.load(f"{ST}/{tag}.npz")
    x, sp, L = z["x"], z["species"], float(z["L"])
    dim = x.shape[1]
    lip = sp != 0
    # membrane normal = axis whose amphiphile density profile has the largest variance
    var, ax = -1, 0
    for a in range(dim):
        h, _ = np.histogram(x[lip][:, a], bins=nbins, range=(0, L))
        if h.var() > var:
            var, ax = h.var(), a
    hh, edges = np.histogram(x[(sp == 1)][:, ax], bins=nbins, range=(0, L))
    ht, _ = np.histogram(x[(sp == 2)][:, ax], bins=nbins, range=(0, L))
    hh = hh / max(hh.max(), 1); ht = ht / max(ht.max(), 1)
    # centre on the tail maximum so the profile is readable, using periodic roll
    shift = nbins // 2 - int(np.argmax(ht))
    hh, ht = np.roll(hh, shift), np.roll(ht, shift)
    # a bilayer: tails peak at the centre, heads peak on BOTH sides of it
    c = nbins // 2
    left, right = hh[:c], hh[c:]
    seg = float(ht[c - 2:c + 3].mean() - hh[c - 2:c + 3].mean())   # tail excess at the core
    both = float(min(left.max(), right.max()))                     # head signal on both faces
    print(f"\n{tag}  (normal = axis {ax})")
    print("  tails " + "".join("#" if v > 0.5 else ("+" if v > 0.2 else ".") for v in ht))
    print("  heads " + "".join("#" if v > 0.5 else ("+" if v > 0.2 else ".") for v in hh))
    print(f"  tail excess at core {seg:+.2f}   head signal on both faces {both:.2f}   "
          f"{'BILAYER (tail core, heads both sides)' if seg > 0.25 and both > 0.4 else 'not a clean bilayer'}")

for tag in sys.argv[1:]:
    profile(tag)
