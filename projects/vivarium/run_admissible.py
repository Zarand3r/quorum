"""Self-assembly measured through the validated harness. Every number here is admissible or refused.

Intact molecules (bond_span=2.0 keeps bonds at 1.01-1.02), minimum image applied at one chokepoint,
both controls printed, and any sample with a deformed molecule or an overshooting integrator is
DISQUALIFIED rather than interpreted.
"""
import argparse

from bilayer3d import build
from harness import header, line, measure


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=30000)
    p.add_argument("--every", type=int, default=6000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--lipids", type=int, default=231)
    p.add_argument("--bound", type=float, default=5.0)
    p.add_argument("--tails", type=int, default=4)
    p.add_argument("--speed", type=float, default=0.002)
    p.add_argument("--repel", type=float, default=12.0)
    p.add_argument("--satt", type=float, default=0.30)
    p.add_argument("--attract", type=float, default=0.30)
    p.add_argument("--kbond", type=float, default=40.0)
    p.add_argument("--span", type=float, default=2.0)
    p.add_argument("--headsigma", type=float, default=1.0)
    p.add_argument("--kt", type=float, default=0.02)
    p.add_argument("--slit", action="store_true")
    p.add_argument("--plant", action="store_true")
    a = p.parse_args(argv)

    kw = dict(n_lip=a.lipids, bound=a.bound, kt=a.kt, speed=a.speed, repel=a.repel,
              k_bond=a.kbond, satt=a.satt, spol=0.90, n_tail=a.tails, head_q=0.0,
              rad_head=0.0, no_water=True, aniso=0.0, polarity=0.0, attract=a.attract,
              bond_span=a.span, head_sigma=a.headsigma,
              wall_axes=(2,) if a.slit else ())
    for tag, pl in (("planted", True), ("random ", False)):
        m = measure(build(seed=a.seed, plant=pl, **kw))
        print(f"  CONTROL {tag}: lamellar={m['lamellar']:.3f} aspect={m['aspect']:.3f} "
              f"bond={m['bond_mean']:.2f}")
    e = build(seed=a.seed, plant=a.plant, **kw)
    print(f"  N={e.cfg.N} lipids={len(e._mol)} tails={a.tails} box={2*a.bound:.0f} "
          f"{'SLIT' if a.slit else 'periodic'} {'PLANTED' if a.plant else 'DISORDERED'}")
    print(header())
    for t in range(0, a.steps + 1, a.every):
        # displacement must be measured over ONE step. Sampling it across the checkpoint interval
        # compares 6000 steps of motion against a per-step threshold and disqualifies every healthy
        # run -- which it did on the first attempt.
        prev = e.X.copy()
        e.step()
        print(line(t, measure(e, prev_X=prev)), flush=True)
        if t < a.steps:
            for _ in range(a.every - 1):
                e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
