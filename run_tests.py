#!/usr/bin/env python3
"""Convenience pytest runner for the quorum project."""

import argparse
import subprocess
import sys


def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="Pytest runner for quorum")
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Include HTML coverage report')
    args = parser.parse_args()

    cmd = ['poetry', 'run', 'pytest', '-v']
    if args.unit:
        cmd.append('tests/unit')
    elif args.integration:
        cmd.append('tests/integration')
    if args.coverage:
        cmd += ['--cov=quorum', '--cov-report=html']

    sys.exit(run(cmd))


if __name__ == "__main__":
    main()
