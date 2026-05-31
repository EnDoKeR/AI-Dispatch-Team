"""Safe core-field gap analysis contracts.

This module summarizes local review-output gaps by field, reason, and readiness
level. It must not expose private review values.
"""

from collections import Counter, defaultdict

from app.document_ai.ratecon_candidates import normalize_list


CORE_FIELD_BROKER_NAME = "broker_name"
CORE_FIELD_BROKER_MC = "broker_mc"
CORE_FIELD_LOAD_NUMBER = "load_number"
CORE_FIELD_RATE = "rate"
CORE_FIELD_PICKUP_LOCATION = "pickup_location"
CORE_FIELD_PICKUP_DATE = "pickup_date"
CORE_FIELD_PICKUP_TIME = "pickup_time"
CORE_FIELD_DELIVERY_LOCATION = "delivery_location"
CORE_FIELD_DELIVERY_DATE = "delivery_date"
CORE_FIELD_DELIVERY_TIME = "delivery_time"
CORE_FIELD_EQUIPMENT = "equipment"
CORE_FIELD_WEIGHT = "weight"
CORE_FIELD_COMMODITY = "commodity"
CORE_FIELD_SPECIAL_REQUIREMENT = "special_requirement"
CORE_FIELD_REFERENCE = "reference"
CORE_FIELD_UNKNOWN = "unknown"

CORE_FIELD_NAMES = {
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_LOAD_NUMBER,
    CORE_FIELD_RATE,
    CORE_FIELD_PICKUP_LOCATION,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_DELIVERY_LOCATION,
    CORE_FIELD_DELIVERY_DATE,
    CORE_FIELD_DELIVERY_TIME,
    CORE_FIELD_EQUIPMENT,
    CORE_FIELD_WEIGHT,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_SPECIAL_REQUIREMENT,
    CORE_FIELD_REFERENCE,
    CORE_FIELD_UNKNOWN,
}

CORE_FIELD_GAP_NO_CANDIDATE = "no_candidate"
CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED = "candidate_exists_but_unresolved"
CORE_FIELD_GAP_CONFLICT = "conflict"
CORE_FIELD_GAP_LOW_CONFIDENCE = "low_confidence"
CORE_FIELD_GAP_SCOPE_FILTERED = "scope_filtered"
CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED = "optional_field_misclassified_as_core"
CORE_FIELD_GAP_NON_APPLICABLE = "non_applicable"
CORE_FIELD_GAP_OCR_NEEDED = "ocr_needed"
CORE_FIELD_GAP_REVIEW_REQUIRED = "review_required"
CORE_FIELD_GAP_UNKNOWN = "unknown"

CORE_FIELD_GAP_REASONS = {
    CORE_FIELD_GAP_NO_CANDIDATE,
    CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
    CORE_FIELD_GAP_CONFLICT,
    CORE_FIELD_GAP_LOW_CONFIDENCE,
    CORE_FIELD_GAP_SCOPE_FILTERED,
    CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
    CORE_FIELD_GAP_NON_APPLICABLE,
    CORE_FIELD_GAP_OCR_NEEDED,
    CORE_FIELD_GAP_REVIEW_REQUIRED,
    CORE_FIELD_GAP_UNKNOWN,
}

CORE_FIELD_GAP_ANALYSIS_VERSION = "core_field_gap_analysis_v1"
CORE_FIELD_GAP_ANALYSIS_MD = "core_field_gap_analysis.md"
CORE_FIELD_GAP_ANALYSIS_JSON = "core_field_gap_analysis.json"

INTAKE_CORE_FIELDS = {
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_LOAD_NUMBER,
    CORE_FIELD_RATE,
    CORE_FIELD_PICKUP_LOCATION,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_DELIVERY_LOCATION,
    CORE_FIELD_DELIVERY_DATE,
}

DISPATCH_DECISION_FIELDS = {
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_LOAD_NUMBER,
    CORE_FIELD_RATE,
    CORE_FIELD_PICKUP_LOCATION,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_DELIVERY_LOCATION,
    CORE_FIELD_DELIVERY_DATE,
    CORE_FIELD_DELIVERY_TIME,
    CORE_FIELD_EQUIPMENT,
    CORE_FIELD_WEIGHT,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_SPECIAL_REQUIREMENT,
}

OPTIONAL_FOR_INTAKE_CORE = {
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_DELIVERY_TIME,
    CORE_FIELD_EQUIPMENT,
    CORE_FIELD_WEIGHT,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_SPECIAL_REQUIREMENT,
    CORE_FIELD_REFERENCE,
}

TARGET_PRIORITY = [
    "broker_load_identity_extraction",
    "load_identifier_extraction",
    "rate_resolution_hardening",
    "stop_span_field_mapping",
    "local_human_review",
]


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_core_field_name(value):
    token = _token(value)
    return token if token in CORE_FIELD_NAMES else CORE_FIELD_UNKNOWN


def normalize_core_field_gap_reason(value):
    token = _token(value)
    return token if token in CORE_FIELD_GAP_REASONS else CORE_FIELD_GAP_UNKNOWN


def recommended_fix_bucket_for_field(field_name, gap_reason=CORE_FIELD_GAP_UNKNOWN):
    field = normalize_core_field_name(field_name)
    reason = normalize_core_field_gap_reason(gap_reason)
    if field in {CORE_FIELD_BROKER_NAME, CORE_FIELD_BROKER_MC}:
        return "broker_load_identity_extraction"
    if field in {CORE_FIELD_LOAD_NUMBER, CORE_FIELD_REFERENCE}:
        return "load_identifier_extraction"
    if field == CORE_FIELD_RATE:
        return "rate_resolution_hardening"
    if field in {
        CORE_FIELD_PICKUP_LOCATION,
        CORE_FIELD_PICKUP_DATE,
        CORE_FIELD_PICKUP_TIME,
        CORE_FIELD_DELIVERY_LOCATION,
        CORE_FIELD_DELIVERY_DATE,
        CORE_FIELD_DELIVERY_TIME,
    }:
        return "stop_span_field_mapping"
    if reason == CORE_FIELD_GAP_OCR_NEEDED:
        return "ocr_queue"
    return "local_human_review"


def build_core_field_gap_record(
    measurement_alias="",
    field_name=CORE_FIELD_UNKNOWN,
    status="",
    gap_reason=CORE_FIELD_GAP_UNKNOWN,
    candidate_count=0,
    conflict_count=0,
    confidence_bucket="",
    readiness_blocker=False,
    extraction_review_blocker=False,
    intake_core_blocker=False,
    dispatch_decision_blocker=False,
    warning_codes=None,
    recommended_fix_bucket="",
    safe_notes=None,
):
    field = normalize_core_field_name(field_name)
    reason = normalize_core_field_gap_reason(gap_reason)
    return {
        "measurement_alias": _text(measurement_alias),
        "field_name": field,
        "status": _token(status),
        "gap_reason": reason,
        "candidate_count": _int(candidate_count),
        "conflict_count": _int(conflict_count),
        "confidence_bucket": _token(confidence_bucket),
        "readiness_blocker": bool(readiness_blocker),
        "extraction_review_blocker": bool(extraction_review_blocker),
        "intake_core_blocker": bool(intake_core_blocker),
        "dispatch_decision_blocker": bool(dispatch_decision_blocker),
        "warning_codes": normalize_list(warning_codes),
        "recommended_fix_bucket": _text(recommended_fix_bucket)
        or recommended_fix_bucket_for_field(field, reason),
        "safe_notes": normalize_list(safe_notes),
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
    )
    if not counts:
        return "local_human_review"
    priority = {bucket: index for index, bucket in enumerate(TARGET_PRIORITY)}
    return sorted(
        counts.items(),
        key=lambda item: (-item[1], priority.get(item[0], len(priority)), item[0]),
    )[0][0]


def build_core_field_gap_aggregate(records, document_count=0):
    normalized_records = [
        build_core_field_gap_record(**record)
        if isinstance(record, dict)
        else build_core_field_gap_record()
        for record in records or []
    ]
    gap_counts_by_field = Counter(record["field_name"] for record in normalized_records)
    gap_counts_by_reason = Counter(record["gap_reason"] for record in normalized_records)
    blocker_counts_by_readiness_level = Counter()
    for record in normalized_records:
        if record["extraction_review_blocker"]:
            blocker_counts_by_readiness_level["extraction_review"] += 1
        if record["intake_core_blocker"]:
            blocker_counts_by_readiness_level["intake_core"] += 1
        if record["dispatch_decision_blocker"]:
            blocker_counts_by_readiness_level["dispatch_decision"] += 1

    conflict_fields = Counter(
        record["field_name"]
        for record in normalized_records
        if record["gap_reason"] == CORE_FIELD_GAP_CONFLICT
    )
    top_core_field_gaps = list(_sorted_counter(gap_counts_by_field).keys())[:10]
    top_conflict_fields = list(_sorted_counter(conflict_fields).keys())[:10]

    return {
        "document_count": _int(document_count),
        "gap_counts_by_field": _sorted_counter(gap_counts_by_field),
        "gap_counts_by_reason": _sorted_counter(gap_counts_by_reason),
        "blocker_counts_by_readiness_level": _sorted_counter(
            blocker_counts_by_readiness_level
        ),
        "aliases_by_field": _aliases_by(normalized_records, "field_name"),
        "aliases_by_reason": _aliases_by(normalized_records, "gap_reason"),
        "top_core_field_gaps": top_core_field_gaps,
        "top_conflict_fields": top_conflict_fields,
        "recommended_next_target": _top_fix_bucket(normalized_records),
        "analysis_version": CORE_FIELD_GAP_ANALYSIS_VERSION,
    }
