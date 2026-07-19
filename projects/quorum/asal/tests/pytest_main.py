"""Bazel ``py_test`` entry point for the ASAL project.

Points pytest at ``tests/`` next to this file. Forwards ``--test_arg``
values from Bazel as CLI args to pytest.
"""

from __future__ import annotations

import os
import sys

import pytest


_HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    return int(pytest.main([_HERE, *sys.argv[1:]]))


if __name__ == "__main__":
    sys.exit(main())
