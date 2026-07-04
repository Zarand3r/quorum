"""Bazel ``py_test`` entry point: run pytest over slice0's test tree.

Bazel runs this under a hermetic sandbox with the project sources on
``sys.path`` (via the target's ``imports`` attribute). We point pytest at the
``tests/`` directory next to this file and at the project's ``pytest.ini`` for
configuration. Extra CLI args passed by Bazel (``--test_arg=-k foo``) forward.
"""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)  # tests/ -> project dir


def main() -> int:
    ini = os.path.join(_PROJECT_ROOT, "pytest.ini")
    args = ["-c", ini, _HERE, *sys.argv[1:]]
    return int(pytest.main(args))


if __name__ == "__main__":
    sys.exit(main())
