"""Analyze local rate candidate forensics without printing money values."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.rate_candidate_forensics import (
    RATE_FORENSICS_JSON,
    RATE_FORENSICS_MD,
    analyze_rate_forensics,
    write_rate_forensics_json,
    write_rate_forensics_md,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze safe rate candidate categories, sections, and conflicts."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    parser.add_argument("--write-md", action="store_true")
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--include-local-document-names-local-only", action="store_true")
    parser.add_argument("--no-console-alias-details", action="store_true")
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    root = Path(args.input_dir)
    try:
        analysis = analyze_rate_forensics(root)
    except LocalReviewAnalysisError as exc:
        print(f"rate_candidate_forensics_error: {exc}")
        return 2

    aggregate = analysis["aggregate"]
    print("Rate candidate forensics summary")
    print(f"documents_analyzed: {aggregate.get('document_count', 0)}")
    print(f"rate_candidate_count: {aggregate.get('rate_candidate_count', 0)}")
    print(f"main_rate_candidate_count: {aggregate.get('main_rate_candidate_count', 0)}")
    print(f"accessorial_candidate_count: {aggregate.get('accessorial_candidate_count', 0)}")
    print(f"quickpay_candidate_count: {aggregate.get('quickpay_candidate_count', 0)}")
    print(f"terms_candidate_count: {aggregate.get('terms_candidate_count', 0)}")
    print(f"billing_candidate_count: {aggregate.get('billing_candidate_count', 0)}")
    print(f"conflict_count: {aggregate.get('conflict_count', 0)}")
    print(f"rate_conflict_reasons: {aggregate.get('records_by_conflict_reason', {})}")
    print(f"rate_category_counts: {aggregate.get('category_counts', {})}")
    print(f"rate_source_section_counts: {aggregate.get('source_section_counts', {})}")
    print(f"selected_root_cause: {aggregate.get('selected_root_cause', '')}")
    print(f"fix_allowed: {aggregate.get('fix_allowed', False)}")
    print(f"recommended_next_action: {aggregate.get('recommended_next_action', '')}")
    print("private_values_printed: False")
    print("raw_text_printed: False")
    print("money_values_printed: False")
    print("local_paths_printed: False")

    if not args.no_console_alias_details:
        for reason, aliases in (
            aggregate.get("aliases_by_conflict_reason", {}) or {}
        ).items():
            print(f"aliases_for_{reason}: {aliases}")

    written = {}
    if args.write_md:
        written.update(write_rate_forensics_md(analysis, root / RATE_FORENSICS_MD))
    if args.write_json:
        written.update(write_rate_forensics_json(analysis, root / RATE_FORENSICS_JSON))
    if written:
        print(f"rate_forensics_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
