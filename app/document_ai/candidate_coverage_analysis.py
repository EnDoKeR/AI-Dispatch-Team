"""Safe candidate coverage analysis contracts.

Coverage analysis tracks where candidate evidence exists or disappears across
the stop-span extraction pipeline. It is count/status only and must not expose
private values.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path

from app.document_ai.local_review_analysis import (
    LocalReviewAnalysisError,
    load_field_review_csv,
    load_stop_review_csv,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)
from app.document_ai.ratecon_candidates import normalize_list
from app.document_ai.core_field_gap_analysis import analyze_core_field_gaps_from_rows
from app.document_ai.ratecon_review_workbook import (
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    SHEET_DOCUMENT_SUMMARY,
    SHEET_FIELD_REVIEW,
    SHEET_RATE_REVIEW,
    SHEET_STOP_REVIEW,
    build_ratecon_review_rows,
)


COVERAGE_STAGE_LAYOUT_LINE = "layout_line"
COVERAGE_STAGE_LINE_FEATURE = "line_feature"
COVERAGE_STAGE_STOP_ANCHOR = "stop_anchor"
COVERAGE_STAGE_STOP_SPAN = "stop_span"
COVERAGE_STAGE_SPAN_FIELD_CANDIDATE = "span_field_candidate"
COVERAGE_STAGE_NORMALIZED_STOP_FIELD = "normalized_stop_field"
COVERAGE_STAGE_CORE_FIELD_MAPPING = "core_field_mapping"
COVERAGE_STAGE_REVIEW_ROW = "review_row"

CANDIDATE_COVERAGE_STAGES = {
    COVERAGE_STAGE_LAYOUT_LINE,
    COVERAGE_STAGE_LINE_FEATURE,
    COVERAGE_STAGE_STOP_ANCHOR,
    COVERAGE_STAGE_STOP_SPAN,
    COVERAGE_STAGE_SPAN_FIELD_CANDIDATE,
    COVERAGE_STAGE_NORMALIZED_STOP_FIELD,
    COVERAGE_STAGE_CORE_FIELD_MAPPING,
    COVERAGE_STAGE_REVIEW_ROW,
}

COVERAGE_STATUS_PRESENT = "present"
COVERAGE_STATUS_MISSING = "missing"
COVERAGE_STATUS_FILTERED = "filtered"
COVERAGE_STATUS_NON_APPLICABLE = "non_applicable"
COVERAGE_STATUS_CONFLICT = "conflict"
COVERAGE_STATUS_LOW_CONFIDENCE = "low_confidence"
COVERAGE_STATUS_REVIEW_REQUIRED = "review_required"
COVERAGE_STATUS_UNKNOWN = "unknown"

CANDIDATE_COVERAGE_STATUSES = {
    COVERAGE_STATUS_PRESENT,
    COVERAGE_STATUS_MISSING,
    COVERAGE_STATUS_FILTERED,
    COVERAGE_STATUS_NON_APPLICABLE,
    COVERAGE_STATUS_CONFLICT,
    COVERAGE_STATUS_LOW_CONFIDENCE,
    COVERAGE_STATUS_REVIEW_REQUIRED,
    COVERAGE_STATUS_UNKNOWN,
}

COVERAGE_GAP_LINE_FEATURE_MISSING = "line_feature_missing"
COVERAGE_GAP_ANCHOR_MISSING = "anchor_missing"
COVERAGE_GAP_SPAN_MISSING = "span_missing"
COVERAGE_GAP_SPAN_BOUNDARY_EXCLUDED_LINE = "span_boundary_excluded_line"
COVERAGE_GAP_CANDIDATE_NOT_GENERATED = "candidate_not_generated"
COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED = "candidate_generated_but_not_normalized"
COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED = "normalized_but_not_core_mapped"
COVERAGE_GAP_IDENTIFIER_LABEL_MISSING = "identifier_label_missing"
COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED = "identifier_candidate_not_generated"
COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND = "only_non_primary_reference_found"
COVERAGE_GAP_CONFLICTING_PRIMARY_IDENTIFIERS = "conflicting_primary_identifiers"
COVERAGE_GAP_WEAK_GENERIC_REFERENCE_REVIEW_REQUIRED = (
    "weak_generic_reference_review_required"
)
COVERAGE_GAP_SCOPE_FILTERED = "scope_filtered"
COVERAGE_GAP_NON_APPLICABLE = "non_applicable"
COVERAGE_GAP_OCR_NEEDED = "ocr_needed"
COVERAGE_GAP_POLICY_EXCLUDED = "policy_excluded"
COVERAGE_GAP_UNKNOWN = "unknown"

CANDIDATE_COVERAGE_GAP_REASONS = {
    COVERAGE_GAP_LINE_FEATURE_MISSING,
    COVERAGE_GAP_ANCHOR_MISSING,
    COVERAGE_GAP_SPAN_MISSING,
    COVERAGE_GAP_SPAN_BOUNDARY_EXCLUDED_LINE,
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED,
    COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED,
    COVERAGE_GAP_IDENTIFIER_LABEL_MISSING,
    COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND,
    COVERAGE_GAP_CONFLICTING_PRIMARY_IDENTIFIERS,
    COVERAGE_GAP_WEAK_GENERIC_REFERENCE_REVIEW_REQUIRED,
    COVERAGE_GAP_SCOPE_FILTERED,
    COVERAGE_GAP_NON_APPLICABLE,
    COVERAGE_GAP_OCR_NEEDED,
    COVERAGE_GAP_POLICY_EXCLUDED,
    COVERAGE_GAP_UNKNOWN,
}

CANDIDATE_COVERAGE_ANALYSIS_VERSION = "candidate_coverage_analysis_v1"
CANDIDATE_COVERAGE_JSON = "candidate_coverage.json"
CANDIDATE_COVERAGE_MD = "candidate_coverage.md"
CANDIDATE_COVERAGE_ANALYSIS_JSON = "candidate_coverage_analysis.json"
CANDIDATE_COVERAGE_ANALYSIS_MD = "candidate_coverage_analysis.md"

MISSING_CANDIDATE_GAP_REASONS = {
    COVERAGE_GAP_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED,
    COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND,
}

STOP_COVERAGE_FIELDS = {
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
}

CORE_COVERAGE_FIELDS = STOP_COVERAGE_FIELDS | {
    "broker_name",
    "load_number",
    "rate",
}

FIELD_TO_SPAN_FIELDS = {
    "pickup_location": ("location",),
    "delivery_location": ("location",),
    "pickup_date": ("date",),
    "delivery_date": ("date",),
    "pickup_time": ("time", "appointment_window"),
    "delivery_time": ("time", "appointment_window"),
}

FIELD_TO_LABEL_CATEGORIES = {
    "pickup_location": ("location", "pickup"),
    "delivery_location": ("location", "delivery"),
    "pickup_date": ("date", "pickup"),
    "delivery_date": ("date", "delivery"),
    "pickup_time": ("time", "pickup"),
    "delivery_time": ("time", "delivery"),
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_count_map(value):
    if not isinstance(value, dict):
        return {}
    return {
        _token(key): _int(count)
        for key, count in value.items()
        if _token(key)
    }


def normalize_coverage_stage(value):
    token = _token(value)
    return token if token in CANDIDATE_COVERAGE_STAGES else COVERAGE_STAGE_REVIEW_ROW


def normalize_coverage_status(value):
    token = _token(value)
    return token if token in CANDIDATE_COVERAGE_STATUSES else COVERAGE_STATUS_UNKNOWN


def normalize_coverage_gap_reason(value):
    token = _token(value)
    return token if token in CANDIDATE_COVERAGE_GAP_REASONS else COVERAGE_GAP_UNKNOWN


def recommended_fix_bucket_for_coverage(field_name, gap_reason):
    field = _token(field_name)
    reason = normalize_coverage_gap_reason(gap_reason)
    if reason == COVERAGE_GAP_OCR_NEEDED:
        return "ocr_queue"
    if reason == COVERAGE_GAP_SCOPE_FILTERED:
        return "scope_filter_review"
    if reason == COVERAGE_GAP_NON_APPLICABLE:
        return "local_human_review"
    if reason == COVERAGE_GAP_SPAN_BOUNDARY_EXCLUDED_LINE:
        return "stop_span_boundary_expansion"
    if reason == COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED:
        return "normalized_stop_field_mapping"
    if reason == COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED:
        return "normalized_to_core_field_mapping"
    if reason in {
        COVERAGE_GAP_IDENTIFIER_LABEL_MISSING,
        COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED,
        COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND,
        COVERAGE_GAP_CONFLICTING_PRIMARY_IDENTIFIERS,
        COVERAGE_GAP_WEAK_GENERIC_REFERENCE_REVIEW_REQUIRED,
    }:
        return "load_identifier_candidate_generation"
    if field in {"pickup_location", "delivery_location"}:
        return "stop_span_location_candidate_generation"
    if field in {"pickup_date", "delivery_date", "pickup_time", "delivery_time"}:
        return "stop_span_date_candidate_generation"
    if field == "load_number":
        return "load_identifier_candidate_generation"
    if field == "broker_name":
        return "broker_identity_candidate_generation"
    if field == "rate":
        return "rate_candidate_generation_or_resolution"
    return "local_human_review"


def build_candidate_coverage_record(
    measurement_alias="",
    field_name="unknown",
    stage=COVERAGE_STAGE_REVIEW_ROW,
    status=COVERAGE_STATUS_UNKNOWN,
    gap_reason=COVERAGE_GAP_UNKNOWN,
    candidate_count=0,
    normalized_field_count=0,
    review_row_count=0,
    evidence_type_counts=None,
    warning_codes=None,
    recommended_fix_bucket="",
):
    field = _token(field_name) or "unknown"
    reason = normalize_coverage_gap_reason(gap_reason)
    return {
        "measurement_alias": _text(measurement_alias),
        "field_name": field,
        "stage": normalize_coverage_stage(stage),
        "status": normalize_coverage_status(status),
        "gap_reason": reason,
        "candidate_count": _int(candidate_count),
        "normalized_field_count": _int(normalized_field_count),
        "review_row_count": _int(review_row_count),
        "evidence_type_counts": _normalize_count_map(evidence_type_counts),
        "warning_codes": normalize_list(warning_codes),
        "recommended_fix_bucket": _text(recommended_fix_bucket)
        or recommended_fix_bucket_for_coverage(field, reason),
    }


def _sorted_counter(counter):
    return {
        key: count
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    }


def _aliases_by(records, key_name):
    grouped = defaultdict(set)
    for record in records or []:
        alias = _text((record or {}).get("measurement_alias"))
        key = _text((record or {}).get(key_name))
        if alias and key:
            grouped[key].add(alias)
    return {key: sorted(values) for key, values in sorted(grouped.items())}


def _top_fix_bucket(records):
    counts = Counter(
        (record or {}).get("recommended_fix_bucket", "local_human_review")
        for record in records or []
        if (record or {}).get("gap_reason")
        not in {
            COVERAGE_GAP_NON_APPLICABLE,
            COVERAGE_GAP_POLICY_EXCLUDED,
            COVERAGE_GAP_UNKNOWN,
        }
    )
    if not counts:
        return "local_human_review"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def build_candidate_coverage_aggregate(records, document_count=0):
    normalized_records = [
        build_candidate_coverage_record(**record)
        if isinstance(record, dict)
        else build_candidate_coverage_record()
        for record in records or []
    ]
    field_counts = Counter(record["field_name"] for record in normalized_records)
    stage_counts = Counter(record["stage"] for record in normalized_records)
    reason_counts = Counter(record["gap_reason"] for record in normalized_records)
    missing_candidate_fields = Counter(
        record["field_name"]
        for record in normalized_records
        if record["gap_reason"] in MISSING_CANDIDATE_GAP_REASONS
    )
    return {
        "document_count": _int(document_count),
        "coverage_counts_by_field": _sorted_counter(field_counts),
        "coverage_counts_by_stage": _sorted_counter(stage_counts),
        "gap_reason_counts": _sorted_counter(reason_counts),
        "aliases_by_gap_reason": _aliases_by(normalized_records, "gap_reason"),
        "top_missing_candidate_fields": list(
            _sorted_counter(missing_candidate_fields).keys()
        )[:10],
        "top_gap_reasons": list(_sorted_counter(reason_counts).keys())[:10],
        "recommended_next_fix": _top_fix_bucket(normalized_records),
        "analysis_version": CANDIDATE_COVERAGE_ANALYSIS_VERSION,
    }


def build_candidate_coverage_result(records=None, document_count=0):
    normalized_records = [
        build_candidate_coverage_record(**record)
        if isinstance(record, dict)
        else build_candidate_coverage_record()
        for record in records or []
    ]
    return {
        "records": normalized_records,
        "aggregate": build_candidate_coverage_aggregate(
            normalized_records,
            document_count=document_count,
        ),
        "analysis_version": CANDIDATE_COVERAGE_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
    }


def _read_json(path, default=None):
    file_path = Path(path)
    if not file_path.exists():
        return default
    return json.loads(file_path.read_text(encoding="utf-8"))


def _rows_by_alias(rows):
    return {
        _text(row.get("document_alias")): row
        for row in rows or []
        if isinstance(row, dict) and _text(row.get("document_alias"))
    }


def _review_row_counts_by_field(field_rows=None, stop_rows=None):
    counts = Counter()
    for row in field_rows or []:
        alias = _text(row.get("Measurement Alias"))
        field = _token(row.get("Field Name"))
        if alias and field:
            counts[(alias, field)] += 1
    for row in stop_rows or []:
        alias = _text(row.get("Measurement Alias"))
        field = _stop_review_core_field(row.get("Stop Type"), row.get("Field Name"))
        if alias and field:
            counts[(alias, field)] += 1
    return counts


def _stop_review_core_field(stop_type, field_name):
    stop_type_token = _token(stop_type)
    field_token = _token(field_name)
    if field_token == "location" and stop_type_token == "pickup":
        return "pickup_location"
    if field_token == "location" and stop_type_token == "delivery":
        return "delivery_location"
    if field_token == "date" and stop_type_token == "pickup":
        return "pickup_date"
    if field_token == "date" and stop_type_token == "delivery":
        return "delivery_date"
    if field_token in {"time", "appointment_window"} and stop_type_token == "pickup":
        return "pickup_time"
    if field_token in {"time", "appointment_window"} and stop_type_token == "delivery":
        return "delivery_time"
    return ""


def _core_gap_records(input_dir):
    payload = _read_json(Path(input_dir) / "core_field_gap_analysis.json", default={}) or {}
    return [
        record
        for record in payload.get("records", []) or []
        if isinstance(record, dict)
        and _token(record.get("field_name")) in CORE_COVERAGE_FIELDS
    ]


def _safe_summary_rows(input_dir):
    payload = _read_json(Path(input_dir) / "safe_summary.json", default={}) or {}
    return [
        row
        for row in payload.get("rows", []) or []
        if isinstance(row, dict)
    ]


def _sum_counts(counts, keys):
    return sum(_int((counts or {}).get(key)) for key in keys)


def _field_status(row, field_name):
    for field in (row or {}).get("field_statuses", []) or []:
        if isinstance(field, dict) and _token(field.get("field_name")) == field_name:
            return _token(field.get("status"))
    return ""


def _is_ocr_row(row):
    return _token((row or {}).get("extraction_status")) == "empty_text"


def _is_non_applicable_record(record):
    return _token((record or {}).get("gap_reason")) in {
        COVERAGE_GAP_NON_APPLICABLE,
        "non_applicable",
    }


def _is_policy_excluded_record(record):
    return _token((record or {}).get("gap_reason")) in {
        COVERAGE_GAP_POLICY_EXCLUDED,
        "optional_missing_field",
    }


def _coverage_record_from_core_gap(record, row, review_counts):
    alias = _text(record.get("measurement_alias"))
    field = _token(record.get("field_name"))
    metrics = (row or {}).get("stop_span_coverage_metrics", {}) or {}
    load_identifier_metrics = (row or {}).get("load_identifier_coverage_metrics", {}) or {}
    candidate_counts = (row or {}).get("candidate_counts_by_field", {}) or {}
    span_fields = FIELD_TO_SPAN_FIELDS.get(field, ())
    label_categories = FIELD_TO_LABEL_CATEGORIES.get(field, ())
    line_feature_count = _sum_counts(
        metrics.get("line_feature_count_by_label_category", {}),
        label_categories,
    )
    anchor_count = sum(_int(count) for count in (metrics.get("anchor_count_by_type", {}) or {}).values())
    span_count = sum(_int(count) for count in (metrics.get("span_count_by_type", {}) or {}).values())
    span_candidate_count = _sum_counts(
        metrics.get("span_field_candidate_count_by_field", {}),
        span_fields,
    )
    normalized_count = _sum_counts(
        metrics.get("normalized_stop_field_count_by_field", {}),
        span_fields,
    )
    core_mapping_count = _int(
        (metrics.get("core_field_mapping_count_by_field", {}) or {}).get(field)
    )
    evidence_type_counts = {}
    if field == "load_number":
        identifier_label_count = _int(
            load_identifier_metrics.get("identifier_label_feature_count")
        )
        primary_identifier_count = _int(
            load_identifier_metrics.get("primary_identifier_candidate_count")
        )
        typed_reference_count = _int(
            load_identifier_metrics.get("typed_reference_candidate_count")
        )
        rejected_reference_count = _int(
            load_identifier_metrics.get("rejected_reference_as_load_id_count")
        )
        conflicting_identifier_count = _int(
            load_identifier_metrics.get("conflicting_primary_identifiers")
        )
        weak_reference_count = _int(
            load_identifier_metrics.get("weak_generic_reference_review_required")
        )
        span_candidate_count = primary_identifier_count
        normalized_count = 0
        core_mapping_count = _int(
            load_identifier_metrics.get("core_load_number_mapping_count")
        )
        evidence_type_counts = {
            "identifier_label_feature_count": identifier_label_count,
            "primary_identifier_candidate_count": primary_identifier_count,
            "typed_reference_candidate_count": typed_reference_count,
            "rejected_reference_as_load_id_count": rejected_reference_count,
            "conflicting_primary_identifiers": conflicting_identifier_count,
            "weak_generic_reference_review_required": weak_reference_count,
        }
    elif field not in STOP_COVERAGE_FIELDS:
        span_candidate_count = _int(candidate_counts.get(field))
        normalized_count = 0
        core_mapping_count = 1 if _field_status(row, field) in {"resolved", "needs_review", "conflict", "low_confidence"} else 0
    review_row_count = _int(review_counts.get((alias, field)))

    if _is_ocr_row(row):
        return build_candidate_coverage_record(
            measurement_alias=alias,
            field_name=field,
            stage=COVERAGE_STAGE_LAYOUT_LINE,
            status=COVERAGE_STATUS_FILTERED,
            gap_reason=COVERAGE_GAP_OCR_NEEDED,
            review_row_count=review_row_count,
        )
    if _is_non_applicable_record(record):
        return build_candidate_coverage_record(
            measurement_alias=alias,
            field_name=field,
            stage=COVERAGE_STAGE_REVIEW_ROW,
            status=COVERAGE_STATUS_NON_APPLICABLE,
            gap_reason=COVERAGE_GAP_NON_APPLICABLE,
            review_row_count=review_row_count,
        )
    if _is_policy_excluded_record(record):
        return build_candidate_coverage_record(
            measurement_alias=alias,
            field_name=field,
            stage=COVERAGE_STAGE_REVIEW_ROW,
            status=COVERAGE_STATUS_FILTERED,
            gap_reason=COVERAGE_GAP_POLICY_EXCLUDED,
            review_row_count=review_row_count,
        )

    status = _token(record.get("status"))
    if field in STOP_COVERAGE_FIELDS:
        if line_feature_count == 0:
            stage = COVERAGE_STAGE_LINE_FEATURE
            reason = COVERAGE_GAP_LINE_FEATURE_MISSING
        elif anchor_count == 0:
            stage = COVERAGE_STAGE_STOP_ANCHOR
            reason = COVERAGE_GAP_ANCHOR_MISSING
        elif span_count == 0:
            stage = COVERAGE_STAGE_STOP_SPAN
            reason = COVERAGE_GAP_SPAN_MISSING
        elif span_candidate_count == 0:
            stage = COVERAGE_STAGE_SPAN_FIELD_CANDIDATE
            reason = COVERAGE_GAP_CANDIDATE_NOT_GENERATED
        elif normalized_count == 0:
            stage = COVERAGE_STAGE_NORMALIZED_STOP_FIELD
            reason = COVERAGE_GAP_CANDIDATE_GENERATED_BUT_NOT_NORMALIZED
        elif core_mapping_count == 0:
            stage = COVERAGE_STAGE_CORE_FIELD_MAPPING
            reason = COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED
        else:
            stage = COVERAGE_STAGE_REVIEW_ROW
            reason = COVERAGE_GAP_UNKNOWN
    elif field == "load_number":
        if span_candidate_count == 0:
            stage = COVERAGE_STAGE_REVIEW_ROW
            if typed_reference_count > 0:
                reason = COVERAGE_GAP_ONLY_NON_PRIMARY_REFERENCE_FOUND
            elif identifier_label_count == 0:
                reason = COVERAGE_GAP_IDENTIFIER_LABEL_MISSING
            else:
                reason = COVERAGE_GAP_IDENTIFIER_CANDIDATE_NOT_GENERATED
        elif core_mapping_count == 0:
            stage = COVERAGE_STAGE_CORE_FIELD_MAPPING
            if conflicting_identifier_count > 0:
                reason = COVERAGE_GAP_CONFLICTING_PRIMARY_IDENTIFIERS
            elif weak_reference_count > 0:
                reason = COVERAGE_GAP_WEAK_GENERIC_REFERENCE_REVIEW_REQUIRED
            else:
                reason = COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED
        else:
            stage = COVERAGE_STAGE_REVIEW_ROW
            reason = COVERAGE_GAP_UNKNOWN
    else:
        if span_candidate_count == 0:
            stage = COVERAGE_STAGE_REVIEW_ROW
            reason = COVERAGE_GAP_CANDIDATE_NOT_GENERATED
        elif core_mapping_count == 0:
            stage = COVERAGE_STAGE_CORE_FIELD_MAPPING
            reason = COVERAGE_GAP_NORMALIZED_BUT_NOT_CORE_MAPPED
        else:
            stage = COVERAGE_STAGE_REVIEW_ROW
            reason = COVERAGE_GAP_UNKNOWN

    coverage_status = COVERAGE_STATUS_MISSING
    if status == "conflict":
        coverage_status = COVERAGE_STATUS_CONFLICT
    elif status == "low_confidence":
        coverage_status = COVERAGE_STATUS_LOW_CONFIDENCE
    elif status in {"needs_review", "review_required"}:
        coverage_status = COVERAGE_STATUS_REVIEW_REQUIRED
    elif reason == COVERAGE_GAP_UNKNOWN:
        coverage_status = COVERAGE_STATUS_PRESENT

    return build_candidate_coverage_record(
        measurement_alias=alias,
        field_name=field,
        stage=stage,
        status=coverage_status,
        gap_reason=reason,
        candidate_count=span_candidate_count,
        normalized_field_count=normalized_count,
        review_row_count=review_row_count,
        evidence_type_counts=evidence_type_counts,
        warning_codes=record.get("warning_codes", []),
    )


def load_candidate_coverage_inputs(input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR):
    root = Path(input_dir)
    if not (root / "safe_summary.json").exists():
        raise LocalReviewAnalysisError("missing safe_summary.json")
    return {
        "safe_summary_rows": _safe_summary_rows(root),
        "core_gap_records": _core_gap_records(root),
        "field_rows": load_field_review_csv(root / REVIEW_FIELD_REVIEW_CSV)
        if (root / REVIEW_FIELD_REVIEW_CSV).exists()
        else [],
        "stop_rows": load_stop_review_csv(root / REVIEW_STOP_REVIEW_CSV)
        if (root / REVIEW_STOP_REVIEW_CSV).exists()
        else [],
    }


def analyze_candidate_coverage_from_rows(
    safe_summary_rows,
    core_gap_records=None,
    field_rows=None,
    stop_rows=None,
):
    rows_by_alias = _rows_by_alias(safe_summary_rows)
    review_counts = _review_row_counts_by_field(field_rows, stop_rows)
    records = []
    for record in core_gap_records or []:
        alias = _text(record.get("measurement_alias"))
        row = rows_by_alias.get(alias, {})
        records.append(_coverage_record_from_core_gap(record, row, review_counts))
    return build_candidate_coverage_result(
        records,
        document_count=len(safe_summary_rows or []),
    )


def analyze_candidate_coverage(input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR):
    artifact = _read_json(Path(input_dir) / CANDIDATE_COVERAGE_JSON, default=None)
    if isinstance(artifact, dict) and "records" in artifact and "aggregate" in artifact:
        return build_candidate_coverage_result(
            artifact.get("records", []),
            document_count=(artifact.get("aggregate", {}) or {}).get("document_count", 0),
        )
    inputs = load_candidate_coverage_inputs(input_dir)
    return analyze_candidate_coverage_from_rows(**inputs)


def analyze_candidate_coverage_from_measurement_rows(
    measurement_rows,
    review_rows_by_sheet=None,
):
    rows_by_sheet = review_rows_by_sheet or build_ratecon_review_rows(
        measurement_rows,
        include_private_values=False,
    )
    core_analysis = analyze_core_field_gaps_from_rows(
        document_rows=rows_by_sheet.get(SHEET_DOCUMENT_SUMMARY, []),
        stop_rows=rows_by_sheet.get(SHEET_STOP_REVIEW, []),
        field_rows=rows_by_sheet.get(SHEET_FIELD_REVIEW, []),
        rate_rows=rows_by_sheet.get(SHEET_RATE_REVIEW, []),
        safe_summary_rows=measurement_rows,
    )
    return analyze_candidate_coverage_from_rows(
        measurement_rows,
        core_gap_records=core_analysis.get("records", []),
        field_rows=rows_by_sheet.get(SHEET_FIELD_REVIEW, []),
        stop_rows=rows_by_sheet.get(SHEET_STOP_REVIEW, []),
    )


def candidate_coverage_markdown_lines(analysis):
    aggregate = (analysis or {}).get("aggregate", {})
    lines = [
        "# Candidate Coverage Analysis",
        "",
        "Local-only analysis. Safe to share: aliases, counts, statuses, fields, stages, and gap reasons.",
        "Do not share private values, raw text, filenames, local paths, rates, addresses, references, or broker identifiers.",
        "",
        f"Documents analyzed: {aggregate.get('document_count', 0)}",
        f"Recommended next fix: {aggregate.get('recommended_next_fix', 'local_human_review')}",
        "",
        "## Top Missing Candidate Fields",
    ]
    for field_name in aggregate.get("top_missing_candidate_fields", []) or []:
        count = aggregate.get("coverage_counts_by_field", {}).get(field_name, 0)
        lines.append(f"- {field_name}: {count}")
    lines.extend(["", "## Coverage Stages"])
    for stage, count in (aggregate.get("coverage_counts_by_stage", {}) or {}).items():
        lines.append(f"- {stage}: {count}")
    lines.extend(["", "## Gap Reasons"])
    for reason, count in (aggregate.get("gap_reason_counts", {}) or {}).items():
        lines.append(f"- {reason}: {count}")
    return lines


def write_candidate_coverage_json(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "json": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_candidate_coverage_md(analysis, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(candidate_coverage_markdown_lines(analysis)) + "\n", encoding="utf-8")
    return {
        "md": path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_candidate_coverage_artifacts(
    analysis,
    output_dir=None,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    json_result = write_candidate_coverage_json(
        analysis,
        output_root / CANDIDATE_COVERAGE_JSON,
    )
    md_result = write_candidate_coverage_md(
        analysis,
        output_root / CANDIDATE_COVERAGE_MD,
    )
    return {
        "paths": {
            "candidate_coverage_json": output_root / CANDIDATE_COVERAGE_JSON,
            "candidate_coverage_md": output_root / CANDIDATE_COVERAGE_MD,
        },
        "aggregate": (analysis or {}).get("aggregate", {}),
        "private_values_printed": bool(
            json_result.get("private_values_printed")
            or md_result.get("private_values_printed")
        ),
        "raw_text_printed": bool(
            json_result.get("raw_text_printed")
            or md_result.get("raw_text_printed")
        ),
    }
