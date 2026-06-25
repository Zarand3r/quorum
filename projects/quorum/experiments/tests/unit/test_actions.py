"""Tests for the action vocabulary."""

from __future__ import annotations

import pytest

from toy_v1 import actions


class TestActionVocab:
    def test_two_actions_stay_and_move(self):
        assert actions.LABELS == ("S", "M")

    def test_label_to_verb_mapping(self):
        assert actions.to_verb("S") == "STAY"
        assert actions.to_verb("M") == "MOVE"

    def test_unknown_label_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            actions.to_verb("X")
