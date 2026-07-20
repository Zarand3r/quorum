"""Render one frame of the packing sim to a standalone SVG (solid boundaries, so packing is visible).

    bazel run //projects/vivarium:render_frame -- --ticks 100 --seed 0 --out /path/frame.svg
"""

from __future__ import annotations

import argparse
import math

from config import DEFAULTS, POS_DIM, VivariumConfig
from pack import PackEngine

_SZ = 640
_MARGIN = 24
_R0 = 13.0
_AMP = 7.0
_STEPS = 44


def _blob_path(cx: float, cy: float, coeffs, scale: float) -> str:
    K = len(coeffs) // 2
    pts = []
    for m in range(_STEPS + 1):
        th = 2 * math.pi * m / _STEPS
        r = _R0
        for k in range(1, K + 1):
            r += _AMP * (coeffs[2 * (k - 1)] * math.cos(k * th) + coeffs[2 * (k - 1) + 1] * math.sin(k * th))
        r = max(4.0, min(34.0, r)) * scale
        pts.append((cx + r * math.cos(th), cy + r * math.sin(th)))
    return "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"


def render(engine, title: str) -> str:
    cfg = engine.cfg
    B = cfg.pos_bound
    span = _SZ - 2 * _MARGIN
    to_x = lambda p: _MARGIN + (p + B) / (2 * B) * span
    to_y = lambda p: _MARGIN + (B - p) / (2 * B) * span
    scale = span / (2 * B) / 6.0  # blob size relative to the dish

    pos = engine.X[:, :POS_DIM]
    C = engine._contour()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_SZ}" height="{_SZ+28}" '
        f'viewBox="0 0 {_SZ} {_SZ+28}">',
        f'<rect width="{_SZ}" height="{_SZ+28}" fill="#0b0e13"/>',
        f'<rect x="{_MARGIN}" y="{_MARGIN}" width="{span}" height="{span}" fill="#0e131b" '
        f'stroke="#1e293b" rx="6"/>',
        f'<text x="{_MARGIN}" y="{_SZ+20}" fill="#94a3b8" font-family="monospace" '
        f'font-size="13">{title}</text>',
    ]
    for i in range(cfg.N):
        cx, cy = to_x(float(pos[i, 0])), to_y(float(pos[i, 1]))
        hue = (i * 47) % 360
        d = _blob_path(cx, cy, C[i], scale)
        parts.append(
            f'<path d="{d}" fill="hsl({hue},65%,58%)" fill-opacity="0.92" '
            f'stroke="hsl({hue},70%,78%)" stroke-width="1.3"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--ticks", type=int, default=100)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    cfg = VivariumConfig(**DEFAULTS)
    e = PackEngine(cfg, a.seed)
    for _ in range(a.ticks):
        e.step()
    title = f"vivarium packing — iter {e.t}, seed {a.seed}  (transformer-only: 1/d² clash-repel + complementary-fit + induced morph)"
    with open(a.out, "w") as f:
        f.write(render(e, title))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
