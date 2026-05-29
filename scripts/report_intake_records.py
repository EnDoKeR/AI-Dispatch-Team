import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.intake_record_report import (
    build_intake_record_report,
    format_intake_record_report,
)
from app.market_intelligence.intake_record_repository import INTAKE_RECORDS_FILE


def build_parser():
    parser = argparse.ArgumentParser(
        description="Print a dry-run intake records report."
    )
    parser.add_argument(
        "--file",
        "--file-path",
        dest="file_path",
        default=INTAKE_RECORDS_FILE,
        help="Intake JSON records file.",
    )

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = build_intake_record_report(args.file_path)
    print(format_intake_record_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
