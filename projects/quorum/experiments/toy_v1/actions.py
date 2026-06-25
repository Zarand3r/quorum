"""Action vocabulary for the toy.

Single-letter action tokens are used so the readout maps cleanly to a
single token per action in any BPE tokenizer (PLAN.md §6 / I4).
"""

from __future__ import annotations

from typing import Final

# Action labels — single letters so they tokenize to one token each.
LABELS: Final[tuple[str, ...]] = ("S", "M")

# Mapping from label to the human-readable verb, used in prompt text and
# in the grid step() action list (which speaks STAY / MOVE).
_LABEL_TO_VERB: Final[dict[str, str]] = {"S": "STAY", "M": "MOVE"}


def to_verb(label: str) -> str:
    """Convert an action label (``"S"`` / ``"M"``) to the canonical verb
    (``"STAY"`` / ``"MOVE"``)."""
    try:
        return _LABEL_TO_VERB[label]
    except KeyError as e:
        raise ValueError(f"unknown action label {label!r}") from e
