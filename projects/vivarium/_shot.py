"""Render any DPD state to SVG. 3-D states are sliced; 2-D states are projected whole.

A 3-D box rendered as a projection is a solid wall of beads and hides everything, so 3-D states are
cut to a slab through the centre thick enough to show one membrane cross-section. The slab thickness
is reported in the caption, because a slice that is too thick manufactures apparent density and a
slice that is too thin manufactures apparent holes.

Colours: water dark blue-grey, heads bright blue, tails orange. Draw order is water, tails, heads, so
the amphiphile structure sits on top of the solvent rather than being buried by it.
"""

import struct
import sys
import zlib

import numpy as np

def write_png(path, img):
    """Minimal RGB PNG. No matplotlib or SVG rasteriser exists in this hermetic toolchain, and a
    structural claim in this project is not allowed without looking at the picture."""
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def disc(img, cx, cy, r, rgb, alpha):
    h, w, _ = img.shape
    x0, x1 = max(int(cx - r) - 1, 0), min(int(cx + r) + 2, w)
    y0, y1 = max(int(cy - r) - 1, 0), min(int(cy + r) + 2, h)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r
    if not m.any():
        return
    sub = img[y0:y1, x0:x1].astype(np.float32)
    col = np.array(rgb, np.float32)
    sub[m] = sub[m] * (1 - alpha) + col * alpha
    img[y0:y1, x0:x1] = sub.astype(np.uint8)


OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"
COL = {0: ("#16213a", 1.9), 1: ("#4db5ff", 4.4), 2: ("#ff9840", 4.4)}
RGB = {0: (30, 42, 72), 1: (77, 181, 255), 2: (255, 152, 64)}


def render(tag, title, sub, slab=4.0, view="xy", out=None):
    """`view` names the two plotted axes; the third is the slice normal.

    A membrane must be viewed EDGE-ON to show anything. Slicing along the membrane normal and
    plotting the other two axes gives a face-on view, which looks like a uniform sheet of heads
    whether or not a bilayer exists underneath. For a slab whose normal is z, use view="xz".
    """
    z = np.load(f"{ST}/{tag}.npz")
    x, sp, L = z["x"], z["species"], float(z["L"])
    dim = x.shape[1]

    ax_i, ax_j = "xyz".index(view[0]), "xyz".index(view[1])
    if dim == 3:
        ax_k = 3 - ax_i - ax_j
        # slice through the centre of mass of the amphiphiles, not the box: an aggregate that has
        # drifted off-centre would otherwise be cut off-axis and look like a fragment
        lip = x[sp != 0]
        c = lip.mean(axis=0)
        rel = x[:, ax_k] - c[ax_k]
        rel -= L * np.round(rel / L)
        keep = np.abs(rel) < slab / 2
        x, sp = x[keep], sp[keep]
        note = f"{view} plane, slab {slab:.1f} rc along {'xyz'[ax_k]}"
    else:
        ax_i, ax_j = 0, 1
        note = "full 2-D box"

    S = 780
    P = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S + 52}" '
         f'viewBox="0 0 {S} {S + 52}"><rect width="{S}" height="{S + 52}" fill="#080b12"/>']
    for s in (0, 2, 1):
        col, r = COL[s]
        op = 0.45 if s == 0 else 0.96
        pts = x[sp == s]
        for p in pts:
            cx, cy = p[ax_i] / L * S, S - p[ax_j] / L * S
            P.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{col}" fill-opacity="{op}"/>')
    P.append(f'<text x="12" y="{S + 20}" fill="#e8eef7" font-family="monospace" '
             f'font-size="15">{title}</text>')
    P.append(f'<text x="12" y="{S + 40}" fill="#8fa3bf" font-family="monospace" '
             f'font-size="12.5">{sub}  |  L={L:.1f}  |  {note}</text>')
    P.append("</svg>")
    path = f"{OUT}/{out or tag}.svg"
    with open(path, "w") as f:
        f.write("".join(P))

    img = np.zeros((S, S, 3), np.uint8)
    img[:, :] = (8, 11, 18)
    for s_ in (0, 2, 1):
        rgb = RGB[s_]
        rad = COL[s_][1] * 0.85
        alpha = 0.5 if s_ == 0 else 0.95
        for p in x[sp == s_]:
            disc(img, p[ax_i] / L * S, S - p[ax_j] / L * S, rad, rgb, alpha)
    png = f"{OUT}/{out or tag}.png"
    write_png(png, img)
    print(png)


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    for spec in sys.argv[1:]:
        parts = spec.split("~")
        render(parts[0], parts[1] if len(parts) > 1 else parts[0],
               parts[2] if len(parts) > 2 else "",
               float(parts[3]) if len(parts) > 3 else 4.0,
               parts[4] if len(parts) > 4 else "xy",
               parts[5] if len(parts) > 5 else None)
