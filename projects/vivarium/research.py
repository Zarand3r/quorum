"""Auto-research sweep: try each 'signs of life' idea against a fixed metric.

Fixed harness (never edited during a run):
  * metric      = measured aliveness of the real run (`none`), higher is better.
  * constraint  = P6 margin = aliveness(none) − aliveness(identity); an aliveness that
                  survives ablating interaction is drift/independent, not life — it must
                  be POSITIVE to count. (Measured, never rewarded — this only scores runs.)
  * eval        = run T ticks, then aliveness.evaluate over a window; repeat over seeds.

Each idea is a set of config overrides on the dock-and-morph substrate. Run:
    bazel run //projects/vivarium:research
It prints a markdown table (best aliveness first) for RESEARCH_LOG.md.
"""

from __future__ import annotations

import numpy as np

from aliveness import evaluate
from config import DEFAULTS, VivariumConfig
from engine import Engine

_SEEDS = (0, 1, 2, 3, 4)
_TICKS = 1000
_WINDOW = 40

# Runnable ideas on the current dock-and-morph substrate (name → overrides → note).
IDEAS: list[tuple[str, dict, str]] = [
    ("baseline-symmetric", {"morph_spin": 0.0}, "attract+repel only (expected: crystallise)"),
    ("morph-spin", {}, "skew rotation on z keeps shape morphing (default)"),
    ("morph-spin-strong", {"morph_spin": 0.4}, "stronger non-settling shape drive"),
    ("chase", {"force_chase": 0.2}, "non-reciprocal (A−Aᵀ) transport + spin (E–I idea)"),
    ("chase-strong", {"force_chase": 0.5}, "stronger non-reciprocal chase"),
    ("chase-only", {"force_chase": 0.3, "morph_spin": 0.0}, "chase without morph-spin"),
    ("chase+weak-attract", {"force_chase": 0.3, "force_attract": 0.04}, "chase dominates, weak pull"),
    ("weak-attract", {"force_attract": 0.03}, "liquid regime (less crystalline)"),
    ("strong-repel", {"force_repel": 0.15}, "more excluded volume"),
    ("low-locality", {"dist_lambda": 0.1}, "wider attention neighbourhood"),
    ("more-neighbors", {"n_neighbors": 16}, "denser interaction graph"),
    ("bigger-pop", {"N": 128, "n_neighbors": 12}, "more agents"),
    # chase + momentum: non-reciprocity breaks the crystal, inertia smooths turbulence → edge.
    ("momentum-only", {"momentum": 0.8}, "inertia, no chase"),
    ("chase+mom-a", {"force_chase": 0.5, "momentum": 0.7, "force_attract": 0.03}, "edge candidate"),
    ("chase+mom-b", {"force_chase": 0.4, "momentum": 0.5, "force_attract": 0.03}, "less inertia"),
    ("chase+mom-c", {"force_chase": 0.6, "momentum": 0.6, "force_attract": 0.03}, "more chase"),
    ("chase+mom-d", {"force_chase": 0.3, "momentum": 0.6, "force_attract": 0.03}, "gentler chase"),
    ("chase+mom+spin", {"force_chase": 0.5, "momentum": 0.7, "force_attract": 0.03, "morph_spin": 0.3}, "+ shape drive"),
]


def _alive(cfg: VivariumConfig, seed: int, ablate: str) -> tuple[float, float]:
    e = Engine(cfg, seed, ablate=ablate)
    for _ in range(_TICKS):
        e.step()
    r = evaluate(e, _WINDOW)
    return r["aliveness"], r["deformation"]


def eval_idea(over: dict) -> dict:
    none, ident, defo = [], [], []
    for s in _SEEDS:
        cfg = VivariumConfig(**{**DEFAULTS, **over})
        a_none, d_none = _alive(cfg, s, "none")
        a_id, _ = _alive(cfg, s, "identity")
        none.append(a_none)
        ident.append(a_id)
        defo.append(d_none)
    none, ident = np.array(none), np.array(ident)
    return {
        "alive_mean": float(none.mean()),
        "alive_best": float(none.max()),
        "identity_mean": float(ident.mean()),
        "p6_margin": float(none.mean() - ident.mean()),
        "deform_mean": float(np.mean(defo)),
        "n_alive": int((none > 0.05).sum()),
    }


def main() -> int:
    rows = []
    for name, over, note in IDEAS:
        r = eval_idea(over)
        rows.append((name, over, note, r))
    rows.sort(key=lambda x: x[3]["alive_mean"], reverse=True)

    print(f"| idea | alive(mean) | alive(best) | identity | P6 margin | deform | live/{len(_SEEDS)} | note |")
    print("|---|---:|---:|---:|---:|---:|---:|---|")
    for name, _over, note, r in rows:
        print(
            f"| {name} | {r['alive_mean']:.3f} | {r['alive_best']:.3f} | {r['identity_mean']:.3f} "
            f"| {r['p6_margin']:+.3f} | {r['deform_mean']:.3f} | {r['n_alive']} | {note} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
