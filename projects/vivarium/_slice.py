"""Render a slab slice of a 3-D DPD state, to ground the `order` metric against a picture.

`order` counts amphiphiles whose axis is within 30 degrees of the box normal. A FLUID bilayer
undulates and its lipids tilt, so an intact membrane can score low while being perfectly intact --
the metric would then be reporting fluidity as melting. The only way to tell is to look.
"""
import sys
import numpy as np

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"
COL = {0: ("#12203a", 1.6), 1: ("#49b0ff", 4.2), 2: ("#ff9a3c", 4.2)}

tag, title, sub, thick = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
z = np.load(f"{ST}/{tag}.npz")
x, sp, L = z["x"], z["species"], float(z["L"])
if x.shape[1] == 3:
    keep = np.abs(x[:, 0] - L / 2) < thick / 2         # slab through the box, viewed edge-on
    p = x[keep][:, 1:]
    s = sp[keep]
else:
    p, s = x, sp
S = 700
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S+34}" '
       f'viewBox="0 0 {S} {S+34}"><rect width="{S}" height="{S+34}" fill="#0a0e17"/>']
for want in (0, 2, 1):
    c, r = COL[want]
    for q in p[s == want]:
        out.append(f'<circle cx="{q[0]/L*S:.1f}" cy="{S - q[1]/L*S:.1f}" r="{r}" fill="{c}" '
                   f'fill-opacity="{0.45 if want == 0 else 0.95}"/>')
out.append(f'<text x="10" y="{S+14}" fill="#e8eef7" font-family="monospace" font-size="13">{title}</text>')
out.append(f'<text x="10" y="{S+30}" fill="#7fd4a0" font-family="monospace" font-size="11">{sub}</text></svg>')
open(f"{OUT}/{tag}.svg", "w").write("".join(out))
import subprocess
subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                f"--user-data-dir=/tmp/cr_{abs(hash(tag))%99999}",
                f"--screenshot={OUT}/{tag}.png", f"--window-size={S+16},{S+50}",
                f"file://{OUT}/{tag}.svg"], capture_output=True)
print(f"  {tag}: {keep.sum() if x.shape[1]==3 else len(x)} beads in slab -> {OUT}/{tag}.png")
