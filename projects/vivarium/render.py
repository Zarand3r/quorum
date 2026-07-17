"""Render / snapshot surface (IMPLEMENTATION_PLAN.md Step 0 — stub).

At Step 0 this is a neutral placeholder so the server/viewer contract exists
before any dynamics do. Step 1 replaces `idle_snapshot` with a real grounded
contour readout (blobs + local edges) computed from the block's *own* `W_c`
(invariant P8), and keeps it strictly read-only (P5).
"""

from __future__ import annotations


def idle_snapshot() -> dict:
    """A mode-agnostic empty snapshot (no agents yet)."""
    return {"status": "idle", "tick": 0, "n": 0, "tokens": [], "edges": []}
