"""Water adds neighbours, raising summed steric pressure until the saturating bond force loses.
Two levers: fewer water particles, or weaker excluded volume. Test both against the pristine
no-water baseline (frac>1.25 = 0.00).
"""
from bicelle2d import build
from harness import bond_stats

print(f"  {'config':<34}{'bond mean':>10}{'max':>7}{'frac>1.25':>11}{'align':>8}")
for tag, nw, rp in (("no water (baseline)", 0, 12.0),
                    ("water 250, repel 12", 250, 12.0),
                    ("water 120, repel 12", 120, 12.0),
                    ("water 250, repel 6",  250, 6.0),
                    ("water 250, repel 3",  250, 3.0)):
    e = build(0, n_lip=63, bound=11.0, kt=0.02, speed=0.0006, repel=rp, k_bond=20.0,
              satt=0.30, n_tail=2, attract=2.0, bond_span=2.0, polarity=0.0, head_q=0.0,
              hydrophobic=0.6, n_water=nw, plant="clump")
    for _ in range(8000):
        e.step()
    mean, mx, frac = bond_stats(e)
    from harness import measure
    m = measure(e)
    print(f"  {tag:<34}{mean:>10.3f}{mx:>7.2f}{frac:>11.2f}{m['align']:>8.3f}", flush=True)
