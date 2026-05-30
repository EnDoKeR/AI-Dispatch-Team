"""Safe output writers for private RateCon measurement summaries."""

import csv
import json
from pathlib import Path


DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_measurement")

SAFE_SUMMARY_JSON = "safe_summary.json"
SAFE_SUMMARY_CSV = "safe_summary.csv"
SAFE_AGGREGATE_JSON = "safe_aggregate.json"
SAFE_AGGREGATE_MD = "safe_aggregate.md"
VALUE_REVIEW_TEMPLATE_CSV = "value_review_template.csv"

SAFE_CSV_COLUMNS = [
    "document_alias",
    "page_count",
    "char_count",
    "triage_route",
    "extraction_status",
    "has_text_layer",
    "likely_image_based",
    "template_status",
    "selected_template_id",
    "template_source",
    "template_confidence_bucket",
    "document_type",
    "ratecon_eligible",
    "extraction_relevant",
    "normal_load_movement",
    "supplemental_only",
    "classification_status",
    "skipped_by_scope",
    "review_required",
    "missing_fields",
    "unresolved_fields",
    "needs_check_fields",
    "low_confidence_fields",
    "conflict_fields",
    "non_applicable_fields",
    "skipped_fields",
    "blocker_categories",
    "candidate_counts_summary",
    "warning_codes",
]

VALUE_REVIEW_TEMPLATE_COLUMNS = [
    "document_alias",
    "user_checked",
    "actual_field_correct_yes_no_unknown",
    "safe_feedback",
    "private_note_do_not_share",
]


class PrivateMeasurementOutputError(ValueError):
    """Raised when output settings could leak private measurement artifacts."""


def _normalize_output_dir(output_dir=None, allow_custom_output_dir=False):
    path = Path(output_dir) if output_dir else DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR

    if output_dir and not allow_custom_output_dir:
        default_parts = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR.parts
        if path.parts[: len(default_parts)] != default_parts:
            raise PrivateMeasurementOutputError(
                "custom output directory requires allow_custom_output_dir=True"
            )

    path.mkdir(parents=True, exist_ok=True)
    return path


def _join(values):
    return ";".join(str(value) for value in values or [] if str(value))


def _candidate_counts_summary(counts):
    return ";".join(
        f"{field_name}={count}"
        for field_name, count in sorted((counts or {}).items())
    )


def _safe_csv_row(row):
    return {
        "document_alias": row.get("document_alias", ""),
        "page_count": row.get("page_count", 0),
        "char_count": row.get("char_count", 0),
        "triage_route": row.get("triage_route", ""),
        "extraction_status": row.get("extraction_status", ""),
        "has_text_layer": row.get("has_text_layer", False),
        "likely_image_based": row.get("likely_image_based", False),
        "template_status": row.get("template_status", ""),
        "selected_template_id": row.get("selected_template_id", ""),
        "template_source": row.get("template_source", ""),
        "template_confidence_bucket": row.get("template_confidence_bucket", ""),
        "document_type": row.get("document_type", ""),
        "ratecon_eligible": row.get("ratecon_eligible", False),
        "extraction_relevant": row.get("extraction_relevant", False),
        "normal_load_movement": row.get("normal_load_movement", False),
        "supplemental_only": row.get("supplemental_only", False),
        "classification_status": row.get("classification_status", ""),
        "skipped_by_scope": row.get("skipped_by_scope", False),
        "review_required": row.get("review_required", False),
        "missing_fields": _join(row.get("missing_fields", [])),
        "unresolved_fields": _join(row.get("unresolved_fields", [])),
        "needs_check_fields": _join(row.get("needs_check_fields", [])),
        "low_confidence_fields": _join(row.get("low_confidence_fields", [])),
        "conflict_fields": _join(row.get("conflict_fields", [])),
        "non_applicable_fields": _join(row.get("non_applicable_fields", [])),
        "skipped_fields": _join(row.get("skipped_fields", [])),
        "blocker_categories": _join(row.get("blocker_categories", [])),
        "candidate_counts_summary": _candidate_counts_summary(
            row.get("candidate_counts_by_field", {})
        ),
        "warning_codes": _join(row.get("warning_codes", [])),
    }


def _assert_safe_payload(payload):
    forbidden_keys = ["raw_text", "private_text", "selected_candidate_value"]

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key) in forbidden_keys:
                    raise PrivateMeasurementOutputError(
                        f"unsafe output field detected: {key}"
                    )
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)


def write_safe_summary_json(rows, aggregate, output_dir=None, allow_custom_output_dir=False):
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    payload = {
        "local_only": True,
        "private_values_redacted": True,
        "raw_text_saved": False,
        "rows": rows or [],
        "aggregate": aggregate or {},
    }
    _assert_safe_payload(payload)
    path = directory / SAFE_SUMMARY_JSON
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_safe_summary_csv(rows, output_dir=None, allow_custom_output_dir=False):
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    path = directory / SAFE_SUMMARY_CSV

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SAFE_CSV_COLUMNS)
        writer.writeheader()
        for row in rows or []:
            writer.writerow(_safe_csv_row(row))

    return path


def write_safe_aggregate_json(aggregate, output_dir=None, allow_custom_output_dir=False):
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    payload = {
        "local_only": True,
        "private_values_redacted": True,
        "raw_text_saved": False,
        "aggregate": aggregate or {},
    }
    _assert_safe_payload(payload)
    path = directory / SAFE_AGGREGATE_JSON
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_safe_aggregate_md(aggregate, output_dir=None, allow_custom_output_dir=False):
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    path = directory / SAFE_AGGREGATE_MD
    lines = [
        "# Safe Private RateCon Measurement Aggregate",
        "",
        "Local-only summary. No raw text or private values included.",
        "",
        f"- document_count: {aggregate.get('document_count', 0)}",
        f"- total_documents: {aggregate.get('total_documents', aggregate.get('document_count', 0))}",
        f"- empty_text_count: {aggregate.get('empty_text_count', 0)}",
        f"- ocr_needed_count: {aggregate.get('ocr_needed_count', 0)}",
        f"- text_extracted_count: {aggregate.get('text_extracted_count', 0)}",
        f"- review_required_count: {aggregate.get('review_required_count', 0)}",
        f"- document_type_counts: {aggregate.get('document_type_counts', {})}",
        f"- ratecon_eligible_count: {aggregate.get('ratecon_eligible_count', 0)}",
        f"- extraction_relevant_count: {aggregate.get('extraction_relevant_count', 0)}",
        f"- normal_load_movement_count: {aggregate.get('normal_load_movement_count', 0)}",
        f"- tonu_count: {aggregate.get('tonu_count', 0)}",
        f"- supplemental_only_count: {aggregate.get('supplemental_only_count', 0)}",
        f"- non_ratecon_count: {aggregate.get('non_ratecon_count', 0)}",
        f"- unknown_review_required_count: {aggregate.get('unknown_review_required_count', 0)}",
        f"- classification_status_counts: {aggregate.get('classification_status_counts', {})}",
        f"- page_role_counts: {aggregate.get('page_role_counts', {})}",
        f"- section_role_counts: {aggregate.get('section_role_counts', {})}",
        f"- extraction_scope_counts: {aggregate.get('extraction_scope_counts', {})}",
        f"- blocker_category_counts: {aggregate.get('blocker_category_counts', {})}",
        f"- critical_field_missing_counts: {aggregate.get('critical_field_missing_counts', {})}",
        f"- eligible_critical_field_missing_counts: {aggregate.get('eligible_critical_field_missing_counts', {})}",
        f"- normal_load_critical_field_missing_counts: {aggregate.get('normal_load_critical_field_missing_counts', {})}",
        f"- normal_load_critical_field_denominator: {aggregate.get('normal_load_critical_field_denominator', 0)}",
        f"- unresolved_counts_by_field: {aggregate.get('unresolved_counts_by_field', {})}",
        f"- low_confidence_counts_by_field: {aggregate.get('low_confidence_counts_by_field', {})}",
        f"- non_applicable_counts_by_field: {aggregate.get('non_applicable_counts_by_field', {})}",
        f"- skipped_counts_by_field: {aggregate.get('skipped_counts_by_field', {})}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_value_review_template_csv(rows, output_dir=None, allow_custom_output_dir=False):
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    path = directory / VALUE_REVIEW_TEMPLATE_CSV

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VALUE_REVIEW_TEMPLATE_COLUMNS)
        writer.writeheader()
        for row in rows or []:
            writer.writerow(
                {
                    "document_alias": row.get("document_alias", ""),
                    "user_checked": "",
                    "actual_field_correct_yes_no_unknown": "",
                    "safe_feedback": "",
                    "private_note_do_not_share": "",
                }
            )

    return path


def write_private_measurement_outputs(
    rows,
    aggregate,
    output_dir=None,
    write_json=False,
    write_csv=False,
    write_md=False,
    write_value_review_template=False,
    allow_custom_output_dir=False,
):
    paths = {}

    if write_json:
        paths["safe_summary_json"] = str(
            write_safe_summary_json(rows, aggregate, output_dir, allow_custom_output_dir)
        )
        paths["safe_aggregate_json"] = str(
            write_safe_aggregate_json(aggregate, output_dir, allow_custom_output_dir)
        )

    if write_csv:
        paths["safe_summary_csv"] = str(
            write_safe_summary_csv(rows, output_dir, allow_custom_output_dir)
        )

    if write_md:
        paths["safe_aggregate_md"] = str(
            write_safe_aggregate_md(aggregate, output_dir, allow_custom_output_dir)
        )

    if write_value_review_template:
        paths["value_review_template_csv"] = str(
            write_value_review_template_csv(rows, output_dir, allow_custom_output_dir)
        )

    return {
        "output_dir": str(_normalize_output_dir(output_dir, allow_custom_output_dir)),
        "paths": paths,
        "local_only": True,
        "private_values_redacted": True,
        "raw_text_saved": False,
    }
