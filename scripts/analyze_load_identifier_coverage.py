"""Analyze local load identifier coverage without printing private values."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.load_identifier_coverage_audit import (
    LOAD_IDENTIFIER_COVERAGE_ANALYSIS_JSON,
    LOAD_IDENTIFIER_COVERAGE_ANALYSIS_MD,
    analyze_load_identifier_coverage,
    write_load_identifier_coverage_json,
    write_load_identifier_coverage_md,
)
from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze safe load identifier coverage by label and stage."
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
        analysis = analyze_load_identifier_coverage(root)
    except LocalReviewAnalysisError as exc:
        print(f"load_identifier_coverage_analysis_error: {exc}")
        return 2

    aggregate = analysis["aggregate"]
    print("Load identifier coverage audit summary")
    print(f"documents_analyzed: {aggregate.get('document_count', 0)}")
    print(f"primary_candidate_count: {aggregate.get('primary_candidate_count', 0)}")
    print(f"typed_reference_count: {aggregate.get('typed_reference_count', 0)}")
    print(
        "rejected_non_primary_count: "
        f"{aggregate.get('rejected_non_primary_count', 0)}"
    )
    print(f"core_mapping_count: {aggregate.get('core_mapping_count', 0)}")
    print(f"top_reasons: {aggregate.get('records_by_reason', {})}")
    print(
        "rejected_non_primary_categories: "
        f"{aggregate.get('records_by_label_category', {})}"
    )
    print(f"recommended_next_fix: {aggregate.get('recommended_next_fix')}")
    print("private_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")

    if not args.no_console_alias_details:
        for reason, aliases in (
            aggregate.get("aliases_by_reason", {}) or {}
        ).items():
            print(f"aliases_for_{reason}: {aliases}")

    written = {}
    if args.write_md:
        written.update(
            write_load_identifier_coverage_md(
                analysis,
                root / LOAD_IDENTIFIER_COVERAGE_ANALYSIS_MD,
            )
        )
    if args.write_json:
        written.update(
            write_load_identifier_coverage_json(
                analysis,
                root / LOAD_IDENTIFIER_COVERAGE_ANALYSIS_JSON,
            )
        )
    if written:
        print(f"load_identifier_coverage_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
