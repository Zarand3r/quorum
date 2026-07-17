"""Golden-path integration test — the spine (IMPLEMENTATION_PLAN.md §A).

A fixed (seed, config) run must reproduce a byte-identical stamped state hash,
and its snapshot must be well-formed and finite. This runs after every step;
if it drifts, the most recent change caused it. Re-stamp ONLY on steps that
intentionally change dynamics (Step 1 = M0, Step 2 = M1, Step 4 = tuned).
"""

from __future__ import annotations

import hashlib

import numpy as np

from config import DEFAULTS, VivariumConfig
from engine import Engine

_GOLDEN_T = 100
# Re-stamped at the M2 objective pivot (signalling: relative-neighbour target).
# Re-stamp only on intentional dynamics changes.
_GOLDEN_HASH = "06a7902ee0a9aa14"


def test_golden_path() -> None:
    cfg = VivariumConfig(**DEFAULTS)
    e = Engine(cfg, seed=0)
    for _ in range(_GOLDEN_T):
        e.step()
    h = hashlib.sha256(e.X.tobytes()).hexdigest()[:16]
    assert h == _GOLDEN_HASH, f"golden-path drift: got {h}"

    snap = e.snapshot()
    assert snap["n"] == cfg.N
    assert len(snap["tokens"]) == cfg.N
    for tok in snap["tokens"]:
        assert np.isfinite(tok["x"]) and np.isfinite(tok["y"])
