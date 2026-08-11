"""Dimension-generic bilayer measure: locally PAIRED and locally FLAT.

`harness.bilayer_fraction` already encodes the right idea but is 2-D only (defect #26): a planted
3-D bilayer scores 0.000 there, identical to a 3-D gas, so every 3-D reading from it is void. This
module rebuilds the same conjunction so a 2-D branched ribbon and a 3-D slab can be scored on one
footing, which is what comparing them requires.

Why a conjunction. Measured here, both halves fail alone:
  * PAIRED alone (anti-aligned axes, touching tail tips, heads splayed across the core) reads
    1.000 on a planted bilayer AND 1.000 on a planted micelle -- a micelle's antipodal molecules
    are anti-aligned with tips that meet at the centre, so it satisfies every pair criterion. This
    reproduces the 1.000-vs-0.984 collision recorded in harness.bilayer_fraction's docstring.
  * FLAT alone cannot separate a bilayer from a nematic droplet, since both have parallel molecules.
A bilayer is the only structure that is both.

Proximity uses TERMINAL tail beads, not tail centroids. In a planted bilayer the two leaflets'
centroids sit ~1.8 apart -- outside any contact cutoff -- because each is pulled back toward its own
head. Gating on centroids read 0.000 on a planted bilayer, i.e. blind in the direction that matters.

The micelle pole is built PHYSICALLY rather than at an arbitrary size: tail tips meet at the centre,
which fixes the radius at one molecule length, which then fixes how many molecules fit at their
natural head spacing. An over-packed micelle would be locally flat merely because its molecules were
crowded into a small angular step, and would make the flatness term look more discriminating than it
is.
"""
import sys
import numpy as np

ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"


def _axes(x, L, b0, nb, nh):
    head = np.stack([x[b0 + t] for t in range(nh)]).mean(axis=0)
    tail = np.stack([x[b0 + t] for t in range(nh, nb)]).mean(axis=0)
    tip = x[b0 + (nb - 1)]
    u = head - tail
    u -= L * np.round(u / L)
    u /= np.linalg.norm(u, axis=1, keepdims=True) + 1e-12
    return head, tip, u


def _mic(a, b, L):
    d = a[:, None, :] - b[None, :, :]
    return d - L * np.round(d / L)


def bilayer_frac(x, L, b0, nb, nh, rcut=1.5, flat=0.90):
    head, tip, u = _axes(x, L, b0, nb, nh)
    dot = u @ u.T
    D = np.linalg.norm(_mic(tip, tip, L), axis=2)
    np.fill_diagonal(D, np.inf)
    H = np.linalg.norm(_mic(head, head, L), axis=2)
    paired = ((D < rcut) & (dot < -0.5) & (H > D)).any(axis=1)

    # local flatness: same-leaflet neighbours (co-aligned, heads close) must be nearly parallel.
    # Inside a micelle consecutive molecules fan by the angular step set by its radius, so this
    # fails there while holding across a flat or gently curved leaflet.
    same = (H < 1.6) & (dot > 0.5)
    np.fill_diagonal(same, False)
    cnt = same.sum(axis=1)
    mean_dot = np.where(cnt > 0, (dot * same).sum(axis=1) / np.maximum(cnt, 1), 0.0)
    is_flat = (cnt >= 2) & (mean_dot > flat)
    return float((paired & is_flat).mean()), float(paired.mean()), float(is_flat.mean())


def _plant_bilayer(dim, nb=4, m=60, pitch=0.9):
    pts, b0 = [], []
    for leaf, sgn in ((0, +1.0), (1, -1.0)):
        for i in range(m):
            if dim == 2:
                base, ax = np.array([(i + 0.5) * pitch, 6.0]), np.array([0.0, 1.0])
            else:
                g = int(np.ceil(np.sqrt(m)))
                base = np.array([(i % g + 0.5) * pitch, (i // g + 0.5) * pitch, 6.0])
                ax = np.array([0.0, 0.0, 1.0])
            for t in range(nb):
                pts.append(base + sgn * (0.4 + (nb - 1 - t) * 0.5) * ax)
            b0.append(len(b0) * nb)
    return np.array(pts), np.array(b0)


def _plant_micelle(dim, nb=4, pitch=0.9):
    R = 0.4 + (nb - 1) * 0.5                     # tips meet at the centre: radius = molecule length
    M = int(2 * np.pi * R / pitch) if dim == 2 else int(4 * np.pi * R ** 2 / pitch ** 2)
    pts, b0, c = [], [], np.full(dim, 10.0)
    for i in range(M):
        if dim == 2:
            th = 2 * np.pi * i / M
            ax = np.array([np.cos(th), np.sin(th)])
        else:
            zc = 1 - 2 * (i + 0.5) / M
            rr = np.sqrt(max(1 - zc * zc, 0.0))
            th = np.pi * (1 + 5 ** 0.5) * i
            ax = np.array([rr * np.cos(th), rr * np.sin(th), zc])
        for t in range(nb):
            pts.append(c + (0.4 + (nb - 1 - t) * 0.5) * ax)    # head outermost
        b0.append(len(b0) * nb)
    return np.array(pts), np.array(b0), M


def calibrate():
    print(f"{'pole':28s}{'bilayer_frac':>14}{'paired':>9}{'flat':>7}")
    for dim in (2, 3):
        x, b0 = _plant_bilayer(dim)
        f, p, fl = bilayer_frac(x % 60.0, 60.0, b0, 4, 1)
        print(f"{f'{dim}-D planted BILAYER':28s}{f:>14.3f}{p:>9.3f}{fl:>7.3f}")
        x, b0, M = _plant_micelle(dim)
        f, p, fl = bilayer_frac(x % 20.0, 20.0, b0, 4, 1)
        print(f"{f'{dim}-D planted MICELLE (M={M})':28s}{f:>14.3f}{p:>9.3f}{fl:>7.3f}")


def largest_aggregate(x, L, b0, nb, contact=1.2):
    """Indices of molecules in the biggest connected cluster (union-find over touching tail beads)."""
    n = len(b0)
    beads = np.concatenate([b0 + t for t in range(nb)])
    owner = np.concatenate([np.arange(n) for _ in range(nb)])
    D = np.linalg.norm(_mic(x[beads], x[beads], L), axis=2)
    i, j = np.nonzero(D < contact)
    par = np.arange(n)
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for a, b in zip(owner[i], owner[j]):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    root = np.array([find(k) for k in range(n)])
    big = np.bincount(root).argmax()
    return np.flatnonzero(root == big)


def score(tag):
    z = np.load(f"{ST}/{tag}.npz")
    x, L = z["x"], float(z["L"])
    if "nb" in set(z.keys()):
        nb, nh, n = int(z["nb"]), int(z.get("nh", 1)), int(z["n_amph"])
        b0 = np.arange(n) * nb
    else:
        heads = np.flatnonzero(z["species"] == 1)
        if len(heads) < 2:
            print(f"{tag:26s} topology not recorded")
            return
        nb, nh, b0 = int(np.median(np.diff(heads))), 1, heads
    f, p, fl = bilayer_frac(x, L, b0, nb, nh)
    sel = largest_aggregate(x, L, b0, nb)
    fa = bilayer_frac(x, L, b0[sel], nb, nh)[0] if len(sel) >= 3 else float("nan")
    print(f"{tag:26s} n={len(b0):4d} {x.shape[1]}-D  whole-box={f:.3f}  "
          f"largest-agg={fa:.3f} (n={len(sel)})  paired={p:.3f} flat={fl:.3f}")


if __name__ == "__main__":
    if "--calibrate" in sys.argv:
        calibrate(); print()
    for t in [a for a in sys.argv[1:] if not a.startswith("--")]:
        score(t)
