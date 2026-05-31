"""Safe candidate coverage analysis contracts.

Coverage analysis tracks where candidate evidence exists or disappears across
the stop-span extraction pipeline. It is count/status only and must not expose
private values.
"""

from collections import Counter, defaultdict

from app.document_ai.ratecon_candidates import normalize_list


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

STOP_COVERAGE_FIELDS = {
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
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
        not in {COVERAGE_GAP_NON_APPLICABLE, COVERAGE_GAP_POLICY_EXCLUDED}
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
        if record["gap_reason"] == COVERAGE_GAP_CANDIDATE_NOT_GENERATED
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
