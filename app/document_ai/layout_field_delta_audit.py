"""Safe local-only audit report for layout field deltas.

The audit consumes already-redacted measurement rows. It never needs raw text,
filenames, paths, or private field values.
"""

from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    PrivateMeasurementOutputError,
)


LAYOUT_FIELD_DELTA_AUDIT_MD = "layout_field_delta_audit.md"

DELTA_IMPROVED = "improved"
DELTA_WORSENED = "worsened"
DELTA_UNCHANGED = "unchanged"
DELTA_NEWLY_CONFLICTING = "newly_conflicting"
DELTA_NEWLY_RESOLVED = "newly_resolved"
DELTA_STILL_UNRESOLVED = "still_unresolved"

DEBUG_BUCKET_STOP_ASSOCIATION = "stop_association"
DEBUG_BUCKET_DATE_TIME_ASSOCIATION = "date_time_association"
DEBUG_BUCKET_RATE_BREAKDOWN = "rate_breakdown"
DEBUG_BUCKET_BROKER_IDENTITY = "broker_identity"
DEBUG_BUCKET_OPERATIONAL_DETAIL = "operational_detail"
DEBUG_BUCKET_SCOPE_FILTER = "scope_filter"
DEBUG_BUCKET_PROVIDER_QUALITY = "provider_quality"
DEBUG_BUCKET_RESOLVER_SCORING = "resolver_scoring"

FORBIDDEN_AUDIT_KEYS = {
    "raw_text",
    "extracted_text",
    "filename",
    "file_path",
    "local_path",
    "broker_name",
    "broker_mc",
    "rate_value",
    "address",
    "reference_value",
    "private_note",
}

_UNRESOLVED_STATUSES = {
    "",
    "missing",
    "needs_review",
    "low_confidence",
    "conflict",
    "unknown",
    "not_applicable",
}


def _text(value):
    return str(value or "").strip()


def _list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [_text(value)] if _text(value) else []
    return [_text(item) for item in value if _text(item)]


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _field_status_map(row):
    explicit = _mapping(row.get("baseline_field_statuses"))
    result = {
        _text(field): _text(status)
        for field, status in explicit.items()
        if _text(field)
    }

    for summary in row.get("field_statuses", []) or []:
        if not isinstance(summary, dict):
            continue
        field_name = _text(summary.get("field_name"))
        if field_name and field_name not in result:
            result[field_name] = _text(summary.get("status")) or "unknown"
    return result


def _layout_status_map(row):
    return {
        _text(field): _text(status)
        for field, status in _mapping(row.get("layout_field_statuses")).items()
        if _text(field)
    }


def _candidate_count_delta(row, field_name):
    baseline_counts = _mapping(row.get("candidate_counts_by_field"))
    layout_counts = _mapping(row.get("layout_candidate_counts_by_field"))
    return int(layout_counts.get(field_name, 0) or 0) - int(
        baseline_counts.get(field_name, 0) or 0
    )


def _classify_delta(field_name, row, baseline_status, layout_status):
    improved = set(_list(row.get("layout_improved_fields")))
    worsened = set(_list(row.get("layout_worsened_fields")))
    unchanged = set(_list(row.get("layout_unchanged_fields")))

    if layout_status == "conflict" and baseline_status != "conflict":
        return DELTA_NEWLY_CONFLICTING
    if layout_status == "resolved" and baseline_status != "resolved":
        return DELTA_NEWLY_RESOLVED
    if field_name in improved:
        return DELTA_IMPROVED
    if field_name in worsened:
        return DELTA_WORSENED
    if field_name in unchanged:
        if layout_status in _UNRESOLVED_STATUSES and baseline_status in _UNRESOLVED_STATUSES:
            return DELTA_STILL_UNRESOLVED
        return DELTA_UNCHANGED
    if baseline_status in _UNRESOLVED_STATUSES and layout_status in _UNRESOLVED_STATUSES:
        return DELTA_STILL_UNRESOLVED
    return DELTA_UNCHANGED


def _debug_bucket(field_name, row):
    field = _text(field_name).lower()
    warnings = set(_list(row.get("warning_codes")))
    provider_status = _text(row.get("layout_provider_status"))

    if provider_status and provider_status != "success":
        return DEBUG_BUCKET_PROVIDER_QUALITY
    if "skipped_by_scope" in warnings or _text(row.get("skipped_by_scope")) == "True":
        return DEBUG_BUCKET_SCOPE_FILTER
    if field in {"pickup_location", "delivery_location", "stop_reference", "reference"}:
        return DEBUG_BUCKET_STOP_ASSOCIATION
    if field in {"pickup_date", "delivery_date", "pickup_time", "delivery_time"}:
        return DEBUG_BUCKET_DATE_TIME_ASSOCIATION
    if field in {"rate", "linehaul", "accessorial_term", "deduction", "tonu_pay"}:
        return DEBUG_BUCKET_RATE_BREAKDOWN
    if field in {"broker_name", "broker_mc", "carrier_name", "load_number"}:
        return DEBUG_BUCKET_BROKER_IDENTITY
    if field in {
        "equipment",
        "weight",
        "commodity",
        "dimensions",
        "special_requirement",
        "tarp_required",
        "straps_required",
        "chains_required",
        "tracking_required",
    }:
        return DEBUG_BUCKET_OPERATIONAL_DETAIL
    return DEBUG_BUCKET_RESOLVER_SCORING


def build_layout_field_delta_audit(rows):
    entries = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        unsafe_keys = FORBIDDEN_AUDIT_KEYS & set(row)
        if unsafe_keys:
            raise PrivateMeasurementOutputError(
                "unsafe layout field delta audit input field detected: "
                + ", ".join(sorted(unsafe_keys))
            )
        alias = _text(row.get("document_alias"))
        if not alias:
            continue

        baseline_statuses = _field_status_map(row)
        layout_statuses = _layout_status_map(row)
        fields = set(baseline_statuses) | set(layout_statuses)
        fields.update(_list(row.get("layout_improved_fields")))
        fields.update(_list(row.get("layout_worsened_fields")))
        fields.update(_list(row.get("layout_unchanged_fields")))

        for field_name in sorted(field for field in fields if _text(field)):
            baseline_status = baseline_statuses.get(field_name, "unknown")
            layout_status = layout_statuses.get(field_name, baseline_status)
            entries.append(
                {
                    "alias": alias,
                    "field_name": field_name,
                    "baseline_status": baseline_status,
                    "layout_status": layout_status,
                    "delta": _classify_delta(
                        field_name,
                        row,
                        baseline_status,
                        layout_status,
                    ),
                    "candidate_count_delta": _candidate_count_delta(row, field_name),
                    "evidence_type_counts": dict(
                        sorted(_mapping(row.get("layout_evidence_type_counts")).items())
                    ),
                    "warning_codes": sorted(_list(row.get("warning_codes"))),
                    "recommended_debug_bucket": _debug_bucket(field_name, row),
                }
            )

    return {
        "entries": entries,
        "entry_count": len(entries),
        "raw_text_saved": False,
        "private_values_redacted": True,
    }


def _normalize_output_dir(output_dir=None, allow_custom_output_dir=False):
    path = Path(output_dir) if output_dir else DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    if output_dir and not allow_custom_output_dir:
        default_parts = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR.parts
        if path.parts[: len(default_parts)] != default_parts:
            raise PrivateMeasurementOutputError(
                "custom layout field delta audit output directory requires explicit allow flag"
            )
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_layout_field_delta_audit_report(
    rows,
    output_dir=None,
    allow_custom_output_dir=False,
):
    audit = build_layout_field_delta_audit(rows)
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    path = directory / LAYOUT_FIELD_DELTA_AUDIT_MD

    lines = [
        "# Safe Layout Field Delta Audit",
        "",
        "Local-only audit. No raw text, filenames, paths, or private values included.",
        "",
        f"- entry_count: {audit['entry_count']}",
        "",
        "| alias | field_name | baseline_status | layout_status | delta | candidate_count_delta | recommended_debug_bucket | warning_codes | evidence_type_counts |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for entry in audit["entries"]:
        lines.append(
            "| {alias} | {field_name} | {baseline_status} | {layout_status} | {delta} | {candidate_count_delta} | {recommended_debug_bucket} | {warning_codes} | {evidence_type_counts} |".format(
                alias=entry["alias"],
                field_name=entry["field_name"],
                baseline_status=entry["baseline_status"],
                layout_status=entry["layout_status"],
                delta=entry["delta"],
                candidate_count_delta=entry["candidate_count_delta"],
                recommended_debug_bucket=entry["recommended_debug_bucket"],
                warning_codes=";".join(entry["warning_codes"]),
                evidence_type_counts=entry["evidence_type_counts"],
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
