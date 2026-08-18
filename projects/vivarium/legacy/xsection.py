"""Cross-section rendering that can be used as evidence.

Separate from `render.py`, which serves the live viewer (`snapshot`, `token_contours`). This module
is for offline figures where the question is "what is actually inside that aggregate".

Two rules, both learned by being burnt:

  DRAW AT TRUE RADIUS. A fixed pixel radius makes an interpenetrating pile look cleanly resolved,
  which is how a collapse once passed for a structure: a published figure drew beads at 3.6-4.5 px
  regardless of scale, so overlap was invisible in either direction. Circles here are sigma scaled
  by the view.

  UNWRAP FIRST, or an aggregate straddling the periodic boundary renders as scattered debris.

In 3-D use a cross-section, never a projection: projecting a filled box superimposes every layer into
mush, while a thin slab shows the internal arrangement that separates a micelle (tail core, head
rim) from a disordered blob.
"""

from __future__ import annotations

import subprocess

import numpy as np

from harness import largest_cluster, unwrap


def _esc(t):
    """Escape text for SVG. A raw '<' in a caption -- e.g. "bilayer <0.30" -- makes the document
    invalid XML, and the renderer then draws only the part before it. Silent, and it corrupted
    several figures before an image showed the parser error banner."""
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

HEAD, TAIL, WATER = "#38bdf8", "#fb923c", "#1e3a5f"


def cross_section(e, path, title="", sub="", axis=None, thickness=2.0, width=560, show_water=True):
    """A slab of thickness `thickness` through the largest aggregate, normal to `axis`.

    `axis=None` picks the cut automatically, and the choice matters more than it looks. Cutting a
    z-normal bilayer perpendicular to z lands the slab in the tail-tail midplane: the image is
    entirely tails, with no heads and no water, and says nothing about layering. To SEE a membrane
    the slab must CONTAIN its normal, so the cut goes perpendicular to the aggregate's LONGEST
    principal axis -- which for a sheet spans (long, short) and shows the head-tail-tail-head stack,
    and for a sphere is arbitrary and therefore harmless.
    """
    pd = e.pd
    idx = np.arange(len(e.X))
    P = unwrap(e, idx)[:, :pd]
    mol = getattr(e, "_mol", None)
    comp = largest_cluster(e) if (mol is not None and len(mol)) else []
    centre = P[mol[comp].ravel()].mean(axis=0) if len(comp) else P.mean(axis=0)
    P = P - centre

    if pd == 3:
        if axis is None:
            src = P[mol[comp].ravel()] if len(comp) else P
            ev, evec = np.linalg.eigh(np.cov(src.T))
            long_axis = evec[:, int(np.argmax(ev))]
            axis = int(np.argmax(np.abs(long_axis)))
        keep = np.abs(P[:, axis]) <= 0.5 * thickness
        plane = [a for a in range(3) if a != axis]
    else:
        keep = np.ones(len(P), dtype=bool)
        plane = [0, 1]

    B = e.cfg.pos_bound
    sc = (width * 0.42) / B
    c = width / 2.0
    sp = np.asarray(e.species)
    sig = e.sigma if e.sigma is not None else np.full(len(P), 0.5)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{width}">'
           f'<rect width="{width}" height="{width}" fill="#0b0e13"/>']

    def xy(i):
        return c + P[i, plane[0]] * sc, c - P[i, plane[1]] * sc

    if show_water:
        for i in np.where(keep & (sp == 0))[0]:
            x, y = xy(i)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{sig[i]*sc:.1f}" '
                       f'fill="{WATER}" opacity="0.26"/>')
    if mol is not None and len(mol):
        nb = mol.shape[1]
        n_back = len(mol) * (nb - 1)
        for a, b in zip(e._bond_i[:n_back], e._bond_j[:n_back]):
            if not (keep[a] and keep[b]) or np.abs(P[b] - P[a]).max() > B:
                continue
            xa, ya = xy(a); xb, yb = xy(b)
            out.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" '
                       f'stroke="#e2e8f0" stroke-width="0.9" opacity="0.5"/>')
    for i in np.where(keep & (sp != 0))[0]:
        x, y = xy(i)
        col = HEAD if int(sp[i]) == 5 else TAIL
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{sig[i]*sc:.1f}" fill="{col}" '
                   f'opacity="0.78" stroke="#0b0e13" stroke-width="0.5"/>')

    n_shown = int((keep & (sp != 0)).sum())
    out.append(f'<rect x="0" y="{width-42}" width="{width}" height="42" fill="#0b0e13" opacity="0.92"/>'
               f'<text x="9" y="{width-25}" fill="#e2e8f0" font-family="monospace" font-size="12">'
               f'{_esc(title)}</text>'
               f'<text x="9" y="{width-8}" fill="#94a3b8" font-family="monospace" font-size="11">'
               f'{_esc(sub)}   slab {thickness:.1f} thick, {n_shown} lipid beads shown</text></svg>')
    open(path + ".svg", "w").write("".join(out))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{abs(hash(path)) % 99999}",
                    f"--screenshot={path}.png", f"--window-size={width+16},{width+16}",
                    f"file://{path}.svg"], capture_output=True)
    return path + ".png"
