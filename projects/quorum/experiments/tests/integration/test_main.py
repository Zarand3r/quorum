"""Smoke tests for the CLI entry point. No torch dependency — runs with
the default ``MockPolicy``."""

from __future__ import annotations

import io
import sys

import pytest

from toy_v1 import main


def _capture(argv):
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = main.main(argv)
    finally:
        sys.stdout = old_stdout
    return rc, buf.getvalue()


class TestCLIMockBackend:
    def test_short_run_exits_zero(self):
        rc, out = _capture(["--ticks", "3", "--n-agents", "8", "--grid-size", "4"])
        assert rc == 0
        # Initial / final blocks rendered.
        assert "Initial grid:" in out
        assert "Final grid:" in out
        # Three tick lines emitted.
        tick_lines = [ln for ln in out.splitlines() if ln.startswith("t=")]
        assert len(tick_lines) == 3
        # I3 gate visible in every tick line.
        for ln in tick_lines:
            assert "fwd_passes=1" in ln

    def test_grid_glyph_legend(self):
        rc, out = _capture(["--ticks", "1", "--n-agents", "4", "--grid-size", "4"])
        assert rc == 0
        # The ASCII grid uses only {., R, B}.
        # Extract the lines between "Initial grid:" and the same-color line.
        section_after_initial = out.split("Initial grid:\n", 1)[1].split("\n\n", 1)[0]
        for ch in section_after_initial:
            if ch == "\n":
                continue
            # Allow ANY of the legend characters and digits / spaces from the
            # initial same-color line that may have been split-on imperfectly.
            assert ch in {".", "R", "B"}, f"unexpected glyph {ch!r}"

    def test_llm_policy_without_extra_fails_loudly(self):
        # Without [llm] extra installed, --policy=llm should exit non-zero
        # with an informative error (not a stack trace).
        rc, _ = _capture(["--policy", "llm", "--ticks", "1"])
        # Either 2 (our explicit error code) — or 0 if torch IS installed,
        # which would mean the smoke environment ran it for real. Both are
        # acceptable here; this test only guards against a Python exception
        # bubbling out.
        assert rc in (0, 2)
