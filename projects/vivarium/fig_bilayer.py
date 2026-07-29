"""Render the SELF-ASSEMBLED bilayer beside the planted reference.

The configuration is the one that produced a slab from a disordered start: 4-bead tails, slit
geometry (walls on z, periodic in x and y), no water, no electrostatics. Solvent-free, so every
token drawn is part of a lipid: orange tails, blue heads.
"""
import subprocess

from bilayer3d import build, lamellar, shape
from make_figures import frame

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
KW = dict(n_lip=231, bound=5.0, kt=0.02, speed=0.005, repel=12.0, k_bond=40.0, satt=0.30,
          spol=0.90, n_tail=4, head_q=0.0, rad_head=0.0, no_water=True, aniso=0.0,
          polarity=0.0, attract=0.30, bond_span=6.0, wall_axes=(2,))


def shoot(e, title, name):
    a1, a2 = shape(e)
    kind = "SLAB" if (a1 < 0.45 and a2 > 0.60) else ("rod" if a2 < 0.45 else "blob")
    tag = f"lamellar {lamellar(e):.3f}  L2/L3 {a2:.2f}  {kind}"
    svg = frame(e, f"{title}   {tag}", hide_water=True)
    fn = f"{OUT}/{name}"
    open(fn + ".svg", "w").write(svg)
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{name}", f"--screenshot={fn}.png",
                    "--window-size=476,476", f"file://{fn}.svg"], capture_output=True)
    print(f"  {title}: {tag} -> {fn}.png", flush=True)


if __name__ == "__main__":
    shoot(build(seed=0, plant=True, **KW), "PLANTED reference", "bilayer_planted")
    e = build(seed=0, plant=False, **KW)
    print("  running self-assembly from disorder...", flush=True)
    for t in range(1, 10001):
        e.step()
        if t % 2500 == 0:
            print(f"    t={t} lamellar={lamellar(e):.3f} L2/L3={shape(e)[1]:.2f}", flush=True)
    shoot(e, "SELF-ASSEMBLED t=10k", "bilayer_emergent")
