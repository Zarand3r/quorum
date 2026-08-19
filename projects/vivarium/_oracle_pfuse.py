"""Does the ORACLE reliably merge two patches in contact? The control that can invalidate our conclusion.

Our model merges two bilayer patches placed in DIRECT CONTACT only 47% of the time at best, and no
lever moves it: temperature, well depth, chi, chain stiffness, coherent rescaling and branched tail
length have all been measured and none helps. The conclusion drawn is that the interaction form cannot
hold an aggregate together at a temperature where it can still rearrange.

That conclusion rests entirely on an assumption nobody has checked: that reliable coalescence is
REQUIRED, i.e. that a healthy membrane model would merge patches in contact close to always. If the
oracle -- which does produce vesicles from a dispersed start -- also merges only about half the time,
then 47% is normal, our criterion is wrong rather than our model, and the whole coalescence line
collapses.

So this runs the identical protocol on `bilipid.py`: two flat two-leaflet patches planted in contact,
several seeds, and the fraction of trials ending as ONE connected aggregate.

FALSIFICATION, STATED BEFORE THE RUN
    If the oracle merges near 100%, our 47% is a genuine defect and the interaction-form conclusion
    stands. If the oracle also lands near 50%, the criterion is wrong: reliable coalescence is not a
    property of working membrane models, our whole coalescence argument is void, and the reviewer
    prompt must be rewritten around a different question.
"""

import sys
from collections import deque

import numpy as np

from bilipid import BiLipid


def plant_two_patches(s, n_each, gap, spacing=1.1):
    """Two flat two-leaflet patches in the xy plane, separated along x by `gap`."""
    per_leaf = n_each // 2
    side = int(np.ceil(np.sqrt(per_leaf)))
    k = 0
    for patch in (0, 1):
        x0 = (-1 if patch == 0 else 1) * (side * spacing + gap) / 2.0
        for leaf, sgn in ((0, +1.0), (1, -1.0)):
            for j in range(per_leaf):
                if k >= s.n_mol:
                    break
                ix, iy = j % side, j // side
                x = x0 + (ix - (side - 1) / 2.0) * spacing
                y = (iy - (side - 1) / 2.0) * spacing
                # head points OUT of the bilayer, tail toward the midplane
                s.h[k] = np.array([x, y, sgn * 1.0])
                s.t[k] = np.array([x, y, sgn * 0.4])
                k += 1
    return k


def largest_frac(s, cut=1.6):
    c = 0.5 * (s.h + s.t)
    n = len(c)
    d = c[:, None, :] - c[None, :, :]
    d -= s.L * np.round(d / s.L)
    adj = np.linalg.norm(d, axis=2) < cut
    np.fill_diagonal(adj, False)
    lab = -np.ones(n, int)
    g = 0
    for st in range(n):
        if lab[st] >= 0:
            continue
        q = deque([st]); lab[st] = g
        while q:
            i = q.popleft()
            for j in np.flatnonzero(adj[i]):
                if lab[j] < 0:
                    lab[j] = g; q.append(j)
        g += 1
    return float(np.bincount(lab).max()) / n


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
    n_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    n_each, L = 30, 22.0

    print(f"ORACLE coalescence: two {n_each}-molecule patches in contact, L={L}, "
          f"{n_seed} seeds, {steps} steps")
    print(f"{'gap':>6}{'merged':>9}{'largest frac (mean)':>22}   verdict", flush=True)
    for gap in (0.0, 1.0, 2.5):
        fr = []
        for sd in range(n_seed):
            s = BiLipid(2 * n_each, L, beta=0.15, seed=sd)
            plant_two_patches(s, n_each, gap)
            for _ in range(steps):
                s.step()
            fr.append(largest_frac(s))
        merged = sum(1 for x in fr if x > 0.9)
        print(f"{gap:>6.1f}{merged:>5}/{n_seed:<3}{float(np.mean(fr)):>22.3f}   "
              f"{'MERGES reliably' if merged >= 0.8 * n_seed else 'partial'}", flush=True)
