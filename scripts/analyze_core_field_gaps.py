"""Analyze local RateCon core-field gaps without printing private values."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.core_field_gap_analysis import (
    CORE_FIELD_GAP_ANALYSIS_JSON,
    CORE_FIELD_GAP_ANALYSIS_MD,
    analyze_core_field_gaps,
    write_core_field_gap_analysis_json,
    write_core_field_gap_analysis_md,
)
from app.document_ai.local_review_analysis import LocalReviewAnalysisError
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze local review outputs by core field and safe gap reason."
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
        analysis = analyze_core_field_gaps(root)
    except LocalReviewAnalysisError as exc:
        print(f"core_field_gap_analysis_error: {exc}")
        return 2

    aggregate = analysis["aggregate"]
    print("Core field gap analysis summary")
    print(f"documents_analyzed: {aggregate.get('document_count', 0)}")
    print(
        "top_true_intake_core_fields: "
        f"{aggregate.get('top_true_intake_core_gaps', [])[:8]}"
    )
    print(
        "top_dispatch_decision_fields: "
        f"{aggregate.get('top_dispatch_decision_gaps', [])[:8]}"
    )
    print(f"top_all_gap_fields: {aggregate.get('top_core_field_gaps', [])[:8]}")
    print(f"top_conflict_fields: {aggregate.get('top_conflict_fields', [])[:8]}")
    print(f"top_gap_reasons: {list((aggregate.get('gap_counts_by_reason', {}) or {}).items())[:8]}")
    print(
        "readiness_blocker_counts: "
        f"{aggregate.get('blocker_counts_by_readiness_level', {})}"
    )
    print(f"recommended_next_target: {aggregate.get('recommended_next_target')}")
    print("private_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")

    if not args.no_console_alias_details:
        for field_name in aggregate.get("top_true_intake_core_gaps", [])[:5]:
            aliases = aggregate.get("aliases_by_field", {}).get(field_name, [])
            print(f"aliases_for_{field_name}: {aliases}")

    written = {}
    if args.write_md:
        written.update(
            write_core_field_gap_analysis_md(
                analysis,
                root / CORE_FIELD_GAP_ANALYSIS_MD,
            )
        )
    if args.write_json:
        written.update(
            write_core_field_gap_analysis_json(
                analysis,
                root / CORE_FIELD_GAP_ANALYSIS_JSON,
            )
        )
    if written:
        print(f"core_field_gap_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
