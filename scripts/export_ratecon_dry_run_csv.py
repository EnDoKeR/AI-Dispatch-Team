import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.ratecon_dry_run_csv_export import (  # noqa: E402
    DEFAULT_CSV_OUTPUT_PATH,
    export_ratecon_dry_run_csv,
)
from scripts.run_private_ratecon_pdf_dry_run import (  # noqa: E402
    DEFAULT_LIMIT,
    DEFAULT_PRIVATE_RATECON_DIR,
    build_private_pdf_dry_run_report,
)


DRY_RUN_WARNING = (
    "DRY RUN ONLY - safe RateCon dry-run CSV export, no raw text saved, no Google Sheets API used"
)


SAMPLE_SAFE_SUMMARIES = [
    {
        "label": "RATECON_001",
        "extraction_status": "TEXT_EXTRACTED",
        "page_count": 2,
        "char_count": 2800,
        "intake_status": "MISSING_FIELDS",
        "result_category": "NEEDS_PARSER_FIX",
        "missing_fields": ["broker_mc", "weight"],
        "needs_check_fields": ["broker_mc"],
        "low_confidence_fields": ["rate"],
        "suspected_parser_gap_fields": ["broker_mc", "weight"],
        "link_candidate_action": "",
        "approval_required": False,
        "warnings": ["sample_safe_row"],
    }
]


def build_safe_summaries(directory, limit, sample=False):
    if sample:
        return list(SAMPLE_SAFE_SUMMARIES)

    report = build_private_pdf_dry_run_report(
        directory=directory,
        limit=limit,
    )
    return list(report.get("results", []))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Export safe RateCon dry-run summaries to a local CSV file."
    )
    parser.add_argument(
        "--directory",
        default=str(DEFAULT_PRIVATE_RATECON_DIR),
        help="Local private RateCon originals folder.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of private PDFs to summarize.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_CSV_OUTPUT_PATH),
        help="CSV output path. Defaults to a gitignored private dry-run folder.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Export a fake sample row instead of reading local private PDFs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print safe JSON export metadata.",
    )
    return parser


def format_export_result(result):
    lines = [
        "RATECON DRY-RUN CSV EXPORT",
        DRY_RUN_WARNING,
        f"Output path: {result['output_path']}",
        f"Rows written: {result['rows_written']}",
        "No raw extracted text, private values, or Google Sheets writes are included.",
    ]
    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    summaries = build_safe_summaries(
        directory=args.directory,
        limit=args.limit,
        sample=args.sample,
    )
    result = export_ratecon_dry_run_csv(
        summaries,
        output_path=args.output,
    )
    result["dry_run_warning"] = DRY_RUN_WARNING

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_export_result(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
