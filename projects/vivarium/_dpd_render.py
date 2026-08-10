"""Render DPD states. The aspect-ratio classifier cannot be trusted on a box-spanning phase.

At phi=0.35 the classifier called a 123-molecule aggregate "micellar" (aspect 1.4). A lamellar phase
that wraps the periodic box is isotropic to a radius-of-gyration measure, which is exactly how this
project's retracted `aspect` metric failed before (same membrane, two boxes, 0.245 vs 0.109). Look.
"""
import glob, os
import numpy as np

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
ST = "/home/rbao/quorum-thermolife/projects/vivarium/docs/runs/states"
COL = {0: ("#12203a", 2.2), 1: ("#49b0ff", 5.0), 2: ("#ff9a3c", 5.0)}   # water, head, tail

def render(tag, title, sub):
    z = np.load(f"{ST}/{tag}.npz")
    x, sp, L = z["x"], z["species"], float(z["L"])
    S = 560
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S+34}" '
             f'viewBox="0 0 {S} {S+34}"><rect width="{S}" height="{S+34}" fill="#0a0e17"/>']
    for s in (0, 2, 1):                       # water behind, then tails, then heads
        c, r = COL[s]
        for p in x[sp == s]:
            cx, cy = p[0] / L * S, S - p[1] / L * S
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{c}" '
                         f'fill-opacity="{0.5 if s == 0 else 0.95}"/>')
    parts.append(f'<text x="10" y="{S+14}" fill="#e8eef7" font-family="monospace" '
                 f'font-size="13">{title}</text>')
    parts.append(f'<text x="10" y="{S+30}" fill="#7fd4a0" font-family="monospace" '
                 f'font-size="11">{sub}</text></svg>')
    open(f"{OUT}/{tag}.svg", "w").write("".join(parts))
    # same headless-Chrome path xsection.py uses; cairosvg is not installed here
    import subprocess
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{abs(hash(tag)) % 99999}",
                    f"--screenshot={OUT}/{tag}.png", f"--window-size={S+16},{S+50}",
                    f"file://{OUT}/{tag}.svg"], capture_output=True)
    print(f"  {tag}: {len(x)} beads, L={L:.1f} -> {OUT}/{tag}.png")

for phi, note in ((5, "micellar (aspect 1.2, largest 6)"),
                  (12, "elongated (aspect 2.2, largest 23)"),
                  (22, "elongated (aspect 2.2, largest 26)"),
                  (35, "classifier said micellar, aspect 1.4, largest 123 -- verify")):
    f = f"{ST}/dpd_phi{phi}.npz"
    if os.path.exists(f):
        render(f"dpd_phi{phi}", f"DPD amphiphiles, phi={phi/100:.2f}", note)
