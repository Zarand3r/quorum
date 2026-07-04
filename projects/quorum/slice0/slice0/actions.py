"""Slice 0 action vocabulary — 5 single-letter tokens.

``{N, S, E, W, Z}``:
    N — move one cell north (row - 1)
    S — move one cell south (row + 1)
    E — move one cell east  (col + 1)
    W — move one cell west  (col - 1)
    Z — stay in place (zero movement)

Chosen for single-token guarantee in any BPE tokenizer (PLAN.md §22 Q4).
Verified at load time by the LLM policy that each ASCII letter tokenizes to
exactly one token in the model's vocab.
"""

from __future__ import annotations

from typing import Final

LABELS: Final[tuple[str, ...]] = ("N", "S", "E", "W", "Z")

# (drow, dcol). Row increases downward on the numpy grid.
_LABEL_TO_DELTA: Final[dict[str, tuple[int, int]]] = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
    "Z": (0, 0),
}


def to_delta(label: str) -> tuple[int, int]:
    """Convert an action label to a ``(drow, dcol)`` shift."""
    if label not in _LABEL_TO_DELTA:
        raise ValueError(f"unknown action label {label!r}; expected one of {LABELS}")
    return _LABEL_TO_DELTA[label]
