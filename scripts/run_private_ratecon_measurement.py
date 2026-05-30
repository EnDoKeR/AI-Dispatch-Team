"""Run safe local-only private RateCon measurement summaries."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.broker_template_registry import BrokerTemplateRegistry, TemplateRegistryError
from app.document_ai.layout_provider import get_available_layout_providers
from app.document_ai.layout_provider_diagnostics import (
    compare_pdfplumber_table_profiles,
    write_layout_provider_diagnostics_report,
)
from app.document_ai.pdfplumber_layout_provider import PDFPLUMBER_TABLE_SETTING_PROFILES
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
from app.document_ai.stop_review_packet import write_stop_review_packet


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


def _print_expected_config_error(reason):
    print("Private RateCon measurement could not start.", file=sys.stderr)
    print(f"Reason: {reason}.", file=sys.stderr)


def _load_registry(
    template_dir,
    private_template_dir=None,
    allow_private_template_overlay=False,
):
    path = Path(template_dir)
    private_path = Path(private_template_dir) if private_template_dir else None

    if private_path and not allow_private_template_overlay:
        raise PrivateMeasurementInputError(
            "private template overlay requires --allow-private-template-overlay"
        )

    if private_path and not private_path.exists():
        raise PrivateMeasurementInputError("private template overlay directory does not exist")

    if path.exists() and private_path:
        return BrokerTemplateRegistry.from_directories(
            [path],
            private_dirs=[private_path],
        )

    if path.exists():
        return BrokerTemplateRegistry.from_directory(path)
    return []


def build_private_ratecon_measurement_report(
    input_dir,
    template_dir=DEFAULT_TEMPLATE_DIR,
    private_template_dir=None,
    allow_private_template_overlay=False,
    alias_prefix="RATECON",
    limit=0,
    output_policy=None,
    layout_provider_name="",
    enable_layout_candidates=False,
    enable_layout_fusion=False,
    enable_no_regression_fusion=True,
    allow_layout_regression_for_debug=False,
    compare_layout_to_text_baseline=False,
    layout_diagnostics=False,
    compare_pdfplumber_table_profiles_enabled=False,
    pdfplumber_table_profile="default",
):
    pdfs = discover_private_pdfs(input_dir)
    if limit and int(limit) > 0:
        pdfs = pdfs[: int(limit)]

    aliases = build_safe_aliases(pdfs, prefix=alias_prefix)
    registry = _load_registry(
        template_dir,
        private_template_dir=private_template_dir,
        allow_private_template_overlay=allow_private_template_overlay,
    )
    policy = output_policy or build_safe_measurement_output_policy()
    rows = [
        measure_private_ratecon_pdf(
            path,
            aliases[path],
            registry,
            output_policy=policy,
            layout_provider_name=layout_provider_name,
            enable_layout_candidates=enable_layout_candidates,
            enable_layout_fusion=enable_layout_fusion,
            enable_no_regression_fusion=enable_no_regression_fusion,
            allow_layout_regression_for_debug=allow_layout_regression_for_debug,
            compare_layout_to_text_baseline=compare_layout_to_text_baseline,
            pdfplumber_table_profile=pdfplumber_table_profile,
        )
        for path in pdfs
    ]
    aggregate = build_private_ratecon_measurement_aggregate(rows)
    table_profile_comparisons = []
    if compare_pdfplumber_table_profiles_enabled and layout_provider_name == "pdfplumber":
        row_by_alias = {row.get("document_alias", ""): row for row in rows}
        for path in pdfs:
            alias = aliases[path]
            row = row_by_alias.get(alias, {})
            if row.get("layout_provider_status") != "success":
                continue
            table_profile_comparisons.append(
                compare_pdfplumber_table_profiles(
                    path,
                    profiles=PDFPLUMBER_TABLE_SETTING_PROFILES,
                    document_alias=alias,
                )
            )

    return {
        "rows": rows,
        "aggregate": aggregate,
        "table_profile_comparisons": table_profile_comparisons,
        "layout_diagnostics_enabled": bool(layout_diagnostics),
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
        f"document_type_counts: {aggregate.get('document_type_counts', {})}",
        f"ratecon_eligible_count: {aggregate.get('ratecon_eligible_count', 0)}",
        f"extraction_relevant_count: {aggregate.get('extraction_relevant_count', 0)}",
        f"normal_load_movement_count: {aggregate.get('normal_load_movement_count', 0)}",
        f"tonu_count: {aggregate.get('tonu_count', 0)}",
        f"supplemental_only_count: {aggregate.get('supplemental_only_count', 0)}",
        f"non_ratecon_count: {aggregate.get('non_ratecon_count', 0)}",
        f"unknown_review_required_count: {aggregate.get('unknown_review_required_count', 0)}",
        f"ocr_needed_count: {aggregate.get('ocr_needed_count', 0)}",
        f"review_required_count: {aggregate.get('review_required_count', 0)}",
        f"classification_status_counts: {aggregate.get('classification_status_counts', {})}",
        f"page_role_counts: {aggregate.get('page_role_counts', {})}",
        f"section_role_counts: {aggregate.get('section_role_counts', {})}",
        f"extraction_scope_counts: {aggregate.get('extraction_scope_counts', {})}",
        f"layout_provider_status_counts: {aggregate.get('layout_provider_status_counts', {})}",
        f"layout_attempted_count: {aggregate.get('layout_attempted_count', 0)}",
        f"layout_success_count: {aggregate.get('layout_success_count', 0)}",
        f"layout_skipped_count: {aggregate.get('layout_skipped_count', 0)}",
        f"layout_failed_count: {aggregate.get('layout_failed_count', 0)}",
        f"layout_quality_bucket_counts: {aggregate.get('layout_quality_bucket_counts', {})}",
        f"layout_likely_issue_bucket_counts: {aggregate.get('layout_likely_issue_bucket_counts', {})}",
        f"layout_total_word_count: {aggregate.get('layout_total_word_count', 0)}",
        f"layout_total_line_count: {aggregate.get('layout_total_line_count', 0)}",
        f"layout_total_table_count: {aggregate.get('layout_total_table_count', 0)}",
        f"layout_total_table_cell_count: {aggregate.get('layout_total_table_cell_count', 0)}",
        f"layout_stop_signal_counts: {aggregate.get('layout_stop_signal_counts', {})}",
        f"fusion_attempted_count: {aggregate.get('fusion_attempted_count', 0)}",
        f"fusion_improved_counts_by_field: {aggregate.get('fusion_improved_counts_by_field', {})}",
        f"fusion_worsened_counts_by_field: {aggregate.get('fusion_worsened_counts_by_field', {})}",
        f"fusion_unchanged_counts_by_field: {aggregate.get('fusion_unchanged_counts_by_field', {})}",
        f"fusion_conflict_counts_by_field: {aggregate.get('fusion_conflict_counts_by_field', {})}",
        f"prevented_regression_counts_by_field: {aggregate.get('prevented_regression_counts_by_field', {})}",
        f"prevented_regression_count: {aggregate.get('prevented_regression_count', 0)}",
        f"stop_group_count_total: {aggregate.get('stop_group_count_total', 0)}",
        f"raw_stop_group_count_total: {aggregate.get('raw_stop_group_count_total', 0)}",
        f"normalized_stop_count_total: {aggregate.get('normalized_stop_count_total', 0)}",
        f"pickup_count_total: {aggregate.get('pickup_count_total', 0)}",
        f"delivery_count_total: {aggregate.get('delivery_count_total', 0)}",
        f"unknown_stop_count_total: {aggregate.get('unknown_stop_count_total', 0)}",
        f"stop_review_required_count_total: {aggregate.get('stop_review_required_count_total', 0)}",
        f"stop_group_quality_bucket_counts: {aggregate.get('stop_group_quality_bucket_counts', {})}",
        f"stop_noise_removed_count_total: {aggregate.get('stop_noise_removed_count_total', 0)}",
        f"stop_duplicate_removed_count_total: {aggregate.get('stop_duplicate_removed_count_total', 0)}",
        f"table_row_merge_count_total: {aggregate.get('table_row_merge_count_total', 0)}",
        f"section_context_merge_count_total: {aggregate.get('section_context_merge_count_total', 0)}",
        f"stop_pattern_counts: {aggregate.get('stop_pattern_counts', {})}",
        f"date_candidate_generated_count_total: {aggregate.get('date_candidate_generated_count_total', 0)}",
        f"date_candidate_attached_count_total: {aggregate.get('date_candidate_attached_count_total', 0)}",
        f"time_candidate_generated_count_total: {aggregate.get('time_candidate_generated_count_total', 0)}",
        f"time_candidate_attached_count_total: {aggregate.get('time_candidate_attached_count_total', 0)}",
        f"overclassified_stop_count_total: {aggregate.get('overclassified_stop_count_total', 0)}",
        f"ambiguous_stop_count_total: {aggregate.get('ambiguous_stop_count_total', 0)}",
        f"duplicate_like_stop_count_total: {aggregate.get('duplicate_like_stop_count_total', 0)}",
        f"noise_removed_count_total: {aggregate.get('noise_removed_count_total', 0)}",
        f"unresolved_due_to_missing_date_total: {aggregate.get('unresolved_due_to_missing_date_total', 0)}",
        f"unresolved_due_to_ambiguous_type_total: {aggregate.get('unresolved_due_to_ambiguous_type_total', 0)}",
        f"stop_field_status_counts: {aggregate.get('stop_field_status_counts', {})}",
        f"normalized_stop_improved_counts_by_field: {aggregate.get('normalized_stop_improved_counts_by_field', {})}",
        f"normalized_stop_conflict_counts_by_field: {aggregate.get('normalized_stop_conflict_counts_by_field', {})}",
        f"normalized_stop_missing_counts_by_field: {aggregate.get('normalized_stop_missing_counts_by_field', {})}",
        f"blocker_category_counts: {aggregate.get('blocker_category_counts', {})}",
        f"eligible_critical_field_missing_counts: {aggregate.get('eligible_critical_field_missing_counts', {})}",
        f"normal_load_critical_field_missing_counts: {aggregate.get('normal_load_critical_field_missing_counts', {})}",
        f"normal_load_critical_field_denominator: {aggregate.get('normal_load_critical_field_denominator', 0)}",
        f"unresolved_counts_by_field: {aggregate.get('unresolved_counts_by_field', {})}",
        f"non_applicable_counts_by_field: {aggregate.get('non_applicable_counts_by_field', {})}",
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
                f"  selected_template: {row.get('selected_template_id', '')}",
                f"  template_source: {row.get('template_source', '')}",
                f"  template_confidence_bucket: {row.get('template_confidence_bucket', '')}",
                f"  document_type: {row.get('document_type', '')}",
                f"  ratecon_eligible: {row.get('ratecon_eligible', False)}",
                f"  extraction_relevant: {row.get('extraction_relevant', False)}",
                f"  normal_load_movement: {row.get('normal_load_movement', False)}",
                f"  supplemental_only: {row.get('supplemental_only', False)}",
                f"  classification_status: {row.get('classification_status', '')}",
                f"  page_role_counts: {row.get('page_role_counts', {})}",
                f"  section_role_counts: {row.get('section_role_counts', {})}",
                f"  skipped_by_scope: {row.get('skipped_by_scope', False)}",
                f"  review_required: {row.get('review_required', False)}",
                f"  blocker_categories: {row.get('blocker_categories', [])}",
                f"  missing_fields: {row.get('missing_fields', [])}",
                f"  unresolved_fields: {row.get('unresolved_fields', [])}",
                f"  needs_check_fields: {row.get('needs_check_fields', [])}",
                f"  low_confidence_fields: {row.get('low_confidence_fields', [])}",
                f"  conflict_fields: {row.get('conflict_fields', [])}",
                f"  non_applicable_fields: {row.get('non_applicable_fields', [])}",
                f"  skipped_fields: {row.get('skipped_fields', [])}",
                f"  layout_provider_status: {row.get('layout_provider_status', '')}",
                f"  layout_candidate_counts_by_field: {row.get('layout_candidate_counts_by_field', {})}",
                f"  layout_evidence_type_counts: {row.get('layout_evidence_type_counts', {})}",
                f"  layout_improved_fields: {row.get('layout_improved_fields', [])}",
                f"  layout_worsened_fields: {row.get('layout_worsened_fields', [])}",
                f"  layout_unchanged_fields: {row.get('layout_unchanged_fields', [])}",
                f"  layout_quality_bucket: {row.get('layout_quality_bucket', '')}",
                f"  layout_total_word_count: {row.get('layout_total_word_count', 0)}",
                f"  layout_total_line_count: {row.get('layout_total_line_count', 0)}",
                f"  layout_total_table_count: {row.get('layout_total_table_count', 0)}",
                f"  layout_total_table_cell_count: {row.get('layout_total_table_cell_count', 0)}",
                f"  layout_stop_signal_counts: {row.get('layout_stop_signal_counts', {})}",
                f"  layout_likely_issue_bucket: {row.get('layout_likely_issue_bucket', '')}",
                f"  layout_table_settings_profile: {row.get('layout_table_settings_profile', '')}",
                f"  fusion_enabled: {row.get('fusion_enabled', False)}",
                f"  fusion_attempted: {row.get('fusion_attempted', False)}",
                f"  fusion_improved_fields: {row.get('fusion_improved_fields', [])}",
                f"  fusion_worsened_fields: {row.get('fusion_worsened_fields', [])}",
                f"  fusion_unchanged_fields: {row.get('fusion_unchanged_fields', [])}",
                f"  fusion_conflict_fields: {row.get('fusion_conflict_fields', [])}",
                f"  prevented_regression_fields: {row.get('prevented_regression_fields', [])}",
                f"  stop_group_count: {row.get('stop_group_count', 0)}",
                f"  raw_stop_group_count: {row.get('raw_stop_group_count', 0)}",
                f"  normalized_stop_count: {row.get('normalized_stop_count', 0)}",
                f"  pickup_count: {row.get('pickup_count', 0)}",
                f"  delivery_count: {row.get('delivery_count', 0)}",
                f"  unknown_stop_count: {row.get('unknown_stop_count', 0)}",
                f"  stop_review_required_count: {row.get('stop_review_required_count', 0)}",
                f"  stop_group_quality_bucket: {row.get('stop_group_quality_bucket', '')}",
                f"  stop_noise_removed_count: {row.get('stop_noise_removed_count', 0)}",
                f"  stop_duplicate_removed_count: {row.get('stop_duplicate_removed_count', 0)}",
                f"  table_row_merge_count: {row.get('table_row_merge_count', 0)}",
                f"  section_context_merge_count: {row.get('section_context_merge_count', 0)}",
                f"  stop_pattern_counts: {row.get('stop_pattern_counts', {})}",
                f"  date_candidate_generated_count: {row.get('date_candidate_generated_count', 0)}",
                f"  date_candidate_attached_count: {row.get('date_candidate_attached_count', 0)}",
                f"  time_candidate_generated_count: {row.get('time_candidate_generated_count', 0)}",
                f"  time_candidate_attached_count: {row.get('time_candidate_attached_count', 0)}",
                f"  overclassified_stop_count: {row.get('overclassified_stop_count', 0)}",
                f"  ambiguous_stop_count: {row.get('ambiguous_stop_count', 0)}",
                f"  duplicate_like_stop_count: {row.get('duplicate_like_stop_count', 0)}",
                f"  noise_removed_count: {row.get('noise_removed_count', 0)}",
                f"  unresolved_due_to_missing_date: {row.get('unresolved_due_to_missing_date', 0)}",
                f"  unresolved_due_to_ambiguous_type: {row.get('unresolved_due_to_ambiguous_type', 0)}",
                f"  stop_field_status_counts: {row.get('stop_field_status_counts', {})}",
                f"  normalized_stop_improved_fields: {row.get('normalized_stop_improved_fields', [])}",
                f"  normalized_stop_conflict_fields: {row.get('normalized_stop_conflict_fields', [])}",
                f"  normalized_stop_missing_fields: {row.get('normalized_stop_missing_fields', [])}",
                f"  candidate_counts_by_field: {row.get('candidate_counts_by_field', {})}",
                f"  warning_codes: {row.get('warning_codes', [])}",
            ]
        )

    if report.get("table_profile_comparisons"):
        lines.append("")
        lines.append(
            f"table_profile_comparison_count: {len(report.get('table_profile_comparisons', []))}"
        )
        for comparison in report.get("table_profile_comparisons", []):
            lines.append(
                "  {alias}: best_table={best_table}; best_stop_signal={best_stop}".format(
                    alias=comparison.get("document_alias", ""),
                    best_table=comparison.get("best_profile_by_table_count", ""),
                    best_stop=comparison.get("best_profile_by_stop_signal_count", ""),
                )
            )

    lines.append("")
    lines.append("SAFE TO SHARE: aliases, counts, statuses, field names, blocker categories.")
    lines.append("DO NOT SHARE: raw text, filenames, broker names, MCs, rates, addresses, references, local paths.")
    return lines


def _diagnostics_from_rows(rows):
    diagnostics = []
    for row in rows or []:
        if not row.get("layout_provider_status"):
            continue
        diagnostics.append(
            {
                "document_alias": row.get("document_alias", ""),
                "provider_name": row.get("layout_provider_name", "pdfplumber"),
                "provider_status": row.get("layout_provider_status", ""),
                "page_count": row.get("page_count", 0),
                "pages": [],
                "total_word_count": row.get("layout_total_word_count", 0),
                "total_line_count": row.get("layout_total_line_count", 0),
                "total_table_count": row.get("layout_total_table_count", 0),
                "total_table_cell_count": row.get("layout_total_table_cell_count", 0),
                "table_settings_profile": row.get("layout_table_settings_profile", ""),
                "layout_quality_bucket": row.get("layout_quality_bucket", ""),
                "stop_evidence_signals": row.get("layout_stop_signal_counts", {}),
                "warning_codes": row.get("warning_codes", []),
                "raw_text_included": False,
                "private_values_redacted": True,
            }
        )
    return diagnostics


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
    parser.add_argument("--private-template-dir", default="")
    parser.add_argument("--allow-private-template-overlay", action="store_true")
    parser.add_argument("--redact-private-template-names", action="store_true", default=True)
    parser.add_argument("--layout-provider", default="")
    parser.add_argument("--enable-layout-candidates", action="store_true")
    parser.add_argument("--enable-layout-fusion", action="store_true")
    parser.add_argument("--layout-diagnostics", action="store_true")
    parser.add_argument("--compare-pdfplumber-table-profiles", action="store_true")
    parser.add_argument(
        "--pdfplumber-table-profile",
        default="default",
        choices=PDFPLUMBER_TABLE_SETTING_PROFILES,
    )
    parser.add_argument("--enable-no-regression-fusion", action="store_true", default=True)
    parser.add_argument("--allow-layout-regression-for-debug", action="store_true")
    parser.add_argument("--compare-layout-to-text-baseline", action="store_true")
    parser.add_argument("--write-stop-review-packet", action="store_true")
    parser.add_argument("--include-private-stop-values-local-only", action="store_true")
    parser.add_argument("--include-filenames-local-only", action="store_true")
    parser.add_argument("--include-file-hash-prefix-local-only", action="store_true")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.confirm_private_local_run:
        print("Refusing to run: pass --confirm-private-local-run for local private measurement.")
        return 2

    if args.enable_layout_candidates and not args.layout_provider:
        _print_expected_config_error(
            "--enable-layout-candidates requires --layout-provider pdfplumber"
        )
        return 2

    if args.enable_layout_fusion and not args.enable_layout_candidates:
        _print_expected_config_error(
            "--enable-layout-fusion requires --enable-layout-candidates"
        )
        return 2

    if args.allow_layout_regression_for_debug and not args.enable_layout_fusion:
        _print_expected_config_error(
            "--allow-layout-regression-for-debug requires --enable-layout-fusion"
        )
        return 2

    if args.compare_pdfplumber_table_profiles and args.layout_provider != "pdfplumber":
        _print_expected_config_error(
            "--compare-pdfplumber-table-profiles requires --layout-provider pdfplumber"
        )
        return 2

    if args.include_private_stop_values_local_only and not args.write_stop_review_packet:
        _print_expected_config_error(
            "--include-private-stop-values-local-only requires --write-stop-review-packet"
        )
        return 2

    if args.layout_provider and args.layout_provider not in get_available_layout_providers():
        _print_expected_config_error(
            f"unknown layout provider {args.layout_provider!r}"
        )
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
            private_template_dir=args.private_template_dir,
            allow_private_template_overlay=args.allow_private_template_overlay,
            alias_prefix=args.alias_prefix,
            limit=args.limit,
            output_policy=policy,
            layout_provider_name=args.layout_provider,
            enable_layout_candidates=args.enable_layout_candidates,
            enable_layout_fusion=args.enable_layout_fusion,
            enable_no_regression_fusion=args.enable_no_regression_fusion,
            allow_layout_regression_for_debug=args.allow_layout_regression_for_debug,
            compare_layout_to_text_baseline=args.compare_layout_to_text_baseline,
            layout_diagnostics=args.layout_diagnostics,
            compare_pdfplumber_table_profiles_enabled=args.compare_pdfplumber_table_profiles,
            pdfplumber_table_profile=args.pdfplumber_table_profile,
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
        if not args.dry_run and args.write_stop_review_packet:
            stop_sets = [
                row.get("normalized_stop_set")
                for row in report["rows"]
                if row.get("normalized_stop_set")
            ]
            packet = write_stop_review_packet(
                stop_sets,
                output_dir=args.output_dir,
                include_private_values_local_only=args.include_private_stop_values_local_only,
            )
            print(
                "stop_review_packet_written: "
                f"{{'csv': '{Path(packet['csv']).name}', "
                f"'md': '{Path(packet['md']).name}', "
                f"'row_count': {packet['row_count']}, "
                f"'include_private_values_local_only': "
                f"{packet['include_private_values_local_only']}}}"
            )
        if not args.dry_run and args.layout_diagnostics:
            diagnostics_path = write_layout_provider_diagnostics_report(
                _diagnostics_from_rows(report["rows"]),
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            print(f"layout_diagnostics_written: {Path(diagnostics_path).name}")
    except (
        PrivateMeasurementInputError,
        PrivateMeasurementOutputError,
        TemplateRegistryError,
        FileNotFoundError,
    ) as exc:
        _print_expected_error(str(exc))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
