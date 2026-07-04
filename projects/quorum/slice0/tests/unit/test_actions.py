"""Actions vocab tests — 5-symbol single-token vocab (N, S, E, W, Z)."""

from __future__ import annotations

import pytest

from slice0 import actions


class TestActionVocab:
    def test_five_labels(self):
        assert actions.LABELS == ("N", "S", "E", "W", "Z")

    def test_label_to_delta_cardinal_directions(self):
        # (drow, dcol) — row grows downward, so N is negative-row.
        assert actions.to_delta("N") == (-1, 0)
        assert actions.to_delta("S") == (1, 0)
        assert actions.to_delta("E") == (0, 1)
        assert actions.to_delta("W") == (0, -1)

    def test_z_is_stay(self):
        assert actions.to_delta("Z") == (0, 0)

    def test_unknown_label_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            actions.to_delta("Q")

    def test_labels_are_single_ascii_chars(self):
        # Every label is exactly one ASCII char; that's the whole point
        # of the vocab choice (guarantees single-token in any BPE).
        for lbl in actions.LABELS:
            assert isinstance(lbl, str)
            assert len(lbl) == 1
            assert lbl.isascii() and lbl.isalpha()
