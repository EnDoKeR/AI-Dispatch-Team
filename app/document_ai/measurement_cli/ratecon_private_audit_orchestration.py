"""Local-only audit/diagnostic orchestration for private RateCon measurement."""

from dataclasses import dataclass

from app.document_ai.candidate_coverage_analysis import (
    analyze_candidate_coverage_from_measurement_rows,
    write_candidate_coverage_artifacts,
)
from app.document_ai.layout_provider_diagnostics import (
    write_layout_provider_diagnostics_report,
)
from app.document_ai.load_identifier_coverage_audit import (
    analyze_load_identifier_coverage_from_rows,
    write_load_identifier_coverage_artifacts,
)
from app.document_ai.load_identifier_source_line_audit import (
    analyze_load_id_source_lines_from_rows,
    write_load_identifier_source_line_artifacts,
)
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    output_file_labels,
    output_file_name,
    validate_private_ratecon_output_dir,
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
from app.document_ai.stop_group_provenance_report import (
    write_stop_group_provenance_report,
)


@dataclass(frozen=True)
class PrivateRateconAuditTaskResult:
    """Printable result from one optional private measurement audit task."""

    task_name: str
    message_label: str
    payload: object


_AUDIT_TASK_FLAGS = [
    ("candidate_coverage", "write_candidate_coverage"),
    ("load_identifier_audit", "write_load_identifier_audit"),
    ("load_identifier_source_line_audit", "write_load_identifier_source_line_audit"),
    ("rate_forensics", "write_rate_forensics"),
    ("rate_conflict_audit", "write_rate_conflict_audit"),
    ("ratecon_shadow_audit", "write_ratecon_shadow_audit"),
    ("stop_provenance_report", "write_stop_provenance_report"),
    ("layout_diagnostics", "layout_diagnostics"),
]


def _rows(report):
    return (report or {}).get("rows", [])


def _allow_custom_output_dir(config):
    return bool(getattr(config, "allow_custom_output_dir", False))


def _dry_run(config):
    return bool(getattr(config, "dry_run", False))


def _safe_output_file_labels(paths):
    return output_file_labels(paths)


def build_private_ratecon_audit_task_plan(config, output_paths=None):
    """Return enabled optional audit tasks without running any writer."""
    if _dry_run(config):
        return []
    return [
        task_name
        for task_name, flag_name in _AUDIT_TASK_FLAGS
        if bool(getattr(config, flag_name, False))
    ]


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


def run_candidate_coverage_audit_if_enabled(
    report,
    config,
    output_paths,
    *,
    review_rows_by_sheet=None,
    analyzer=analyze_candidate_coverage_from_measurement_rows,
    writer=write_candidate_coverage_artifacts,
):
    if _dry_run(config) or not getattr(config, "write_candidate_coverage", False):
        return None
    coverage_analysis = analyzer(
        _rows(report),
        review_rows_by_sheet=review_rows_by_sheet,
    )
    coverage = writer(
        coverage_analysis,
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
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
    return PrivateRateconAuditTaskResult(
        task_name="candidate_coverage",
        message_label="candidate_coverage_written",
        payload=labels,
    )


def run_load_identifier_audit_if_enabled(
    report,
    config,
    output_paths,
    *,
    analyzer=analyze_load_identifier_coverage_from_rows,
    writer=write_load_identifier_coverage_artifacts,
):
    if _dry_run(config) or not getattr(config, "write_load_identifier_audit", False):
        return None
    load_identifier_analysis = analyzer(_rows(report))
    load_identifier_audit = writer(
        load_identifier_analysis,
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
    )
    aggregate = load_identifier_audit.get("aggregate", {})
    labels = {
        "files": _safe_output_file_labels(load_identifier_audit.get("paths", {})),
        "document_count": aggregate.get("document_count", 0),
        "primary_candidate_count": aggregate.get("primary_candidate_count", 0),
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
        "raw_text_printed": load_identifier_audit.get("raw_text_printed", False),
    }
    return PrivateRateconAuditTaskResult(
        task_name="load_identifier_audit",
        message_label="load_identifier_audit_written",
        payload=labels,
    )


def run_load_identifier_source_line_audit_if_enabled(
    report,
    config,
    output_paths,
    *,
    analyzer=analyze_load_id_source_lines_from_rows,
    writer=write_load_identifier_source_line_artifacts,
):
    if _dry_run(config) or not getattr(
        config,
        "write_load_identifier_source_line_audit",
        False,
    ):
        return None
    source_line_analysis = analyzer(_rows(report))
    source_line_audit = writer(
        source_line_analysis,
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
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
        "primary_candidate_count": aggregate.get("primary_candidate_count", 0),
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
        "raw_text_printed": source_line_audit.get("raw_text_printed", False),
        "line_text_printed": source_line_audit.get("line_text_printed", False),
    }
    return PrivateRateconAuditTaskResult(
        task_name="load_identifier_source_line_audit",
        message_label="load_identifier_source_line_audit_written",
        payload=labels,
    )


def run_rate_forensics_if_enabled(
    report,
    config,
    output_paths,
    *,
    analyzer=analyze_rate_forensics_from_measurement_rows,
    writer=write_rate_forensics_artifacts,
):
    if _dry_run(config) or not getattr(config, "write_rate_forensics", False):
        return None
    rate_forensics_analysis = analyzer(_rows(report))
    rate_forensics = writer(
        rate_forensics_analysis,
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
        raw=True,
    )
    aggregate = rate_forensics.get("aggregate", {})
    labels = {
        "files": rate_forensics.get("files", {}),
        "document_count": aggregate.get("document_count", 0),
        "rate_candidate_count": aggregate.get("rate_candidate_count", 0),
        "main_candidate_count": aggregate.get("main_rate_candidate_count", 0),
        "accessorial_candidate_count": aggregate.get(
            "accessorial_candidate_count",
            0,
        ),
        "quickpay_candidate_count": aggregate.get("quickpay_candidate_count", 0),
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
        "money_values_printed": rate_forensics.get("money_values_printed", False),
    }
    return PrivateRateconAuditTaskResult(
        task_name="rate_forensics",
        message_label="rate_forensics_written",
        payload=labels,
    )


def run_rate_conflict_audit_if_enabled(
    report,
    config,
    output_paths,
    *,
    analyzer=analyze_rate_conflict_audit_from_measurement_rows,
    writer=write_rate_conflict_audit_artifacts,
):
    if _dry_run(config) or not getattr(config, "write_rate_conflict_audit", False):
        return None
    rate_conflict_analysis = analyzer(_rows(report))
    rate_conflict_audit = writer(
        rate_conflict_analysis,
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
        raw=True,
    )
    aggregate = rate_conflict_audit.get("aggregate", {})
    labels = {
        "files": rate_conflict_audit.get("files", {}),
        "document_count": aggregate.get("document_count", 0),
        "equivalent_group_count": aggregate.get("equivalent_group_count", 0),
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
        "raw_text_printed": rate_conflict_audit.get("raw_text_printed", False),
        "money_values_printed": rate_conflict_audit.get(
            "money_values_printed",
            False,
        ),
    }
    return PrivateRateconAuditTaskResult(
        task_name="rate_conflict_audit",
        message_label="rate_conflict_audit_written",
        payload=labels,
    )


def run_ratecon_shadow_audit_if_enabled(
    report,
    config,
    output_paths,
    *,
    record_builder=shadow_records_from_rows,
    writer=write_ratecon_shadow_audit_artifacts,
):
    if _dry_run(config) or not getattr(config, "write_ratecon_shadow_audit", False):
        return None
    shadow_records = record_builder(_rows(report))
    shadow_audit = writer(
        shadow_records,
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
    )
    aggregate = shadow_audit.get("aggregate", {})
    labels = {
        "files": shadow_audit.get("files", {}),
        "documents_processed": aggregate.get("documents_processed", 0),
        "shadow_success": aggregate.get("shadow_success", 0),
        "shadow_failed": aggregate.get("shadow_failed", 0),
        "needs_review_count": (aggregate.get("review_gate", {}) or {}).get(
            "needs_review_count",
            0,
        ),
        "primary_layer_counts": (
            aggregate.get("failure_attribution", {}) or {}
        ).get("primary_layer_counts", {}),
        "private_values_printed": shadow_audit.get(
            "private_values_printed",
            False,
        ),
        "raw_text_printed": shadow_audit.get("raw_text_printed", False),
        "money_values_printed": shadow_audit.get("money_values_printed", False),
    }
    return PrivateRateconAuditTaskResult(
        task_name="ratecon_shadow_audit",
        message_label="ratecon_shadow_audit_written",
        payload=labels,
    )


def run_stop_provenance_report_if_enabled(
    report,
    config,
    output_paths,
    *,
    writer=write_stop_group_provenance_report,
):
    if _dry_run(config) or not getattr(config, "write_stop_provenance_report", False):
        return None
    provenance_report = writer(
        _rows(report),
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
    )
    labels = {
        "json": output_file_name(provenance_report["json"]),
        "md": output_file_name(provenance_report["md"]),
        "row_count": provenance_report["row_count"],
    }
    return PrivateRateconAuditTaskResult(
        task_name="stop_provenance_report",
        message_label="stop_provenance_report_written",
        payload=labels,
    )


def run_layout_diagnostics_if_enabled(
    report,
    config,
    output_paths,
    *,
    writer=write_layout_provider_diagnostics_report,
):
    if _dry_run(config) or not getattr(config, "layout_diagnostics", False):
        return None
    diagnostics_path = writer(
        _diagnostics_from_rows(_rows(report)),
        output_dir=output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
    )
    return PrivateRateconAuditTaskResult(
        task_name="layout_diagnostics",
        message_label="layout_diagnostics_written",
        payload=output_file_name(diagnostics_path),
    )


def run_private_ratecon_audit_exports(
    report,
    config,
    output_paths,
    *,
    review_rows_by_sheet=None,
    task_names=None,
):
    """Run enabled local-only audit exports without changing audit algorithms."""
    task_plan = build_private_ratecon_audit_task_plan(config, output_paths)
    if task_names is not None:
        allowed_tasks = set(task_names)
        task_plan = [task_name for task_name in task_plan if task_name in allowed_tasks]
    if not task_plan:
        return []
    validate_private_ratecon_output_dir(
        output_paths.output_dir,
        allow_custom_output_dir=_allow_custom_output_dir(config),
    )
    task_runners = [
        (
            "candidate_coverage",
            lambda: run_candidate_coverage_audit_if_enabled(
                report,
                config,
                output_paths,
                review_rows_by_sheet=review_rows_by_sheet,
            ),
        ),
        (
            "load_identifier_audit",
            lambda: run_load_identifier_audit_if_enabled(report, config, output_paths),
        ),
        (
            "load_identifier_source_line_audit",
            lambda: run_load_identifier_source_line_audit_if_enabled(
                report,
                config,
                output_paths,
            ),
        ),
        (
            "rate_forensics",
            lambda: run_rate_forensics_if_enabled(report, config, output_paths),
        ),
        (
            "rate_conflict_audit",
            lambda: run_rate_conflict_audit_if_enabled(report, config, output_paths),
        ),
        (
            "ratecon_shadow_audit",
            lambda: run_ratecon_shadow_audit_if_enabled(report, config, output_paths),
        ),
        (
            "stop_provenance_report",
            lambda: run_stop_provenance_report_if_enabled(report, config, output_paths),
        ),
        (
            "layout_diagnostics",
            lambda: run_layout_diagnostics_if_enabled(report, config, output_paths),
        ),
    ]
    results = [
        runner()
        for task_name, runner in task_runners
        if task_name in task_plan
    ]
    return [result for result in results if result is not None]
