"""Which way does a 2-D patch close: by bending GLOBALLY, or by its two ends finding each other?

WHY THIS EXISTS. The canonical vesicle pathway in the literature is
    micelles -> bilayer patch (bicelle) -> the patch bends CONTINUOUSLY into a cup -> the rim seals.
The bending is GLOBAL: curvature develops along the whole patch, and the rim closes because the whole
sheet curls. `docs/SUCCESSES.md` has claimed the opposite for this model -- "two ends of a ribbon
meeting, at constant aggregate size, never by an aggregate curving" -- and that claim was never
measured against an instrument that could distinguish the two. It was read off cluster size, which is
constant under BOTH pathways and therefore cannot separate them.

THE DISCRIMINATOR. Order the lipids along the ribbon's backbone and compute the turning angle at each
interior lipid. Then:

    global bending   curvature spread along the whole contour   -> LOW  cv = std(kappa)/mean(kappa)
    ends finding     curvature concentrated near the two ends   -> HIGH cv

`validate()` builds both pathways synthetically, as controls the metric MUST separate, because a
metric that has only ever been run on the data it is meant to explain is not evidence.
"""
from __future__ import annotations

import numpy as np


def backbone_order(C, L):
    """Order lipid centroids along the aggregate's backbone by nearest-neighbour walk from an end."""
    n = len(C)
    D = C[:, None, :] - C[None, :, :]
    D -= L * np.round(D / L)
    R = np.sqrt((D * D).sum(-1))
    np.fill_diagonal(R, np.inf)
    # an END is the point whose two nearest neighbours are most nearly on the SAME side
    start, best = 0, -np.inf
    for i in range(n):
        j, k = np.argsort(R[i])[:2]
        u = C[j] - C[i]; u -= L * np.round(u / L)
        v = C[k] - C[i]; v -= L * np.round(v / L)
        cos = float(u @ v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-12)
        if cos > best:
            best, start = cos, i
    order, seen = [start], {start}
    for _ in range(n - 1):
        cur = order[-1]
        cand = [j for j in np.argsort(R[cur]) if j not in seen]
        if not cand:
            break
        order.append(int(cand[0])); seen.add(int(cand[0]))
    return np.array(order)


def curvature_profile(C, L):
    """Turning angle at each interior point of the ordered backbone, in radians."""
    o = backbone_order(C, L)
    P = C[o]
    d = np.diff(P, axis=0)
    d -= L * np.round(d / L)
    nrm = np.linalg.norm(d, axis=1, keepdims=True)
    t = d / np.maximum(nrm, 1e-12)
    cos = np.clip((t[:-1] * t[1:]).sum(1), -1.0, 1.0)
    return np.arccos(cos)


def bending_uniformity(C, L):
    """cv = std/mean of the turning angle along the backbone.

    LOW  -> curvature spread evenly: the patch is bending as a whole (canonical).
    HIGH -> curvature concentrated: the ends are hooking toward each other.
    """
    k = curvature_profile(C, L)
    if len(k) < 4 or k.mean() < 1e-9:
        return float("nan")
    return float(k.std() / k.mean())


def _arc(n, frac, L, curl_ends=False, R=12.0):
    """A ribbon closed by fraction `frac`. `curl_ends` puts ALL the curvature in the last 25%."""
    if not curl_ends:
        th = np.linspace(0.0, 2 * np.pi * frac, n)
        return np.stack([R * np.cos(th), R * np.sin(th)], 1)
    # straight middle, hooked ends: same endpoints, curvature only near the tips
    m = int(n * 0.5)
    e = (n - m) // 2
    total = 2 * np.pi * frac
    seg = np.concatenate([np.linspace(0, total / 2, e, endpoint=False),
                          np.zeros(m),
                          np.linspace(0, total / 2, n - m - e)])
    ang = np.cumsum(seg) - seg.sum() / 2
    step = 2 * np.pi * R / n
    P = np.zeros((n, 2))
    for i in range(1, n):
        P[i] = P[i - 1] + step * np.array([np.cos(ang[i]), np.sin(ang[i])])
    return P - P.mean(0)


def validate() -> int:
    """The metric must SEPARATE global bending from end-hooking at the same closure fraction."""
    L = 400.0
    print("  the two pathways, built synthetically, closing by the same amount\n")
    print(f"  {'closed':>8} {'GLOBAL bending cv':>19} {'ENDS hooking cv':>17} {'separates?':>12}")
    ok = True
    for frac in (0.5, 0.7, 0.85, 0.95):
        g = bending_uniformity(_arc(60, frac, L, curl_ends=False), L)
        e = bending_uniformity(_arc(60, frac, L, curl_ends=True), L)
        sep = e > g * 2.0
        ok &= sep
        print(f"  {frac:>8.2f} {g:>19.3f} {e:>17.3f} {str(sep):>12}")
    print(f"\n  metric separates the two pathways at every closure fraction: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(validate())
