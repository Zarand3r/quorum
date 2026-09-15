from tests.test_field_scaling import _per_step

def test_margin_probe():
    for _ in range(3):
        ts, ns = _per_step(60, 900, 40.0)
        tb, nb = _per_step(240, 3600, 80.0)
        print(f"n {ns}->{nb} grow {nb/ns:.1f} ratio {tb/ts:.2f} gate {0.35*(nb/ns)**2:.2f} "
              f"t_small {ts*1e3:.1f}ms t_big {tb*1e3:.1f}ms")
