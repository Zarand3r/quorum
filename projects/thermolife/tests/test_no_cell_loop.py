"""Step 5 — P6: no per-cell Python loop in the hot path (PLAN.md I6).

Structural scan: the env/ physics and the sim/ tick path must not iterate over
grid cells (``np.ndindex``/``ndenumerate`` or a ``for`` over a height/width
range). A constant-size neighbor tuple (the forager's 4 offsets) is allowed.
Plus a wall-clock budget so a "clever but slow" rule is caught early.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from env.config import load_world_config
from sim.runner import run

_ROOT = Path(__file__).resolve().parent.parent
_GRID_LOOP = re.compile(
    r"np\.ndindex|\.ndenumerate|for\s+\w+\s+in\s+range\([^)]*"
    r"(height|width|shape\[0\]|shape\[1\])",
)


def _hot_path_files() -> list[Path]:
    files = list((_ROOT / "env").glob("*.py"))
    files += [_ROOT / "sim" / "tick.py", _ROOT / "sim" / "forager.py"]
    return files


def test_no_grid_loop_in_hot_path() -> None:
    offenders = [
        f.relative_to(_ROOT)
        for f in _hot_path_files()
        if _GRID_LOOP.search(f.read_text())
    ]
    assert not offenders, f"per-cell loop found in hot path: {offenders}"


def test_tick_throughput_budget() -> None:
    cfg = load_world_config(_ROOT / "configs" / "world.yaml", scenario="static_gradient")
    t0 = time.perf_counter()
    run(cfg, seed=42, ticks=1000)
    elapsed = time.perf_counter() - t0
    assert elapsed < 10.0, f"1000 ticks took {elapsed:.2f}s (> 10s budget)"
