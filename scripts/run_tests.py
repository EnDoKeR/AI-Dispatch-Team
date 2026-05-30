"""Canonical unittest runner for the project.

Bare ``python -m unittest discover`` starts at the repository root in this
project and can find zero tests. This runner always discovers from ``tests`` and
fails if discovery returns an empty suite.
"""

import argparse
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_DIR = REPO_ROOT / "tests"
DEFAULT_PATTERN = "test_*.py"


def _ensure_repo_root_on_path():
    repo_root = str(REPO_ROOT)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def discover_test_suite(start_dir=DEFAULT_TEST_DIR, pattern=DEFAULT_PATTERN):
    start_path = Path(start_dir)
    _ensure_repo_root_on_path()
    loader = unittest.defaultTestLoader
    return loader.discover(str(start_path), pattern=pattern)


def count_tests(suite):
    return suite.countTestCases()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run the official AI Dispatch Team unittest suite. "
            "Discovery is pinned to the tests directory and fails on zero tests."
        )
    )
    parser.add_argument("--start-dir", default=str(DEFAULT_TEST_DIR))
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    start_dir = Path(args.start_dir)
    print("Official test command: py scripts/run_tests.py")
    print(f"Fallback command: py -m unittest discover -s {start_dir} -p {args.pattern!r}")

    if not start_dir.exists():
        print(f"ERROR: test start directory does not exist: {start_dir}", file=sys.stderr)
        return 2

    suite = discover_test_suite(start_dir=start_dir, pattern=args.pattern)
    test_count = count_tests(suite)
    print(f"Discovered tests: {test_count}")

    if test_count == 0:
        print(
            "ERROR: unittest discovery found zero tests. "
            "Use an explicit tests directory or fix discovery configuration.",
            file=sys.stderr,
        )
        return 2

    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
