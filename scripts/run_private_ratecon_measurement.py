"""Run safe local-only private RateCon measurement summaries."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.private_measurement import build_safe_measurement_output_policy
from app.document_ai.private_measurement_inputs import (
    PrivateMeasurementInputError,
    build_safe_aliases,
    discover_private_pdfs,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    PrivateMeasurementOutputError,
    write_private_measurement_outputs,
)
from app.document_ai.private_measurement_pipeline import measure_private_ratecon_pdf
from app.document_ai.private_measurement_reports import (
    build_private_ratecon_measurement_aggregate,
)


DEFAULT_TEMPLATE_DIR = REPO_ROOT / "tests" / "fixtures" / "document_ai" / "broker_templates"


SAFETY_BANNER = (
    "PRIVATE LOCAL MEASUREMENT - no raw text printed or saved; "
    "private values redacted; outputs are local-only and ignored; "
    "do not commit generated outputs"
)


def _safe_output_file_labels(paths):
    return {
        key: Path(value).name
        for key, value in (paths or {}).items()
    }


def _print_expected_error(reason):
    print("Private RateCon measurement could not start.", file=sys.stderr)
    print(f"Reason: {reason}.", file=sys.stderr)
    print(
        "Replace the example path with a real local folder containing RateCon PDFs.",
        file=sys.stderr,
    )
    print("Tip: start with --limit 3 for the first safe run.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Example:", file=sys.stderr)
    print(
        'py scripts/run_private_ratecon_measurement.py --input-dir '
        '"C:\\Users\\YOUR_NAME\\Documents\\RateCons" '
        "--confirm-private-local-run --limit 3 --write-json --write-csv --write-md",
        file=sys.stderr,
    )


def _load_registry(template_dir):
    path = Path(template_dir)
    if path.exists():
        return BrokerTemplateRegistry.from_directory(path)
    return []


def build_private_ratecon_measurement_report(
    input_dir,
    template_dir=DEFAULT_TEMPLATE_DIR,
    alias_prefix="RATECON",
    limit=0,
    output_policy=None,
):
    pdfs = discover_private_pdfs(input_dir)
    if limit and int(limit) > 0:
        pdfs = pdfs[: int(limit)]

    aliases = build_safe_aliases(pdfs, prefix=alias_prefix)
    registry = _load_registry(template_dir)
    policy = output_policy or build_safe_measurement_output_policy()
    rows = [
        measure_private_ratecon_pdf(path, aliases[path], registry, output_policy=policy)
        for path in pdfs
    ]
    aggregate = build_private_ratecon_measurement_aggregate(rows)

    return {
        "rows": rows,
        "aggregate": aggregate,
        "document_count": len(rows),
        "input_dir_included": False,
        "filenames_included": False,
        "raw_text_printed": False,
        "raw_text_saved": False,
        "private_values_redacted": True,
    }


def format_private_measurement_report(report):
    aggregate = report.get("aggregate", {})
    lines = [
        SAFETY_BANNER,
        f"documents_measured: {report.get('document_count', 0)}",
        f"triage_route_counts: {aggregate.get('triage_route_counts', {})}",
        f"extraction_status_counts: {aggregate.get('extraction_status_counts', {})}",
        f"template_status_counts: {aggregate.get('template_status_counts', {})}",
        f"review_required_count: {aggregate.get('review_required_count', 0)}",
        f"blocker_category_counts: {aggregate.get('blocker_category_counts', {})}",
    ]

    for row in report.get("rows", []):
        lines.extend(
            [
                "",
                row.get("document_alias", ""),
                f"  page_count: {row.get('page_count', 0)}",
                f"  char_count: {row.get('char_count', 0)}",
                f"  triage_route: {row.get('triage_route', '')}",
                f"  extraction_status: {row.get('extraction_status', '')}",
                f"  template_status: {row.get('template_status', '')}",
                f"  review_required: {row.get('review_required', False)}",
                f"  blocker_categories: {row.get('blocker_categories', [])}",
                f"  missing_fields: {row.get('missing_fields', [])}",
                f"  needs_check_fields: {row.get('needs_check_fields', [])}",
                f"  conflict_fields: {row.get('conflict_fields', [])}",
                f"  candidate_counts_by_field: {row.get('candidate_counts_by_field', {})}",
                f"  warning_codes: {row.get('warning_codes', [])}",
            ]
        )

    lines.append("")
    lines.append("SAFE TO SHARE: aliases, counts, statuses, field names, blocker categories.")
    lines.append("DO NOT SHARE: raw text, filenames, broker names, MCs, rates, addresses, references, local paths.")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run safe local-only private RateCon measurement. Requires explicit "
            "confirmation and never prints raw text or private values."
        )
    )
    parser.add_argument("--input-dir", required=True, help="Local private PDF directory.")
    parser.add_argument(
        "--confirm-private-local-run",
        action="store_true",
        help="Required confirmation that this is a local private run.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
        help="Local-only output directory for safe summaries.",
    )
    parser.add_argument(
        "--template-dir",
        default=str(DEFAULT_TEMPLATE_DIR),
        help="Fake/anonymized broker template directory.",
    )
    parser.add_argument("--alias-prefix", default="RATECON")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--write-csv", action="store_true")
    parser.add_argument("--write-md", action="store_true")
    parser.add_argument("--write-value-review-template", action="store_true")
    parser.add_argument("--include-filenames-local-only", action="store_true")
    parser.add_argument("--include-file-hash-prefix-local-only", action="store_true")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.confirm_private_local_run:
        print("Refusing to run: pass --confirm-private-local-run for local private measurement.")
        return 2

    try:
        policy = build_safe_measurement_output_policy(
            include_filenames=args.include_filenames_local_only,
            include_file_hash_prefix=args.include_file_hash_prefix_local_only,
            include_private_values=False,
            include_raw_text=False,
        )
        report = build_private_ratecon_measurement_report(
            input_dir=args.input_dir,
            template_dir=args.template_dir,
            alias_prefix=args.alias_prefix,
            limit=args.limit,
            output_policy=policy,
        )

        for line in format_private_measurement_report(report):
            print(line)

        if not args.dry_run and any(
            [
                args.write_json,
                args.write_csv,
                args.write_md,
                args.write_value_review_template,
            ]
        ):
            output = write_private_measurement_outputs(
                report["rows"],
                report["aggregate"],
                output_dir=args.output_dir,
                write_json=args.write_json,
                write_csv=args.write_csv,
                write_md=args.write_md,
                write_value_review_template=args.write_value_review_template,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            print(f"safe_outputs_written: {_safe_output_file_labels(output['paths'])}")
    except (PrivateMeasurementInputError, PrivateMeasurementOutputError, FileNotFoundError) as exc:
        _print_expected_error(str(exc))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
