"""Parameter search and annealing, so neither has to be retyped into a scratch probe again.

Written because the alternative kept costing real time: `spanning` was re-implemented three times,
a clump-start helper was lost with the shell that wrote it, and every result lived only in a log file
under /tmp. Three things this fixes.

  ANNEALING IS FIRST-CLASS. bicelle2d has had a cooling schedule for months, reachable only from its
  argv parser, so no probe in this project has ever used one -- while its own help text says "the
  droplet is a kinetic trap; cooling is the standard way out". `anneal` makes it a function.

  RESULTS ARE APPEND-ONLY. A sweep writes every row to a TSV as it goes, so a killed shell or a
  machine reboot costs the remaining rows and not the finished ones. Rows are never rewritten.

  THE STAGE CRITERION IS ONE FUNCTION. `stage3` was being re-expressed inline each time, which is how
  a criterion silently drifts between runs.
"""

from __future__ import annotations

import itertools
import os
import time

from harness import bond_stats, measure


def anneal(e, total, hot, cold, cool_frac=0.6, every=None, on_sample=None):
    """Run `total` steps, cooling linearly from `hot` to `cold` over the first `cool_frac`, then hold.

    Ordering happens on the way DOWN: too cold from the start and the system freezes into whatever
    disordered arrangement it began in, which is the trap every fixed-kT run in this project has sat
    in. `hot == cold` reproduces a plain fixed-temperature run exactly, so it is the honest control.
    """
    n_cool = max(1, int(cool_frac * total))
    for step in range(total):
        e.temperature = hot + (cold - hot) * min(1.0, step / n_cool)
        e.step()
        if every and on_sample and (step + 1) % every == 0:
            on_sample(step + 1, e)
    e.temperature = cold
    return e


def stage3(m):
    """The spanning-bilayer criterion, in ONE place: ordered AND spanning AND not collapsed.

    All three at once. Each alone is reachable and meaningless: a dense pile is ordered, a percolating
    network spans, and dispersed lipids are uncollapsed.
    """
    return bool(m["splay"] < 0.30 and m["spanning"] > 0.80 and m["packing"] > 0.35)


def sweep(build_fn, grid, steps, log_path, hot=None, cold=0.02, samples=(), label=""):
    """Cartesian sweep over `grid` (name -> values), appending one TSV row per sample.

    `build_fn(**params)` returns a fresh engine. `hot=None` means no annealing (fixed kT at `cold`),
    which is the control the annealed runs must be compared against.
    """
    keys = list(grid)
    first = not os.path.exists(log_path)
    with open(log_path, "a", buffering=1) as fh:
        if first:
            fh.write("\t".join(["label", "t"] + keys +
                               ["splay", "spanning", "packing", "align", "head_enrich",
                                "bond_mean", "ok", "stage3"]) + "\n")
        for combo in itertools.product(*(grid[k] for k in keys)):
            params = dict(zip(keys, combo))
            e = build_fn(**params)
            marks = sorted(samples or (steps,))

            def record(t, eng):
                m = measure(eng)
                bmean, _, _ = bond_stats(eng)
                fh.write("\t".join([label, str(t)] + [str(params[k]) for k in keys] +
                                   [f"{m['splay']:.4f}", f"{m['spanning']:.3f}",
                                    f"{m['packing']:.4f}", f"{m['align']:.4f}",
                                    f"{m['head_enrich']:.3f}", f"{bmean:.4f}",
                                    str(bool(m["ok"])), str(stage3(m))]) + "\n")
                print(f"  {label} {params} t={t}  splay {m['splay']:.3f}  span {m['spanning']:.2f}  "
                      f"pack {m['packing']:.3f}  {'*** STAGE 3 ***' if stage3(m) else ''}",
                      flush=True)

            t0 = time.perf_counter()
            anneal(e, steps, cold if hot is None else hot, cold,
                   every=marks[0] if len(set(marks)) == 1 else 1,
                   on_sample=(lambda t, eng: record(t, eng) if t in marks else None))
            print(f"    ({time.perf_counter() - t0:.0f}s)", flush=True)
