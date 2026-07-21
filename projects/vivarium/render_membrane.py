"""Render a membrane snapshot to SVG — VISUAL proof (the user judges self-assembly by eye).

Water = pale hollow dots. Lipids = filled dots with a short stalk drawn from head toward tail
(the grounded orientation `o`), tail end capped. A bilayer reads as two lipid rows with the stalks
(tails) pointing INTO the seam and heads facing the water on both sides.

    bazel run //projects/vivarium:render_membrane -- --out /tmp/mem.svg \
        --beta 4 --torque 0.4 --nematic 0.5 --water 0.45 --ga 0.15 --ticks 1800
"""

from __future__ import annotations

import argparse

import numpy as np

from membrane import MembraneEngine
from metrics_membrane import LIPID, WATER

_W = 720


def _zoom_frame(e):
    """Unwrap the largest lipid cluster around its COM and return (center, half_extent)."""
    from metrics_membrane import _clusters, _min_image
    sp = e.species
    lip = np.where(sp == LIPID)[0]
    groups = _clusters(e.pos[lip], e.L, 1.6)
    largest = lip[max(groups, key=len)]
    ref = e.pos[largest[0]]
    up = ref + _min_image(e.pos[largest] - ref, e.L)
    c = up.mean(0)
    half = float(np.abs(up - c).max()) + 1.2
    return c, half, largest


def _svg(e: MembraneEngine, zoom=False) -> str:
    if zoom:
        c, half, _ = _zoom_frame(e)
        s = _W / (2 * half)

        def X(x, k):
            from metrics_membrane import _min_image
            return (_min_image(x - c[k], e.L) + half) * s
        return _svg_body(e, X)
    s = _W / e.L

    def X(x, k=0):  # world → pixel (torus origin at corner)
        return (x + e.pos_bound) * s
    return _svg_body(e, X)


def _svg_body(e: MembraneEngine, X) -> str:
    L = e.L

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_W}" '
        f'viewBox="0 0 {_W} {_W}">',
        f'<rect width="{_W}" height="{_W}" fill="#0b1220"/>',
    ]
    is_lip = e.species == LIPID
    inb = lambda x, y: -20 <= x <= _W + 20 and -20 <= y <= _W + 20
    # water first (background)
    for i in np.where(~is_lip)[0]:
        p = e.pos[i]
        cx, cy = X(p[0], 0), X(p[1], 1)
        if not inb(cx, cy):
            continue
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.2" '
                     f'fill="none" stroke="#2b6cb0" stroke-width="1" opacity="0.5"/>')
    # lipids with tail stalk
    stalk = 0.5  # world units, head→tail
    for i in np.where(is_lip)[0]:
        p = e.pos[i]
        o = e.orient[i]
        cx, cy = X(p[0], 0), X(p[1], 1)
        if not inb(cx, cy):
            continue
        tx, ty = X(p[0] + stalk * o[0], 0), X(p[1] + stalk * o[1], 1)
        # clip stalks that wrap the torus (avoid long lines across the box)
        if abs(tx - cx) < _W / 2 and abs(ty - cy) < _W / 2:
            parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                         f'stroke="#f6ad55" stroke-width="2" opacity="0.85"/>')
            parts.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="1.8" fill="#f6ad55"/>')
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.6" fill="#e53e3e"/>')  # head
    m = e.measure()
    parts.append(f'<text x="10" y="{_W-14}" fill="#cbd5e0" font-family="monospace" '
                 f'font-size="15">t={e.t}  H={m["H"]:.3f}  sheet={m["sheetness"]:.2f}  '
                 f'clusters={m["n_lipid_clusters"]}</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def _diag(e):
    pos, o, sp, L = e.pos, e.orient, e.species, e.L
    lip = np.where(sp == LIPID)[0]
    mi = lambda d: d - L * np.round(d / L)
    dcom, dtl, dtw = [], [], []
    for i in lip:
        d = mi(pos - pos[i]); d2 = (d * d).sum(1); near = d2 < 2.0 ** 2; near[i] = False
        ll = near & (sp == LIPID); ww = near & (sp != LIPID)
        if ll.sum() > 0:
            cd = d[ll].mean(0); cd /= np.linalg.norm(cd) + 1e-9
            dcom.append(o[i] @ cd)
            dl = d[ll] / (np.linalg.norm(d[ll], axis=1, keepdims=True) + 1e-9)
            dtl.append((dl @ o[i]).mean())
        if ww.sum() > 0:
            dw = d[ww] / (np.linalg.norm(d[ww], axis=1, keepdims=True) + 1e-9)
            dtw.append((dw @ o[i]).mean())
    f = lambda v: float(np.mean(v)) if v else float("nan")
    print(f"tail·(dir to lipid COM)      = {f(dcom):+.3f}  (+ tails point INTO lipid core = bilayer)")
    print(f"tail·(bearing to lipid nbrs) = {f(dtl):+.3f}")
    print(f"tail·(bearing to water nbrs) = {f(dtw):+.3f}  (- tails point AWAY from water = good)")
    m = e.measure()
    print(f"S={m['S']:.3f} side={m['side']:.3f} sheet={m['sheetness']:.2f} "
          f"clusters={m['n_lipid_clusters']}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="/tmp/membrane.svg")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=14000)
    p.add_argument("--N", type=int, default=96)
    p.add_argument("--water", type=float, default=0.45)
    p.add_argument("--beta", type=float, default=1.0)
    p.add_argument("--ga", type=float, default=0.35)
    p.add_argument("--gr", type=float, default=0.15)
    p.add_argument("--gc", type=float, default=0.02)
    p.add_argument("--gi", type=float, default=1.0)
    p.add_argument("--kappa", type=float, default=2.0)
    p.add_argument("--temp", type=float, default=0.10)
    p.add_argument("--anneal", type=int, default=8000)
    p.add_argument("--torque", type=float, default=0.28)
    p.add_argument("--nematic", type=float, default=0.0)
    p.add_argument("--mom", type=float, default=0.6)
    p.add_argument("--lam", type=float, default=0.6)
    p.add_argument("--diag", action="store_true")
    p.add_argument("--zoom", action="store_true")
    a = p.parse_args(argv)
    e = MembraneEngine(a.seed, N=a.N, water_frac=a.water, beta=a.beta, ga=a.ga, gr=a.gr, gc=a.gc,
                       gi=a.gi, kappa=a.kappa, torque=a.torque, nematic=a.nematic, momentum=a.mom,
                       dist_lambda=a.lam, temp=a.temp, anneal=a.anneal)
    for _ in range(a.ticks):
        e.step()
    if a.diag:
        _diag(e)
        return 0
    with open(a.out, "w") as f:
        f.write(_svg(e, zoom=a.zoom))
    m = e.measure()
    print(f"wrote {a.out}  H={m['H']:.3f}  sheet={m['sheetness']:.2f}  "
          f"clusters={m['n_lipid_clusters']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
