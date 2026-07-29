
from bilayer3d import build, metrics
e = build(seed=0, n_lip=231, bound=5.0, kt=0.0, speed=0.005, repel=12.0, k_bond=8.0,
          satt=0.30, spol=0.90, plant=True, n_tail=2, head_q=0.0, rad_head=0.0,
          no_water=True, aniso=0.0)
b,h,n,o,c = metrics(e)
print(f"PLANTED CONTROL: nematic={n:+.3f} opposed={o:.3f}  (opposed must be high, was 0.123)")
