"""Static SVG snapshots of real model state — the fold and the economy.

Dependency-free (hand-written SVG, no matplotlib). Renders ACTUAL engine output,
not a mockup: the fold frame is the trained docking fold; the eco frame is a live
E0 forager economy. This is effectively a still-frame first cut of the Step-6
viewer the economy still lacks.

  bazel run //projects/thermolife:render -- /abs/out/dir
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from eco.config import load_eco_config
from eco.engine import EcoEngine
from eco.policies import hand_forager
from eco.state import source_at
from fold.config import load_fold_config
from fold.engine import FoldEngine

_CFGDIR = Path(__file__).resolve().parent.parent / "configs"
_RUN = SimpleNamespace(value="RUNNING")
W = H = 640
PAD = 48


def _fit(pts: np.ndarray):
    """Map data points → SVG viewport (square, aspect-preserving, y flipped)."""
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    span = float(max((hi - lo).max(), 1e-6))
    s = (min(W, H) - 2 * PAD) / span
    cx, cy = (lo + hi) / 2.0

    def xf(p):
        x = W / 2 + (p[0] - cx) * s
        y = H / 2 - (p[1] - cy) * s  # flip y so up is up
        return x, y

    return xf


def _hdr(title: str, sub: str, bg: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="ui-monospace,monospace">'
        f'<rect width="{W}" height="{H}" fill="{bg}"/>'
        f'<text x="{PAD}" y="34" fill="#e8e8ea" font-size="18" font-weight="700">{title}</text>'
        f'<text x="{PAD}" y="56" fill="#9aa0aa" font-size="13">{sub}</text>'
    )


def render_fold(out: Path) -> None:
    cfg = load_fold_config(_CFGDIR / "fold.yaml")
    eng = FoldEngine(cfg, seed=0, trained_npz=str(_CFGDIR / "trained_fold.npz"))
    for _ in range(cfg.k_harmonics * 2):  # a handful of iterations → docked
        eng.step()
    snap = eng.snapshot(_RUN)
    toks, edges = snap["tokens"], snap["edges"]
    partner = snap.get("partner")
    allpts = np.array([p for t in toks for p in t["contour"]])
    xf = _fit(allpts)

    palette = ["#5aa9e6", "#7fc8a9", "#e6a15a", "#c98bdb", "#e6708a",
               "#8ad0d0", "#d0c46a", "#b0b0e0"]
    parts = [_hdr("thermolife — trained docking fold",
                  f'iteration {2*cfg.k_harmonics} · docked {int(100*snap.get("accuracy",0))}% '
                  f'· 8 tokens fold into complementary pairs', "#141417")]
    # docking bonds first (under the blobs)
    for i, j, wgt in edges:
        x1, y1 = xf(toks[i]["pos"]); x2, y2 = xf(toks[j]["pos"])
        good = partner is not None and partner[i] == j
        col = "#49d17a" if good else "#8a8a92"
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                     f'stroke="{col}" stroke-width="{0.6+3.2*wgt:.2f}" '
                     f'stroke-opacity="{0.25+0.7*wgt:.2f}"/>')
    # contour blobs
    for i, t in enumerate(toks):
        pathpts = " ".join(f"{xf(p)[0]:.1f},{xf(p)[1]:.1f}" for p in t["contour"])
        c = palette[i % len(palette)]
        parts.append(f'<polygon points="{pathpts}" fill="{c}" fill-opacity="0.34" '
                     f'stroke="{c}" stroke-width="2"/>')
        px, py = xf(t["pos"])
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" fill="{c}"/>')
    parts.append('<text x="48" y="620" fill="#6a6a72" font-size="12">'
                 'green bond = locked onto true complementary partner · '
                 'shape = attention query/key (grounded)</text></svg>')
    out.write_text("".join(parts))


def render_eco(out: Path, policy=None, label: str = "E0 forager", ticks: int = 150) -> None:
    cfg = load_eco_config(_CFGDIR / "eco.yaml")
    eng = EcoEngine(cfg, policy=policy or hand_forager)
    trail = []
    for _ in range(ticks):
        eng.tick()
        trail.append(source_at(eng.state.t, cfg)[:2].copy())
        if eng.state.n == 0:
            break
    st = eng.state
    # recompute current transfer edges (read-only) for the render
    edges = []
    if st.n:
        _, _, tr = eng.policy(st, cfg)
        ii, jj = np.where(tr > 0.02)
        edges = list(zip(ii.tolist(), jj.tolist()))
    pos = st.x[:, :2]
    src = st.mu[:2]
    trail = np.array(trail[-60:])
    allpts = np.vstack([pos, src[None, :], trail])
    xf = _fit(allpts)

    emax = float(st.e.max()) if st.n else 1.0
    parts = [_hdr(f"thermolife — economy ({label})",
                  f'tick {st.t} · {st.n} tokens tracking a drifting resource · '
                  f'{len(edges)} transfer edges · residual {abs(eng.last_residual):.0e}',
                  "#101418")]
    # energy-transfer edges (attention operator only)
    for i, j in edges[:400]:
        ax, ay = xf(pos[i]); bx, by = xf(pos[j])
        parts.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                     f'stroke="#7fd1d1" stroke-opacity="0.5" stroke-width="1"/>')
    # harvest field around the source
    sx, sy = xf(src)
    rad = float(np.linalg.norm(xf(src + np.array([cfg.sigma_r, 0])) - np.array([sx, sy])))
    parts.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{2*rad:.1f}" fill="#e6a15a" '
                 f'fill-opacity="0.06" stroke="#e6a15a" stroke-opacity="0.25" '
                 f'stroke-dasharray="4 4"/>')
    # source orbit trail
    tr = " ".join(f"{xf(p)[0]:.1f},{xf(p)[1]:.1f}" for p in trail)
    parts.append(f'<polyline points="{tr}" fill="none" stroke="#e6a15a" '
                 f'stroke-opacity="0.35" stroke-width="1.5" stroke-dasharray="2 3"/>')
    # tokens: radius + opacity ∝ energy
    for i in range(st.n):
        x, y = xf(pos[i])
        e = float(st.e[i])
        r = 2.0 + 4.0 * np.sqrt(max(e, 0.0) / max(emax, 1e-6))
        op = 0.35 + 0.5 * min(e / max(emax, 1e-6), 1.0)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                     f'fill="#5aa9e6" fill-opacity="{op:.2f}"/>')
    # source marker (on top)
    parts.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="7" fill="#ffb347" '
                 f'stroke="#fff" stroke-width="1.5"/>')
    parts.append('<text x="48" y="620" fill="#6a6a72" font-size="12">'
                 'orange = drifting resource source (dashed = orbit + harvest range) · '
                 'blue = tokens, size/opacity ∝ energy</text></svg>')
    out.write_text("".join(parts))


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out.mkdir(parents=True, exist_ok=True)
    render_fold(out / "fold.svg")
    render_eco(out / "eco.svg")
    # E1 attention economy (alive frame, before it starves) → shows transfer edges
    cfg = load_eco_config(_CFGDIR / "eco.yaml")
    from eco.interaction import make_attention_policy
    render_eco(out / "eco_attention.svg",
               policy=make_attention_policy(cfg, seed=0),
               label="E1 attention operator", ticks=40)
    print(f"wrote {out}/fold.svg, eco.svg, eco_attention.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
