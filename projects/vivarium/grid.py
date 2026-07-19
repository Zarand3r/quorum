"""Grid search maximizing measured aliveness (P6 holds by construction: identity freezes).

    bazel run //projects/vivarium:grid

Fast harness: 3 seeds, T ticks, aliveness.evaluate over a window. Edit GRID and re-run;
prints the top configs by mean aliveness. Deterministic → reproducible.
"""

from __future__ import annotations

import itertools

import numpy as np

from aliveness import evaluate
from config import DEFAULTS, VivariumConfig
from engine import Engine

_SEEDS = (0, 1, 2)
_TICKS = 2000  # measure POST-transient: the alive flicker decays by ~1500, so T=800 rewarded a
_WINDOW = 40   # dying transient. Sustained aliveness must survive to here.

GRID: dict[str, list] = {
    "force_chase": [0.6, 0.8, 1.0],
    "momentum": [0.4, 0.5, 0.6],
    "morph_spin": [0.3, 0.4],
    "force_attract": [0.02],
    "force_repel": [0.02],
}


def _alive(over: dict) -> tuple[float, float, float]:
    a, d = [], []
    for s in _SEEDS:
        cfg = VivariumConfig(**{**DEFAULTS, **over})
        e = Engine(cfg, s)
        for _ in range(_TICKS):
            e.step()
        r = evaluate(e, _WINDOW)
        a.append(r["aliveness"])
        d.append(r["deformation"])
    return float(np.mean(a)), float(np.max(a)), float(np.mean(d))


def main() -> int:
    keys = list(GRID)
    results = []
    for combo in itertools.product(*[GRID[k] for k in keys]):
        over = dict(zip(keys, combo))
        mean, best, deform = _alive(over)
        results.append((mean, best, deform, over))
    results.sort(reverse=True, key=lambda x: x[0])
    print(f"top configs by mean aliveness ({len(results)} evaluated, seeds {_SEEDS}, T={_TICKS}):")
    for mean, best, deform, over in results[:15]:
        knobs = " ".join(f"{k}={v}" for k, v in over.items())
        print(f"  mean={mean:.3f} best={best:.3f} deform={deform:.3f}  {knobs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
