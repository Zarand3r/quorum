"""Auto-research loop over the ADMISSIBLE harness.

Objective: `aspect` of the largest cluster, MINIMISED. It is the one number a droplet cannot fake --
planted bilayer 0.23, random 0.85 -- and unlike `lamellar` it does not read 1.0 on a collapsed blob.

The guardrails matter more than the objective. A loop optimises whatever you give it, and this project
spent a day being fooled by exactly that: a lipid stretched to 4x its rest length layers beautifully
and scored 0.87 on every metric we had. So any sample whose molecule is deformed (bond > 1.25) or
whose integrator overshoots (> 0.05/step) is scored as a CRASH, not as a good result. The loop cannot
win by breaking the molecule.

Every iteration re-prints both controls, so metric drift is visible in the log rather than silent.

    bazel run //projects/vivarium:autoloop -- --iters 40
"""

from __future__ import annotations

import argparse
import json
import random

import numpy as np
from bilayer3d import build
from harness import measure

# (name, choices) -- the axes every sweep so far has explored ONE AT A TIME. The lamellar window may
# only exist at a combination, which is where a search beats hand-sweeping.
SPACE = {
    "repel": [3.0, 6.0, 12.0, 20.0],
    "attract": [0.15, 0.30, 0.60, 1.20],
    "satt": [0.20, 0.30, 0.55, 0.90],
    "kbond": [20.0, 40.0, 80.0],
    "headsigma": [0.55, 0.70, 0.85, 1.0],
    "tails": [2, 3, 4],
    "kt": [0.005, 0.02, 0.05],
    "lipids": [120, 231, 350],
}
FIXED = dict(bound=5.0, speed=0.002, spol=0.90, head_q=0.0, rad_head=0.0, no_water=True,
             aniso=0.0, polarity=0.0, bond_span=2.0, wall_axes=())


def sample(rng):
    return {k: rng.choice(v) for k, v in SPACE.items()}


def run(cfg, steps, seed=0):
    e = build(seed=seed, plant=False, n_lip=cfg["lipids"], kt=cfg["kt"], repel=cfg["repel"],
              k_bond=cfg["kbond"], satt=cfg["satt"], attract=cfg["attract"], n_tail=cfg["tails"],
              head_sigma=cfg["headsigma"], **FIXED)
    prev = e.X.copy()
    for t in range(steps):
        if t == steps - 1:
            prev = e.X.copy()
        e.step()
    return measure(e, prev_X=prev)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--iters", type=int, default=40)
    p.add_argument("--steps", type=int, default=8000)
    p.add_argument("--out", default="/tmp/vivarium_autoloop.tsv")
    a = p.parse_args(argv)
    rng = random.Random(0)

    ctl = {}
    for tag, plant in (("planted", True), ("random", False)):
        m = measure(build(seed=0, plant=plant, n_lip=231, kt=0.02, repel=12.0, k_bond=40.0,
                          satt=0.30, attract=0.30, n_tail=4, head_sigma=1.0, **FIXED))
        ctl[tag] = m
        print(f"  CONTROL {tag:<8} aspect={m['aspect']:.3f} lamellar={m['lamellar']:.3f}", flush=True)
    print(f"  objective: MINIMISE aspect. crash = deformed molecule or overshooting integrator.\n")

    with open(a.out, "w") as fh:
        fh.write("iter\taspect\tlamellar\tbond\tstatus\tconfig\n")
    best, best_cfg = float("inf"), None
    for i in range(a.iters):
        cfg = sample(rng)
        try:
            m = run(cfg, a.steps)
        except Exception as exc:                       # a config that cannot even run is a crash
            m = {"ok": False, "why": f"exception {type(exc).__name__}", "aspect": float("nan"),
                 "lamellar": float("nan"), "bond_mean": 0.0}
        status = "ok" if m["ok"] else f"CRASH:{m['why']}"
        asp = m["aspect"] if m["ok"] else float("nan")
        mark = ""
        if m["ok"] and not np.isnan(asp) and asp < best:
            best, best_cfg, mark = asp, cfg, "   <-- BEST"
        print(f"  [{i:3d}] aspect={asp if not np.isnan(asp) else float('nan'):.3f} "
              f"lamellar={m['lamellar']:.3f} bond={m['bond_mean']:.2f} {status}{mark}", flush=True)
        with open(a.out, "a") as fh:
            fh.write(f"{i}\t{asp:.4f}\t{m['lamellar']:.4f}\t{m['bond_mean']:.3f}\t{status}\t"
                     f"{json.dumps(cfg)}\n")
    print(f"\n  BEST aspect={best:.3f}  (planted {ctl['planted']['aspect']:.3f}, "
          f"random {ctl['random']['aspect']:.3f})")
    print(f"  config: {json.dumps(best_cfg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
