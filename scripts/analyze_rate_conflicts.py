"""Analyze local rate conflict audit artifacts without printing money values."""

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
from app.document_ai.rate_conflict_audit import (
    RATE_CONFLICT_AUDIT_JSON,
    RATE_CONFLICT_AUDIT_MD,
    analyze_rate_conflict_audit,
    write_rate_conflict_audit_json,
    write_rate_conflict_audit_md,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze safe rate conflict groups and review routing reasons."
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
        analysis = analyze_rate_conflict_audit(root)
    except LocalReviewAnalysisError as exc:
        print(f"rate_conflict_audit_error: {exc}")
        return 2

    aggregate = analysis["aggregate"]
    print("Rate conflict audit summary")
    print(f"documents_analyzed: {aggregate.get('document_count', 0)}")
    print(f"rate_conflict_records: {len(analysis.get('records', []))}")
    print(f"equivalent_group_count: {aggregate.get('equivalent_group_count', 0)}")
    print(
        "different_strong_total_count: "
        f"{aggregate.get('different_strong_total_count', 0)}"
    )
    print(f"conflict_count: {aggregate.get('conflict_count', 0)}")
    print(f"review_required_count: {aggregate.get('review_required_count', 0)}")
    print(f"selected_rate_present_count: {aggregate.get('selected_rate_present_count', 0)}")
    print(f"core_rate_mapped_count: {aggregate.get('core_rate_mapped_count', 0)}")
    print(f"rate_conflict_reasons: {aggregate.get('records_by_conflict_reason', {})}")
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
        written.update(
            write_rate_conflict_audit_md(analysis, root / RATE_CONFLICT_AUDIT_MD)
        )
    if args.write_json:
        written.update(
            write_rate_conflict_audit_json(
                analysis,
                root / RATE_CONFLICT_AUDIT_JSON,
            )
        )
    if written:
        print(f"rate_conflict_audit_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
