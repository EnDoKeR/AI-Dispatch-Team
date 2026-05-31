"""Analyze local candidate coverage without printing private values."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.candidate_coverage_analysis import (
    CANDIDATE_COVERAGE_ANALYSIS_JSON,
    CANDIDATE_COVERAGE_ANALYSIS_MD,
    analyze_candidate_coverage,
    write_candidate_coverage_json,
    write_candidate_coverage_md,
)
from app.document_ai.candidate_coverage_target_selector import (
    CANDIDATE_COVERAGE_TARGET_SELECTION_JSON,
    CANDIDATE_COVERAGE_TARGET_SELECTION_MD,
    select_candidate_coverage_target,
    write_candidate_coverage_target_json,
    write_candidate_coverage_target_md,
)
from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze safe candidate coverage by field and pipeline stage."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    parser.add_argument("--write-md", action="store_true")
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--select-next-target", action="store_true")
    parser.add_argument("--include-local-document-names-local-only", action="store_true")
    parser.add_argument("--no-console-alias-details", action="store_true")
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    root = Path(args.input_dir)
    try:
        analysis = analyze_candidate_coverage(root)
    except LocalReviewAnalysisError as exc:
        print(f"candidate_coverage_analysis_error: {exc}")
        return 2

    aggregate = analysis["aggregate"]
    print("Candidate coverage analysis summary")
    print(f"documents_analyzed: {aggregate.get('document_count', 0)}")
    print(
        "top_fields_with_no_candidates: "
        f"{aggregate.get('top_missing_candidate_fields', [])[:8]}"
    )
    print(
        "stage_disappearance_counts: "
        f"{aggregate.get('coverage_counts_by_stage', {})}"
    )
    print(f"gap_reason_counts: {aggregate.get('gap_reason_counts', {})}")
    print(f"recommended_next_fix: {aggregate.get('recommended_next_fix')}")
    print("private_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")

    decision = None
    if args.select_next_target:
        decision = select_candidate_coverage_target(analysis)
        print("Candidate coverage target selection")
        print(f"selected_target: {decision.get('selected_target')}")
        print(f"affected_field_count: {decision.get('affected_field_count', 0)}")
        print(f"affected_alias_count: {decision.get('affected_alias_count', 0)}")
        print(f"supporting_fields: {decision.get('supporting_fields', [])}")
        print(f"supporting_gap_reasons: {decision.get('supporting_gap_reasons', {})}")
        print(f"confidence: {decision.get('confidence')}")
        print("private_values_printed: False")
        print("raw_text_printed: False")

    if not args.no_console_alias_details:
        for reason in aggregate.get("top_gap_reasons", [])[:5]:
            aliases = aggregate.get("aliases_by_gap_reason", {}).get(reason, [])
            print(f"aliases_for_{reason}: {aliases}")

    written = {}
    if args.write_md:
        written.update(
            write_candidate_coverage_md(
                analysis,
                root / CANDIDATE_COVERAGE_ANALYSIS_MD,
            )
        )
        if decision:
            written.update(
                write_candidate_coverage_target_md(
                    decision,
                    root / CANDIDATE_COVERAGE_TARGET_SELECTION_MD,
                )
            )
    if args.write_json:
        written.update(
            write_candidate_coverage_json(
                analysis,
                root / CANDIDATE_COVERAGE_ANALYSIS_JSON,
            )
        )
        if decision:
            written.update(
                write_candidate_coverage_target_json(
                    decision,
                    root / CANDIDATE_COVERAGE_TARGET_SELECTION_JSON,
                )
            )
    if written:
        print(f"candidate_coverage_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
