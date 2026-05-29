import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.market_reload_watch_scenario_runner import (
    format_scenario_result,
    run_market_reload_watch_scenario,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run a dry-run market + reload-watch scenario."
    )
    parser.add_argument(
        "--file-path",
        default="",
        help="Optional reload-watch JSON records file for the dry-run.",
    )

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = run_market_reload_watch_scenario(file_path=args.file_path)
    print(format_scenario_result(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
