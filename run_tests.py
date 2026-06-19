#!/usr/bin/env python3
"""Convenience pytest runner for the market project."""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Pytest runner for market (via uv)")
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Include HTML coverage report')
    args = parser.parse_args()

    cmd = ['uv', 'run', 'pytest', '-v']
    if args.unit:
        cmd.append('tests/unit')
    elif args.integration:
        cmd.append('tests/integration')
    if args.coverage:
        cmd += ['--cov=market', '--cov-report=html']

    print(f"$ {' '.join(cmd)}")
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
