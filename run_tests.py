#!/usr/bin/env python3
"""
Simple test runner for Pelosi Market Sentiment Forecasting Service.
"""

import sys
import subprocess
import argparse


def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n🔍 {description}")
    print("=" * 50)
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test runner for Pelosi")
    
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    
    args = parser.parse_args()
    
    # Build pytest command
    if args.unit:
        cmd = 'poetry run pytest tests/unit -v'
        description = "Running unit tests"
    elif args.integration:
        cmd = 'poetry run pytest tests/integration -v'
        description = "Running integration tests"
    else:
        cmd = 'poetry run pytest -v'
        description = "Running all tests"
    
    # Add coverage if requested
    if args.coverage:
        cmd += ' --cov=pelosi --cov-report=html'
    
    # Run the tests
    success = run_command(cmd, description)
    
    if args.coverage and success:
        print("\n📊 Coverage report generated in htmlcov/index.html")
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Tests passed!")
    else:
        print("💥 Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 