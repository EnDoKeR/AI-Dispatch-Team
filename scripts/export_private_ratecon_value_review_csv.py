import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.ratecon_value_review_csv_export import (  # noqa: E402
    DEFAULT_VALUE_REVIEW_CSV_PATH,
    export_ratecon_value_review_csv,
)
from scripts.run_private_ratecon_pdf_dry_run import (  # noqa: E402
    DEFAULT_PRIVATE_RATECON_DIR,
    _safe_limit,
    list_private_pdf_files,
)
from app.market_intelligence.intake.ratecon_pdf_dry_run import (  # noqa: E402
    run_ratecon_pdf_dry_run,
)


DEFAULT_LIMIT = 3
DRY_RUN_WARNING = (
    "DRY RUN ONLY - private RateCon value review CSV written locally; no text saved, no cases linked or created"
)


def _value_summary(label, result):
    dry_run_result = result.get("dry_run_result") or {}

    return {
        "label": label,
        "parser_output": dict(dry_run_result.get("parser_output") or {}),
        "ratecon_core_summary": dict(
            dry_run_result.get("ratecon_core_summary") or {}
        ),
        "intake_summary": dict(dry_run_result.get("intake_summary") or {}),
        "result_category": result.get("status", ""),
        "warnings": list(result.get("warnings", [])),
    }


def build_private_ratecon_value_review_summaries(
    directory=DEFAULT_PRIVATE_RATECON_DIR,
    limit=DEFAULT_LIMIT,
    runner=run_ratecon_pdf_dry_run,
):
    pdf_files = list_private_pdf_files(directory)
    safe_limit = _safe_limit(limit)
    summaries = []

    for index, path in enumerate(pdf_files[:safe_limit], start=1):
        label = f"RATECON_{index:03d}"
        result = runner(path, anonymized_label=label)
        summaries.append(_value_summary(label, result))

    return {
        "directory": str(Path(directory)),
        "total_pdf_files": len(pdf_files),
        "processed_count": len(summaries),
        "limit": safe_limit,
        "summaries": summaries,
        "privacy_warning": DRY_RUN_WARNING,
        "raw_text_saved": False,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Export local private RateCon extracted values for visual CSV review."
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
        help="Maximum number of private PDFs to process.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_VALUE_REVIEW_CSV_PATH),
        help="CSV output path. Defaults to a gitignored private dry-run folder.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print safe JSON export metadata.",
    )
    return parser


def format_export_result(result):
    lines = [
        "PRIVATE RATECON VALUE REVIEW CSV EXPORT",
        DRY_RUN_WARNING,
        f"Output path: {result['output_path']}",
        f"Rows written: {result['rows_written']}",
        "The CSV may contain private extracted values locally. Do not commit it.",
    ]
    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = build_private_ratecon_value_review_summaries(
        directory=args.directory,
        limit=args.limit,
    )
    result = export_ratecon_value_review_csv(
        report["summaries"],
        output_path=args.output,
    )
    result["dry_run_warning"] = DRY_RUN_WARNING
    result["processed_count"] = report["processed_count"]
    result["raw_text_saved"] = False
    result["private_text_saved"] = False

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_export_result(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
