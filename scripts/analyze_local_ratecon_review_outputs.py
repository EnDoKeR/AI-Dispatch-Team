"""Analyze ignored local RateCon review CSV outputs safely."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.local_review_analysis import (
    LocalReviewAnalysisError,
    analyze_local_review_outputs,
    write_local_review_analysis_json,
    write_local_review_analysis_md,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)


LOCAL_REVIEW_ANALYSIS_MD = "local_review_analysis.md"
LOCAL_REVIEW_ANALYSIS_JSON = "local_review_analysis.json"


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze local RateCon review CSV outputs without printing values."
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


def _safe_summary_lines(analysis, no_console_alias_details=False):
    aggregate = (analysis or {}).get("aggregate", {})
    lines = [
        "Local RateCon review analysis summary",
        f"documents_analyzed: {aggregate.get('document_count', 0)}",
        f"readiness_counts: {aggregate.get('readiness_counts', {})}",
        f"ocr_needed_count: {aggregate.get('ocr_needed_count', 0)}",
        f"top_issue_categories: {aggregate.get('top_issue_categories', [])}",
        f"top_fields_by_review_need: {aggregate.get('top_fields_by_review_need', [])}",
        f"recommended_next_fix: {aggregate.get('recommended_next_fix', '')}",
        "private_values_printed: False",
        "raw_text_printed: False",
        "local_paths_printed: False",
    ]
    if not no_console_alias_details:
        aliases_by_issue = aggregate.get("aliases_by_issue_category", {})
        for category in aggregate.get("top_issue_categories", [])[:5]:
            lines.append(
                f"aliases_for_{category}: {aliases_by_issue.get(category, [])}"
            )
    return lines


def run_analysis(args):
    analysis = analyze_local_review_outputs(
        input_dir=args.input_dir,
        include_local_document_names=args.include_local_document_names_local_only,
    )
    written = {}
    root = Path(args.input_dir)
    if args.write_md:
        written.update(
            write_local_review_analysis_md(
                analysis,
                root / LOCAL_REVIEW_ANALYSIS_MD,
            )
        )
    if args.write_json:
        written.update(
            write_local_review_analysis_json(
                analysis,
                root / LOCAL_REVIEW_ANALYSIS_JSON,
            )
        )
    return analysis, written


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        analysis, written = run_analysis(args)
    except LocalReviewAnalysisError as exc:
        print("Local RateCon review analysis could not run.", file=sys.stderr)
        print(f"Reason: {exc}.", file=sys.stderr)
        return 2

    for line in _safe_summary_lines(
        analysis,
        no_console_alias_details=args.no_console_alias_details,
    ):
        print(line)
    if written:
        print(f"analysis_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
