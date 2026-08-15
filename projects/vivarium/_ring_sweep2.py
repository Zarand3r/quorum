"""Planted-ring sweep, redone: density held FIXED, verdict from the gated radial assay.

Two faults invalidated the first sweep. `bound` was held at 16.0 while N varied, so token density ran
0.39-0.82 against the validated 0.907 -- most dilute exactly where rings were largest, which is where
they fragmented. And the verdict came from a centroid-based lumen radius that returned four false
HOLLOW results.

Here both are fixed: hydration is held at the validated 3.97 waters per lipid and the box is scaled
so token density stays at 0.907 for every N, and the verdict comes from `ring_assay.classify`, whose
positive / negative / adversarial gates must pass before it may be used.

HYPOTHESIS      some N in 50..120 sustains the five-band signature
                (lumen water -> inner heads -> tail core -> outer heads -> bulk) at curvature 0.
FALSIFICATION   if every N at matched density is `filled` or `fragmented`, native Vivarium packing
                cannot hold a closed ring, and curvature tuning is beside the point.
"""
import sys
import numpy as np
from bicelle2d import build
from fig2d import render
from ring_assay import classify, plant_ring, self_test, radial_profiles, largest_cluster_mols

DENSITY = 439.0 / 22.0 ** 2      # the validated configuration's token density
W_PER_LIPID = 250.0 / 63.0       # and its hydration

if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    sizes = [int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "50,65,80,100,120").split(",")]
    cv = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

    print("assay gates:")
    if not self_test():
        print("GATES FAILED -- refusing to run the sweep")
        sys.exit(1)

    print(f"\nMATCHED-DENSITY RING SWEEP  curvature={cv}  steps={steps}  "
          f"density={DENSITY:.3f}  {W_PER_LIPID:.2f} waters/lipid", flush=True)
    print(f"{'N':>5}{'nW':>6}{'bound':>7}{'R_mid':>7}{'t':>7}{'frac':>7}{'r_core':>8}"
          f"{'inH':>5}{'outH':>6}{'lumR':>7}{'lum/bulk':>10}   verdict", flush=True)
    for n_lip in sizes:
        nw = int(round(W_PER_LIPID * n_lip))
        tokens = 3 * n_lip + nw
        bound = (tokens / DENSITY) ** 0.5 / 2.0
        R_mid = n_lip * 1.0 / (4.0 * np.pi)
        e = build(0, plant=False, n_lip=n_lip, n_water=nw, bound=bound, kt=0.02, speed=0.001,
                  repel=12.0, k_bond=30.0, satt=0.30, n_tail=2, bond_span=2.0,
                  polarity=0.80, head_q=1.2, hydrophobic=0.6, attract=1.0)
        e.curvature = cv
        plant_ring(e, R_mid=R_mid)
        for t in (0, steps):
            if t:
                for _ in range(steps):
                    e.step()
            v, d = classify(e)
            render(e, f"RING N={n_lip} matched density, curvature={cv}, t={t}",
                   f"ring2_N{n_lip:03d}_t{t}")
            print(f"{n_lip:>5}{nw:>6}{bound:>7.1f}{R_mid:>7.2f}{t:>7}{d.get('frac',0):>7.2f}"
                  f"{d.get('r_core',0):>8.2f}{str(d.get('inner_heads','-'))[:1]:>5}"
                  f"{str(d.get('outer_heads','-'))[:1]:>6}{d.get('lumen_r',0):>7.2f}"
                  f"{d.get('lumen_ratio',0):>10.2f}   {v}", flush=True)
