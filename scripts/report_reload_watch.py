import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.reload_watch_report import (
    build_reload_watch_report,
    format_reload_watch_report,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Print a dry-run reload-watch records report."
    )
    parser.add_argument(
        "--file",
        default="data/reload_watch_records.json",
        help="Reload-watch JSON records file.",
    )

    return parser


def main():
    args = build_parser().parse_args()
    report = build_reload_watch_report(args.file)
    print(format_reload_watch_report(report))


if __name__ == "__main__":
    main()
