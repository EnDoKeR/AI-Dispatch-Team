"""Analyze local load identifier source-line coverage without private values."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.load_identifier_source_line_audit import (
    LOAD_ID_SOURCE_LINE_ANALYSIS_JSON,
    LOAD_ID_SOURCE_LINE_ANALYSIS_MD,
    analyze_load_identifier_source_lines,
    write_load_identifier_source_line_json,
    write_load_identifier_source_line_md,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze safe load identifier source-line coverage."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    parser.add_argument("--write-md", action="store_true")
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument(
        "--include-local-document-names-local-only",
        action="store_true",
        help="Accepted for workflow symmetry; console output remains aliases/counts only.",
    )
    parser.add_argument("--no-console-alias-details", action="store_true")
    return parser


def _print_summary(analysis, include_aliases=True):
    aggregate = analysis.get("aggregate", {})
    header_load_identity_count = aggregate.get(
        "header_identifier_like_line_count",
        0,
    ) + aggregate.get("load_identity_identifier_like_line_count", 0)
    stop_billing_terms_count = aggregate.get(
        "stop_section_identifier_like_line_count",
        0,
    ) + aggregate.get("billing_terms_identifier_like_line_count", 0)
    print("Load identifier source-line forensics summary")
    print(f"documents_analyzed: {aggregate.get('document_count', 0)}")
    print(
        "identifier_like_source_line_count: "
        f"{aggregate.get('identifier_like_line_count', 0)}"
    )
    print(
        "header_load_identity_source_line_count: "
        f"{header_load_identity_count}"
    )
    print(
        "stop_billing_terms_source_line_count: "
        f"{stop_billing_terms_count}"
    )
    print(f"label_detected_count: {aggregate.get('detected_label_count', 0)}")
    print(f"label_classified_count: {aggregate.get('classified_label_count', 0)}")
    print(f"primary_candidate_count: {aggregate.get('primary_candidate_count', 0)}")
    print(f"core_mapping_count: {aggregate.get('core_mapping_count', 0)}")
    print(
        "rejected_non_primary_count: "
        f"{aggregate.get('rejected_non_primary_count', 0)}"
    )
    print(f"top_reasons: {aggregate.get('records_by_reason', {})}")
    print(
        "shared_root_cause_candidates: "
        f"{aggregate.get('shared_root_cause_candidates', {})}"
    )
    print(f"fix_allowed: {aggregate.get('fix_allowed', False)}")
    print(f"selected_root_cause: {aggregate.get('selected_root_cause', '')}")
    print(f"recommended_next_action: {aggregate.get('recommended_next_action', '')}")
    print(f"private_values_printed: {analysis.get('private_values_included', False)}")
    print(f"raw_text_printed: {analysis.get('raw_text_included', False)}")
    print(f"line_text_printed: {analysis.get('line_text_included', False)}")
    print("local_paths_printed: False")
    if include_aliases:
        for reason, aliases in (aggregate.get("aliases_by_reason", {}) or {}).items():
            print(f"aliases_for_{reason}: {aliases}")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.input_dir)

    try:
        analysis = analyze_load_identifier_source_lines(root)
    except Exception as exc:
        print(f"load_identifier_source_line_analysis_error: {exc}")
        return 2

    _print_summary(analysis, include_aliases=not args.no_console_alias_details)

    written = {}
    if args.write_md:
        written.update(
            write_load_identifier_source_line_md(
                analysis,
                root / LOAD_ID_SOURCE_LINE_ANALYSIS_MD,
            )
        )
    if args.write_json:
        written.update(
            write_load_identifier_source_line_json(
                analysis,
                root / LOAD_ID_SOURCE_LINE_ANALYSIS_JSON,
            )
        )
    if written:
        print(f"load_identifier_source_line_outputs_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
