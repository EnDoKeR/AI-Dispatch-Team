"""Run safe local-only private RateCon measurement summaries."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.broker_template_registry import BrokerTemplateRegistry, TemplateRegistryError
from app.document_ai.candidate_coverage_analysis import (
    analyze_candidate_coverage_from_measurement_rows,
    write_candidate_coverage_artifacts,
)
from app.document_ai.load_identifier_coverage_audit import (
    analyze_load_identifier_coverage_from_rows,
    write_load_identifier_coverage_artifacts,
)
from app.document_ai.load_identifier_source_line_audit import (
    analyze_load_id_source_lines_from_rows,
    write_load_identifier_source_line_artifacts,
)
from app.document_ai.layout_provider import (
    LayoutProviderDependencyError,
    get_available_layout_providers,
    require_provider_dependency,
)
from app.document_ai.layout_provider_diagnostics import (
    compare_pdfplumber_table_profiles,
    write_layout_provider_diagnostics_report,
)
from app.document_ai.pdfplumber_layout_settings import PDFPLUMBER_TABLE_SETTING_PROFILES
from app.document_ai.layout_provider_contract import SHADOW_LAYOUT_PROVIDER_CHOICES
from app.document_ai.ocr_provider_contract import (
    OCR_PAGE_MODE_CHOICES,
    OCR_PROVIDER_CHOICES,
)
from app.document_ai.ratecon_ocr_candidate_policy import OCR_CANDIDATE_POLICIES
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
from app.document_ai.private_measurement_review_export import write_ratecon_review_export
from app.document_ai.private_measurement_pipeline import measure_private_ratecon_pdf
from app.document_ai.private_measurement_reports import (
    build_private_ratecon_measurement_aggregate,
)
from app.document_ai.rate_candidate_forensics import (
    analyze_rate_forensics_from_measurement_rows,
    write_rate_forensics_artifacts,
)
from app.document_ai.rate_conflict_audit import (
    analyze_rate_conflict_audit_from_measurement_rows,
    write_rate_conflict_audit_artifacts,
)
from app.document_ai.ratecon_shadow_audit import (
    shadow_records_from_rows,
    write_ratecon_shadow_audit_artifacts,
)
from app.document_ai.ratecon_review_workbook import write_ratecon_review_artifacts
from app.document_ai.field_candidate_resolver import (
    LOAD_RANKING_PROFILES,
    RANKING_PROFILES,
    RATE_RANKING_PROFILES,
)
from app.document_ai.field_candidate_generators import LOAD_CANDIDATE_PROFILES
from app.document_ai.stop_review_packet import write_stop_review_packet
from app.document_ai.stop_group_provenance_report import (
    write_stop_group_provenance_report,
)
from app.integrations import google_sheets_review as sheets_review


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
    natural_sort_inputs=False,
    enable_stop_span_extractor=False,
    compare_stop_span_to_stop_group_pipeline=False,
    ratecon_shadow_document_pipeline=False,
    include_document_ai_debug=False,
    strict_ratecon_shadow_document_pipeline=False,
    ratecon_shadow_use_legacy_final_candidates=True,
    ratecon_shadow_layout_provider="native_text",
    ratecon_shadow_table_profile="default",
    ratecon_shadow_ranking_profile="baseline",
    ratecon_shadow_load_candidate_profile="baseline",
    ratecon_shadow_load_ranking_profile=None,
    ratecon_shadow_rate_ranking_profile=None,
    ratecon_shadow_ocr_provider="none",
    ratecon_shadow_ocr_pages="ocr_required",
    ratecon_shadow_ocr_dpi=200,
    ratecon_shadow_ocr_candidate_policy="baseline",
    strict_ratecon_shadow_ocr=False,
    include_private_eval_values=False,
):
    pdfs = discover_private_pdfs(input_dir, natural_sort=natural_sort_inputs)
    if limit and int(limit) > 0:
        pdfs = pdfs[: int(limit)]

    aliases = build_safe_aliases(pdfs, prefix=alias_prefix, natural_sort=natural_sort_inputs)
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
            enable_stop_span_extractor=enable_stop_span_extractor,
            compare_stop_span_to_stop_group_pipeline=compare_stop_span_to_stop_group_pipeline,
            ratecon_shadow_document_pipeline=ratecon_shadow_document_pipeline,
            include_document_ai_debug=include_document_ai_debug,
            strict_ratecon_shadow_document_pipeline=strict_ratecon_shadow_document_pipeline,
            ratecon_shadow_use_legacy_final_candidates=(
                ratecon_shadow_use_legacy_final_candidates
            ),
            ratecon_shadow_layout_provider=ratecon_shadow_layout_provider,
            ratecon_shadow_table_profile=ratecon_shadow_table_profile,
            ratecon_shadow_ranking_profile=ratecon_shadow_ranking_profile,
            ratecon_shadow_load_candidate_profile=ratecon_shadow_load_candidate_profile,
            ratecon_shadow_load_ranking_profile=ratecon_shadow_load_ranking_profile,
            ratecon_shadow_rate_ranking_profile=ratecon_shadow_rate_ranking_profile,
            ratecon_shadow_ocr_provider=ratecon_shadow_ocr_provider,
            ratecon_shadow_ocr_pages=ratecon_shadow_ocr_pages,
            ratecon_shadow_ocr_dpi=ratecon_shadow_ocr_dpi,
            ratecon_shadow_ocr_candidate_policy=ratecon_shadow_ocr_candidate_policy,
            strict_ratecon_shadow_ocr=strict_ratecon_shadow_ocr,
            include_private_eval_values=include_private_eval_values,
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
        "local_document_names_by_alias": {aliases[path]: path.stem for path in pdfs},
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
        f"raw_stop_signal_count_total: {aggregate.get('raw_stop_signal_count_total', 0)}",
        f"premerge_stop_group_count_total: {aggregate.get('premerge_stop_group_count_total', 0)}",
        f"post_single_line_cluster_stop_group_count_total: {aggregate.get('post_single_line_cluster_stop_group_count_total', 0)}",
        f"post_row_merge_stop_group_count_total: {aggregate.get('post_row_merge_stop_group_count_total', 0)}",
        f"post_section_merge_stop_group_count_total: {aggregate.get('post_section_merge_stop_group_count_total', 0)}",
        f"post_noise_filter_stop_group_count_total: {aggregate.get('post_noise_filter_stop_group_count_total', 0)}",
        f"post_dedupe_stop_group_count_total: {aggregate.get('post_dedupe_stop_group_count_total', 0)}",
        f"post_date_time_attachment_stop_group_count_total: {aggregate.get('post_date_time_attachment_stop_group_count_total', 0)}",
        f"normalized_stop_count_total: {aggregate.get('normalized_stop_count_total', 0)}",
        f"pickup_count_total: {aggregate.get('pickup_count_total', 0)}",
        f"delivery_count_total: {aggregate.get('delivery_count_total', 0)}",
        f"generic_stop_count_total: {aggregate.get('generic_stop_count_total', 0)}",
        f"unknown_stop_count_total: {aggregate.get('unknown_stop_count_total', 0)}",
        f"stop_review_required_count_total: {aggregate.get('stop_review_required_count_total', 0)}",
        f"stop_group_quality_bucket_counts: {aggregate.get('stop_group_quality_bucket_counts', {})}",
        f"stop_noise_removed_count_total: {aggregate.get('stop_noise_removed_count_total', 0)}",
        f"stop_duplicate_removed_count_total: {aggregate.get('stop_duplicate_removed_count_total', 0)}",
        f"single_line_cluster_merge_count_total: {aggregate.get('single_line_cluster_merge_count_total', 0)}",
        f"table_row_merge_count_total: {aggregate.get('table_row_merge_count_total', 0)}",
        f"section_context_merge_count_total: {aggregate.get('section_context_merge_count_total', 0)}",
        f"stop_pipeline_passthrough_count: {aggregate.get('stop_pipeline_passthrough_count', 0)}",
        f"stop_pipeline_first_changed_stage_counts: {aggregate.get('stop_pipeline_first_changed_stage_counts', {})}",
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
        f"stop_span_extractor_attempted_count: {aggregate.get('stop_span_extractor_attempted_count', 0)}",
        f"span_anchor_count_total: {aggregate.get('span_anchor_count_total', 0)}",
        f"stop_span_count_total: {aggregate.get('stop_span_count_total', 0)}",
        f"span_normalized_stop_count_total: {aggregate.get('span_normalized_stop_count_total', 0)}",
        f"span_pickup_count_total: {aggregate.get('span_pickup_count_total', 0)}",
        f"span_delivery_count_total: {aggregate.get('span_delivery_count_total', 0)}",
        f"span_generic_stop_count_total: {aggregate.get('span_generic_stop_count_total', 0)}",
        f"span_unknown_count_total: {aggregate.get('span_unknown_count_total', 0)}",
        f"span_date_resolved_count_total: {aggregate.get('span_date_resolved_count_total', 0)}",
        f"span_date_missing_count_total: {aggregate.get('span_date_missing_count_total', 0)}",
        f"span_time_resolved_count_total: {aggregate.get('span_time_resolved_count_total', 0)}",
        f"span_time_missing_count_total: {aggregate.get('span_time_missing_count_total', 0)}",
        f"span_review_required_count_total: {aggregate.get('span_review_required_count_total', 0)}",
        f"span_passthrough_count: {aggregate.get('span_passthrough_count', 0)}",
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
                f"  raw_stop_signal_count: {row.get('raw_stop_signal_count', 0)}",
                f"  premerge_stop_group_count: {row.get('premerge_stop_group_count', 0)}",
                f"  post_single_line_cluster_stop_group_count: {row.get('post_single_line_cluster_stop_group_count', 0)}",
                f"  post_row_merge_stop_group_count: {row.get('post_row_merge_stop_group_count', 0)}",
                f"  post_section_merge_stop_group_count: {row.get('post_section_merge_stop_group_count', 0)}",
                f"  post_noise_filter_stop_group_count: {row.get('post_noise_filter_stop_group_count', 0)}",
                f"  post_dedupe_stop_group_count: {row.get('post_dedupe_stop_group_count', 0)}",
                f"  post_date_time_attachment_stop_group_count: {row.get('post_date_time_attachment_stop_group_count', 0)}",
                f"  normalized_stop_count: {row.get('normalized_stop_count', 0)}",
                f"  pickup_count: {row.get('pickup_count', 0)}",
                f"  delivery_count: {row.get('delivery_count', 0)}",
                f"  generic_stop_count: {row.get('generic_stop_count', 0)}",
                f"  unknown_stop_count: {row.get('unknown_stop_count', 0)}",
                f"  stop_review_required_count: {row.get('stop_review_required_count', 0)}",
                f"  stop_group_quality_bucket: {row.get('stop_group_quality_bucket', '')}",
                f"  stop_noise_removed_count: {row.get('stop_noise_removed_count', 0)}",
                f"  stop_duplicate_removed_count: {row.get('stop_duplicate_removed_count', 0)}",
                f"  single_line_cluster_merge_count: {row.get('single_line_cluster_merge_count', 0)}",
                f"  table_row_merge_count: {row.get('table_row_merge_count', 0)}",
                f"  section_context_merge_count: {row.get('section_context_merge_count', 0)}",
                f"  stop_pipeline_passthrough_detected: {(row.get('stop_pipeline_trace', {}) or {}).get('passthrough_detected', False)}",
                f"  stop_pipeline_first_changed_stage: {(row.get('stop_pipeline_trace', {}) or {}).get('first_stage_that_changed', '')}",
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
                f"  stop_span_extractor_enabled: {row.get('stop_span_extractor_enabled', False)}",
                f"  stop_span_comparison_enabled: {row.get('stop_span_comparison_enabled', False)}",
                f"  old_raw_stop_groups: {row.get('old_raw_stop_groups', 0)}",
                f"  old_normalized_stops: {row.get('old_normalized_stops', 0)}",
                f"  span_anchor_count: {row.get('span_anchor_count', 0)}",
                f"  stop_span_count: {row.get('stop_span_count', 0)}",
                f"  span_normalized_stop_count: {row.get('span_normalized_stop_count', 0)}",
                f"  span_pickup_count: {row.get('span_pickup_count', 0)}",
                f"  span_delivery_count: {row.get('span_delivery_count', 0)}",
                f"  span_generic_stop_count: {row.get('span_generic_stop_count', 0)}",
                f"  span_unknown_count: {row.get('span_unknown_count', 0)}",
                f"  span_date_resolved_count: {row.get('span_date_resolved_count', 0)}",
                f"  span_date_missing_count: {row.get('span_date_missing_count', 0)}",
                f"  span_time_resolved_count: {row.get('span_time_resolved_count', 0)}",
                f"  span_time_missing_count: {row.get('span_time_missing_count', 0)}",
                f"  span_review_required_count: {row.get('span_review_required_count', 0)}",
                f"  span_passthrough_detected: {row.get('span_passthrough_detected', False)}",
                f"  stop_span_delta: {row.get('stop_span_delta', 0)}",
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


def _load_google_review_config_from_args(args):
    config = sheets_review.load_google_sheets_review_config(args.google_config)
    return sheets_review.GoogleSheetsReviewConfig(
        spreadsheet_id=args.google_spreadsheet_id or config.spreadsheet_id,
        credentials_json_path=args.google_credentials_json or config.credentials_json_path,
        worksheet_prefix=args.google_worksheet_prefix or config.worksheet_prefix,
        service_account_email=config.service_account_email,
        default_sync_mode=config.default_sync_mode,
        allow_private_review_value_sync=getattr(
            config,
            "allow_private_review_value_sync",
            False,
        ),
    )


def _sync_google_review_tabs(report, args):
    mode = (
        sheets_review.SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
        if args.include_private_review_values_google_test_only
        else sheets_review.SYNC_MODE_STATUS_ONLY
    )
    if args.include_private_review_values_google_test_only:
        config = _load_google_review_config_from_args(args)
        if not config.allow_private_review_value_sync:
            raise sheets_review.GoogleSheetsReviewConfigError(
                "private review value sync requires allow_private_review_value_sync=true in local config"
            )
    rows_by_tab = sheets_review.build_google_review_tab_rows(
        report["rows"],
        local_document_names_by_alias=report.get("local_document_names_by_alias", {}),
        sync_mode=mode,
        include_private_values=args.include_private_review_values_google_test_only,
        worksheet_prefix=args.google_worksheet_prefix,
    )
    config = _load_google_review_config_from_args(args)
    client = sheets_review.connect_to_google_sheet(config)
    result = client.batch_update_review_tabs(rows_by_tab)
    result["sync_mode"] = mode
    return result


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
    parser.add_argument("--write-stop-provenance-report", action="store_true")
    parser.add_argument("--write-google-sheet-export", action="store_true")
    parser.add_argument("--write-review-workbook", action="store_true")
    parser.add_argument("--write-review-csvs", action="store_true")
    parser.add_argument("--write-candidate-coverage", action="store_true")
    parser.add_argument("--write-load-identifier-audit", action="store_true")
    parser.add_argument("--write-load-identifier-source-line-audit", action="store_true")
    parser.add_argument("--write-rate-forensics", action="store_true")
    parser.add_argument("--write-rate-conflict-audit", action="store_true")
    parser.add_argument("--ratecon-shadow-document-pipeline", action="store_true")
    parser.add_argument("--include-document-ai-debug", action="store_true")
    parser.add_argument("--write-ratecon-shadow-audit", action="store_true")
    parser.add_argument("--strict-ratecon-shadow-document-pipeline", action="store_true")
    parser.add_argument(
        "--ratecon-shadow-layout-provider",
        default="native_text",
        choices=SHADOW_LAYOUT_PROVIDER_CHOICES,
        help=(
            "Shadow-only document layout provider. Default native_text preserves "
            "existing behavior; auto/pdfplumber are diagnostic sidecars only."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-table-profile",
        default="default",
        choices=PDFPLUMBER_TABLE_SETTING_PROFILES,
        help="Shadow-only pdfplumber table profile when coordinate layout is requested.",
    )
    parser.add_argument(
        "--ratecon-shadow-ranking-profile",
        default="baseline",
        choices=sorted(RANKING_PROFILES),
        help=(
            "Shadow-only resolver ranking profile. Default baseline preserves "
            "current behavior; gold_diagnostic_v1 is an explicit local "
            "gold-evaluation experiment."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-load-candidate-profile",
        default="baseline",
        choices=sorted(LOAD_CANDIDATE_PROFILES),
        help=(
            "Shadow-only load candidate generation profile. Default baseline "
            "preserves current candidate generation; header_recall_v1 enables "
            "a local gold-recall experiment for generic document header/title "
            "load identifiers; header_recall_table_safety_v1 also applies "
            "generic table-neighbor safety metadata/penalties; "
            "header_recall_table_abstain_v1 conservatively abstains from "
            "ambiguous table-neighbor load selections."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-load-ranking-profile",
        default=None,
        choices=sorted(LOAD_RANKING_PROFILES),
        help=(
            "Shadow-only field-scoped load_number ranking/candidate profile. "
            "When set to a header_recall* profile, it also drives the "
            "corresponding load candidate generation profile. If omitted, "
            "the legacy broad --ratecon-shadow-ranking-profile behavior is "
            "preserved."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-rate-ranking-profile",
        default=None,
        choices=sorted(RATE_RANKING_PROFILES),
        help=(
            "Shadow-only field-scoped total_carrier_rate ranking profile. "
            "money_abstain_v1 applies local-only money-context abstention. "
            "If omitted, the legacy broad --ratecon-shadow-ranking-profile "
            "behavior is preserved."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-provider",
        default="none",
        choices=OCR_PROVIDER_CHOICES,
        help=(
            "Shadow-only optional local OCR provider. Default none preserves "
            "current behavior; auto/tesseract never use cloud services."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-pages",
        default="ocr_required",
        choices=OCR_PAGE_MODE_CHOICES,
        help="Shadow-only OCR page selection mode.",
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-dpi",
        default=200,
        type=int,
        choices=[150, 200, 300],
        help="Shadow-only OCR render DPI when local OCR is explicitly enabled.",
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-candidate-policy",
        default="baseline",
        choices=sorted(OCR_CANDIDATE_POLICIES),
        help=(
            "Shadow-only OCR candidate selection policy. "
            "fill_missing_strict_v1 keeps OCR diagnostic and only lets safe OCR "
            "candidates fill missing load/rate fields."
        ),
    )
    parser.add_argument(
        "--strict-ratecon-shadow-ocr",
        action="store_true",
        help="Fail cleanly when explicit shadow OCR cannot run.",
    )
    parser.add_argument(
        "--ratecon-shadow-use-legacy-final-candidates",
        action="store_true",
        help=(
            "Explicitly enable diagnostic legacy-final FieldCandidate fallback "
            "in shadow mode. This is already enabled by default for private "
            "measurement diagnostics."
        ),
    )
    parser.add_argument(
        "--no-ratecon-shadow-legacy-final-candidates",
        action="store_true",
        help=(
            "Disable diagnostic legacy-final FieldCandidate fallback in shadow mode. "
            "Independent candidates are always counted separately."
        ),
    )
    parser.add_argument("--sync-review-google-sheet", action="store_true")
    parser.add_argument("--confirm-google-review-sync", action="store_true")
    parser.add_argument("--google-config", default="")
    parser.add_argument("--google-spreadsheet-id", default="")
    parser.add_argument("--google-credentials-json", default="")
    parser.add_argument("--google-worksheet-prefix", default="RC_")
    parser.add_argument("--natural-sort-inputs", action="store_true")
    parser.add_argument("--enable-stop-span-extractor", action="store_true")
    parser.add_argument("--compare-stop-span-to-stop-group-pipeline", action="store_true")
    parser.add_argument("--include-private-stop-values-local-only", action="store_true")
    parser.add_argument("--include-private-review-values-local-only", action="store_true")
    parser.add_argument("--include-private-review-values-google-test-only", action="store_true")
    parser.add_argument(
        "--include-private-eval-values",
        action="store_true",
        help=(
            "Local-only gold-evaluation mode: include comparable private legacy, "
            "shadow, and candidate values in the shadow audit. Outputs must stay "
            "under .local_outputs and must not be committed."
        ),
    )
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

    if args.enable_stop_span_extractor and not args.enable_layout_candidates:
        _print_expected_config_error(
            "--enable-stop-span-extractor requires --enable-layout-candidates"
        )
        return 2

    if (
        args.compare_stop_span_to_stop_group_pipeline
        and not args.enable_stop_span_extractor
    ):
        _print_expected_config_error(
            "--compare-stop-span-to-stop-group-pipeline requires --enable-stop-span-extractor"
        )
        return 2

    if args.write_ratecon_shadow_audit and not args.ratecon_shadow_document_pipeline:
        _print_expected_config_error(
            "--write-ratecon-shadow-audit requires --ratecon-shadow-document-pipeline"
        )
        return 2

    if args.include_document_ai_debug and not args.ratecon_shadow_document_pipeline:
        _print_expected_config_error(
            "--include-document-ai-debug requires --ratecon-shadow-document-pipeline"
        )
        return 2

    if args.include_private_eval_values and not (
        args.ratecon_shadow_document_pipeline and args.write_ratecon_shadow_audit
    ):
        _print_expected_config_error(
            "--include-private-eval-values requires --ratecon-shadow-document-pipeline and --write-ratecon-shadow-audit"
        )
        return 2

    if (
        args.strict_ratecon_shadow_document_pipeline
        and not args.ratecon_shadow_document_pipeline
    ):
        _print_expected_config_error(
            "--strict-ratecon-shadow-document-pipeline requires --ratecon-shadow-document-pipeline"
        )
        return 2

    if args.include_private_stop_values_local_only and not args.write_stop_review_packet:
        _print_expected_config_error(
            "--include-private-stop-values-local-only requires --write-stop-review-packet"
        )
        return 2

    if args.include_private_review_values_local_only and not (
        args.write_review_workbook or args.write_review_csvs
    ):
        _print_expected_config_error(
            "--include-private-review-values-local-only requires --write-review-workbook or --write-review-csvs"
        )
        return 2

    if args.sync_review_google_sheet and not args.confirm_google_review_sync:
        _print_expected_config_error(
            "--sync-review-google-sheet requires --confirm-google-review-sync"
        )
        return 2

    if args.sync_review_google_sheet and not (
        args.write_review_workbook or args.write_review_csvs
    ):
        _print_expected_config_error(
            "--sync-review-google-sheet requires --write-review-workbook or --write-review-csvs"
        )
        return 2

    if (
        args.include_private_review_values_google_test_only
        and not args.sync_review_google_sheet
    ):
        _print_expected_config_error(
            "--include-private-review-values-google-test-only requires --sync-review-google-sheet"
        )
        return 2

    if args.layout_provider and args.layout_provider not in get_available_layout_providers():
        _print_expected_config_error(
            f"unknown layout provider {args.layout_provider!r}"
        )
        return 2

    if args.layout_provider == "pdfplumber":
        try:
            require_provider_dependency(args.layout_provider)
        except LayoutProviderDependencyError:
            _print_expected_config_error(
                "pdfplumber is not installed. Install optional dependency with: pip install pdfplumber"
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
            natural_sort_inputs=args.natural_sort_inputs,
            enable_stop_span_extractor=args.enable_stop_span_extractor,
            compare_stop_span_to_stop_group_pipeline=(
                args.compare_stop_span_to_stop_group_pipeline
            ),
            ratecon_shadow_document_pipeline=args.ratecon_shadow_document_pipeline,
            include_document_ai_debug=args.include_document_ai_debug,
            strict_ratecon_shadow_document_pipeline=(
                args.strict_ratecon_shadow_document_pipeline
            ),
            ratecon_shadow_use_legacy_final_candidates=(
                args.ratecon_shadow_use_legacy_final_candidates
                or not args.no_ratecon_shadow_legacy_final_candidates
            ),
            ratecon_shadow_layout_provider=args.ratecon_shadow_layout_provider,
            ratecon_shadow_table_profile=args.ratecon_shadow_table_profile,
            ratecon_shadow_ranking_profile=args.ratecon_shadow_ranking_profile,
            ratecon_shadow_load_candidate_profile=args.ratecon_shadow_load_candidate_profile,
            ratecon_shadow_load_ranking_profile=args.ratecon_shadow_load_ranking_profile,
            ratecon_shadow_rate_ranking_profile=args.ratecon_shadow_rate_ranking_profile,
            ratecon_shadow_ocr_provider=args.ratecon_shadow_ocr_provider,
            ratecon_shadow_ocr_pages=args.ratecon_shadow_ocr_pages,
            ratecon_shadow_ocr_dpi=args.ratecon_shadow_ocr_dpi,
            ratecon_shadow_ocr_candidate_policy=args.ratecon_shadow_ocr_candidate_policy,
            strict_ratecon_shadow_ocr=args.strict_ratecon_shadow_ocr,
            include_private_eval_values=args.include_private_eval_values,
        )

        for line in format_private_measurement_report(report):
            print(line)

        review_rows_by_sheet = None

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
        if not args.dry_run and args.write_google_sheet_export:
            export = write_ratecon_review_export(
                report["rows"],
                output_dir=args.output_dir,
                local_document_names_by_alias=report.get("local_document_names_by_alias", {}),
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            labels = {
                "csv": Path(export["csv"]).name,
                "row_count": export["row_count"],
            }
            if export.get("xlsx"):
                labels["xlsx"] = Path(export["xlsx"]).name
            print(f"google_sheet_export_written: {labels}")
        if not args.dry_run and (args.write_review_workbook or args.write_review_csvs):
            review = write_ratecon_review_artifacts(
                report["rows"],
                output_dir=args.output_dir,
                local_document_names_by_alias=report.get("local_document_names_by_alias", {}),
                include_private_values=args.include_private_review_values_local_only,
                write_workbook=args.write_review_workbook,
                write_csvs=args.write_review_csvs,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            review_rows_by_sheet = review.get("rows_by_sheet", {})
            labels = {
                "files": _safe_output_file_labels(review.get("paths", {})),
                "document_rows": review["summary"].get("document_rows", 0),
                "stop_review_rows": review["summary"].get("stop_review_rows", 0),
                "field_review_rows": review["summary"].get("field_review_rows", 0),
                "rate_review_rows": review["summary"].get("rate_review_rows", 0),
                "readiness_level_counts": review["summary"].get(
                    "readiness_level_counts",
                    {},
                ),
                "integrity_issue_counts": review["summary"].get(
                    "integrity_issue_counts",
                    {},
                ),
                "include_private_values_local_only": review.get(
                    "include_private_values_local_only",
                    False,
                ),
                "xlsx_written": review.get("xlsx_written", False),
                "csvs_written": review.get("csvs_written", False),
            }
            print(f"review_workbook_export_written: {labels}")
        if not args.dry_run and args.write_candidate_coverage:
            coverage_analysis = analyze_candidate_coverage_from_measurement_rows(
                report["rows"],
                review_rows_by_sheet=review_rows_by_sheet,
            )
            coverage = write_candidate_coverage_artifacts(
                coverage_analysis,
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            aggregate = coverage.get("aggregate", {})
            labels = {
                "files": _safe_output_file_labels(coverage.get("paths", {})),
                "document_count": aggregate.get("document_count", 0),
                "top_missing_candidate_fields": aggregate.get(
                    "top_missing_candidate_fields",
                    [],
                )[:8],
                "coverage_counts_by_stage": aggregate.get(
                    "coverage_counts_by_stage",
                    {},
                ),
                "gap_reason_counts": aggregate.get("gap_reason_counts", {}),
                "recommended_next_fix": aggregate.get("recommended_next_fix", ""),
                "private_values_printed": coverage.get("private_values_printed", False),
                "raw_text_printed": coverage.get("raw_text_printed", False),
            }
            print(f"candidate_coverage_written: {labels}")
        if not args.dry_run and args.write_load_identifier_audit:
            load_identifier_analysis = analyze_load_identifier_coverage_from_rows(
                report["rows"],
            )
            load_identifier_audit = write_load_identifier_coverage_artifacts(
                load_identifier_analysis,
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            aggregate = load_identifier_audit.get("aggregate", {})
            labels = {
                "files": _safe_output_file_labels(
                    load_identifier_audit.get("paths", {})
                ),
                "document_count": aggregate.get("document_count", 0),
                "primary_candidate_count": aggregate.get(
                    "primary_candidate_count",
                    0,
                ),
                "typed_reference_count": aggregate.get("typed_reference_count", 0),
                "rejected_non_primary_count": aggregate.get(
                    "rejected_non_primary_count",
                    0,
                ),
                "core_mapping_count": aggregate.get("core_mapping_count", 0),
                "records_by_reason": aggregate.get("records_by_reason", {}),
                "private_values_printed": load_identifier_audit.get(
                    "private_values_printed",
                    False,
                ),
                "raw_text_printed": load_identifier_audit.get(
                    "raw_text_printed",
                    False,
                ),
            }
            print(f"load_identifier_audit_written: {labels}")
        if not args.dry_run and args.write_load_identifier_source_line_audit:
            source_line_analysis = analyze_load_id_source_lines_from_rows(
                report["rows"],
            )
            source_line_audit = write_load_identifier_source_line_artifacts(
                source_line_analysis,
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
                raw=True,
            )
            aggregate = source_line_audit.get("aggregate", {})
            labels = {
                "files": _safe_output_file_labels(source_line_audit.get("paths", {})),
                "document_count": aggregate.get("document_count", 0),
                "identifier_like_source_line_count": aggregate.get(
                    "identifier_like_line_count",
                    0,
                ),
                "label_detected_count": aggregate.get("detected_label_count", 0),
                "label_classified_count": aggregate.get("classified_label_count", 0),
                "primary_candidate_count": aggregate.get(
                    "primary_candidate_count",
                    0,
                ),
                "core_mapping_count": aggregate.get("core_mapping_count", 0),
                "rejected_non_primary_count": aggregate.get(
                    "rejected_non_primary_count",
                    0,
                ),
                "fix_allowed": aggregate.get("fix_allowed", False),
                "private_values_printed": source_line_audit.get(
                    "private_values_printed",
                    False,
                ),
                "raw_text_printed": source_line_audit.get(
                    "raw_text_printed",
                    False,
                ),
                "line_text_printed": source_line_audit.get(
                    "line_text_printed",
                    False,
                ),
            }
            print(f"load_identifier_source_line_audit_written: {labels}")
        if not args.dry_run and args.write_rate_forensics:
            rate_forensics_analysis = analyze_rate_forensics_from_measurement_rows(
                report["rows"],
            )
            rate_forensics = write_rate_forensics_artifacts(
                rate_forensics_analysis,
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
                raw=True,
            )
            aggregate = rate_forensics.get("aggregate", {})
            labels = {
                "files": rate_forensics.get("files", {}),
                "document_count": aggregate.get("document_count", 0),
                "rate_candidate_count": aggregate.get("rate_candidate_count", 0),
                "main_candidate_count": aggregate.get(
                    "main_rate_candidate_count",
                    0,
                ),
                "accessorial_candidate_count": aggregate.get(
                    "accessorial_candidate_count",
                    0,
                ),
                "quickpay_candidate_count": aggregate.get(
                    "quickpay_candidate_count",
                    0,
                ),
                "terms_candidate_count": aggregate.get("terms_candidate_count", 0),
                "conflict_count": aggregate.get("conflict_count", 0),
                "records_by_conflict_reason": aggregate.get(
                    "records_by_conflict_reason",
                    {},
                ),
                "private_values_printed": rate_forensics.get(
                    "private_values_printed",
                    False,
                ),
                "raw_text_printed": rate_forensics.get("raw_text_printed", False),
                "money_values_printed": rate_forensics.get(
                    "money_values_printed",
                    False,
                ),
            }
            print(f"rate_forensics_written: {labels}")
        if not args.dry_run and args.write_rate_conflict_audit:
            rate_conflict_analysis = analyze_rate_conflict_audit_from_measurement_rows(
                report["rows"],
            )
            rate_conflict_audit = write_rate_conflict_audit_artifacts(
                rate_conflict_analysis,
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
                raw=True,
            )
            aggregate = rate_conflict_audit.get("aggregate", {})
            labels = {
                "files": rate_conflict_audit.get("files", {}),
                "document_count": aggregate.get("document_count", 0),
                "equivalent_group_count": aggregate.get(
                    "equivalent_group_count",
                    0,
                ),
                "different_strong_total_count": aggregate.get(
                    "different_strong_total_count",
                    0,
                ),
                "conflict_count": aggregate.get("conflict_count", 0),
                "records_by_conflict_reason": aggregate.get(
                    "records_by_conflict_reason",
                    {},
                ),
                "private_values_printed": rate_conflict_audit.get(
                    "private_values_printed",
                    False,
                ),
                "raw_text_printed": rate_conflict_audit.get(
                    "raw_text_printed",
                    False,
                ),
                "money_values_printed": rate_conflict_audit.get(
                    "money_values_printed",
                    False,
                ),
            }
            print(f"rate_conflict_audit_written: {labels}")
        if not args.dry_run and args.write_ratecon_shadow_audit:
            shadow_records = shadow_records_from_rows(report["rows"])
            shadow_audit = write_ratecon_shadow_audit_artifacts(
                shadow_records,
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            aggregate = shadow_audit.get("aggregate", {})
            labels = {
                "files": shadow_audit.get("files", {}),
                "documents_processed": aggregate.get("documents_processed", 0),
                "shadow_success": aggregate.get("shadow_success", 0),
                "shadow_failed": aggregate.get("shadow_failed", 0),
                "needs_review_count": (
                    aggregate.get("review_gate", {}) or {}
                ).get("needs_review_count", 0),
                "primary_layer_counts": (
                    aggregate.get("failure_attribution", {}) or {}
                ).get("primary_layer_counts", {}),
                "private_values_printed": shadow_audit.get(
                    "private_values_printed",
                    False,
                ),
                "raw_text_printed": shadow_audit.get("raw_text_printed", False),
                "money_values_printed": shadow_audit.get(
                    "money_values_printed",
                    False,
                ),
            }
            print(f"ratecon_shadow_audit_written: {labels}")
        if not args.dry_run and args.sync_review_google_sheet:
            sync_result = _sync_google_review_tabs(report, args)
            sync_labels = {
                "google_sheet_sync": "completed",
                "tabs_updated": sync_result.get("tabs_updated", []),
                "row_counts": sync_result.get("row_counts", {}),
                "sync_mode": sync_result.get("sync_mode", "status_only"),
                "private_values_printed": sync_result.get(
                    "private_values_printed",
                    False,
                ),
                "credentials_printed": sync_result.get("credentials_printed", False),
                "spreadsheet_id_printed": sync_result.get(
                    "spreadsheet_id_printed",
                    False,
                ),
            }
            print(f"google_sheet_sync: {sync_labels}")
        if not args.dry_run and args.write_stop_provenance_report:
            provenance_report = write_stop_group_provenance_report(
                report["rows"],
                output_dir=args.output_dir,
                allow_custom_output_dir=args.allow_custom_output_dir,
            )
            print(
                "stop_provenance_report_written: "
                f"{{'json': '{Path(provenance_report['json']).name}', "
                f"'md': '{Path(provenance_report['md']).name}', "
                f"'row_count': {provenance_report['row_count']}}}"
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
        sheets_review.GoogleSheetsReviewConfigError,
        sheets_review.GoogleSheetsReviewClientError,
    ) as exc:
        _print_expected_error(str(exc))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
