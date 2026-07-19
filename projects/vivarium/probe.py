"""Read-only aliveness probe over a run (measurement only — never optimised).

    bazel run //projects/vivarium:probe -- --ticks 3000 --every 300

Prints the measured aliveness gauge at checkpoints so we can watch (not reward)
what the colony is doing — e.g. whether it collapses.
"""

from __future__ import annotations

import argparse

from aliveness import evaluate
from config import DEFAULTS, VivariumConfig
from engine import Engine


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="measured aliveness probe")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, default=3000)
    p.add_argument("--every", type=int, default=300)
    p.add_argument("--window", type=int, default=40)
    # config overrides (dock-and-morph knobs)
    p.add_argument("--lam", type=float, default=None, help="dist_lambda (attention locality)")
    p.add_argument("--ga", type=float, default=None, help="force_attract γ_a")
    p.add_argument("--gr", type=float, default=None, help="force_repel γ_r")
    p.add_argument("--gc", type=float, default=None, help="force_chase γ_c (non-reciprocal)")
    p.add_argument("--spin", type=float, default=None, help="morph_spin")
    p.add_argument("--mom", type=float, default=None, help="momentum (inertia)")
    p.add_argument("--k", type=int, default=None, help="n_neighbors")
    p.add_argument("--N", type=int, default=None)
    p.add_argument("--ablate", choices=["none", "identity", "shuffle"], default="none")
    a = p.parse_args(argv)

    over = {}
    if a.lam is not None:
        over["dist_lambda"] = a.lam
    if a.ga is not None:
        over["force_attract"] = a.ga
    if a.gr is not None:
        over["force_repel"] = a.gr
    if a.gc is not None:
        over["force_chase"] = a.gc
    if a.spin is not None:
        over["morph_spin"] = a.spin
    if a.mom is not None:
        over["momentum"] = a.mom
    if a.k is not None:
        over["n_neighbors"] = a.k
    if a.N is not None:
        over["N"] = a.N
    cfg = VivariumConfig(**{**DEFAULTS, **over})
    e = Engine(cfg, a.seed, ablate=a.ablate)
    print(" tick  alive  spread  motion  cohere  struct  deform    lyap")
    for _ in range(0, a.ticks + 1, a.every):
        r = evaluate(e, a.window)
        print(
            f"{e.t:5d}  {r['aliveness']:.3f}  {r['spread']:.3f}  {r['motion']:.4f}"
            f"   {r['coherence']:.3f}   {r['structure']:.3f}   {r['deformation']:.3f}"
            f"  {r['lyapunov']:+.3f}"
        )
        for _ in range(a.every):
            e.step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
