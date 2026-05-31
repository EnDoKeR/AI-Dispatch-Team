"""Safe load identifier coverage audit contracts.

The audit records load identifier pipeline progress as aliases, counts,
statuses, and label categories only. It must not carry private identifier
values or raw document text.
"""

from collections import Counter, defaultdict


LOAD_ID_AUDIT_STAGE_SOURCE_LINE = "source_line"
LOAD_ID_AUDIT_STAGE_LABEL_DETECTED = "label_detected"
LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED = "label_classified"
LOAD_ID_AUDIT_STAGE_TYPED_CANDIDATE_GENERATED = "typed_candidate_generated"
LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED = "primary_candidate_classified"
LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED = (
    "non_primary_reference_rejected"
)
LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED = "core_load_number_mapped"
LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED = "review_row_emitted"

LOAD_IDENTIFIER_COVERAGE_STAGES = {
    LOAD_ID_AUDIT_STAGE_SOURCE_LINE,
    LOAD_ID_AUDIT_STAGE_LABEL_DETECTED,
    LOAD_ID_AUDIT_STAGE_LABEL_CLASSIFIED,
    LOAD_ID_AUDIT_STAGE_TYPED_CANDIDATE_GENERATED,
    LOAD_ID_AUDIT_STAGE_PRIMARY_CANDIDATE_CLASSIFIED,
    LOAD_ID_AUDIT_STAGE_NON_PRIMARY_REFERENCE_REJECTED,
    LOAD_ID_AUDIT_STAGE_CORE_LOAD_NUMBER_MAPPED,
    LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED,
}

LOAD_ID_AUDIT_STATUS_PRESENT = "present"
LOAD_ID_AUDIT_STATUS_MISSING = "missing"
LOAD_ID_AUDIT_STATUS_REJECTED = "rejected"
LOAD_ID_AUDIT_STATUS_CONFLICT = "conflict"
LOAD_ID_AUDIT_STATUS_LOW_CONFIDENCE = "low_confidence"
LOAD_ID_AUDIT_STATUS_NON_APPLICABLE = "non_applicable"
LOAD_ID_AUDIT_STATUS_OCR_NEEDED = "ocr_needed"
LOAD_ID_AUDIT_STATUS_UNKNOWN = "unknown"

LOAD_IDENTIFIER_COVERAGE_STATUSES = {
    LOAD_ID_AUDIT_STATUS_PRESENT,
    LOAD_ID_AUDIT_STATUS_MISSING,
    LOAD_ID_AUDIT_STATUS_REJECTED,
    LOAD_ID_AUDIT_STATUS_CONFLICT,
    LOAD_ID_AUDIT_STATUS_LOW_CONFIDENCE,
    LOAD_ID_AUDIT_STATUS_NON_APPLICABLE,
    LOAD_ID_AUDIT_STATUS_OCR_NEEDED,
    LOAD_ID_AUDIT_STATUS_UNKNOWN,
}

LOAD_ID_AUDIT_REASON_IDENTIFIER_ABSENT = "identifier_absent_in_document"
LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED = "identifier_label_not_detected"
LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED = (
    "identifier_label_detected_but_unclassified"
)
LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED = "primary_candidate_not_generated"
LOAD_ID_AUDIT_REASON_PRIMARY_REJECTED_AS_NON_PRIMARY = (
    "primary_candidate_rejected_as_non_primary"
)
LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES = (
    "only_non_primary_references_found"
)
LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED = (
    "primary_candidate_generated_but_not_core_mapped"
)
LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT = (
    "multiple_primary_identifiers_conflict"
)
LOAD_ID_AUDIT_REASON_CONTEXT_MISSING = "context_missing_header_or_load_identity"
LOAD_ID_AUDIT_REASON_SCOPE_FILTERED = "scope_filtered"
LOAD_ID_AUDIT_REASON_OCR_NEEDED = "ocr_needed"
LOAD_ID_AUDIT_REASON_UNKNOWN = "unknown"

LOAD_IDENTIFIER_COVERAGE_REASONS = {
    LOAD_ID_AUDIT_REASON_IDENTIFIER_ABSENT,
    LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED,
    LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED,
    LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED,
    LOAD_ID_AUDIT_REASON_PRIMARY_REJECTED_AS_NON_PRIMARY,
    LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES,
    LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED,
    LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT,
    LOAD_ID_AUDIT_REASON_CONTEXT_MISSING,
    LOAD_ID_AUDIT_REASON_SCOPE_FILTERED,
    LOAD_ID_AUDIT_REASON_OCR_NEEDED,
    LOAD_ID_AUDIT_REASON_UNKNOWN,
}

LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER = "load_number"
LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER = "order_number"
LOAD_ID_LABEL_CATEGORY_TENDER_ID = "tender_id"
LOAD_ID_LABEL_CATEGORY_PRO_NUMBER = "pro_number"
LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER = "freight_bill_number"
LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER = "shipment_number"
LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER = "trip_number"
LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER = "dispatch_number"
LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE = "generic_reference"
LOAD_ID_LABEL_CATEGORY_PO_NUMBER = "po_number"
LOAD_ID_LABEL_CATEGORY_BOL_NUMBER = "bol_number"
LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER = "pickup_number"
LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER = "delivery_number"
LOAD_ID_LABEL_CATEGORY_APPOINTMENT_NUMBER = "appointment_number"
LOAD_ID_LABEL_CATEGORY_CUSTOMER_REFERENCE = "customer_reference"
LOAD_ID_LABEL_CATEGORY_CARRIER_REFERENCE = "carrier_reference"
LOAD_ID_LABEL_CATEGORY_UNKNOWN = "unknown"

LOAD_IDENTIFIER_LABEL_CATEGORIES = {
    LOAD_ID_LABEL_CATEGORY_LOAD_NUMBER,
    LOAD_ID_LABEL_CATEGORY_ORDER_NUMBER,
    LOAD_ID_LABEL_CATEGORY_TENDER_ID,
    LOAD_ID_LABEL_CATEGORY_PRO_NUMBER,
    LOAD_ID_LABEL_CATEGORY_FREIGHT_BILL_NUMBER,
    LOAD_ID_LABEL_CATEGORY_SHIPMENT_NUMBER,
    LOAD_ID_LABEL_CATEGORY_TRIP_NUMBER,
    LOAD_ID_LABEL_CATEGORY_DISPATCH_NUMBER,
    LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE,
    LOAD_ID_LABEL_CATEGORY_PO_NUMBER,
    LOAD_ID_LABEL_CATEGORY_BOL_NUMBER,
    LOAD_ID_LABEL_CATEGORY_PICKUP_NUMBER,
    LOAD_ID_LABEL_CATEGORY_DELIVERY_NUMBER,
    LOAD_ID_LABEL_CATEGORY_APPOINTMENT_NUMBER,
    LOAD_ID_LABEL_CATEGORY_CUSTOMER_REFERENCE,
    LOAD_ID_LABEL_CATEGORY_CARRIER_REFERENCE,
    LOAD_ID_LABEL_CATEGORY_UNKNOWN,
}

LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION = "load_identifier_coverage_audit_v1"


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_load_identifier_stage(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_COVERAGE_STAGES
        else LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED
    )


def normalize_load_identifier_status(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_COVERAGE_STATUSES
        else LOAD_ID_AUDIT_STATUS_UNKNOWN
    )


def normalize_load_identifier_reason(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_COVERAGE_REASONS
        else LOAD_ID_AUDIT_REASON_UNKNOWN
    )


def normalize_load_identifier_label_category(value):
    token = _token(value)
    return (
        token
        if token in LOAD_IDENTIFIER_LABEL_CATEGORIES
        else LOAD_ID_LABEL_CATEGORY_UNKNOWN
    )


def recommended_fix_bucket_for_load_identifier(reason, label_category=""):
    normalized_reason = normalize_load_identifier_reason(reason)
    category = normalize_load_identifier_label_category(label_category)
    if normalized_reason == LOAD_ID_AUDIT_REASON_OCR_NEEDED:
        return "ocr_queue"
    if normalized_reason == LOAD_ID_AUDIT_REASON_SCOPE_FILTERED:
        return "scope_filter_review"
    if normalized_reason in {
        LOAD_ID_AUDIT_REASON_LABEL_NOT_DETECTED,
        LOAD_ID_AUDIT_REASON_CONTEXT_MISSING,
    }:
        return "load_identifier_label_section_coverage"
    if normalized_reason == LOAD_ID_AUDIT_REASON_LABEL_UNCLASSIFIED:
        return "load_identifier_label_classification"
    if normalized_reason in {
        LOAD_ID_AUDIT_REASON_PRIMARY_NOT_GENERATED,
        LOAD_ID_AUDIT_REASON_PRIMARY_REJECTED_AS_NON_PRIMARY,
    }:
        return "primary_candidate_classification"
    if normalized_reason == LOAD_ID_AUDIT_REASON_PRIMARY_NOT_CORE_MAPPED:
        return "primary_to_core_mapping"
    if normalized_reason == LOAD_ID_AUDIT_REASON_MULTIPLE_PRIMARY_CONFLICT:
        return "local_human_review"
    if normalized_reason == LOAD_ID_AUDIT_REASON_ONLY_NON_PRIMARY_REFERENCES:
        return "header_context_or_human_review"
    if category == LOAD_ID_LABEL_CATEGORY_GENERIC_REFERENCE:
        return "generic_header_reference_review_candidate"
    return "local_human_review"


def build_load_identifier_coverage_record(
    measurement_alias="",
    stage=LOAD_ID_AUDIT_STAGE_REVIEW_ROW_EMITTED,
    status=LOAD_ID_AUDIT_STATUS_UNKNOWN,
    reason=LOAD_ID_AUDIT_REASON_UNKNOWN,
    identifier_label_category=LOAD_ID_LABEL_CATEGORY_UNKNOWN,
    candidate_count=0,
    primary_candidate_count=0,
    typed_reference_count=0,
    rejected_non_primary_count=0,
    core_mapping_count=0,
    warning_codes=None,
    recommended_fix_bucket="",
):
    normalized_reason = normalize_load_identifier_reason(reason)
    normalized_category = normalize_load_identifier_label_category(
        identifier_label_category
    )
    return {
        "measurement_alias": _text(measurement_alias),
        "stage": normalize_load_identifier_stage(stage),
        "status": normalize_load_identifier_status(status),
        "reason": normalized_reason,
        "identifier_label_category": normalized_category,
        "candidate_count": _int(candidate_count),
        "primary_candidate_count": _int(primary_candidate_count),
        "typed_reference_count": _int(typed_reference_count),
        "rejected_non_primary_count": _int(rejected_non_primary_count),
        "core_mapping_count": _int(core_mapping_count),
        "warning_codes": [str(code or "").strip() for code in warning_codes or [] if str(code or "").strip()],
        "recommended_fix_bucket": recommended_fix_bucket
        or recommended_fix_bucket_for_load_identifier(
            normalized_reason,
            normalized_category,
        ),
    }


def build_load_identifier_coverage_aggregate(records, document_count=0):
    normalized_records = [
        build_load_identifier_coverage_record(**record) for record in records
    ]
    reason_counts = Counter(record["reason"] for record in normalized_records)
    stage_counts = Counter(record["stage"] for record in normalized_records)
    label_counts = Counter(
        record["identifier_label_category"] for record in normalized_records
    )
    aliases_by_reason = defaultdict(list)
    aliases_by_label_category = defaultdict(list)
    fix_counts = Counter()
    for record in normalized_records:
        alias = record["measurement_alias"]
        if alias and alias not in aliases_by_reason[record["reason"]]:
            aliases_by_reason[record["reason"]].append(alias)
        category = record["identifier_label_category"]
        if alias and alias not in aliases_by_label_category[category]:
            aliases_by_label_category[category].append(alias)
        fix_counts[record["recommended_fix_bucket"]] += 1

    recommended_next_fix = (
        fix_counts.most_common(1)[0][0] if fix_counts else "local_human_review"
    )
    return {
        "document_count": _int(document_count),
        "records_by_reason": dict(sorted(reason_counts.items())),
        "records_by_stage": dict(sorted(stage_counts.items())),
        "records_by_label_category": dict(sorted(label_counts.items())),
        "primary_candidate_count": sum(
            record["primary_candidate_count"] for record in normalized_records
        ),
        "typed_reference_count": sum(
            record["typed_reference_count"] for record in normalized_records
        ),
        "rejected_non_primary_count": sum(
            record["rejected_non_primary_count"] for record in normalized_records
        ),
        "core_mapping_count": sum(
            record["core_mapping_count"] for record in normalized_records
        ),
        "aliases_by_reason": {
            key: sorted(values) for key, values in sorted(aliases_by_reason.items())
        },
        "aliases_by_label_category": {
            key: sorted(values)
            for key, values in sorted(aliases_by_label_category.items())
        },
        "recommended_next_fix": recommended_next_fix,
        "analysis_version": LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION,
    }


def build_load_identifier_coverage_result(records, document_count=0):
    normalized_records = [
        build_load_identifier_coverage_record(**record) for record in records
    ]
    return {
        "analysis_version": LOAD_IDENTIFIER_COVERAGE_ANALYSIS_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "records": normalized_records,
        "aggregate": build_load_identifier_coverage_aggregate(
            normalized_records,
            document_count=document_count,
        ),
    }
