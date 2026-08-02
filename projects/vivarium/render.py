"""Rendering that can be trusted as evidence.

Two rules, both learned by being burnt:

  DRAW AT TRUE RADIUS. A fixed pixel radius makes an interpenetrating pile look cleanly resolved,
  which is how a collapse passed for a structure: the published micelle figure drew beads at 3.6-4.5
  px regardless of scale, so overlap was invisible in either direction. Circles here are sigma
  scaled by the view.

  UNWRAP FIRST. An aggregate straddling the periodic boundary renders as scattered debris, and the
  same class of error corrupted the bond measurements for days.

In 3-D use `cross_section`, not a projection: projecting a filled box superimposes every layer into
mush, while a thin slab through the aggregate shows the internal head/tail arrangement that actually
separates a micelle (tails in, heads out, ONE shell) from a disordered blob.
"""

from __future__ import annotations

import subprocess

import numpy as np

from harness import largest_cluster, unwrap

HEAD, TAIL, WATER = "#38bdf8", "#fb923c", "#1e3a5f"


def cross_section(e, path, title="", sub="", axis=None, thickness=2.0, width=560, show_water=True):
    """A slab of thickness `thickness` through the largest aggregate, normal to `axis`.

    Beads are drawn at their TRUE radius, so overlap reads as overlap. Only beads whose centre lies
    inside the slab are drawn, so what you see is a genuine cut rather than a projection.

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
    if mol is not None and len(mol):
        comp = largest_cluster(e)
        if len(comp):
            centre = P[mol[comp].ravel()].mean(axis=0)
        else:
            centre = P.mean(axis=0)
    else:
        centre = P.mean(axis=0)
    P = P - centre

    if pd == 3:
        if axis is None:
            src = P[mol[comp].ravel()] if (mol is not None and len(mol) and len(comp)) else P
            ev, evec = np.linalg.eigh(np.cov(src.T))
            long_axis = evec[:, int(np.argmax(ev))]
            axis = int(np.argmax(np.abs(long_axis)))    # the box axis most aligned with it
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
        bi, bj = e._bond_i[:len(mol) * (nb - 1)], e._bond_j[:len(mol) * (nb - 1)]
        for a, b in zip(bi, bj):
            if not (keep[a] and keep[b]):
                continue
            if np.abs(P[b] - P[a]).max() > B:      # a bond that still spans the box is a wrap artefact
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
               f'{title}</text>'
               f'<text x="9" y="{width-8}" fill="#94a3b8" font-family="monospace" font-size="11">'
               f'{sub}   slab {thickness:.1f} thick, {n_shown} lipid beads shown</text></svg>')

    open(path + ".svg", "w").write("".join(out))
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{abs(hash(path)) % 99999}",
                    f"--screenshot={path}.png", f"--window-size={width+16},{width+16}",
                    f"file://{path}.svg"], capture_output=True)
    return path + ".png"
