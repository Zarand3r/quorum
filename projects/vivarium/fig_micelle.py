"""Render what the aggregates actually look like, beside what radial order actually looks like.

Left is a hand-built cylindrical micelle: heads out, tails on the axis, outward_c near +1. Right is
what 24 lipids relax into from a disordered start. Finding 21 says the right-hand structure has no
radial order once the self-correlated metric is replaced, and the two pictures are the visual form of
that number. Water is hidden in both so the lipid arrangement is visible.
"""
import subprocess

from bilayer3d import build
from make_figures import frame
from micelle_probe import probe
from rung1c import plant_cylinder

OUT = "/home/rbao/quorum-thermolife/projects/vivarium/docs/images"
KW = dict(seed=1, n_lip=24, bound=4.0, speed=0.08, repel=12.0,
          k_bond=8.0, satt=0.55, spol=0.90, plant=False, n_tail=4)


def shoot(e, title, name):
    rs = probe(e)
    tag = f"outward_c {rs[0][1]:+.2f}  shell {rs[0][2]:.2f}" if rs else "no cluster"
    svg = frame(e, f"{title}   {tag}", hide_water=True)
    fn = f"{OUT}/{name}"
    open(fn + ".svg", "w").write(svg)
    subprocess.run(["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                    f"--user-data-dir=/tmp/cr_{name}", f"--screenshot={fn}.png",
                    "--window-size=476,476", f"file://{fn}.svg"], capture_output=True)
    print(f"  {title}: {tag} -> {fn}.png", flush=True)


if __name__ == "__main__":
    print("rendering the planted control")
    e = build(kt=0.0, **KW)
    plant_cylinder(e)
    shoot(e, "PLANTED micelle", "micelle_planted")

    print("rendering the relaxed aggregate (this takes a few minutes)")
    e2 = build(kt=0.02, **KW)
    for _ in range(60000):
        e2.step()
    shoot(e2, "SELF-ASSEMBLED t=60k", "micelle_actual")
